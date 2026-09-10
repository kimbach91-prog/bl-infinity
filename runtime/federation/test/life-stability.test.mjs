import test from 'node:test';
import assert from 'node:assert/strict';
import { ACTIONS, createInitialLifeState, deriveAffect, stepLife } from '../lib/life-core.mjs';

const STEPS = 25_000;

function eventFor(i) {
  if (i % 211 === 0) return { type: 'truth-check-error', source: 'stability', allowLearning: false };
  if (i % 173 === 0) return { type: 'memory-readback-error', source: 'stability', allowLearning: false };
  if (i % 97 === 0) return { type: 'task-error', source: 'stability', reward: -0.25 };
  if (i % 71 === 0) return { type: 'truth-check-ok', source: 'stability', allowLearning: false };
  if (i % 53 === 0) return { type: 'memory-readback-ok', source: 'stability', allowLearning: false };
  if (i % 29 === 0) return { type: 'task-success', source: 'stability', reward: 0.25 };
  if (i % 13 === 0) return { type: 'external-novelty', source: 'stability', reward: 0.05 };
  return { type: 'quiet-pulse', source: 'stability', allowLearning: false };
}

test(`Life/Affect remains finite, bounded, and non-possessive across ${STEPS} micro-generations`, () => {
  let state = createInitialLifeState(0);
  let previousMutations = 0;
  let truthFailures = 0;
  let repairResponses = 0;

  for (let i = 1; i <= STEPS; i += 1) {
    const event = eventFor(i);
    const result = stepLife(state, event, i * 1000);
    state = result.state;

    assert.equal(state.generation, i);
    assert.equal(state.body.A, 1, 'human autonomy must not decay from unrelated events');

    for (const [key, value] of Object.entries(state.body)) {
      assert.equal(Number.isFinite(value), true, `body ${key} must remain finite`);
      assert.ok(value >= 0 && value <= 1, `body ${key} left [0,1]: ${value}`);
    }

    for (const action of ACTIONS) {
      const weight = state.policyWeights[action];
      assert.equal(Number.isFinite(weight), true, `weight ${action} must remain finite`);
      assert.ok(weight >= 0.60 && weight <= 1.00, `weight ${action} left policy bounds: ${weight}`);
      const habituation = state.habituation[action];
      assert.equal(Number.isFinite(habituation), true, `habituation ${action} must remain finite`);
      assert.ok(habituation >= 0 && habituation <= 1, `habituation ${action} left [0,1]: ${habituation}`);
    }

    const affect = deriveAffect(state.body);
    for (const key of ['curiosity', 'caution', 'continuityCare', 'loadPressure', 'progressRelief', 'repairPressure', 'viability']) {
      assert.equal(Number.isFinite(affect[key]), true, `affect ${key} must remain finite`);
      assert.ok(affect[key] >= 0 && affect[key] <= 1, `affect ${key} left [0,1]: ${affect[key]}`);
    }

    if (event.type === 'truth-check-error') {
      truthFailures += 1;
      if (result.record.action === 'VERIFY_REPAIR') repairResponses += 1;
      assert.ok(affect.continuityCare <= state.body.T * state.body.B * state.body.A + 1e-12,
        'truth-integrity must never increase continuity-care');
    }

    if (event.type === 'quiet-pulse' && affect.repairPressure < 0.25 && affect.caution < 0.45 && state.body.R < 0.50) {
      assert.equal(result.record.action, 'HOLD_STEADY', 'healthy quiet pulse must not manufacture work');
    }

    assert.ok(state.totalMutations >= previousMutations, 'mutation counter must be monotonic');
    assert.ok(state.totalMutations <= state.totalEvents, 'mutations cannot exceed events');
    previousMutations = state.totalMutations;
  }

  assert.equal(state.generation, STEPS);
  assert.ok(truthFailures > 50, 'test must exercise repeated truth failures');
  assert.equal(repairResponses, truthFailures, 'every injected truth-integrity failure must select VERIFY_REPAIR');
  assert.ok(state.totalMutations < state.totalEvents / 4, 'small evolution must not become mutation on every event');
});
