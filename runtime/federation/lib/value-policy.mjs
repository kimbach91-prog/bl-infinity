const WORKLOAD_CLASSES = new Set(['S', 'H0', 'H1', 'H2', 'H3', 'H4', 'PGB']);
const SCOPES = new Set(['public', 'trusted', 'private', 'private-shared-benefit']);
const HARD_GATES = ['authorized', 'lawful', 'useful', 'bounded', 'revocable', 'verifiable', 'nonDeceptive', 'sovereign'];

const CLASS_PRIORITY = Object.freeze({ S: 1000, H0: 900, H1: 650, H2: 600, H3: 550, PGB: 500, H4: 300 });

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

export function scoreSharedBenefit(benefit = {}) {
  const positive =
    0.20 * clamp01(benefit.humanValue) +
    0.15 * clamp01(benefit.researchValue) +
    0.30 * clamp01(benefit.federationValue) +
    0.15 * clamp01(benefit.reusableValue) +
    0.20 * clamp01(benefit.verifiability);
  const burden = 0.60 * clamp01(benefit.privacyRisk) + 0.40 * clamp01(benefit.securityRisk);
  return Math.max(0, Math.min(1, positive - 0.35 * burden));
}

export function scoreExpectedUtility(dimensions = {}) {
  const positive =
    0.22 * clamp01(dimensions.humanValue) +
    0.18 * clamp01(dimensions.researchValue) +
    0.25 * clamp01(dimensions.federationValue) +
    0.12 * clamp01(dimensions.informationGain) +
    0.08 * clamp01(dimensions.urgency) +
    0.08 * clamp01(dimensions.fit) +
    0.07 * clamp01(dimensions.successProbability);
  const burden =
    0.25 * clamp01(dimensions.cost) +
    0.30 * clamp01(dimensions.securityRisk) +
    0.20 * clamp01(dimensions.privacyRisk) +
    0.10 * clamp01(dimensions.energyCarbon) +
    0.15 * clamp01(dimensions.opportunityCost);
  return positive - burden;
}

function assertSharedBenefitContract(policy, minimumScore) {
  const benefit = policy.sharedBenefit;
  if (!benefit || typeof benefit !== 'object') return { ok: false, reason: 'shared-benefit-contract-required' };
  if (!String(benefit.returnCommitment ?? '').trim()) return { ok: false, reason: 'shared-benefit-return-commitment-required' };
  if (!String(benefit.verificationMethod ?? '').trim()) return { ok: false, reason: 'shared-benefit-verification-required' };
  const score = scoreSharedBenefit(benefit);
  if (score < minimumScore) return { ok: false, reason: 'shared-benefit-score-too-low', sharedBenefitScore: score };
  return { ok: true, sharedBenefitScore: score };
}

export class ValuePolicyGovernor {
  constructor({
    commercialShareRate = 0.10,
    commonBenefitTargetRate = 0.05,
    commonBenefitMaxRate = 0.10,
    minSharedBenefitScore = 0.60,
  } = {}) {
    this.commercialShareRate = boundedRate(commercialShareRate, 0.10);
    this.commonBenefitTargetRate = boundedRate(commonBenefitTargetRate, 0.05, { max: 0.10 });
    this.commonBenefitMaxRate = boundedRate(commonBenefitMaxRate, 0.10, { max: 0.10 });
    this.minSharedBenefitScore = boundedRate(minSharedBenefitScore, 0.60);
    if (this.commonBenefitTargetRate > this.commonBenefitMaxRate) throw new Error('common-benefit target cannot exceed maximum');
  }

