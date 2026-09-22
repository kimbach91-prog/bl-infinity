import test from 'node:test';
import assert from 'node:assert/strict';
import { createFederationRuntime } from '../lib/runtime.mjs';

function provider(id = 'local', telemetry = {}) {
  return {
    id,
    kind: 'local',
    capabilities: ['compute.echo'],
    authorization: {
      consentRef: `consent:${id}`,
      expiresAt: '2099-01-01T00:00:00.000Z',
      allowedDataClasses: ['public'],
      maxTaskCostUsd: 100,
    },
    limits: { maxConcurrency: 4, maxCostPerTaskUsd: 100, maxExecutionMs: 5000 },
    telemetry: {
      trust: 0.9,
      availability: 0.99,
      p95LatencyMs: 10,
      costPerUnitUsd: 0.01,
      inFlight: 0,
      ...telemetry,
    },
    dataLocations: ['local'],
    dataPolicy: { retention: 'none' },
    regions: ['local'],
    tags: ['test'],
  };
}

function envelopedTask(id, overrides = {}) {
  return {
    id,
    capability: 'compute.echo',
    payload: { ok: true },
    dataClass: 'public',
    dataLocation: 'local',
    tenantId: 'test',
    estimatedCostUsd: 0.05,
    estimatedWorkUnits: 5,
    estimatedTokens: 100,
    computeTier: 'T2',
    computeEnvelope: {
      purpose: 'integration-test',
      authority: 'test-suite',
      limits: {
        energyJoules: 100,
        costUsd: 1,
        acceleratorSeconds: 100,
        tokens: 1000,
        wallTimeMs: 5000,
      },
      tierCeiling: 'T2',
      assuranceLevel: 'medium',
      catastrophicRiskClass: 0,
    },
    ...overrides,
  };
}

test('runtime reserves multidimensional resources before dispatch and closes the task after success', async () => {
  let executions = 0;
  const runtime = createFederationRuntime({
    providers: [provider('efficient', { energyPerUnitJoules: 10 })],
    localHandlers: { 'compute.echo': async (payload) => { executions += 1; return payload; } },
    resourceEnvelopeConfig: { globalLimits: { energyJoules: 1000, costUsd: 100, tokens: 10000 } },
  });

  const task = envelopedTask('energy-ok');
  await runtime.orchestrator.submit(task);
  const result = await runtime.orchestrator.runOnce();
  assert.equal(result.error, undefined);
  assert.equal(executions, 1);

  const envelope = runtime.resourceEnvelope.taskSnapshot(task.id);
  assert.equal(envelope.state, 'closed');
  assert.equal(envelope.spent.energyJoules, 50);
  assert.equal(envelope.spent.tokens, 100);
  assert.equal(envelope.reserved.energyJoules, 0);
});

test('runtime refuses dispatch when estimated provider energy exceeds the task envelope', async () => {
  let executions = 0;
  const runtime = createFederationRuntime({
    providers: [provider('hungry', { energyPerUnitJoules: 10 })],
    localHandlers: { 'compute.echo': async (payload) => { executions += 1; return payload; } },
  });

  const task = envelopedTask('energy-blocked', {
    computeEnvelope: {
      ...envelopedTask('template').computeEnvelope,
      limits: { ...envelopedTask('template').computeEnvelope.limits, energyJoules: 20 },
    },
  });
  await runtime.orchestrator.submit(task);
  const result = await runtime.orchestrator.runOnce();
  assert.match(result.error, /all eligible providers failed/);
  assert.equal(executions, 0);

  const envelope = runtime.resourceEnvelope.taskSnapshot(task.id);
  assert.equal(envelope.spent.energyJoules, 0);
  assert.equal(envelope.reserved.energyJoules, 0);
});

test('finite energy envelope fails closed when energy estimate depends on an unmeasured provider', async () => {
  let executions = 0;
  const runtime = createFederationRuntime({
    providers: [provider('unmeasured')],
    localHandlers: { 'compute.echo': async (payload) => { executions += 1; return payload; } },
  });

  const task = envelopedTask('energy-unmeasured');
  await runtime.orchestrator.submit(task);
  const result = await runtime.orchestrator.runOnce();
  assert.match(result.error, /no eligible provider/);
  assert.equal(executions, 0);
});

test('T5 cannot be entered through runtime without explicit HPC authorization', async () => {
  let executions = 0;
  const runtime = createFederationRuntime({
    providers: [provider('hpc', { energyPerUnitJoules: 1 })],
    localHandlers: { 'compute.echo': async (payload) => { executions += 1; return payload; } },
  });

  const task = envelopedTask('hpc-denied', { computeTier: 'T5' });
  await runtime.orchestrator.submit(task);
  const result = await runtime.orchestrator.runOnce();
  assert.match(result.error, /all eligible providers failed/);
  assert.equal(executions, 0);
});
