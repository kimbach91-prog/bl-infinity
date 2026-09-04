const WORKLOAD_CLASSES = new Set(['S', 'H0', 'H1', 'H2', 'H3', 'H4', 'PGB', 'PFR']);
const SCOPES = new Set(['public', 'trusted', 'private', 'private-shared-benefit', 'private-federation-return']);
const HARD_GATES = ['authorized', 'lawful', 'useful', 'bounded', 'revocable', 'verifiable', 'nonDeceptive', 'sovereign'];

const CLASS_PRIORITY = Object.freeze({ S: 1000, H0: 900, H1: 650, H2: 600, H3: 550, PGB: 500, PFR: 500, H4: 300 });

function clamp01(value) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return 0;
  return Math.min(1, Math.max(0, number));
}

function boundedRate(value, fallback, { max = 1 } = {}) {
  const number = Number(value ?? fallback);
  if (!Number.isFinite(number) || number < 0 || number > max) throw new Error(`invalid rate: ${value}`);
  return number;
}

function roundMoney(value) { return Math.round((Number(value) + Number.EPSILON) * 1e6) / 1e6; }

export function scoreFederationReturn(benefit = {}) {
  const positive =
    0.10 * clamp01(benefit.humanValue) +
    0.10 * clamp01(benefit.researchValue) +
    0.40 * clamp01(benefit.federationValue) +
    0.15 * clamp01(benefit.reusableValue) +
    0.15 * clamp01(benefit.verifiability) +
    0.10 * clamp01(benefit.revenueOrComputeReturn);
  const burden = 0.55 * clamp01(benefit.privacyRisk) + 0.45 * clamp01(benefit.securityRisk);
  return Math.max(0, Math.min(1, positive - 0.35 * burden));
}

// Backward-compatible export. v0.4 canonical term is Federation Return / Strategic Reinvestment.
export const scoreSharedBenefit = scoreFederationReturn;

export function scoreExpectedUtility(dimensions = {}) {
  const positive =
    0.10 * clamp01(dimensions.humanValue) +
    0.10 * clamp01(dimensions.researchValue) +
    0.35 * clamp01(dimensions.federationValue) +
    0.12 * clamp01(dimensions.informationGain) +
    0.08 * clamp01(dimensions.urgency) +
    0.08 * clamp01(dimensions.fit) +
    0.07 * clamp01(dimensions.successProbability) +
    0.10 * clamp01(dimensions.revenueOrComputeReturn);
  const burden =
    0.25 * clamp01(dimensions.cost) +
    0.30 * clamp01(dimensions.securityRisk) +
    0.20 * clamp01(dimensions.privacyRisk) +
    0.10 * clamp01(dimensions.energyCarbon) +
    0.15 * clamp01(dimensions.opportunityCost);
  return positive - burden;
}

function getFederationReturnContract(policy) {
  return policy.federationReturn ?? policy.sharedBenefit ?? null;
}

function assertFederationReturnContract(policy, minimumScore) {
  const benefit = getFederationReturnContract(policy);
  if (!benefit || typeof benefit !== 'object') return { ok: false, reason: 'shared-benefit-contract-required' };
  if (!String(benefit.returnCommitment ?? '').trim()) return { ok: false, reason: 'shared-benefit-return-commitment-required' };
  if (!String(benefit.verificationMethod ?? '').trim()) return { ok: false, reason: 'shared-benefit-verification-required' };
  const score = scoreFederationReturn(benefit);
  if (score < minimumScore) return { ok: false, reason: 'shared-benefit-score-too-low', sharedBenefitScore: score, federationReturnScore: score };
  return { ok: true, sharedBenefitScore: score, federationReturnScore: score };
}

export class ValuePolicyGovernor {
  constructor({
    commercialShareRate = 0.10,
    commonBenefitTargetRate = 0.05,
    commonBenefitMaxRate = 0.10,
    strategicReinvestmentTargetRate = commonBenefitTargetRate,
    strategicReinvestmentMaxRate = commonBenefitMaxRate,
    minSharedBenefitScore = 0.60,
    minFederationReturnScore = minSharedBenefitScore,
  } = {}) {
    this.commercialShareRate = boundedRate(commercialShareRate, 0.10);
    this.strategicReinvestmentTargetRate = boundedRate(strategicReinvestmentTargetRate, 0.05, { max: 0.10 });
    this.strategicReinvestmentMaxRate = boundedRate(strategicReinvestmentMaxRate, 0.10, { max: 0.10 });
    this.minFederationReturnScore = boundedRate(minFederationReturnScore, 0.60);
    if (this.strategicReinvestmentTargetRate > this.strategicReinvestmentMaxRate) throw new Error('strategic-reinvestment target cannot exceed maximum');

    // Compatibility properties retained for v0.3 callers.
    this.commonBenefitTargetRate = this.strategicReinvestmentTargetRate;
    this.commonBenefitMaxRate = this.strategicReinvestmentMaxRate;
    this.minSharedBenefitScore = this.minFederationReturnScore;
  }

