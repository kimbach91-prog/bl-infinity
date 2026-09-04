import test from 'node:test';
import assert from 'node:assert/strict';
import {
  expectedDamage,
  counterfactualAvoidedDamage,
  knowledgeEvidenceMultiplier,
  valueKnowledge,
  damageGroundedKnowledgeSettlement,
  realizedLearningProfit,
  projectSupercompoundingLearning,
} from '../lib/knowledge-value.mjs';

test('counterfactual damage is probability-weighted and only positive reduction is counted', () => {
  const before = [{ probability: 0.2, directImpactUsd: 1000 }];
  const after = [{ probability: 0.05, directImpactUsd: 1000 }];
  assert.equal(expectedDamage(before), 200);
  assert.deepEqual(counterfactualAvoidedDamage({ before, after }), {
    expectedBeforeUsd: 200,
    expectedAfterUsd: 50,
    avoidedDamageUsd: 150,
  });
});

test('knowledge value separates booked realized value from discounted expected option value', () => {
  const result = valueKnowledge({
    realized: { computeSavingsUsd: 60, revenueUpliftUsd: 40 },
    expected: { avoidedLossUsd: 100 },
    costs: { implementationUsd: 10, verificationUsd: 10 },
    quality: { confidence: 1, evidenceQuality: 1, reproducibility: 1, adoptionProbability: 1, transferability: 1, durability: 1 },
  });
  assert.equal(result.realizedGrossUsd, 100);
  assert.equal(result.expectedRiskAdjustedUsd, 100);
  assert.equal(result.realizedNetUsd, 80);
  assert.equal(result.totalRiskAdjustedValueUsd, 180);
  assert.equal(result.bookedRealizedValueUsd, 80);
  assert.equal(result.unbookedExpectedOptionValueUsd, 100);
});

test('weak evidence collapses expected knowledge multiplier instead of minting value from confidence claims', () => {
  assert.equal(knowledgeEvidenceMultiplier({ confidence: 1, evidenceQuality: 1, reproducibility: 0, adoptionProbability: 1, transferability: 1, durability: 1 }), 0);
});

test('knowledge success fee is grounded only in verified realized value', () => {
  assert.deepEqual(damageGroundedKnowledgeSettlement({ verifiedRealizedValueUsd: 2000, successFeeRate: 0.2 }), {
    verifiedRealizedValueUsd: 2000,
    successFeeRate: 0.2,
    knowledgeFeeUsd: 400,
    valueRetainedByBeneficiaryUsd: 1600,
  });
});

test('realized learning profit counts measured cost, loss and revenue deltas net of implementation cost', () => {
  assert.deepEqual(realizedLearningProfit({
    baselineUnitCostUsd: 10,
    improvedUnitCostUsd: 8,
    units: 10,
    baselineExpectedLossUsd: 100,
    improvedExpectedLossUsd: 70,
    realizedRevenueUpliftUsd: 10,
    learningImplementationCostUsd: 5,
  }), {
    costSavingsUsd: 20,
    lossReductionUsd: 30,
    revenueUpliftUsd: 10,
    implementationCostUsd: 5,
    grossLearningValueUsd: 60,
    realizedLearningProfitUsd: 55,
  });
});

test('supercompounding model labels future value as projected, never realized', () => {
  const result = projectSupercompoundingLearning({
    horizonPeriods: 2,
    startingRealizedProfitUsd: 100,
    reusableKnowledgeValuePerPeriodUsd: 10,
    knowledgeRetentionRate: 1,
    workloadGrowthRate: 0,
    futureKnowledgeOpportunityValuePerPeriodUsd: 100,
    metaLearningRateImprovement: 0.1,
    treasuryReinvestmentRate: 0.5,
    computeGrossReturnRate: 0.1,
    discountRate: 0,
  });
  assert.equal(result.classification, 'PROJECTED_NOT_REALIZED');
  assert.equal(result.periods[0].projectedIncrementalValueUsd, 25);
  assert.equal(result.periods[0].projectedTreasuryCapitalUsd, 125);
  assert.ok(result.projectedEndingTreasuryCapitalUsd > 125);
  assert.ok(result.npvProjectedIncrementalValueUsd > 25);
});
