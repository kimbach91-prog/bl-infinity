import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { stableFingerprint } from '../lib/life-core.mjs';
import { LifeDaemon } from '../worker/life-daemon.mjs';

function options(dir) {
  return {
    statePath: path.join(dir, 'state.json'),
    journalPath: path.join(dir, 'journal.ndjson'),
    leasePath: path.join(dir, 'life.lock'),
    checkpointPath: path.join(dir, 'checkpoint.json'),
    pendingPath: path.join(dir, 'state.json.pending'),
    pulseMs: 5000,
    leaseTtlMs: 20_000,
    logger: { info() {}, warn() {}, error() {} },
    sampleRuntime: async () => ({ humanAutonomy: 1 }),
  };
}

async function seedHealthyLineage(dir) {
  const opts = options(dir);
  const daemon = new LifeDaemon(opts);
  await daemon.start();
  await daemon.stop({ reason: 'seed' });
  const state = JSON.parse(await fs.readFile(opts.statePath, 'utf8'));
  return { opts, state };
}

test('pending recovery rejects a validly hashed generation that forks from a different journal head', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-fork-'));
  const { opts, state } = await seedHealthyLineage(dir);

  const journalBase = {
    at: new Date().toISOString(),
    generation: state.generation + 1,
    eventType: 'forged-pending-test',
    eventSource: 'test',
    novelty: true,
    action: 'HOLD_STEADY',
    actionScore: 0,
    viability: 1,
    affect: {},
    mutation: false,
    reward: 0,
    body: state.body,
    inputAt: new Date().toISOString(),
    lineageId: state.lineageId,
    incarnationId: state.incarnationId,
    prevHash: 'forked-head-that-is-not-current-tail',
  };
  const journalHash = stableFingerprint(journalBase);
  const pendingState = {
    ...state,
    generation: state.generation + 1,
    journalHead: journalHash,
    lastAction: 'HOLD_STEADY',
  };
  await fs.writeFile(opts.pendingPath, `${JSON.stringify({
    version: 1,
    state: pendingState,
    journal: { ...journalBase, journalHash },
  }, null, 2)}\n`, 'utf8');

  const next = new LifeDaemon(opts);
  await assert.rejects(
    () => next.start(),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED' && /does not extend/.test(error.message),
  );
});

test('pending recovery rejects a pending journal whose own hash is invalid', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'deus-life-pending-hash-'));
  const { opts, state } = await seedHealthyLineage(dir);
  const pending = {
    version: 1,
    state: { ...state, generation: state.generation + 1, journalHead: 'invalid-hash' },
    journal: {
      generation: state.generation + 1,
      lineageId: state.lineageId,
      incarnationId: state.incarnationId,
      prevHash: state.journalHead,
      journalHash: 'invalid-hash',
    },
  };
  await fs.writeFile(opts.pendingPath, `${JSON.stringify(pending, null, 2)}\n`, 'utf8');

  const next = new LifeDaemon(opts);
  await assert.rejects(
    () => next.start(),
    (error) => error?.code === 'LIFE_JOURNAL_DIVERGED' && /hash verification failed/.test(error.message),
  );
});
