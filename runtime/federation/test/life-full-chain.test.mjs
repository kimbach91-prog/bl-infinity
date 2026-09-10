import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { stableFingerprint } from '../lib/life-core.mjs';
import { verifyLifeJournalChain } from '../lib/life-journal-verify.mjs';

function makeRow({ generation, prevHash, lineageId = 'lineage-1', eventType = 'test' }) {
  const base = {
    at: `2026-09-10T01:${String(generation).padStart(2, '0')}:00.000Z`,
    generation,
    eventType,
    eventSource: 'full-chain-test',
    novelty: true,
    action: 'HOLD_STEADY',
    actionScore: 0,
    viability: 1,
    affect: {},
    mutation: false,
    reward: 0,
    body: { A: 1, H: 1 },
    inputAt: `2026-09-10T01:${String(generation).padStart(2, '0')}:00.000Z`,
    lineageId,
    incarnationId: 'incarnation-1',
    prevHash,
  };
  return { ...base, journalHash: stableFingerprint(base) };
}

async function writeChain(dir) {
  const journalPath = path.join(dir, 'journal.ndjson');
  const rows = [];
  let prevHash = null;
  for (let generation = 1; generation <= 4; generation += 1) {
    const row = makeRow({ generation, prevHash });
    rows.push(row);
    prevHash = row.journalHash;
  }
  await fs.writeFile(journalPath, `${rows.map((row) => JSON.stringify(row)).join('\n')}\n`, 'utf8');
  return { journalPath, rows, head: prevHash };
}

test('streaming full-chain verifier accepts a coherent causal journal', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-full-chain-ok-'));
  const { journalPath, head } = await writeChain(dir);
  const result = await verifyLifeJournalChain({ journalPath, expectedHead: head, expectedLineageId: 'lineage-1' });
  assert.equal(result.ok, true);
  assert.equal(result.hashedRows, 4);
  assert.equal(result.head, head);
  assert.equal(result.lastGeneration, 4);
});

test('streaming full-chain verifier detects an interior historical mutation even if tail hash text is untouched', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-full-chain-tamper-'));
  const { journalPath, rows, head } = await writeChain(dir);
  rows[1].action = 'INSPECT_TEST';
  await fs.writeFile(journalPath, `${rows.map((row) => JSON.stringify(row)).join('\n')}\n`, 'utf8');
  await assert.rejects(
    () => verifyLifeJournalChain({ journalPath, expectedHead: head, expectedLineageId: 'lineage-1' }),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED' && /hash mismatch at line 2/.test(error.message),
  );
});

test('streaming full-chain verifier rejects a lineage id swap inside a validly rehashed chain', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-full-chain-lineage-'));
  const journalPath = path.join(dir, 'journal.ndjson');
  const row1 = makeRow({ generation: 1, prevHash: null, lineageId: 'lineage-1' });
  const row2 = makeRow({ generation: 2, prevHash: row1.journalHash, lineageId: 'lineage-2' });
  await fs.writeFile(journalPath, `${JSON.stringify(row1)}\n${JSON.stringify(row2)}\n`, 'utf8');
  await assert.rejects(
    () => verifyLifeJournalChain({ journalPath, expectedHead: row2.journalHash, expectedLineageId: 'lineage-1' }),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED' && /lineageId changed/.test(error.message),
  );
});
