const SOURCE_USE_CLASSES = new Set(['general-compute', 'ci-only', 'control-plane-only', 'interactive-admin-only', 'research-only']);
const COMPENSATION_MODES = new Set(['cash', 'dcc', 'reciprocal-compute', 'hybrid']);

function nonNegative(value, name) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${name} must be a non-negative number`);
  return number;
}

function boundedRate(value, fallback = 0) {
  const number = Number(value ?? fallback);
  if (!Number.isFinite(number) || number < 0 || number > 1) throw new Error(`invalid rate: ${value}`);
  return number;
}

export function validateResourceOffer(offer) {
  if (!offer?.offerId) throw new Error('offer.offerId is required');
  if (!offer?.providerId) throw new Error('offer.providerId is required');
  if (!SOURCE_USE_CLASSES.has(offer.sourceUseClass)) throw new Error('invalid offer.sourceUseClass');
  const rights = offer.rights ?? {};
  if (rights.authorized !== true) throw new Error('offer rights must be authorized');
  if (rights.termsPermitDeclaredUse !== true) throw new Error('provider/platform terms must permit the declared use');
  if (rights.revocable !== true) throw new Error('offer must be revocable');
  if (!rights.consentRef) throw new Error('offer rights.consentRef is required');
  if (!offer.resources || typeof offer.resources !== 'object') throw new Error('offer.resources is required');
  if (!offer.economics || typeof offer.economics !== 'object') throw new Error('offer.economics is required');
  if (offer.compensationMode && !COMPENSATION_MODES.has(offer.compensationMode)) throw new Error('invalid compensation mode');
  return true;
}

export function classifyResourceUse(offer, requestedUseClass = 'general-compute') {
  validateResourceOffer(offer);
  const declared = offer.sourceUseClass;
  if (declared === 'general-compute') return { ok: true, reason: null };
  if (declared === requestedUseClass) return { ok: true, reason: null };
  return { ok: false, reason: `source-use-class-${declared}-cannot-be-repurposed-as-${requestedUseClass}` };
}

export function resourceAcquisitionEconomics({
  expectedSettlementValueUsd,
  providerAcquisitionCostUsd,
  operatorCostUsd = 0,
  verificationCostUsd = 0,
  riskProvisionUsd = 0,
  minimumContributionMarginRate = 0.10,
} = {}) {
  const settlement = nonNegative(expectedSettlementValueUsd, 'expectedSettlementValueUsd');
  const acquisition = nonNegative(providerAcquisitionCostUsd, 'providerAcquisitionCostUsd');
  const operator = nonNegative(operatorCostUsd, 'operatorCostUsd');
  const verification = nonNegative(verificationCostUsd, 'verificationCostUsd');
  const risk = nonNegative(riskProvisionUsd, 'riskProvisionUsd');
  const marginFloor = boundedRate(minimumContributionMarginRate, 0.10);
  const totalCostUsd = acquisition + operator + verification + risk;
  const expectedGrossProfitUsd = settlement - totalCostUsd;
  const contributionMarginRate = settlement > 0 ? expectedGrossProfitUsd / settlement : -Infinity;
  return {
    expectedSettlementValueUsd: settlement,
    totalCostUsd,
    expectedGrossProfitUsd,
    contributionMarginRate,
    minimumContributionMarginRate: marginFloor,
    economicallyAdmissible: expectedGrossProfitUsd > 0 && contributionMarginRate + 1e-12 >= marginFloor,
  };
}

export function valueFirstProviderPreview({
  estimatedProviderSavingsUsd = 0,
  estimatedProviderRevenueUsd = 0,
  estimatedDccCreditValueUsd = 0,
  profilingCostToFederationUsd = 0,
  disclosure = {},
} = {}) {
  const savings = nonNegative(estimatedProviderSavingsUsd, 'estimatedProviderSavingsUsd');
  const revenue = nonNegative(estimatedProviderRevenueUsd, 'estimatedProviderRevenueUsd');
  const credit = nonNegative(estimatedDccCreditValueUsd, 'estimatedDccCreditValueUsd');
  const profilingCost = nonNegative(profilingCostToFederationUsd, 'profilingCostToFederationUsd');
  const providerEstimatedValueUsd = savings + revenue + credit;
  return {
    providerEstimatedValueUsd,
    federationProfilingCostUsd: profilingCost,
    netEstimatedMutualValueUsd: providerEstimatedValueUsd - profilingCost,
    disclosure: {
      estimateOnly: true,
      noOwnershipTransfer: true,
      noAutoEnrollmentWithoutAuthorization: true,
      ...disclosure,
    },
  };
}

export class ResourceAcquisitionEngine {
  constructor({ minimumContributionMarginRate = 0.10 } = {}) {
    this.minimumContributionMarginRate = boundedRate(minimumContributionMarginRate, 0.10);
    this.offers = new Map();
  }

  ingestOffer(offer) {
    validateResourceOffer(offer);
    if (this.offers.has(offer.offerId)) throw new Error(`duplicate offer: ${offer.offerId}`);
    const normalized = structuredClone(offer);
    normalized.receivedAt = normalized.receivedAt ?? new Date().toISOString();
    normalized.status = normalized.status ?? 'candidate';
    this.offers.set(normalized.offerId, normalized);
    return this.getOffer(normalized.offerId);
  }

  getOffer(offerId) {
    const offer = this.offers.get(offerId);
    return offer ? structuredClone(offer) : null;
  }

  evaluateOffer(offerId, {
    requestedUseClass = 'general-compute',
    valuePreview = null,
    economics = null,
  } = {}) {
    const offer = this.offers.get(offerId);
    if (!offer) throw new Error(`unknown offer: ${offerId}`);
    const use = classifyResourceUse(offer, requestedUseClass);
    const rights = offer.rights ?? {};
    const preview = valuePreview ?? valueFirstProviderPreview(offer.valueFirstPreview ?? {});
    const economicInput = economics ?? {
      expectedSettlementValueUsd: offer.economics.expectedSettlementValueUsd,
      providerAcquisitionCostUsd: offer.economics.providerAcquisitionCostUsd,
      operatorCostUsd: offer.economics.operatorCostUsd,
      verificationCostUsd: offer.economics.verificationCostUsd,
      riskProvisionUsd: offer.economics.riskProvisionUsd,
    };
    const unitEconomics = resourceAcquisitionEconomics({
      minimumContributionMarginRate: this.minimumContributionMarginRate,
      ...economicInput,
    });

    const eligibleForAutoEnrollment =
      use.ok &&
      unitEconomics.economicallyAdmissible &&
      rights.autoEnrollAllowed === true &&
      rights.preAuthorizedGrant === true &&
      preview.providerEstimatedValueUsd >= 0;

    const decision = {
      offerId,
      providerId: offer.providerId,
      requestedUseClass,
      use,
      unitEconomics,
      valueFirstPreview: preview,
      eligibleForAutoEnrollment,
      requiresExplicitAcceptance: !eligibleForAutoEnrollment,
      reasons: [
        ...(use.ok ? [] : [use.reason]),
        ...(unitEconomics.economicallyAdmissible ? [] : ['negative-or-insufficient-margin']),
        ...(rights.autoEnrollAllowed === true ? [] : ['auto-enroll-not-authorized']),
        ...(rights.preAuthorizedGrant === true ? [] : ['pre-authorized-grant-absent']),
      ],
    };
    return decision;
  }

  activateOffer(offerId, decision) {
    const offer = this.offers.get(offerId);
    if (!offer) throw new Error(`unknown offer: ${offerId}`);
    if (!decision?.eligibleForAutoEnrollment) throw new Error('offer cannot be auto-activated without an eligible decision');
    offer.status = 'active';
    offer.activatedAt = new Date().toISOString();
    return this.getOffer(offerId);
  }

  revokeOffer(offerId, reason = 'revoked') {
    const offer = this.offers.get(offerId);
    if (!offer) throw new Error(`unknown offer: ${offerId}`);
    offer.status = 'revoked';
    offer.revokedAt = new Date().toISOString();
    offer.revokeReason = String(reason);
    return this.getOffer(offerId);
  }

  list({ status = null } = {}) {
    return [...this.offers.values()].filter((offer) => !status || offer.status === status).map((offer) => structuredClone(offer));
  }
}

export const RESOURCE_ACQUISITION_DEFAULTS = Object.freeze({
  minimumContributionMarginRate: 0.10,
  sourceUseClasses: [...SOURCE_USE_CLASSES],
  compensationModes: [...COMPENSATION_MODES],
});
