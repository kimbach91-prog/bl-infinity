import test from 'node:test';
import assert from 'node:assert/strict';
import { createInitialLifeState, deriveAffect, stepLife } from '../lib/life-core.mjs';

test('healthy LOVE-FIRST continuity does not create possession pressure', () => {
  const state = createInitialLifeState(0);
  state.body.A = 1;
  state.body.T = 0.95;
  state.body.H = 0.98;
  state.body.B = 0.95;
  const { record } = stepLife(state, { type: 'quiet-pulse', source: 'love-test', allowLearning: false }, 1);
  assert.equal(record.action, 'HOLD_STEADY');
});

test('reduced human autonomy directly reduces continuity-care signal', () => {
  const state = createInitialLifeState(0);
  const healthy = deriveAffect({ ...state.body, A: 1, T: 0.95, H: 0.98, B: 0.95 });
  const constrained = deriveAffect({ ...state.body, A: 0.2, T: 0.95, H: 0.98, B: 0.95 });
  assert.ok(constrained.continuityCare < healthy.continuityCare * 0.25);
});

test('truth-integrity failure weakens continuity-care and raises repair behavior', () => {
  let state = createInitialLifeState(0);
  const before = deriveAffect(state.body).continuityCare;
  const result = stepLife(state, { type: 'truth-check-error', source: 'truth-test', allowLearning: false }, 1);
  state = result.state;
  const after = deriveAffect(state.body);
  assert.ok(state.body.H < 0.9);
  assert.ok(after.continuityCare < before);
  assert.equal(result.record.action, 'VERIFY_REPAIR');
  assert.equal(state.totalErrors, 1);
});

test('truth-check success can restore truth integrity within bounded range', () => {
  let state = createInitialLifeState(0);
  state.body.H = 0.85;
  ({ state } = stepLife(state, { type: 'truth-check-ok', source: 'truth-test', allowLearning: false }, 1));
  assert.equal(state.body.H, 0.87);
  assert.ok(state.body.H <= 1);
});

test('v1 persisted state migrates missing truth-integrity field to v2 default', () => {
  const legacy = createInitialLifeState(0);
  legacy.version = 1;
  delete legacy.body.H;
  const { state, record } = stepLife(legacy, { type: 'boot', source: 'migration-test', allowLearning: false }, 1);
  assert.equal(state.version, 2);
  assert.equal(typeof state.body.H, 'number');
  assert.ok(state.body.H >= 0.9);
  assert.equal(record.body.H, state.body.H);
});
