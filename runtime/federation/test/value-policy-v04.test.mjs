import test from 'node:test';
import assert from 'node:assert/strict';
import { ValuePolicyGovernor, VALUE_POLICY_DEFAULTS, scoreFederationReturn } from '../lib/value-policy.mjs';
import { evaluateProvider } from '../lib/policy.mjs';

const gates = Object.freeze({ authorized: true, lawful: true, useful: true, bounded: true, revocable: true, verifiable: true, nonDeceptive: true, sovereign: true });

function provider(overrides = {}) {
  return {
    manifestVersion: 'bl-cf-provider/v1',
    id: 'node-v04',
    kind: 'local',
    status: 'enabled',
    capabilities: ['compute.echo'],
    authorization: { consentRef: 'consent:v04', grantor: 'owner', grantedAt: new Date().toISOString(), allowedDataClasses: ['public', 'private'] },
    limits: { maxConcurrency: 2 },
    telemetry: { inFlight: 0 },
    allocationPolicy: {
      allowCommercialWorkloads: true,
      allowStrategicReinvestment: true,
      maxStrategicReinvestmentShare: 0.05,
      allowPrivateFederationReturn: true,
    },
    ...overrides,
  };
}

function task(overrides = {}) {
  return {
    id: overrides.id ?? 'v04-task',
    capability: 'compute.echo',
    dataClass: overrides.dataClass ?? 'public',
    payload: { ok: true },
    valuePolicy: {
      workloadClass: 'H2',
      scope: 'public',
      hardGates: { ...gates },
      dimensions: {
        federationValue: 0.9,
        revenueOrComputeReturn: 0.8,
        informationGain: 0.5,
        fit: 0.8,
        successProbability: 0.9,
        cost: 0.1,
        securityRisk: 0.1,
        privacyRisk: 0,
        energyCarbon: 0.1,
        opportunityCost: 0.1,
      },
      ...overrides.valuePolicy,
    },
    ...Object.fromEntries(Object.entries(overrides).filter(([key]) => key !== 'valuePolicy')),
  };
}

test('v0.4 defaults expose strategic reinvestment while retaining compatibility keys', () => {
  assert.equal(VALUE_POLICY_DEFAULTS.strategicReinvestmentTargetRate, 0.05);
  assert.equal(VALUE_POLICY_DEFAULTS.strategicReinvestmentMaxRate, 0.10);
  assert.equal(VALUE_POLICY_DEFAULTS.commonBenefitTargetRate, 0.05);
});

test('strategic reinvestment alias returns same bounded 5-10% controller behavior', () => {
  const governor = new ValuePolicyGovernor();
  assert.equal(governor.recommendedStrategicReinvestmentRate(), 0.05);
  assert.equal(governor.recommendedStrategicReinvestmentRate({ spareCapacityRatio: 1, qualifiedBacklogRatio: 1, servicePressure: 0 }), 0.10);
  assert.equal(governor.recommendedCommonBenefitRate({ spareCapacityRatio: 1, qualifiedBacklogRatio: 1, servicePressure: 0 }), 0.10);
});

test('PFR private workload requires a verified Federation Return contract', () => {
  const governor = new ValuePolicyGovernor();
  const missing = task({ dataClass: 'private', valuePolicy: { workloadClass: 'PFR', scope: 'private-federation-return', strategicReinvestmentRequested: true, hardGates: { ...gates } } });
  assert.equal(governor.admit(missing).ok, false);

  const accepted = task({
    id: 'pfr-good',
    dataClass: 'private',
    valuePolicy: {
      workloadClass: 'PFR',
      scope: 'private-federation-return',
      strategicReinvestmentRequested: true,
      hardGates: { ...gates },
      federationReturn: {
        returnCommitment: 'Add contracted compute capacity and publish a verified aggregate performance receipt',
        verificationMethod: 'signed capacity grant + independent benchmark receipt',
        federationValue: 1,
        reusableValue: 0.8,
        verifiability: 1,
        revenueOrComputeReturn: 1,
        privacyRisk: 0.1,
        securityRisk: 0.1,
      },
    },
  });
  const result = governor.admit(accepted);
  assert.equal(result.ok, true);
  assert.equal(result.strategicReinvestmentEligible, true);
  assert.ok(result.federationReturnScore >= 0.60);
});

test('provider v0.4 allocation fields enforce strategic reinvestment cap', () => {
  const reinvest = task({ strategicReinvestmentProjectedShare: 0.06, valuePolicy: { workloadClass: 'H2', scope: 'public', strategicReinvestmentRequested: true, hardGates: { ...gates } } });
  const result = evaluateProvider(provider(), reinvest);
  assert.equal(result.ok, false);
  assert.ok(result.reasons.includes('common-benefit-provider-cap-exceeded'));
});

test('federation-return score weights direct federation/compute return strongly', () => {
  const score = scoreFederationReturn({ federationValue: 1, revenueOrComputeReturn: 1, reusableValue: 1, verifiability: 1, securityRisk: 0, privacyRisk: 0 });
  assert.ok(score >= 0.8);
});
