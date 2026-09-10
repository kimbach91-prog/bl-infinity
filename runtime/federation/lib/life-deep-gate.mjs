import fs from 'node:fs/promises';
import { verifyLifeJournalChain } from './life-journal-verify.mjs';

export async function verifyPersistentLifeStateIfPresent({
  statePath = process.env.DEUS_LIFE_STATE_PATH || './storage/deus-life-state.json',
  journalPath = process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson',
  pendingPath = process.env.DEUS_LIFE_PENDING_PATH || `${statePath}.pending`,
} = {}) {
  if (await exists(pendingPath)) {
    return { ok: true, skipped: 'pending-recovery-required' };
  }

  const state = await readStateOrNull(statePath);
  if (!state) return { ok: true, skipped: 'no-persisted-state' };

  const verification = await verifyLifeJournalChain({
    journalPath,
    expectedHead: state.journalHead ?? null,
    expectedLineageId: state.lineageId ?? null,
  });
  return { ok: true, skipped: null, stateGeneration: state.generation, ...verification };
}

export async function verifyRunningLifeSnapshot({
  snapshot,
  journalPath = process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson',
} = {}) {
  if (!snapshot) throw new Error('running life snapshot is required');
  return verifyLifeJournalChain({
    journalPath,
    expectedHead: snapshot.journalHead ?? null,
    expectedLineageId: snapshot.lineageId ?? null,
  });
}

async function exists(filePath) {
  try { await fs.access(filePath); return true; }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}

async function readStateOrNull(filePath) {
  try {
    const state = JSON.parse(await fs.readFile(filePath, 'utf8'));
    if (!state || typeof state !== 'object' || !state.body || !Number.isSafeInteger(state.generation)) {
      const error = new Error('persisted life state is structurally invalid');
      error.code = 'LIFE_JOURNAL_DIVERGED';
      throw error;
    }
    return state;
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    if (error instanceof SyntaxError) {
      error.code = 'LIFE_JOURNAL_DIVERGED';
      throw error;
    }
    throw error;
  }
}
