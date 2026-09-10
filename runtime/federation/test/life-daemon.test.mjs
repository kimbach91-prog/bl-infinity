import test from 'node:test';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';
import { LifeDaemon } from '../worker/life-daemon.mjs';

test('daemon keeps a referenced pulse handle, persists lineage, changes incarnation, and resumes generation', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-'));
  const statePath = path.join(dir, 'state.json');
  const journalPath = path.join(dir, 'journal.ndjson');
  const leasePath = path.join(dir, 'life.lock');
  const checkpointPath = path.join(dir, 'checkpoint.json');
  const logger = { info() {}, warn() {}, error() {} };
  const options = {
    statePath,
    journalPath,
    leasePath,
    checkpointPath,
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger,
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  };

  const daemon = new LifeDaemon(options);
  await daemon.start();
  assert.equal(typeof daemon.timer?.hasRef, 'function');
  assert.equal(daemon.timer.hasRef(), true);
  const firstBoot = daemon.snapshot();
  assert.equal(typeof firstBoot.lineageId, 'string');
  assert.equal(typeof firstBoot.incarnationId, 'string');
  assert.equal(firstBoot.bootCount, 1);

  await daemon.emit({ type: 'task-success', source: 'test', reward: 0.25 });
  const gen = daemon.snapshot().generation;
  assert.ok(gen >= 2);
  await daemon.stop({ reason: 'test' });

  const persisted = JSON.parse(await fs.readFile(statePath, 'utf8'));
  assert.equal(persisted.generation, daemon.snapshot().generation);
  assert.equal(persisted.lineageId, firstBoot.lineageId);
  assert.equal(typeof persisted.lastShutdownAt, 'string');
  const checkpoint = JSON.parse(await fs.readFile(checkpointPath, 'utf8'));
  assert.equal(checkpoint.lineageId, firstBoot.lineageId);
  assert.ok(checkpoint.generation >= 2);

  const daemon2 = new LifeDaemon(options);
  await daemon2.start();
  const secondBoot = daemon2.snapshot();
  assert.ok(secondBoot.generation > persisted.generation);
  assert.equal(secondBoot.lineageId, firstBoot.lineageId);
  assert.notEqual(secondBoot.incarnationId, firstBoot.incarnationId);
  assert.equal(secondBoot.bootCount, 2);
  assert.equal(daemon2.timer.hasRef(), true);
  await daemon2.stop({ reason: 'test' });
});
