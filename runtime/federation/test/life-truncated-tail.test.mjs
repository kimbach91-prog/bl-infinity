import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { LifeDaemon } from '../worker/life-daemon.mjs';

function options(dir, extra = {}) {
  const statePath = path.join(dir, 'state.json');
  return {
    statePath,
    journalPath: path.join(dir, 'journal.ndjson'),
    leasePath: path.join(dir, 'life.lock'),
    checkpointPath: path.join(dir, 'checkpoint.json'),
    pendingPath: `${statePath}.pending`,
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger: { info() {}, warn() {}, error() {} },
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
    ...extra,
  };
}

async function seed(dir) {
  const opts = options(dir);
  const daemon = new LifeDaemon(opts);
  await daemon.start();
  await daemon.stop({ reason: 'seed' });
  return opts;
}

async function readRows(filePath) {
  const raw = await fs.readFile(filePath, 'utf8');
  return raw.split(/\r?\n/u).filter(Boolean).map((line) => JSON.parse(line));
}

test('truncated uncommitted final journal write is trimmed and replayed from pending intent exactly once', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-tail-recover-'));
  const opts = await seed(dir);
  const committedBefore = JSON.parse(await fs.readFile(opts.statePath, 'utf8'));

  let injected = false;
  const crashing = new LifeDaemon(options(dir, {
    faultInjector: async (point) => {
      if (!injected && point === 'after-pending') {
        injected = true;
        throw new Error('INJECT_AFTER_PENDING');
      }
    },
  }));
  await assert.rejects(() => crashing.start(), /INJECT_AFTER_PENDING/);

  const pending = JSON.parse(await fs.readFile(opts.pendingPath, 'utf8'));
  assert.equal(pending.journal.prevHash, committedBefore.journalHead);
  const full = JSON.stringify(pending.journal);
  const partial = full.slice(0, Math.max(1, Math.floor(full.length / 2)));
  await fs.appendFile(opts.journalPath, partial, 'utf8');

  const recovered = new LifeDaemon(opts);
  await recovered.start();
  const rows = await readRows(opts.journalPath);
  assert.equal(rows.filter((row) => row.journalHash === pending.journal.journalHash).length, 1);
  assert.equal(rows.at(-2).journalHash, pending.journal.journalHash, 'recovered pending row should precede the new boot generation');
  assert.equal(recovered.snapshot().lineageId, committedBefore.lineageId);
  assert.ok(recovered.snapshot().generation > pending.state.generation);
  await assert.rejects(() => fs.access(opts.pendingPath), (error) => error?.code === 'ENOENT');
  await recovered.stop({ reason: 'test' });
});

test('newline-terminated malformed journal row is not auto-trimmed as a crash fragment', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-tail-tamper-'));
  const opts = await seed(dir);

  let injected = false;
  const crashing = new LifeDaemon(options(dir, {
    faultInjector: async (point) => {
      if (!injected && point === 'after-pending') {
        injected = true;
        throw new Error('INJECT_AFTER_PENDING');
      }
    },
  }));
  await assert.rejects(() => crashing.start(), /INJECT_AFTER_PENDING/);
  await fs.appendFile(opts.journalPath, '{"malformed":true\n', 'utf8');

  const recovered = new LifeDaemon(opts);
  await assert.rejects(
    () => recovered.start(),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED' && /not a partial-tail crash candidate/.test(error.message),
  );
});
