import fs from 'node:fs';
import readline from 'node:readline';
import { stableFingerprint } from './life-core.mjs';

export async function verifyLifeJournalChain({ journalPath, expectedHead = null, expectedLineageId = null } = {}) {
  if (!journalPath) throw new Error('journalPath is required');
  let input;
  try {
    input = fs.createReadStream(journalPath, { encoding: 'utf8' });
    await onceOpen(input);
  } catch (error) {
    if (error.code === 'ENOENT' && !expectedHead) return emptyResult();
    throw divergence(`life journal unavailable: ${error.message}`);
  }

  const rl = readline.createInterface({ input, crlfDelay: Infinity });
  let lineNumber = 0;
  let hashedRows = 0;
  let legacyRows = 0;
  let previousHash = null;
  let previousGeneration = null;
  let lineageId = null;
  let hashedStarted = false;

  try {
    for await (const raw of rl) {
      lineNumber += 1;
      const line = raw.trim();
      if (!line) continue;
      let row;
      try { row = JSON.parse(line); }
      catch { throw divergence(`invalid JSON at journal line ${lineNumber}`); }

      if (!row.journalHash) {
        if (hashedStarted) throw divergence(`unhashed row appears after hash chain began at line ${lineNumber}`);
        legacyRows += 1;
        continue;
      }
      hashedStarted = true;

      const { journalHash, ...base } = row;
      if (stableFingerprint(base) !== journalHash) {
        throw divergence(`journal hash mismatch at line ${lineNumber}`);
      }

      if ((row.prevHash ?? null) !== previousHash) {
        throw divergence(`journal prevHash mismatch at line ${lineNumber}`);
      }

      if (previousGeneration !== null && Number.isSafeInteger(row.generation) && row.generation !== previousGeneration + 1) {
        throw divergence(`journal generation discontinuity at line ${lineNumber}`);
      }
      if (Number.isSafeInteger(row.generation)) previousGeneration = row.generation;

      if (row.lineageId) {
        if (!lineageId) lineageId = row.lineageId;
        else if (row.lineageId !== lineageId) throw divergence(`journal lineageId changed at line ${lineNumber}`);
      }

      previousHash = journalHash;
      hashedRows += 1;
    }
  } finally {
    rl.close();
    input.destroy();
  }

  if ((expectedHead ?? null) !== previousHash) {
    throw divergence('persisted state journalHead does not equal verified full journal head');
  }
  if (expectedLineageId && lineageId && expectedLineageId !== lineageId) {
    throw divergence('persisted state lineageId does not equal verified journal lineageId');
  }

  return {
    ok: true,
    totalRows: legacyRows + hashedRows,
    legacyRows,
    hashedRows,
    head: previousHash,
    lineageId,
    lastGeneration: previousGeneration,
  };
}

function onceOpen(stream) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      stream.off('open', onOpen);
      stream.off('error', onError);
    };
    const onOpen = () => { cleanup(); resolve(); };
    const onError = (error) => { cleanup(); reject(error); };
    stream.once('open', onOpen);
    stream.once('error', onError);
  });
}

function emptyResult() {
  return { ok: true, totalRows: 0, legacyRows: 0, hashedRows: 0, head: null, lineageId: null, lastGeneration: null };
}

function divergence(message) {
  const error = new Error(message);
  error.code = 'LIFE_JOURNAL_DIVERGED';
  return error;
}
