import fs from 'node:fs/promises';
import path from 'node:path';
import { stableFingerprint } from '../lib/life-core.mjs';

const journalPath = process.argv[2] || process.env.DEUS_LIFE_JOURNAL_PATH || './storage/deus-life-events.ndjson';
const statePath = process.argv[3] || process.env.DEUS_LIFE_STATE_PATH || './storage/deus-life-state.json';

const rows = await readRows(journalPath);
const state = await readJson(statePath);
let previousHash = null;
let hashedRows = 0;
let legacyRows = 0;
let firstHashedIndex = null;

for (let index = 0; index < rows.length; index += 1) {
  const row = rows[index];
  if (!row.journalHash) {
    if (hashedRows > 0) fail(`legacy/unhashed row appears after hash chain began at line ${index + 1}`);
    legacyRows += 1;
    continue;
  }

  if (firstHashedIndex === null) firstHashedIndex = index;
  const { journalHash, ...base } = row;
  const recomputed = stableFingerprint(base);
  if (recomputed !== journalHash) fail(`journal hash mismatch at line ${index + 1}`);

  if (hashedRows === 0) {
    if (row.prevHash !== null && row.prevHash !== undefined) {
      fail(`first hashed row must begin a new anchored chain with prevHash=null at line ${index + 1}`);
    }
  } else if (row.prevHash !== previousHash) {
    fail(`journal chain discontinuity at line ${index + 1}`);
  }

  previousHash = journalHash;
  hashedRows += 1;
}

if (state?.journalHead && state.journalHead !== previousHash) {
  fail('persisted state journalHead does not equal verified journal tail');
}

console.log(JSON.stringify({
  ok: true,
  journalPath: path.resolve(journalPath),
  statePath: path.resolve(statePath),
  totalRows: rows.length,
  legacyRows,
  hashedRows,
  firstHashedLine: firstHashedIndex === null ? null : firstHashedIndex + 1,
  head: previousHash,
  stateHeadMatches: !state?.journalHead || state.journalHead === previousHash,
}));

async function readRows(filePath) {
  const raw = await fs.readFile(filePath, 'utf8');
  return raw.split(/\r?\n/u).filter(Boolean).map((line, index) => {
    try { return JSON.parse(line); }
    catch { fail(`invalid JSON at journal line ${index + 1}`); }
  });
}

async function readJson(filePath) {
  try { return JSON.parse(await fs.readFile(filePath, 'utf8')); }
  catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function fail(message) {
  console.error(JSON.stringify({ ok: false, error: message }));
  process.exit(1);
}