  admit(task) {
    const policy = task?.valuePolicy;
    if (!policy) {
      return {
        ok: true,
        legacy: true,
        priority: 0,
        utility: null,
        strategicReinvestmentEligible: false,
        commonBenefitEligible: false,
      };
    }

    const workloadClass = String(policy.workloadClass ?? task.workloadClass ?? '');
    const scope = String(policy.scope ?? 'public');
    if (!WORKLOAD_CLASSES.has(workloadClass)) return { ok: false, reason: 'invalid-workload-class' };
    if (!SCOPES.has(scope)) return { ok: false, reason: 'invalid-value-policy-scope' };

    const gates = policy.hardGates ?? {};
    const failedGate = HARD_GATES.find((gate) => gates[gate] !== true);
    if (failedGate) return { ok: false, reason: `hard-gate-failed:${failedGate}` };

    const strategicReinvestmentRequested =
      policy.strategicReinvestmentRequested === true ||
      policy.commonBenefitRequested === true ||
      workloadClass === 'PGB' ||
      workloadClass === 'PFR';

    const privateFederationReturn =
      scope === 'private-federation-return' ||
      scope === 'private-shared-benefit' ||
      workloadClass === 'PGB' ||
      workloadClass === 'PFR';

    const needsFederationReturn = privateFederationReturn || (workloadClass === 'H4' && strategicReinvestmentRequested);
    let federationReturnScore = null;
    if (needsFederationReturn) {
      const returned = assertFederationReturnContract(policy, this.minFederationReturnScore);
      if (!returned.ok) return returned;
      federationReturnScore = returned.federationReturnScore;
    }

    if (strategicReinvestmentRequested && workloadClass === 'H4' && federationReturnScore == null) {
      return { ok: false, reason: 'commercial-common-benefit-requires-shared-benefit' };
    }

    if (strategicReinvestmentRequested && ['private', 'private-shared-benefit', 'private-federation-return'].includes(scope) && federationReturnScore == null) {
      return { ok: false, reason: 'private-common-benefit-requires-shared-benefit' };
    }

    const utility = scoreExpectedUtility(policy.dimensions ?? {});
    const fairnessDebt = clamp01(policy.fairnessDebt);
    const founderBoost = policy.founderSponsored === true && strategicReinvestmentRequested ? 25 : 0;
    const returnBoost = federationReturnScore == null ? 0 : Math.round(federationReturnScore * 40);
    const utilityBoost = Math.round(utility * 100);
    const priority = CLASS_PRIORITY[workloadClass] + utilityBoost + returnBoost + founderBoost - Math.round(fairnessDebt * 120);

    return {
      ok: true,
      legacy: false,
      workloadClass,
      scope,
      utility,
      federationReturnScore,
      sharedBenefitScore: federationReturnScore,
      strategicReinvestmentRequested,
      strategicReinvestmentEligible: strategicReinvestmentRequested,
      commonBenefitRequested: strategicReinvestmentRequested,
      commonBenefitEligible: strategicReinvestmentRequested,
      priority,
    };
  }

  recommendedStrategicReinvestmentRate({ spareCapacityRatio = 0, qualifiedBacklogRatio = 0, servicePressure = 0, providerCap = null } = {}) {
    const spare = clamp01(spareCapacityRatio);
    const backlog = clamp01(qualifiedBacklogRatio);
    const pressure = clamp01(servicePressure);
    const adaptive = this.strategicReinvestmentTargetRate +
      (this.strategicReinvestmentMaxRate - this.strategicReinvestmentTargetRate) * Math.min(spare, backlog) * (1 - pressure);
    const cap = providerCap == null
      ? this.strategicReinvestmentMaxRate
      : boundedRate(providerCap, this.strategicReinvestmentMaxRate, { max: this.strategicReinvestmentMaxRate });
    return Math.max(0, Math.min(adaptive, this.strategicReinvestmentMaxRate, cap));
  }

  strategicReinvestmentBudget({ eligibleComputeUnits, rate = null, providerCap = null, ...signals } = {}) {
    const units = Number(eligibleComputeUnits ?? 0);
    if (!Number.isFinite(units) || units < 0) throw new Error('eligibleComputeUnits must be a non-negative number');
    const selectedRate = rate == null
      ? this.recommendedStrategicReinvestmentRate({ ...signals, providerCap })
      : Math.min(
        boundedRate(rate, this.strategicReinvestmentTargetRate, { max: this.strategicReinvestmentMaxRate }),
        providerCap == null ? this.strategicReinvestmentMaxRate : boundedRate(providerCap, this.strategicReinvestmentMaxRate, { max: this.strategicReinvestmentMaxRate }),
      );
    return {
      eligibleComputeUnits: units,
      rate: selectedRate,
      strategicReinvestmentUnits: units * selectedRate,
      commonBenefitUnits: units * selectedRate,
    };
  }

  // v0.3 compatibility aliases.
  recommendedCommonBenefitRate(signals = {}) {
    return this.recommendedStrategicReinvestmentRate(signals);
  }

  commonBenefitBudget(input = {}) {
    return this.strategicReinvestmentBudget(input);
  }

  commercialSettlement({ eligibleCommercialSettlementValue } = {}) {
    const ecsv = Number(eligibleCommercialSettlementValue ?? 0);
    if (!Number.isFinite(ecsv) || ecsv < 0) throw new Error('eligibleCommercialSettlementValue must be a non-negative number');
    const officialProtocolShare = roundMoney(ecsv * this.commercialShareRate);
    return {
      eligibleCommercialSettlementValue: ecsv,
      commercialShareRate: this.commercialShareRate,
      officialProtocolShare,
      remainderBeforeOtherSettlementRules: roundMoney(ecsv - officialProtocolShare),
    };
  }
}

export const VALUE_POLICY_DEFAULTS = Object.freeze({
  commercialShareRate: 0.10,
  strategicReinvestmentTargetRate: 0.05,
  strategicReinvestmentMaxRate: 0.10,
  minFederationReturnScore: 0.60,
  // Compatibility keys retained for existing callers/tests.
  commonBenefitTargetRate: 0.05,
  commonBenefitMaxRate: 0.10,
  minSharedBenefitScore: 0.60,
});
