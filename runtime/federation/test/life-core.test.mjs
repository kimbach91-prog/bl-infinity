import test from 'node:test';
import assert from 'node:assert/strict';
import { createInitialLifeState, rangeHealth, stepLife } from '../lib/life-core.mjs';

test('range health is 1 inside the healthy interval', () => {
  assert.equal(rangeHealth(1, [0.9, 1]), 1);
  assert.equal(rangeHealth(0.95, [0.9, 1]), 1);
});

test('quiet repeated input does not produce policy mutation', () => {
  let state = createInitialLifeState(0);
  ({ state } = stepLife(state, { type: 'quiet-pulse', source: 'test', allowLearning: false }, 1));
  const before = state.totalMutations;
  ({ state } = stepLife(state, { type: 'quiet-pulse', source: 'test', allowLearning: false }, 2));
  assert.equal(state.totalMutations, before);
});

test('healthy continuity does not force preserve-context action', () => {
  const state = createInitialLifeState(0);
  const { record } = stepLife(state, { type: 'boot', source: 'test', allowLearning: false }, 1);
  assert.notEqual(record.action, 'PRESERVE_CONTEXT');
});

test('a memory integrity failure raises repair-oriented behavior', () => {
  let state = createInitialLifeState(0);
  state.body.M = 0.1;
  state.body.C = 0.4;
  const { record } = stepLife(state, { type: 'memory-readback-error', source: 'test', allowLearning: false }, 1);
  assert.equal(record.action, 'VERIFY_REPAIR');
});

test('learning changes bounded policy weights only on permitted novelty', () => {
  let state = createInitialLifeState(0);
  const first = stepLife(state, { type: 'external-novelty', source: 'test', reward: 0.5 }, 1);
  state = first.state;
  assert.ok(state.totalMutations <= 1);
  for (const value of Object.values(state.policyWeights)) {
    assert.ok(value >= 0.6 && value <= 1);
  }
});
