import { createHash } from 'node:crypto';
import { db } from './state.js';
import type { Seat } from './config.js';
import type {
  DeliveryState,
  DocRoundSignalRecord,
  DocRoundSignalRequest
} from './types.js';

function deliveryId(args: {
  roundId: string;
  signalType: string;
  seat: Seat;
  documentId: string;
  revision?: string | null;
}): string {
  return createHash('sha256')
    .update(`${args.roundId}:${args.signalType}:${args.seat}:${args.documentId}:${args.revision || 'none'}`)
    .digest('hex');
}

export async function publishDocRoundSignal(req: DocRoundSignalRequest): Promise<DocRoundSignalRecord[]> {
  const now = new Date().toISOString();
  const uniqueSeats = [...new Set(req.to)];
  const records: DocRoundSignalRecord[] = uniqueSeats.map((seat) => ({
    protocol: 'DEUS-DOC-ROUND/1.0',
    deliveryId: deliveryId({
      roundId: req.round_id,
      signalType: req.signal_type,
      seat,
      documentId: req.document_id!,
      revision: req.doc_revision_id
    }),
    seat,
    roundId: req.round_id,
    tenantId: req.tenant_id,
    taskId: req.task_id,
    signalType: req.signal_type,
    from: req.from,
    documentId: req.document_id!,
    marker: req.marker || `[ROUND ${req.round_id}`,
    docRevisionId: req.doc_revision_id || null,
    state: req.state,
    status: 'PENDING',
    createdAt: now,
    updatedAt: now,
    metadata: req.metadata || {}
  }));

  await db.runTransaction(async (tx) => {
    const refs = records.map((record) =>
      db.collection('deus_doc_round_seats').doc(record.seat).collection('deliveries').doc(record.deliveryId)
    );
    const existing = refs.length ? await tx.getAll(...refs) : [];

    records.forEach((record, index) => {
      if (!existing[index]?.exists) tx.create(refs[index], record);
    });

    const roundRef = db.collection('deus_doc_rounds').doc(req.round_id);
    tx.set(roundRef, {
      protocol: 'DEUS-DOC-ROUND/1.0',
      roundId: req.round_id,
      tenantId: req.tenant_id,
      taskId: req.task_id,
      documentId: req.document_id,
      marker: req.marker || `[ROUND ${req.round_id}`,
      lastSignalType: req.signal_type,
      lastState: req.state,
      lastFrom: req.from,
      lastRevisionId: req.doc_revision_id || null,
      lastSignalAt: now,
      metadata: req.metadata || {}
    }, { merge: true });
  });

  return records;
}

export async function getPendingDocRoundSignals(seat: Seat, limit = 25): Promise<DocRoundSignalRecord[]> {
  const snap = await db.collection('deus_doc_round_seats').doc(seat).collection('deliveries')
    .where('status', '==', 'PENDING')
    .limit(Math.min(Math.max(limit, 1), 100))
    .get();

  return snap.docs.map((doc) => doc.data() as DocRoundSignalRecord)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export async function updateDocRoundSignalState(args: {
  seat: Seat;
  deliveryId: string;
  status: DeliveryState;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const ref = db.collection('deus_doc_round_seats').doc(args.seat).collection('deliveries').doc(args.deliveryId);
  await ref.set({
    status: args.status,
    updatedAt: new Date().toISOString(),
    ...(args.metadata ? { ackMetadata: args.metadata } : {})
  }, { merge: true });
}

export async function readDocRoundState(roundId: string): Promise<Record<string, unknown> | null> {
  const snap = await db.collection('deus_doc_rounds').doc(roundId).get();
  return snap.exists ? (snap.data() as Record<string, unknown>) : null;
}
