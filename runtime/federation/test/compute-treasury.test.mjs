import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeResourceValueUsd,
  verifiedEfficiencySurplus,
  valueFirstCommercialQuote,
  DeusComputeTreasury,
  COMPUTE_TREASURY_DEFAULTS,
} from '../lib/compute-treasury.mjs';

test('compute treasury defaults preserve 10% protocol share and conservative DCC backing', () => {
  assert.equal(COMPUTE_TREASURY_DEFAULTS.protocolCommercialShareRate, 0.10);
  assert.equal(COMPUTE_TREASURY_DEFAULTS.dccMinimumBackingRatio, 1.20);
});

test('heterogeneous resource vector can be valued against an explicit price vector', () => {
  const result = computeResourceValueUsd(
    { cpuCoreSeconds: 10, gpuNormalizedSeconds: 2, memoryGiBSeconds: 20, egressGiB: 1 },
    { cpuCoreSecond: 0.01, gpuNormalizedSecond: 1, memoryGiBSecond: 0.001, storageGiBHour: 0, egressGiB: 0.1, requestUnit: 0 },
  );
  assert.equal(result.totalUsd, 2.22);
});

test('verified efficiency surplus subtracts verification, switching and risk before calling savings real', () => {
  assert.deepEqual(verifiedEfficiencySurplus({
    baselineAllInCostUsd: 100,
    actualAllInCostUsd: 70,
    verificationCostUsd: 5,
    riskProvisionUsd: 5,
  }), {
    baselineAllInCostUsd: 100,
    netActualUsd: 80,
    verifiedEfficiencySurplusUsd: 20,
  });
});

test('value-first quote keeps customer savings while preserving the configured positive margin', () => {
  const quote = valueFirstCommercialQuote({
    baselineMarketPriceUsd: 100,
    providerAcquisitionCostUsd: 50,
    minimumGrossMarginRate: 0.10,
    intelligenceSurplusShareRate: 0.25,
  });
  assert.equal(quote.economicallyAdmissible, true);
  assert.ok(quote.quotedPriceUsd < 100);
  assert.ok(quote.customerSavingsUsd > 0);
  assert.ok(quote.grossMarginRate >= 0.10);
  assert.ok(quote.grossProfitUsd > 0);
});

test('DCC cannot be minted beyond verified backing at the minimum backing ratio', () => {
  const treasury = new DeusComputeTreasury({ dccMinimumBackingRatio: 1.20, dccReferenceUnitValueUsd: 1 });
  treasury.addBacking({ cashUsd: 120 });
  assert.equal(treasury.maximumDccOutstanding(), 100);
  treasury.mintDcc(100, { backingRef: 'cash:test' });
  assert.equal(treasury.dccStatus().backingRatio, 1.2);
  assert.throws(() => treasury.mintDcc(1), (error) => error.code === 'DCC_BACKING_INSUFFICIENT');
  treasury.burnDcc(20);
  assert.equal(treasury.dccStatus().dccOutstanding, 80);
});

test('protocol revenue, verified intelligence surplus and verified knowledge profit are booked separately', () => {
  const treasury = new DeusComputeTreasury();
  const protocol = treasury.commercialProtocolSettlement({ eligibleCommercialSettlementValueUsd: 100 });
  assert.equal(protocol.protocolRevenueUsd, 10);
  const efficiency = treasury.bookVerifiedEfficiencyProfit({ baselineAllInCostUsd: 100, actualAllInCostUsd: 70, verificationCostUsd: 5, riskProvisionUsd: 5 });
  assert.equal(efficiency.treasuryCapturedEfficiencyProfitUsd, 5);
  treasury.bookVerifiedKnowledgeProfit(7);
  const snapshot = treasury.snapshot();
  assert.equal(snapshot.realizedProtocolRevenueUsd, 10);
  assert.equal(snapshot.realizedEfficiencyProfitUsd, 5);
  assert.equal(snapshot.realizedKnowledgeProfitUsd, 7);
  assert.equal(snapshot.totalRealizedTreasuryRevenueUsd, 22);
});
