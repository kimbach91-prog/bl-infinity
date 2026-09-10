import fs from 'node:fs/promises';
import { stableFingerprint } from './life-core.mjs';

export async function recoverUncommittedPartialJournalTail({ journalPath, expectedCommittedHead }) {
  const buffer = await fs.readFile(journalPath);
  if (buffer.length === 0) return { recovered: false, tail: null, truncatedBytes: 0 };

  if (buffer.at(-1) === 0x0a) {
    const error = new Error('journal ends on a newline; malformed final row is not a partial-tail crash candidate');
    error.code = 'LIFE_JOURNAL_DIVERGED';
    throw error;
  }

  const lastNewline = buffer.lastIndexOf(0x0a);
  const keepBytes = lastNewline >= 0 ? lastNewline + 1 : 0;
  const completePrefix = buffer.subarray(0, keepBytes);
  const tail = parseLastCompleteRow(completePrefix);
  const observedHead = tail?.journalHash ?? null;

  if (observedHead !== (expectedCommittedHead ?? null)) {
    const error = new Error('partial journal tail does not follow the persisted committed head');
    error.code = 'LIFE_JOURNAL_DIVERGED';
    error.observedHead = observedHead;
    error.expectedCommittedHead = expectedCommittedHead ?? null;
    throw error;
  }

  if (tail) verifyJournalEnvelope(tail);

  const truncatedBytes = buffer.length - keepBytes;
  if (truncatedBytes <= 0) return { recovered: false, tail, truncatedBytes: 0 };
  await fs.truncate(journalPath, keepBytes);
  return { recovered: true, tail, truncatedBytes };
}

function parseLastCompleteRow(buffer) {
  if (!buffer.length) return null;
  let end = buffer.length;
  while (end > 0 && (buffer[end - 1] === 0x0a || buffer[end - 1] === 0x0d)) end -= 1;
  if (end <= 0) return null;
  const previousNewline = buffer.lastIndexOf(0x0a, end - 1);
  const line = buffer.subarray(previousNewline + 1, end).toString('utf8').trim();
  if (!line) return null;
  try { return JSON.parse(line); }
  catch (cause) {
    const error = new Error('last complete journal row is invalid JSON');
    error.code = 'LIFE_JOURNAL_DIVERGED';
    error.cause = cause;
    throw error;
  }
}

function verifyJournalEnvelope(row) {
  if (!row?.journalHash) {
    const error = new Error('last complete journal row has no hash');
    error.code = 'LIFE_JOURNAL_DIVERGED';
    throw error;
  }
  const { journalHash, ...base } = row;
  if (stableFingerprint(base) !== journalHash) {
    const error = new Error('last complete journal row hash verification failed');
    error.code = 'LIFE_JOURNAL_DIVERGED';
    throw error;
  }
}
