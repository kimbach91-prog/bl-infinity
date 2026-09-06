import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DependencyResilienceGovernor,
  evaluateDependencyDomain,
  evaluateDependencyPortfolio,
  simulateFailure,
} from '../lib/dependency-resilience.mjs';

function dep(id, overrides = {}) {
  return {
    id,
    domain: 'compute',
    providerId: id,
    controlGroup: id,
    jurisdiction: id === 'a' ? 'VN' : 'SG',
    upstreamCloud: id,
    rootCredentialAuthority: id,
    weight: 1,
    operational: true,
    testedFallback: true,
    ...overrides,
  };
}

test('healthy critical domain passes when no single provider or jurisdiction dominates and fallbacks are tested', () => {
  const result = evaluateDependencyDomain([
    dep('a', { weight: 0.4, jurisdiction: 'VN' }),
    dep('b', { weight: 0.3, jurisdiction: 'SG' }),
    dep('c', { weight: 0.3, jurisdiction: 'JP' }),
  ]);
  assert.equal(result.ok, true);
  assert.equal(result.metrics.independentSubstituteCount, 3);
  assert.equal(result.metrics.testedFallbackCount, 3);
});

test('single provider concentration is a hard failure', () => {
  const result = evaluateDependencyDomain([
    dep('a', { weight: 0.7, jurisdiction: 'VN' }),
    dep('b', { weight: 0.3, jurisdiction: 'SG' }),
  ]);
  assert.equal(result.ok, false);
  assert.ok(result.violations.includes('single-provider-concentration-exceeded'));
});

test('different brands sharing a control group still fail anti-capture concentration', () => {
  const result = evaluateDependencyDomain([
    dep('a', { providerId: 'brand-a', controlGroup: 'group-x', weight: 0.3, jurisdiction: 'VN' }),
    dep('b', { providerId: 'brand-b', controlGroup: 'group-x', weight: 0.3, jurisdiction: 'SG' }),
    dep('c', { providerId: 'brand-c', controlGroup: 'group-y', weight: 0.4, jurisdiction: 'JP' }),
  ]);
  assert.equal(result.ok, false);
  assert.ok(result.violations.includes('single-control-group-concentration-exceeded'));
});

test('unknown dependency metadata does not count as independent substitute', () => {
  const result = evaluateDependencyDomain([
    dep('a', { weight: 0.5, jurisdiction: 'VN' }),
    dep('b', { weight: 0.5, jurisdiction: null, controlGroup: null }),
  ], { maxSingleProviderShare: 0.5, maxSingleJurisdictionShare: 1, maxSingleControlGroupShare: 1 });
  assert.equal(result.metrics.independentSubstituteCount, 1);
  assert.ok(result.warnings.includes('unknown-dependency-is-not-counted-as-independent'));
  assert.ok(result.violations.includes('insufficient-independent-substitutes'));
});

test('documented but untested fallback does not satisfy tested-fallback gate', () => {
  const result = evaluateDependencyDomain([
    dep('a', { weight: 0.5, jurisdiction: 'VN', testedFallback: false }),
    dep('b', { weight: 0.5, jurisdiction: 'SG', testedFallback: false }),
  ], { maxSingleProviderShare: 0.5, maxSingleJurisdictionShare: 0.5, maxSingleControlGroupShare: 0.5 });
  assert.equal(result.ok, false);
  assert.ok(result.violations.includes('insufficient-tested-fallbacks'));
});

test('portfolio evaluates independent domains separately', () => {
  const entries = [
    dep('a', { domain: 'compute', weight: 0.5, jurisdiction: 'VN' }),
    dep('b', { domain: 'compute', weight: 0.5, jurisdiction: 'SG' }),
    dep('pay-a', { domain: 'payments', providerId: 'pay-a', controlGroup: 'pay-a', jurisdiction: 'VN', upstreamBank: 'bank-a', rootCredentialAuthority: 'pay-a', weight: 0.5, testedFallback: true }),
    dep('pay-b', { domain: 'payments', providerId: 'pay-b', controlGroup: 'pay-b', jurisdiction: 'SG', upstreamBank: 'bank-b', rootCredentialAuthority: 'pay-b', weight: 0.5, testedFallback: true }),
  ];
  const result = evaluateDependencyPortfolio(entries, {
    defaultThresholds: { maxSingleProviderShare: 0.5, maxSingleJurisdictionShare: 0.5, maxSingleControlGroupShare: 0.5 },
  });
  assert.equal(result.ok, true);
  assert.equal(result.domainCount, 2);
});

test('failure simulation removes every dependency sharing the failed upstream', () => {
  const entries = [
    dep('a', { upstreamCloud: 'cloud-x', weight: 0.3, jurisdiction: 'VN' }),
    dep('b', { upstreamCloud: 'cloud-x', weight: 0.3, jurisdiction: 'SG' }),
    dep('c', { upstreamCloud: 'cloud-y', weight: 0.4, jurisdiction: 'JP' }),
  ];
  const simulated = simulateFailure(entries, { upstreamCloud: 'cloud-x' }, {
    defaultThresholds: { maxSingleProviderShare: 1, maxSingleJurisdictionShare: 1, maxSingleControlGroupShare: 1, minimumIndependentSubstitutes: 1, minimumTestedExternalFallbacks: 1 },
  });
  assert.deepEqual(new Set(simulated.affectedIds), new Set(['a', 'b']));
  assert.deepEqual(simulated.survivorIds, ['c']);
});

test('governor critical-ready gate fails when required domain is missing or concentrated', () => {
  const governor = new DependencyResilienceGovernor({
    defaultThresholds: { maxSingleProviderShare: 0.5, maxSingleJurisdictionShare: 0.5, maxSingleControlGroupShare: 0.5 },
  });
  governor.upsert(dep('a', { weight: 0.8, jurisdiction: 'VN' }));
  governor.upsert(dep('b', { weight: 0.2, jurisdiction: 'SG' }));
  assert.throws(
    () => governor.assertCriticalReady(['compute', 'identity']),
    (error) => error.code === 'DEPENDENCY_RESILIENCE_GATE_FAILED'
      && error.missingDomains.includes('identity')
      && error.failedDomains.includes('compute'),
  );
});
