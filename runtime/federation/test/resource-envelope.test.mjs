import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ResourceEnvelopeGovernor,
  chooseComputeTier,
  evaluateStop,
} from '../lib/resource-envelope.mjs';

test('resource envelope blocks task-level energy overspend before execution', () => {
  const governor = new ResourceEnvelopeGovernor();
  governor.openTask({ taskId: 'task-a', limits: { energyJoules: 100, tokens: 1000 } });
  const first = governor.authorize('task-a', { energyJoules: 80, tokens: 200 }, { tier: 'T2' });
  assert.equal(first.ok, true);
  const second = governor.authorize('task-a', { energyJoules: 21 }, { tier: 'T2' });
  assert.deepEqual(second, {
    ok: false,
    reason: 'task-energyJoules-limit-exceeded',
    dimension: 'energyJoules',
  });
});

test('resource envelope enforces aggregate global caps across tasks', () => {
  const governor = new ResourceEnvelopeGovernor({ globalLimits: { tokens: 1000 } });
  governor.openTask({ taskId: 'task-a', limits: { tokens: 1000 } });
  governor.openTask({ taskId: 'task-b', limits: { tokens: 1000 } });
  const a = governor.authorize('task-a', { tokens: 700 }, { tier: 'T2' });
  assert.equal(a.ok, true);
  const b = governor.authorize('task-b', { tokens: 301 }, { tier: 'T2' });
  assert.deepEqual(b, {
    ok: false,
    reason: 'global-tokens-limit-exceeded',
    dimension: 'tokens',
  });
});

test('T5 HPC is never authorized implicitly', () => {
  const governor = new ResourceEnvelopeGovernor();
  governor.openTask({ taskId: 'task-a', tierCeiling: 'T4' });
  assert.equal(governor.authorize('task-a', {}, { tier: 'T5' }).reason, 't5-explicit-authorization-required');
  const approved = governor.authorize('task-a', { acceleratorSeconds: 10 }, { tier: 'T5', explicitHpcAuthorization: true });
  assert.equal(approved.ok, true);
});

test('task tier ceiling rejects silent model escalation', () => {
  const governor = new ResourceEnvelopeGovernor();
  governor.openTask({ taskId: 'task-a', tierCeiling: 'T2' });
  const result = governor.authorize('task-a', { tokens: 10 }, { tier: 'T4' });
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'task-tier-ceiling-exceeded');
});

test('commit rejects actual usage that exceeds the envelope', () => {
  const governor = new ResourceEnvelopeGovernor();
  governor.openTask({ taskId: 'task-a', limits: { costUsd: 1 } });
  const reservation = governor.authorize('task-a', { costUsd: 0.5 }, { tier: 'T2' });
  assert.equal(reservation.ok, true);
  assert.throws(
    () => governor.commit(reservation.reservation.id, { costUsd: 1.1 }),
    (error) => error.code === 'RESOURCE_ENVELOPE_EXCEEDED' && error.dimension === 'costUsd',
  );
});

test('commit and release update reserved/spent counters deterministically', () => {
  const governor = new ResourceEnvelopeGovernor({ globalLimits: { energyJoules: 1000 } });
  governor.openTask({ taskId: 'task-a', limits: { energyJoules: 500 } });
  const r1 = governor.authorize('task-a', { energyJoules: 100 }, { tier: 'T1' });
  const r2 = governor.authorize('task-a', { energyJoules: 50 }, { tier: 'T2' });
  governor.commit(r1.reservation.id, { energyJoules: 90 });
  governor.release(r2.reservation.id, 'not-needed');
  const task = governor.taskSnapshot('task-a');
  assert.equal(task.spent.energyJoules, 90);
  assert.equal(task.reserved.energyJoules, 0);
  const global = governor.snapshot();
  assert.equal(global.globalSpent.energyJoules, 90);
  assert.equal(global.globalReserved.energyJoules, 0);
});

test('compute tier routing always prefers reuse/determinism before larger models', () => {
  assert.deepEqual(chooseComputeTier({ cacheHit: true, uncertainty: 1, novelty: 1 }), { tier: 'T0', reason: 'reuse-hit' });
  assert.deepEqual(chooseComputeTier({ deterministicAvailable: true }), { tier: 'T0', reason: 'deterministic-tool-available' });
  assert.equal(chooseComputeTier({ edgeEligible: true, uncertainty: 0.1, novelty: 0.1 }).tier, 'T1');
  assert.equal(chooseComputeTier({ specialistAvailable: true, uncertainty: 0.4, novelty: 0.4 }).tier, 'T2');
  assert.equal(chooseComputeTier({ independentVerificationRequired: true }).tier, 'T3');
  assert.equal(chooseComputeTier({ specialistAvailable: false, uncertainty: 0.9, novelty: 0.9 }).tier, 'T4');
});

test('stop logic terminates diminishing-return compute', () => {
  assert.equal(evaluateStop({ quality: 0.95, minimumQuality: 0.9 }).reason, 'required-quality-reached');
  assert.equal(evaluateStop({ quality: 0.1, minimumQuality: 0.9, newMaterialEvidence: false }).reason, 'no-material-new-evidence');
  assert.deepEqual(
    evaluateStop({
      quality: 0.5,
      minimumQuality: 0.9,
      marginalQualityGain: 0.001,
      marginalEnergyJoules: 100,
      minimumGainPerJoule: 0.0001,
    }),
    { stop: true, reason: 'marginal-gain-per-joule-below-threshold', gainPerJoule: 0.00001 },
  );
  assert.equal(evaluateStop({ quality: 0.5, minimumQuality: 0.9 }).stop, false);
});