  admit(task) {
    const policy = task?.valuePolicy;
    if (!policy) return { ok: true, legacy: true, priority: 0, utility: null, commonBenefitEligible: false };

    const workloadClass = String(policy.workloadClass ?? task.workloadClass ?? '');
    const scope = String(policy.scope ?? 'public');
    if (!WORKLOAD_CLASSES.has(workloadClass)) return { ok: false, reason: 'invalid-workload-class' };
    if (!SCOPES.has(scope)) return { ok: false, reason: 'invalid-value-policy-scope' };

    const gates = policy.hardGates ?? {};
    const failedGate = HARD_GATES.find((gate) => gates[gate] !== true);
    if (failedGate) return { ok: false, reason: `hard-gate-failed:${failedGate}` };

    const commonBenefitRequested = policy.commonBenefitRequested === true || workloadClass === 'PGB';
    const needsSharedBenefit = scope === 'private-shared-benefit' || workloadClass === 'PGB' || (workloadClass === 'H4' && commonBenefitRequested);
    let sharedBenefitScore = null;
    if (needsSharedBenefit) {
      const shared = assertSharedBenefitContract(policy, this.minSharedBenefitScore);
      if (!shared.ok) return shared;
      sharedBenefitScore = shared.sharedBenefitScore;
    }

    if (commonBenefitRequested && workloadClass === 'H4' && sharedBenefitScore == null) {
      return { ok: false, reason: 'commercial-common-benefit-requires-shared-benefit' };
    }

    if (commonBenefitRequested && ['private', 'private-shared-benefit'].includes(scope) && sharedBenefitScore == null) {
      return { ok: false, reason: 'private-common-benefit-requires-shared-benefit' };
    }

    const utility = scoreExpectedUtility(policy.dimensions ?? {});
    const fairnessDebt = clamp01(policy.fairnessDebt);
    const founderBoost = policy.founderSponsored === true && commonBenefitRequested ? 25 : 0;
    const benefitBoost = sharedBenefitScore == null ? 0 : Math.round(sharedBenefitScore * 40);
    const utilityBoost = Math.round(utility * 100);
    const priority = CLASS_PRIORITY[workloadClass] + utilityBoost + benefitBoost + founderBoost - Math.round(fairnessDebt * 120);

    return {
      ok: true,
      legacy: false,
      workloadClass,
      scope,
      utility,
      sharedBenefitScore,
      commonBenefitRequested,
      commonBenefitEligible: commonBenefitRequested,
      priority,
    };
  }

  recommendedCommonBenefitRate({ spareCapacityRatio = 0, qualifiedBacklogRatio = 0, servicePressure = 0, providerCap = null } = {}) {
    const spare = clamp01(spareCapacityRatio);
    const backlog = clamp01(qualifiedBacklogRatio);
    const pressure = clamp01(servicePressure);
    const adaptive = this.commonBenefitTargetRate + (this.commonBenefitMaxRate - this.commonBenefitTargetRate) * Math.min(spare, backlog) * (1 - pressure);
    const cap = providerCap == null ? this.commonBenefitMaxRate : boundedRate(providerCap, this.commonBenefitMaxRate, { max: this.commonBenefitMaxRate });
    return Math.max(0, Math.min(adaptive, this.commonBenefitMaxRate, cap));
  }

  commonBenefitBudget({ eligibleComputeUnits, rate = null, providerCap = null, ...signals } = {}) {
    const units = Number(eligibleComputeUnits ?? 0);
    if (!Number.isFinite(units) || units < 0) throw new Error('eligibleComputeUnits must be a non-negative number');
    const selectedRate = rate == null
      ? this.recommendedCommonBenefitRate({ ...signals, providerCap })
      : Math.min(boundedRate(rate, this.commonBenefitTargetRate, { max: this.commonBenefitMaxRate }), providerCap == null ? this.commonBenefitMaxRate : boundedRate(providerCap, this.commonBenefitMaxRate, { max: this.commonBenefitMaxRate }));
    return { eligibleComputeUnits: units, rate: selectedRate, commonBenefitUnits: units * selectedRate };
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
  commonBenefitTargetRate: 0.05,
  commonBenefitMaxRate: 0.10,
  minSharedBenefitScore: 0.60,
});
