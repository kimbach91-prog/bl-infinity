import { Firestore, Timestamp } from '@google-cloud/firestore';
import { config, type Seat } from './config.js';
import type { DeliveryRecord, DeliveryState } from './types.js';

export interface ControlState {
  driveCursor?: string | null;
  mode?: 'HOT' | 'WARM' | 'IDLE';
  nextPollAt?: string | null;
  lastActivityAt?: string | null;
  lastHarvestAt?: string | null;
  leaseOwner?: string | null;
  leaseUntil?: FirebaseFirestore.Timestamp | null;
  fencingEpoch?: number;
}

export const db = new Firestore(config.projectId ? { projectId: config.projectId } : undefined);
const controlRef = db.collection('deus_signal_fabric').doc('control');

export async function readControl(): Promise<ControlState> {
  const snap = await controlRef.get();
  return (snap.data() || {}) as ControlState;
}

export async function acquireLease(owner: string): Promise<number | null> {
  return db.runTransaction(async (tx) => {
    const snap = await tx.get(controlRef);
    const state = (snap.data() || {}) as ControlState;
    const now = Timestamp.now();
    const leaseUntil = state.leaseUntil;
    if (leaseUntil && leaseUntil.toMillis() > now.toMillis() && state.leaseOwner && state.leaseOwner !== owner) {
      return null;
    }
    const epoch = (state.fencingEpoch || 0) + 1;
    tx.set(controlRef, {
      leaseOwner: owner,
      leaseUntil: Timestamp.fromMillis(now.toMillis() + config.leaseSeconds * 1000),
      fencingEpoch: epoch
    }, { merge: true });
    return epoch;
  });
}

export async function finalizeHarvest(args: {
  owner: string;
  fencingEpoch: number;
  nextCursor: string;
  deliveries: DeliveryRecord[];
  activity: boolean;
  mode: 'HOT' | 'WARM' | 'IDLE';
  nextPollAt: string;
}): Promise<void> {
  await db.runTransaction(async (tx) => {
    const snap = await tx.get(controlRef);
    const state = (snap.data() || {}) as ControlState;
    if (state.leaseOwner !== args.owner || state.fencingEpoch !== args.fencingEpoch) {
      throw new Error(`FENCING_REJECTED expected owner=${args.owner} epoch=${args.fencingEpoch}`);
    }

    for (const delivery of args.deliveries) {
      const ref = db.collection('deus_signal_seats').doc(delivery.seat).collection('deliveries').doc(delivery.deliveryId);
      tx.set(ref, delivery, { merge: true });
    }

    const now = new Date().toISOString();
    tx.set(controlRef, {
      driveCursor: args.nextCursor,
      mode: args.mode,
      nextPollAt: args.nextPollAt,
      lastHarvestAt: now,
      ...(args.activity ? { lastActivityAt: now } : {}),
      leaseOwner: null,
      leaseUntil: null
    }, { merge: true });
  });
}

export async function bootstrapCursor(cursor: string): Promise<void> {
  await controlRef.set({
    driveCursor: cursor,
    mode: 'HOT',
    nextPollAt: new Date().toISOString(),
    lastHarvestAt: new Date().toISOString()
  }, { merge: true });
}

export async function getPendingDeliveries(seat: Seat, limit = 25): Promise<DeliveryRecord[]> {
  const snap = await db.collection('deus_signal_seats').doc(seat).collection('deliveries')
    .where('status', '==', 'PENDING')
    .limit(Math.min(Math.max(limit, 1), 100))
    .get();
  return snap.docs.map((doc) => doc.data() as DeliveryRecord)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export async function updateDeliveryState(args: {
  seat: Seat;
  deliveryId: string;
  status: DeliveryState;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const ref = db.collection('deus_signal_seats').doc(args.seat).collection('deliveries').doc(args.deliveryId);
  await ref.set({
    status: args.status,
    updatedAt: new Date().toISOString(),
    ...(args.metadata ? { ackMetadata: args.metadata } : {})
  }, { merge: true });
}
