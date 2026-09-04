import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validateResourceOffer,
  classifyResourceUse,
  resourceAcquisitionEconomics,
  valueFirstProviderPreview,
  ResourceAcquisitionEngine,
} from '../lib/resource-acquisition.mjs';

function offer(overrides = {}) {
  return {
    offerId: overrides.offerId ?? 'offer-1',
    providerId: overrides.providerId ?? 'provider-1',
    sourceUseClass: overrides.sourceUseClass ?? 'general-compute',
    rights: {
      authorized: true,
      termsPermitDeclaredUse: true,
      revocable: true,
      consentRef: 'consent:offer-1',
      autoEnrollAllowed: true,
      preAuthorizedGrant: true,
      ...overrides.rights,
    },
    resources: { cpuCoreSeconds: 1000 },
    economics: {
      expectedSettlementValueUsd: 100,
      providerAcquisitionCostUsd: 50,
      operatorCostUsd: 10,
      verificationCostUsd: 0,
      riskProvisionUsd: 5,
      ...overrides.economics,
    },
    valueFirstPreview: {
      estimatedProviderSavingsUsd: 5,
      estimatedProviderRevenueUsd: 10,
      estimatedDccCreditValueUsd: 0,
      profilingCostToFederationUsd: 1,
      ...overrides.valueFirstPreview,
    },
    compensationMode: overrides.compensationMode ?? 'dcc',
  };
}

test('resource offer requires lawful authority, revocability and terms-compatible use', () => {
  assert.equal(validateResourceOffer(offer()), true);
  assert.throws(() => validateResourceOffer(offer({ rights: { termsPermitDeclaredUse: false } })), /terms must permit/);
});

test('restricted CI/admin sources cannot be silently repurposed as general compute', () => {
  const ciOffer = offer({ sourceUseClass: 'ci-only' });
  assert.equal(classifyResourceUse(ciOffer, 'ci-only').ok, true);
  const general = classifyResourceUse(ciOffer, 'general-compute');
  assert.equal(general.ok, false);
  assert.match(general.reason, /cannot-be-repurposed/);
});

test('acquisition economics reject negative or insufficient margin', () => {
  const good = resourceAcquisitionEconomics({ expectedSettlementValueUsd: 100, providerAcquisitionCostUsd: 50, operatorCostUsd: 10, riskProvisionUsd: 5, minimumContributionMarginRate: 0.10 });
  assert.equal(good.economicallyAdmissible, true);
  const bad = resourceAcquisitionEconomics({ expectedSettlementValueUsd: 100, providerAcquisitionCostUsd: 95, operatorCostUsd: 10, minimumContributionMarginRate: 0.10 });
  assert.equal(bad.economicallyAdmissible, false);
});

test('value-first preview gives provider an estimate before asking for ongoing grant', () => {
  const preview = valueFirstProviderPreview({ estimatedProviderSavingsUsd: 5, estimatedProviderRevenueUsd: 10, profilingCostToFederationUsd: 2 });
  assert.equal(preview.providerEstimatedValueUsd, 15);
  assert.equal(preview.netEstimatedMutualValueUsd, 13);
  assert.equal(preview.disclosure.noAutoEnrollmentWithoutAuthorization, true);
});

test('engine auto-activates only pre-authorized profitable terms-compatible offers', () => {
  const engine = new ResourceAcquisitionEngine({ minimumContributionMarginRate: 0.10 });
  engine.ingestOffer(offer());
  const decision = engine.evaluateOffer('offer-1');
  assert.equal(decision.eligibleForAutoEnrollment, true);
  const active = engine.activateOffer('offer-1', decision);
  assert.equal(active.status, 'active');
});

test('without explicit auto-enrollment authority the engine creates a proposal rather than taking compute', () => {
  const engine = new ResourceAcquisitionEngine();
  engine.ingestOffer(offer({ offerId: 'manual', rights: { autoEnrollAllowed: false, preAuthorizedGrant: true } }));
  const decision = engine.evaluateOffer('manual');
  assert.equal(decision.eligibleForAutoEnrollment, false);
  assert.equal(decision.requiresExplicitAcceptance, true);
  assert.ok(decision.reasons.includes('auto-enroll-not-authorized'));
});
