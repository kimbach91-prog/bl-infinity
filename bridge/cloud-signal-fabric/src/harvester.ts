import { createHash, randomUUID } from 'node:crypto';
import { config } from './config.js';
import { getStartCursor, listManifestChanges, readManifest } from './drive.js';
import { acquireLease, bootstrapCursor, finalizeHarvest, readControl } from './state.js';
import type { DeliveryRecord } from './types.js';

const isoAfterMinutes = (minutes: number): string => new Date(Date.now() + minutes * 60_000).toISOString();

function deliveryId(messageId: string, seat: string, revision?: string | null): string {
  return createHash('sha256').update(`${messageId}:${seat}:${revision || 'none'}`).digest('hex');
}

function chooseMode(args: { activity: boolean; hasMore: boolean; lastActivityAt?: string | null }): 'HOT' | 'WARM' | 'IDLE' {
  if (args.activity || args.hasMore) return 'HOT';
  if (!args.lastActivityAt) return 'IDLE';
  const ageMinutes = (Date.now() - Date.parse(args.lastActivityAt)) / 60_000;
  if (ageMinutes <= config.hotWindowMinutes) return 'HOT';
  if (ageMinutes <= config.warmWindowMinutes) return 'WARM';
  return 'IDLE';
}

function cadenceMinutes(mode: 'HOT' | 'WARM' | 'IDLE'): number {
  if (mode === 'HOT') return config.hotMinutes;
  if (mode === 'WARM') return config.warmMinutes;
  return config.idleMinutes;
}

export async function harvest(options: { force?: boolean } = {}): Promise<Record<string, unknown>> {
  const before = await readControl();
  if (!before.driveCursor) {
    const cursor = await getStartCursor();
    await bootstrapCursor(cursor);
    return { ok: true, state: 'BOOTSTRAPPED', cursorInitialized: true, forced: Boolean(options.force), modelCalls: 0 };
  }

  if (!options.force && before.nextPollAt && Date.parse(before.nextPollAt) > Date.now()) {
    return { ok: true, state: 'NOT_DUE', mode: before.mode || 'IDLE', nextPollAt: before.nextPollAt, modelCalls: 0 };
  }

  const owner = `harvester_${randomUUID()}`;
  const epoch = await acquireLease(owner);
  if (epoch === null) return { ok: true, state: 'LEASE_BUSY', modelCalls: 0 };

  const page = await listManifestChanges(before.driveCursor);
  const deliveries: DeliveryRecord[] = [];
  const failures: Array<{ fileId: string; error: string }> = [];
  const now = new Date().toISOString();

  for (const change of page.changes) {
    try {
      const manifest = await readManifest(change.fileId);
      const uniqueSeats = [...new Set(manifest.to)];
      for (const seat of uniqueSeats) {
        deliveries.push({
          deliveryId: deliveryId(manifest.message_id, seat, manifest.artifact_revision),
          seat,
          manifest,
          sourceManifestFileId: change.fileId,
          sourceManifestVersion: change.version || null,
          status: 'PENDING',
          createdAt: now,
          updatedAt: now,
          fencingEpoch: epoch
        });
      }
    } catch (error) {
      failures.push({ fileId: change.fileId, error: error instanceof Error ? error.message : String(error) });
    }
  }

  const activity = deliveries.length > 0 || failures.length > 0;
  const mode = chooseMode({ activity, hasMore: page.hasMore, lastActivityAt: before.lastActivityAt });
  const nextPollAt = isoAfterMinutes(cadenceMinutes(mode));

  await finalizeHarvest({
    owner,
    fencingEpoch: epoch,
    nextCursor: page.nextCursor,
    deliveries,
    activity,
    mode,
    nextPollAt
  });

  if (failures.length) console.error(JSON.stringify({ event: 'MANIFEST_PARSE_FAILURES', failures }));
  return {
    ok: true,
    state: 'HARVESTED',
    forced: Boolean(options.force),
    fencingEpoch: epoch,
    manifestChanges: page.changes.length,
    deliveries: deliveries.length,
    failures: failures.length,
    hasMore: page.hasMore,
    mode,
    nextPollAt,
    modelCalls: 0
  };
}
