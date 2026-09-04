import test from 'node:test';
import assert from 'node:assert/strict';
import { ValuePolicyGovernor, VALUE_POLICY_DEFAULTS } from '../lib/value-policy.mjs';
import { evaluateProvider } from '../lib/policy.mjs';

const gates = Object.freeze({ authorized: true, lawful: true, useful: true, bounded: true, revocable: true, verifiable: true, nonDeceptive: true, sovereign: true });

function valueTask(overrides = {}) {
  return {
    id: overrides.id ?? 'value-task', capability: 'compute.echo', dataClass: overrides.dataClass ?? 'public', payload: { ok: true },
    valuePolicy: {
      workloadClass: 'H2', scope: 'public', hardGates: { ...gates },
      dimensions: { humanValue: 0.6, researchValue: 0.8, federationValue: 0.7, informationGain: 0.8, fit: 0.8, successProbability: 0.9, cost: 0.1, securityRisk: 0.1, privacyRisk: 0, energyCarbon: 0.1, opportunityCost: 0.1 },
      ...overrides.valuePolicy,
    },
    ...Object.fromEntries(Object.entries(overrides).filter(([key]) => key !== 'valuePolicy')),
  };
}

function provider(overrides = {}) {
  return {
    manifestVersion: 'bl-cf-provider/v1', id: 'node-test', kind: 'local', status: 'enabled',
    capabilities: ['compute.echo'],
    authorization: { consentRef: 'consent:test', grantor: 'owner', grantedAt: new Date().toISOString(), allowedDataClasses: ['public', 'private'] },
    limits: { maxConcurrency: 2 }, telemetry: { inFlight: 0 },
    allocationPolicy: { allowCommercialWorkloads: false, allowCommonBenefit: true, maxCommonBenefitShare: 0.05, allowPrivateSharedBenefit: false },
    ...overrides,
  };
}

test('default economics are 10% protocol share and 5%-10% common-benefit band', () => {
  assert.equal(VALUE_POLICY_DEFAULTS.commercialShareRate, 0.10);
  assert.equal(VALUE_POLICY_DEFAULTS.commonBenefitTargetRate, 0.05);
  assert.equal(VALUE_POLICY_DEFAULTS.commonBenefitMaxRate, 0.10);
  const governor = new ValuePolicyGovernor();
  assert.deepEqual(governor.commercialSettlement({ eligibleCommercialSettlementValue: 100 }), {
    eligibleCommercialSettlementValue: 100,
    commercialShareRate: 0.10,
    officialProtocolShare: 10,
    remainderBeforeOtherSettlementRules: 90,
  });
});

test('adaptive common-benefit rate stays inside the configured/provider ceiling', () => {
  const governor = new ValuePolicyGovernor();
  assert.equal(governor.recommendedCommonBenefitRate(), 0.05);
  assert.equal(governor.recommendedCommonBenefitRate({ spareCapacityRatio: 1, qualifiedBacklogRatio: 1, servicePressure: 0 }), 0.10);
  assert.equal(governor.recommendedCommonBenefitRate({ spareCapacityRatio: 1, qualifiedBacklogRatio: 1, servicePressure: 0, providerCap: 0.03 }), 0.03);
});

test('legacy tasks remain admissible for backward compatibility', () => {
  const governor = new ValuePolicyGovernor();
  const result = governor.admit({ id: 'legacy', capability: 'compute.echo', dataClass: 'public' });
  assert.equal(result.ok, true);
  assert.equal(result.legacy, true);
});

test('value-aware task fails closed when a hard gate is missing', () => {
  const governor = new ValuePolicyGovernor();
  const task = valueTask();
  delete task.valuePolicy.hardGates.sovereign;
  const result = governor.admit(task);
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'hard-gate-failed:sovereign');
});

test('normal commercial task cannot silently consume common-benefit capacity', () => {
  const governor = new ValuePolicyGovernor();
  const task = valueTask({ valuePolicy: { workloadClass: 'H4', scope: 'trusted', commonBenefitRequested: true, hardGates: { ...gates } } });
  const result = governor.admit(task);
  assert.equal(result.ok, false);
  assert.match(result.reason, /shared-benefit/);
});

test('private shared-benefit work is admitted only with strong verifiable common return', () => {
  const governor = new ValuePolicyGovernor();
  const task = valueTask({
    dataClass: 'private',
    valuePolicy: {
      workloadClass: 'PGB', scope: 'private-shared-benefit', commonBenefitRequested: true, hardGates: { ...gates },
      sharedBenefit: {
        returnCommitment: 'Publish a reusable scheduler benchmark artifact', verificationMethod: 'independent artifact hash + benchmark replay',
        humanValue: 0.5, researchValue: 0.8, federationValue: 1, reusableValue: 1, verifiability: 1, privacyRisk: 0.1, securityRisk: 0.1,
      },
    },
  });
  const result = governor.admit(task);
  assert.equal(result.ok, true);
  assert.equal(result.commonBenefitEligible, true);
  assert.ok(result.sharedBenefitScore >= 0.60);
});

test('Founder sponsorship can prioritize qualifying common work but never bypass hard gates', () => {
  const governor = new ValuePolicyGovernor();
  const normal = governor.admit(valueTask({ valuePolicy: { workloadClass: 'H2', scope: 'public', commonBenefitRequested: true, founderSponsored: false, hardGates: { ...gates } } }));
  const sponsored = governor.admit(valueTask({ id: 'sponsored', valuePolicy: { workloadClass: 'H2', scope: 'public', commonBenefitRequested: true, founderSponsored: true, hardGates: { ...gates } } }));
  assert.equal(normal.ok, true);
  assert.equal(sponsored.ok, true);
  assert.equal(sponsored.priority - normal.priority, 25);
  const invalid = valueTask({ id: 'invalid', valuePolicy: { workloadClass: 'H2', scope: 'public', commonBenefitRequested: true, founderSponsored: true, hardGates: { ...gates, lawful: false } } });
  assert.equal(governor.admit(invalid).ok, false);
});

test('provider must explicitly opt into commercial and common-benefit work', () => {
  const commercial = valueTask({ valuePolicy: { workloadClass: 'H4', scope: 'trusted', commonBenefitRequested: false, hardGates: { ...gates } } });
  const commercialResult = evaluateProvider(provider(), commercial);
  assert.equal(commercialResult.ok, false);
  assert.ok(commercialResult.reasons.includes('commercial-workload-not-opted-in'));

  const common = valueTask({ valuePolicy: { workloadClass: 'H2', scope: 'public', commonBenefitRequested: true, hardGates: { ...gates } } });
  assert.equal(evaluateProvider(provider(), common).ok, true);

  const noCommon = provider({ allocationPolicy: { allowCommercialWorkloads: false, allowCommonBenefit: false, maxCommonBenefitShare: 0, allowPrivateSharedBenefit: false } });
  const noCommonResult = evaluateProvider(noCommon, common);
  assert.equal(noCommonResult.ok, false);
  assert.ok(noCommonResult.reasons.includes('common-benefit-not-opted-in'));
});

test('provider lower common-benefit cap is enforceable for projected rolling share', () => {
  const task = valueTask({ commonBenefitProjectedShare: 0.06, valuePolicy: { workloadClass: 'H2', scope: 'public', commonBenefitRequested: true, hardGates: { ...gates } } });
  const result = evaluateProvider(provider(), task);
  assert.equal(result.ok, false);
  assert.ok(result.reasons.includes('common-benefit-provider-cap-exceeded'));
});
