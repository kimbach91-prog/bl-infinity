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

function positive(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new Error(`${name} must be > 0`);
  return number;
}

function round(value, digits = 8) {
  const factor = 10 ** digits;
  return Math.round((Number(value) + Number.EPSILON) * factor) / factor;
}

export const DEFAULT_COMPUTE_PRICE_VECTOR_USD = Object.freeze({
  cpuCoreSecond: 0,
  gpuNormalizedSecond: 0,
  memoryGiBSecond: 0,
  storageGiBHour: 0,
  egressGiB: 0,
  requestUnit: 0,
});

export function computeResourceValueUsd(resource = {}, priceVector = DEFAULT_COMPUTE_PRICE_VECTOR_USD) {
  const units = {
    cpuCoreSecond: nonNegative(resource.cpuCoreSeconds, 'cpuCoreSeconds'),
    gpuNormalizedSecond: nonNegative(resource.gpuNormalizedSeconds, 'gpuNormalizedSeconds'),
    memoryGiBSecond: nonNegative(resource.memoryGiBSeconds, 'memoryGiBSeconds'),
    storageGiBHour: nonNegative(resource.storageGiBHours, 'storageGiBHours'),
    egressGiB: nonNegative(resource.egressGiB, 'egressGiB'),
    requestUnit: nonNegative(resource.requestUnits, 'requestUnits'),
  };
  const components = Object.fromEntries(Object.entries(units).map(([key, unit]) => {
    const price = nonNegative(priceVector[key], `priceVector.${key}`);
    return [key, unit * price];
  }));
  return { units, componentsUsd: components, totalUsd: Object.values(components).reduce((sum, x) => sum + x, 0) };
}

export function verifiedEfficiencySurplus({
  baselineAllInCostUsd,
  actualAllInCostUsd,
  verificationCostUsd = 0,
  switchingCostUsd = 0,
  riskProvisionUsd = 0,
} = {}) {
  const baseline = nonNegative(baselineAllInCostUsd, 'baselineAllInCostUsd');
  const actual = nonNegative(actualAllInCostUsd, 'actualAllInCostUsd');
  const verification = nonNegative(verificationCostUsd, 'verificationCostUsd');
  const switching = nonNegative(switchingCostUsd, 'switchingCostUsd');
  const risk = nonNegative(riskProvisionUsd, 'riskProvisionUsd');
  const netActualUsd = actual + verification + switching + risk;
  return {
    baselineAllInCostUsd: baseline,
    netActualUsd,
    verifiedEfficiencySurplusUsd: Math.max(0, baseline - netActualUsd),
  };
}

export function valueFirstCommercialQuote({
  baselineMarketPriceUsd,
  providerAcquisitionCostUsd,
  operatorCostUsd = 0,
  verificationCostUsd = 0,
  riskProvisionUsd = 0,
  minimumGrossMarginRate = 0.10,
  intelligenceSurplusShareRate = 0.25,
  maximumOfferPriceUsd = Infinity,
} = {}) {
  const baseline = nonNegative(baselineMarketPriceUsd, 'baselineMarketPriceUsd');
  const acquisition = nonNegative(providerAcquisitionCostUsd, 'providerAcquisitionCostUsd');
  const operator = nonNegative(operatorCostUsd, 'operatorCostUsd');
  const verification = nonNegative(verificationCostUsd, 'verificationCostUsd');
  const risk = nonNegative(riskProvisionUsd, 'riskProvisionUsd');
  const marginRate = boundedRate(minimumGrossMarginRate, 0.10);
  const intelligenceRate = boundedRate(intelligenceSurplusShareRate, 0.25);
  const cap = maximumOfferPriceUsd === Infinity ? Infinity : nonNegative(maximumOfferPriceUsd, 'maximumOfferPriceUsd');

  const allInCostUsd = acquisition + operator + verification + risk;
  const minimumPriceForMarginUsd = marginRate >= 1 ? Infinity : allInCostUsd / (1 - marginRate);
  const surplusAboveMarginFloorUsd = Math.max(0, baseline - minimumPriceForMarginUsd);
  const intelligenceFeeUsd = surplusAboveMarginFloorUsd * intelligenceRate;
  const quotedPriceUsd = Math.min(cap, baseline, minimumPriceForMarginUsd + intelligenceFeeUsd);
  const grossProfitUsd = Math.max(0, quotedPriceUsd - allInCostUsd);
  const grossMarginRate = quotedPriceUsd > 0 ? grossProfitUsd / quotedPriceUsd : 0;
  const customerSavingsUsd = Math.max(0, baseline - quotedPriceUsd);
  const economicallyAdmissible = quotedPriceUsd >= minimumPriceForMarginUsd && quotedPriceUsd <= baseline && grossMarginRate + 1e-12 >= marginRate;

  return {
    baselineMarketPriceUsd: baseline,
    allInCostUsd,
    minimumGrossMarginRate: marginRate,
    minimumPriceForMarginUsd,
    surplusAboveMarginFloorUsd,
    intelligenceSurplusShareRate: intelligenceRate,
    intelligenceFeeUsd,
    quotedPriceUsd,
    customerSavingsUsd,
    grossProfitUsd,
    grossMarginRate,
    economicallyAdmissible,
    principle: 'VALUE_FIRST_POSITIVE_MARGIN',
  };
}

