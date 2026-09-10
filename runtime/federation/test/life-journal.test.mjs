import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { LifeDaemon } from '../worker/life-daemon.mjs';

function paths(dir) {
  return {
    statePath: path.join(dir, 'state.json'),
    journalPath: path.join(dir, 'journal.ndjson'),
    leasePath: path.join(dir, 'life.lock'),
    checkpointPath: path.join(dir, 'checkpoint.json'),
    pendingPath: path.join(dir, 'state.json.pending'),
  };
}

function options(dir, extra = {}) {
  return {
    ...paths(dir),
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger: { info() {}, warn() {}, error() {} },
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
    ...extra,
  };
}

async function readJournal(filePath) {
  const raw = await fs.readFile(filePath, 'utf8');
  return raw.split(/\r?\n/u).filter(Boolean).map((line) => JSON.parse(line));
}

test('crash after pending intent recovers the exact generation once', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-pending-'));
  let injected = false;
  const broken = new LifeDaemon(options(dir, {
    faultInjector: async (point) => {
      if (!injected && point === 'after-pending') {
        injected = true;
        throw new Error('INJECTED_AFTER_PENDING');
      }
    },
  }));
  await assert.rejects(() => broken.start(), /INJECTED_AFTER_PENDING/);

  const p = paths(dir);
  const pending = JSON.parse(await fs.readFile(p.pendingPath, 'utf8'));
  assert.equal(pending.state.generation, 1);

  const recovered = new LifeDaemon(options(dir));
  await recovered.start();
  const rows = await readJournal(p.journalPath);
  const hashes = rows.map((row) => row.journalHash);
  assert.equal(new Set(hashes).size, hashes.length);
  assert.equal(rows[0].generation, 1);
  assert.equal(rows[1].generation, 2);
  assert.equal(recovered.snapshot().journalHead, rows.at(-1).journalHash);
  await recovered.stop({ reason: 'test' });
});

test('crash after journal append does not duplicate the pending journal row', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-journal-'));
  let injected = false;
  const broken = new LifeDaemon(options(dir, {
    faultInjector: async (point) => {
      if (!injected && point === 'after-journal') {
        injected = true;
        throw new Error('INJECTED_AFTER_JOURNAL');
      }
    },
  }));
  await assert.rejects(() => broken.start(), /INJECTED_AFTER_JOURNAL/);

  const p = paths(dir);
  const before = await readJournal(p.journalPath);
  assert.equal(before.length, 1);

  const recovered = new LifeDaemon(options(dir));
  await recovered.start();
  const after = await readJournal(p.journalPath);
  assert.equal(after.filter((row) => row.journalHash === before[0].journalHash).length, 1);
  assert.equal(new Set(after.map((row) => row.journalHash)).size, after.length);
  await recovered.stop({ reason: 'test' });
});

test('tampered journal tail is rejected instead of silently continuing lineage', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-tamper-'));
  const p = paths(dir);
  const daemon = new LifeDaemon(options(dir));
  await daemon.start();
  await daemon.stop({ reason: 'test' });

  const rows = await readJournal(p.journalPath);
  rows.at(-1).action = 'INSPECT_TEST';
  await fs.writeFile(p.journalPath, `${rows.map((row) => JSON.stringify(row)).join('\n')}\n`, 'utf8');

  const next = new LifeDaemon(options(dir));
  await assert.rejects(
    () => next.start(),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED',
  );
});
