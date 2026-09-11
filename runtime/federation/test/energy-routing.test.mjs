import test from 'node:test';
import assert from 'node:assert/strict';
import { ProviderRegistry, rankCandidates } from '../lib/fabric.mjs';
import { TelemetryBook } from '../lib/telemetry.mjs';

function provider(id, telemetry = {}) {
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
    limits: { maxConcurrency: 4, maxCostPerTaskUsd: 100 },
    telemetry: {
      trust: 0.9,
      availability: 0.99,
      p95LatencyMs: 10,
      costPerUnitUsd: 0.01,
      inFlight: 0,
      ...telemetry,
    },
    dataLocations: ['local'],
  };
}

test('energy-aware tasks fail closed when a provider has no measured energy telemetry', () => {
  const registry = new ProviderRegistry([provider('unmeasured')]);
  const ranked = rankCandidates(registry, {
    id: 't-energy',
    capability: 'compute.echo',
    dataClass: 'public',
    dataLocation: 'local',
    requiresEnergyTelemetry: true,
  });
  assert.equal(ranked.length, 0);
});

test('explicit task energy ceiling rejects a provider above the measured limit', () => {
  const registry = new ProviderRegistry([provider('hot', { energyPerUnitJoules: 50 })]);
  const ranked = rankCandidates(registry, {
    id: 't-limit',
    capability: 'compute.echo',
    dataClass: 'public',
    dataLocation: 'local',
    maxEnergyPerUnitJoules: 20,
  });
  assert.equal(ranked.length, 0);
});

test('energy-aware routing prefers lower measured joules when other signals are equal', () => {
  const registry = new ProviderRegistry([
    provider('efficient', { energyPerUnitJoules: 5 }),
    provider('hungry', { energyPerUnitJoules: 50 }),
  ]);
  const ranked = rankCandidates(registry, {
    id: 't-rank',
    capability: 'compute.echo',
    dataClass: 'public',
    dataLocation: 'local',
    requiresEnergyTelemetry: true,
  });
  assert.equal(ranked.length, 2);
  assert.equal(ranked[0].provider.id, 'efficient');
  assert.ok(ranked[0].score > ranked[1].score);
});

test('ordinary tasks remain backward compatible when energy telemetry is absent', () => {
  const registry = new ProviderRegistry([provider('legacy')]);
  const ranked = rankCandidates(registry, {
    id: 't-legacy',
    capability: 'compute.echo',
    dataClass: 'public',
    dataLocation: 'local',
  });
  assert.equal(ranked.length, 1);
  assert.equal(ranked[0].provider.id, 'legacy');
});

test('telemetry preserves seeded energy and updates it only from measured samples', () => {
  const telemetry = new TelemetryBook({ alpha: 0.5 });
  telemetry.ensure('p', { energyPerUnitJoules: 100 });
  assert.equal(telemetry.snapshot('p').energyPerUnitJoules, 100);
  telemetry.updateEnergy('p', { energyJoules: 100, workUnits: 2 });
  assert.equal(telemetry.snapshot('p').energyPerUnitJoules, 75);
  telemetry.success('p', { latencyMs: 1, energyPerUnitJoules: 25 });
  assert.equal(telemetry.snapshot('p').energyPerUnitJoules, 50);
});
