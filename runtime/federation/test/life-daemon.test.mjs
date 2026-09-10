import test from 'node:test';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';
import { LifeDaemon } from '../worker/life-daemon.mjs';

test('daemon keeps a referenced pulse handle, persists state, and resumes generation', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-'));
  const statePath = path.join(dir, 'state.json');
  const journalPath = path.join(dir, 'journal.ndjson');
  const logger = { info() {}, warn() {}, error() {} };
  const daemon = new LifeDaemon({
    statePath,
    journalPath,
    pulseMs: 5000,
    logger,
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  });
  await daemon.start();
  assert.equal(typeof daemon.timer?.hasRef, 'function');
  assert.equal(daemon.timer.hasRef(), true);
  await daemon.emit({ type: 'external-novelty', source: 'test', reward: 0.25 });
  const gen = daemon.snapshot().generation;
  assert.ok(gen >= 2);
  await daemon.stop({ reason: 'test' });

  const persisted = JSON.parse(await fs.readFile(statePath, 'utf8'));
  assert.equal(persisted.generation, daemon.snapshot().generation);

  const daemon2 = new LifeDaemon({
    statePath,
    journalPath,
    pulseMs: 5000,
    logger,
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  });
  await daemon2.start();
  assert.ok(daemon2.snapshot().generation > persisted.generation);
  assert.equal(daemon2.timer.hasRef(), true);
  await daemon2.stop({ reason: 'test' });
});
