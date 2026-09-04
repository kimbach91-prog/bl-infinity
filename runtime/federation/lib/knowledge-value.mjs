function nonNegative(value, name) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${name} must be a non-negative number`);
  return number;
}

function rate(value, fallback = 0) {
  const number = Number(value ?? fallback);
  if (!Number.isFinite(number) || number < 0 || number > 1) throw new Error(`invalid rate: ${value}`);
  return number;
}

function sumValues(object = {}) {
  return Object.values(object).reduce((sum, value) => sum + nonNegative(value, 'value component'), 0);
}

export function expectedDamage(scenarios = []) {
  if (!Array.isArray(scenarios)) throw new Error('scenarios must be an array');
  return scenarios.reduce((total, scenario, index) => {
    const probability = rate(scenario?.probability, 0);
    const directImpactUsd = nonNegative(scenario?.directImpactUsd, `scenario[${index}].directImpactUsd`);
    const recoveryCostUsd = nonNegative(scenario?.recoveryCostUsd, `scenario[${index}].recoveryCostUsd`);
    const downtimeCostUsd = nonNegative(scenario?.downtimeCostUsd, `scenario[${index}].downtimeCostUsd`);
    const secondaryImpactUsd = nonNegative(scenario?.secondaryImpactUsd, `scenario[${index}].secondaryImpactUsd`);
    return total + probability * (directImpactUsd + recoveryCostUsd + downtimeCostUsd + secondaryImpactUsd);
  }, 0);
}

export function counterfactualAvoidedDamage({ before = [], after = [] } = {}) {
  const expectedBeforeUsd = expectedDamage(before);
  const expectedAfterUsd = expectedDamage(after);
  const avoidedDamageUsd = Math.max(0, expectedBeforeUsd - expectedAfterUsd);
  return { expectedBeforeUsd, expectedAfterUsd, avoidedDamageUsd };
}

export function knowledgeEvidenceMultiplier({
  confidence = 0,
  evidenceQuality = 0,
  reproducibility = 0,
  adoptionProbability = 0,
  transferability = 0,
  durability = 0,
} = {}) {
  const core = [confidence, evidenceQuality, reproducibility, adoptionProbability].map((x) => rate(x));
  const geometricCore = Math.pow(core.reduce((product, x) => product * x, 1), 1 / core.length);
  const transferModifier = 0.5 + 0.5 * rate(transferability);
  const durabilityModifier = 0.5 + 0.5 * rate(durability);
  return geometricCore * transferModifier * durabilityModifier;
}

export function valueKnowledge({
  realized = {},
  expected = {},
  costs = {},
  quality = {},
  overlapAdjustmentUsd = 0,
} = {}) {
  const realizedGrossUsd = sumValues(realized);
  const expectedGrossUsd = Math.max(0, sumValues(expected) - nonNegative(overlapAdjustmentUsd, 'overlapAdjustmentUsd'));
  const evidenceMultiplier = knowledgeEvidenceMultiplier(quality);
  const expectedRiskAdjustedUsd = expectedGrossUsd * evidenceMultiplier;
  const totalCostsUsd = sumValues(costs);
  const realizedNetUsd = Math.max(0, realizedGrossUsd - totalCostsUsd);
  const totalRiskAdjustedValueUsd = Math.max(0, realizedGrossUsd + expectedRiskAdjustedUsd - totalCostsUsd);

  return {
    realizedGrossUsd,
    expectedGrossUsd,
    evidenceMultiplier,
    expectedRiskAdjustedUsd,
    totalCostsUsd,
    realizedNetUsd,
    totalRiskAdjustedValueUsd,
    bookedRealizedValueUsd: realizedNetUsd,
    unbookedExpectedOptionValueUsd: Math.max(0, totalRiskAdjustedValueUsd - realizedNetUsd),
  };
}

export function damageGroundedKnowledgeSettlement({
  verifiedRealizedValueUsd,
  successFeeRate = 0.20,
  minimumFeeUsd = 0,
  maximumFeeUsd = Infinity,
} = {}) {
  const verified = nonNegative(verifiedRealizedValueUsd, 'verifiedRealizedValueUsd');
  const feeRate = rate(successFeeRate, 0.20);
  const floor = nonNegative(minimumFeeUsd, 'minimumFeeUsd');
  const cap = maximumFeeUsd === Infinity ? Infinity : nonNegative(maximumFeeUsd, 'maximumFeeUsd');
  const fee = Math.min(cap, Math.max(floor, verified * feeRate));
  return {
    verifiedRealizedValueUsd: verified,
    successFeeRate: feeRate,
    knowledgeFeeUsd: fee,
    valueRetainedByBeneficiaryUsd: Math.max(0, verified - fee),
  };
}

export function realizedLearningProfit({
  baselineUnitCostUsd = 0,
  improvedUnitCostUsd = 0,
  units = 0,
  baselineExpectedLossUsd = 0,
  improvedExpectedLossUsd = 0,
  realizedRevenueUpliftUsd = 0,
  learningImplementationCostUsd = 0,
} = {}) {
  const baselineUnit = nonNegative(baselineUnitCostUsd, 'baselineUnitCostUsd');
  const improvedUnit = nonNegative(improvedUnitCostUsd, 'improvedUnitCostUsd');
  const n = nonNegative(units, 'units');
  const costSavingsUsd = Math.max(0, baselineUnit - improvedUnit) * n;
  const lossReductionUsd = Math.max(0, nonNegative(baselineExpectedLossUsd, 'baselineExpectedLossUsd') - nonNegative(improvedExpectedLossUsd, 'improvedExpectedLossUsd'));
  const revenueUpliftUsd = nonNegative(realizedRevenueUpliftUsd, 'realizedRevenueUpliftUsd');
  const implementationCostUsd = nonNegative(learningImplementationCostUsd, 'learningImplementationCostUsd');
  const grossLearningValueUsd = costSavingsUsd + lossReductionUsd + revenueUpliftUsd;
  const realizedLearningProfitUsd = Math.max(0, grossLearningValueUsd - implementationCostUsd);
  return { costSavingsUsd, lossReductionUsd, revenueUpliftUsd, implementationCostUsd, grossLearningValueUsd, realizedLearningProfitUsd };
}

export function projectSupercompoundingLearning({
  horizonPeriods = 12,
  startingRealizedProfitUsd = 0,
  reusableKnowledgeValuePerPeriodUsd = 0,
  knowledgeRetentionRate = 0.95,
  workloadGrowthRate = 0,
  futureKnowledgeOpportunityValuePerPeriodUsd = 0,
  metaLearningRateImprovement = 0,
  treasuryReinvestmentRate = 0.50,
  computeGrossReturnRate = 0.10,
  discountRate = 0.02,
} = {}) {
  const periods = Number(horizonPeriods);
  if (!Number.isSafeInteger(periods) || periods < 1 || periods > 1200) throw new Error('horizonPeriods must be an integer between 1 and 1200');

  let treasuryCapitalUsd = nonNegative(startingRealizedProfitUsd, 'startingRealizedProfitUsd');
  const reusableBase = nonNegative(reusableKnowledgeValuePerPeriodUsd, 'reusableKnowledgeValuePerPeriodUsd');
  const opportunityBase = nonNegative(futureKnowledgeOpportunityValuePerPeriodUsd, 'futureKnowledgeOpportunityValuePerPeriodUsd');
  const retention = rate(knowledgeRetentionRate, 0.95);
  const growth = rate(workloadGrowthRate, 0);
  const metaRate = rate(metaLearningRateImprovement, 0);
  const reinvestRate = rate(treasuryReinvestmentRate, 0.50);
  const computeReturnRate = rate(computeGrossReturnRate, 0.10);
  const discount = rate(discountRate, 0.02);

  const periodsOut = [];
  let npvProjectedIncrementalValueUsd = 0;

  for (let t = 1; t <= periods; t += 1) {
    const retentionFactor = Math.pow(retention, t - 1);
    const workloadFactor = Math.pow(1 + growth, t - 1);
    const reuseDividendUsd = reusableBase * retentionFactor * workloadFactor;
    const metaLearningDividendUsd = opportunityBase * metaRate * retentionFactor * workloadFactor;
    const reinvestedUsd = treasuryCapitalUsd * reinvestRate;
    const computeReinvestmentDividendUsd = reinvestedUsd * computeReturnRate;
    const projectedIncrementalValueUsd = reuseDividendUsd + metaLearningDividendUsd + computeReinvestmentDividendUsd;
    const discountFactor = Math.pow(1 + discount, t);
    const presentValueUsd = projectedIncrementalValueUsd / discountFactor;
    npvProjectedIncrementalValueUsd += presentValueUsd;
    treasuryCapitalUsd += projectedIncrementalValueUsd;
    periodsOut.push({
      period: t,
      reuseDividendUsd,
      metaLearningDividendUsd,
      reinvestedUsd,
      computeReinvestmentDividendUsd,
      projectedIncrementalValueUsd,
      presentValueUsd,
      projectedTreasuryCapitalUsd: treasuryCapitalUsd,
    });
  }

  return {
    horizonPeriods: periods,
    npvProjectedIncrementalValueUsd,
    projectedEndingTreasuryCapitalUsd: treasuryCapitalUsd,
    periods: periodsOut,
    classification: 'PROJECTED_NOT_REALIZED',
  };
}