export class DeusComputeTreasury {
  constructor({
    protocolCommercialShareRate = 0.10,
    intelligenceSurplusShareRate = 0.25,
    minimumGrossMarginRate = 0.10,
    dccMinimumBackingRatio = 1.20,
    dccReferenceUnitValueUsd = 1,
  } = {}) {
    this.protocolCommercialShareRate = boundedRate(protocolCommercialShareRate, 0.10);
    this.intelligenceSurplusShareRate = boundedRate(intelligenceSurplusShareRate, 0.25);
    this.minimumGrossMarginRate = boundedRate(minimumGrossMarginRate, 0.10);
    this.dccMinimumBackingRatio = positive(dccMinimumBackingRatio, 'dccMinimumBackingRatio');
    if (this.dccMinimumBackingRatio < 1) throw new Error('dccMinimumBackingRatio must be >= 1');
    this.dccReferenceUnitValueUsd = positive(dccReferenceUnitValueUsd, 'dccReferenceUnitValueUsd');
    this.cashBackingUsd = 0;
    this.committedComputeBackingUsd = 0;
    this.reservedLiabilitiesUsd = 0;
    this.dccOutstanding = 0;
    this.realizedProtocolRevenueUsd = 0;
    this.realizedEfficiencyProfitUsd = 0;
    this.realizedKnowledgeProfitUsd = 0;
  }

  addBacking({ cashUsd = 0, committedComputeValueUsd = 0 } = {}) {
    this.cashBackingUsd += nonNegative(cashUsd, 'cashUsd');
    this.committedComputeBackingUsd += nonNegative(committedComputeValueUsd, 'committedComputeValueUsd');
    return this.snapshot();
  }

  setReservedLiabilitiesUsd(value) {
    this.reservedLiabilitiesUsd = nonNegative(value, 'reservedLiabilitiesUsd');
    return this.snapshot();
  }

  availableBackingUsd() {
    return Math.max(0, this.cashBackingUsd + this.committedComputeBackingUsd - this.reservedLiabilitiesUsd);
  }

  dccLiabilityUsd() {
    return this.dccOutstanding * this.dccReferenceUnitValueUsd;
  }

  backingRatio() {
    const liability = this.dccLiabilityUsd();
    return liability <= 0 ? Infinity : this.availableBackingUsd() / liability;
  }

  maximumDccOutstanding() {
    return this.availableBackingUsd() / (this.dccReferenceUnitValueUsd * this.dccMinimumBackingRatio);
  }

  mintDcc(amount, { backingRef = null } = {}) {
    const units = nonNegative(amount, 'amount');
    const nextOutstanding = this.dccOutstanding + units;
    const maximum = this.maximumDccOutstanding();
    if (nextOutstanding > maximum + 1e-12) {
      const error = new Error('DCC mint would breach minimum backing ratio');
      error.code = 'DCC_BACKING_INSUFFICIENT';
      error.maximumDccOutstanding = maximum;
      throw error;
    }
    this.dccOutstanding = nextOutstanding;
    return { mintedDcc: units, backingRef, ...this.dccStatus() };
  }

