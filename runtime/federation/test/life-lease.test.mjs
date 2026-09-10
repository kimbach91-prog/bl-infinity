import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { LifeDaemon } from '../worker/life-daemon.mjs';
import { acquireLease, createLeaseOwnerId, releaseLease } from '../lib/life-lease.mjs';

test('single-writer lease blocks a second live owner', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-lease-'));
  const leasePath = path.join(dir, 'life.lock');
  const owner1 = createLeaseOwnerId('one');
  const owner2 = createLeaseOwnerId('two');
  await acquireLease({ leasePath, ownerId: owner1, ttlMs: 90_000 });
  await assert.rejects(
    () => acquireLease({ leasePath, ownerId: owner2, ttlMs: 90_000 }),
    (error) => error.code === 'LIFE_LEASE_HELD',
  );
  await releaseLease({ leasePath, ownerId: owner1 });
});

test('daemon resumes state while owning a live lease', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-'));
  const opts = {
    statePath: path.join(dir, 'state.json'),
    journalPath: path.join(dir, 'journal.ndjson'),
    leasePath: path.join(dir, 'life.lock'),
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger: { info() {}, warn() {}, error() {} },
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  };
  const daemon = new LifeDaemon(opts);
  await daemon.start();
  assert.equal(daemon.timer.hasRef(), true);
  await daemon.emit({ type: 'external-novelty', source: 'test', reward: 0.25 });
  await daemon.stop({ reason: 'test' });
  const generation = daemon.snapshot().generation;

  const daemon2 = new LifeDaemon(opts);
  await daemon2.start();
  assert.ok(daemon2.snapshot().generation > generation);
  await daemon2.stop({ reason: 'test' });
});

test('backup recovers when primary state is corrupt', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-recover-'));
  const opts = {
    statePath: path.join(dir, 'state.json'),
    journalPath: path.join(dir, 'journal.ndjson'),
    leasePath: path.join(dir, 'life.lock'),
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger: { info() {}, warn() {}, error() {} },
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  };
  const daemon = new LifeDaemon(opts);
  await daemon.start();
  await daemon.emit({ type: 'external-novelty', source: 'test' });
  await daemon.emit({ type: 'memory-readback-ok', source: 'test' });
  await daemon.stop({ reason: 'test' });
  await fs.writeFile(opts.statePath, '{broken', 'utf8');

  const recovered = new LifeDaemon(opts);
  await recovered.start();
  assert.ok(recovered.snapshot().generation >= 2);
  await recovered.stop({ reason: 'test' });
});