  burnDcc(amount, { reason = 'redeemed' } = {}) {
    const units = nonNegative(amount, 'amount');
    if (units > this.dccOutstanding + 1e-12) throw new Error('cannot burn more DCC than outstanding');
    this.dccOutstanding = Math.max(0, this.dccOutstanding - units);
    return { burnedDcc: units, reason, ...this.dccStatus() };
  }

  commercialProtocolSettlement({ eligibleCommercialSettlementValueUsd } = {}) {
    const ecsv = nonNegative(eligibleCommercialSettlementValueUsd, 'eligibleCommercialSettlementValueUsd');
    const protocolRevenueUsd = round(ecsv * this.protocolCommercialShareRate, 6);
    this.realizedProtocolRevenueUsd += protocolRevenueUsd;
    return {
      eligibleCommercialSettlementValueUsd: ecsv,
      protocolCommercialShareRate: this.protocolCommercialShareRate,
      protocolRevenueUsd,
      remainderBeforeOtherSettlementRulesUsd: round(ecsv - protocolRevenueUsd, 6),
    };
  }

  bookVerifiedEfficiencyProfit(input = {}) {
    const surplus = verifiedEfficiencySurplus(input);
    const capturedUsd = surplus.verifiedEfficiencySurplusUsd * this.intelligenceSurplusShareRate;
    this.realizedEfficiencyProfitUsd += capturedUsd;
    return { ...surplus, intelligenceSurplusShareRate: this.intelligenceSurplusShareRate, treasuryCapturedEfficiencyProfitUsd: capturedUsd };
  }

  bookVerifiedKnowledgeProfit(verifiedProfitUsd) {
    const amount = nonNegative(verifiedProfitUsd, 'verifiedProfitUsd');
    this.realizedKnowledgeProfitUsd += amount;
    return { bookedKnowledgeProfitUsd: amount, realizedKnowledgeProfitUsd: this.realizedKnowledgeProfitUsd };
  }

  quoteValueFirst(input = {}) {
    return valueFirstCommercialQuote({
      minimumGrossMarginRate: this.minimumGrossMarginRate,
      intelligenceSurplusShareRate: this.intelligenceSurplusShareRate,
      ...input,
    });
  }

  dccStatus() {
    return {
      dccOutstanding: this.dccOutstanding,
      dccReferenceUnitValueUsd: this.dccReferenceUnitValueUsd,
      dccLiabilityUsd: this.dccLiabilityUsd(),
      dccMinimumBackingRatio: this.dccMinimumBackingRatio,
      backingRatio: this.backingRatio(),
      maximumDccOutstanding: this.maximumDccOutstanding(),
      availableBackingUsd: this.availableBackingUsd(),
    };
  }

  snapshot() {
    return {
      cashBackingUsd: this.cashBackingUsd,
      committedComputeBackingUsd: this.committedComputeBackingUsd,
      reservedLiabilitiesUsd: this.reservedLiabilitiesUsd,
      realizedProtocolRevenueUsd: this.realizedProtocolRevenueUsd,
      realizedEfficiencyProfitUsd: this.realizedEfficiencyProfitUsd,
      realizedKnowledgeProfitUsd: this.realizedKnowledgeProfitUsd,
      totalRealizedTreasuryRevenueUsd: this.realizedProtocolRevenueUsd + this.realizedEfficiencyProfitUsd + this.realizedKnowledgeProfitUsd,
      ...this.dccStatus(),
    };
  }
}

export const COMPUTE_TREASURY_DEFAULTS = Object.freeze({
  protocolCommercialShareRate: 0.10,
  intelligenceSurplusShareRate: 0.25,
  minimumGrossMarginRate: 0.10,
  dccMinimumBackingRatio: 1.20,
  dccReferenceUnitValueUsd: 1,
});
