const DEFAULT_THRESHOLDS = Object.freeze({
  maxSingleProviderShare: 0.40,
  maxSingleJurisdictionShare: 0.50,
  maxSingleControlGroupShare: 0.50,
  minimumIndependentSubstitutes: 2,
  minimumTestedExternalFallbacks: 1,
});

function boundedShare(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${name} must be a non-negative finite number`);
  return number;
}

function boundedRate(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0 || number > 1) throw new Error(`${name} must be between 0 and 1`);
  return number;
}

function positiveInt(value, name) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 0) throw new Error(`${name} must be a non-negative integer`);
  return number;
}

function normalizeThresholds(input = {}) {
  return {
    maxSingleProviderShare: boundedRate(input.maxSingleProviderShare ?? DEFAULT_THRESHOLDS.maxSingleProviderShare, 'maxSingleProviderShare'),
    maxSingleJurisdictionShare: boundedRate(input.maxSingleJurisdictionShare ?? DEFAULT_THRESHOLDS.maxSingleJurisdictionShare, 'maxSingleJurisdictionShare'),
    maxSingleControlGroupShare: boundedRate(input.maxSingleControlGroupShare ?? DEFAULT_THRESHOLDS.maxSingleControlGroupShare, 'maxSingleControlGroupShare'),
    minimumIndependentSubstitutes: positiveInt(input.minimumIndependentSubstitutes ?? DEFAULT_THRESHOLDS.minimumIndependentSubstitutes, 'minimumIndependentSubstitutes'),
    minimumTestedExternalFallbacks: positiveInt(input.minimumTestedExternalFallbacks ?? DEFAULT_THRESHOLDS.minimumTestedExternalFallbacks, 'minimumTestedExternalFallbacks'),
  };
}

function validateDependency(entry) {
  if (!entry?.id) throw new Error('dependency.id is required');
  if (!entry?.domain) throw new Error('dependency.domain is required');
  boundedShare(entry.weight ?? 1, `dependency(${entry.id}).weight`);
  if (entry.operational != null && typeof entry.operational !== 'boolean') throw new Error(`dependency(${entry.id}).operational must be boolean`);
  if (entry.testedFallback != null && typeof entry.testedFallback !== 'boolean') throw new Error(`dependency(${entry.id}).testedFallback must be boolean`);
  return true;
}

function sumBy(entries, selector) {
  const map = new Map();
  for (const entry of entries) {
    const key = selector(entry);
    if (!key) continue;
    map.set(key, (map.get(key) ?? 0) + Number(entry.weight ?? 1));
  }
  return map;
}

function normalizedShares(entries, selector) {
  const total = entries.reduce((sum, entry) => sum + Number(entry.weight ?? 1), 0);
  if (total <= 0) return new Map();
  return new Map([...sumBy(entries, selector)].map(([key, value]) => [key, value / total]));
}

function largestShare(map) {
  let key = null;
  let share = 0;
  for (const [candidate, value] of map) {
    if (value > share) { key = candidate; share = value; }
  }
  return { key, share };
}

function hhi(map) {
  return [...map.values()].reduce((sum, share) => sum + share ** 2, 0);
}

function independenceKey(entry) {
  const required = [
    entry.providerId,
    entry.controlGroup,
    entry.jurisdiction,
  ];
  if (required.some((value) => value == null || value === '')) return null;
  const upstream = [
    entry.upstreamCloud ?? '-',
    entry.upstreamBank ?? '-',
    entry.upstreamModelProvider ?? '-',
    entry.upstreamRegistry ?? '-',
    entry.rootCredentialAuthority ?? '-',
    entry.energySourceGroup ?? '-',
    entry.networkCarrierGroup ?? '-',
  ];
  return [...required, ...upstream].join('|');
}

function correlationKey(entry) {
  return [
    entry.controlGroup ?? `provider:${entry.providerId ?? 'UNKNOWN'}`,
    entry.upstreamCloud ?? '-',
    entry.upstreamBank ?? '-',
    entry.upstreamModelProvider ?? '-',
    entry.upstreamRegistry ?? '-',
    entry.rootCredentialAuthority ?? '-',
    entry.energySourceGroup ?? '-',
    entry.networkCarrierGroup ?? '-',
  ].join('|');
}

function compactMap(map) {
  return Object.fromEntries([...map.entries()].sort(([a], [b]) => String(a).localeCompare(String(b))));
}

export function evaluateDependencyDomain(entries, thresholds = {}) {
  const policy = normalizeThresholds(thresholds);
  const normalized = entries.map((entry) => {
    validateDependency(entry);
    return { operational: true, testedFallback: false, weight: 1, ...structuredClone(entry) };
  });
  if (!normalized.length) {
    return {
      ok: false,
      domain: null,
      violations: ['no-dependencies-declared'],
      warnings: [],
      metrics: { count: 0 },
    };
  }
  const domains = new Set(normalized.map((entry) => entry.domain));
  if (domains.size !== 1) throw new Error('evaluateDependencyDomain requires entries from exactly one domain');
  const domain = normalized[0].domain;
  const providerShares = normalizedShares(normalized, (entry) => entry.providerId ?? 'UNKNOWN');
  const jurisdictionShares = normalizedShares(normalized, (entry) => entry.jurisdiction ?? 'UNKNOWN');
  const controlShares = normalizedShares(normalized, (entry) => entry.controlGroup ?? `provider:${entry.providerId ?? 'UNKNOWN'}`);
  const correlatedShares = normalizedShares(normalized, correlationKey);

  const largestProvider = largestShare(providerShares);
  const largestJurisdiction = largestShare(jurisdictionShares);
  const largestControlGroup = largestShare(controlShares);
  const largestCorrelated = largestShare(correlatedShares);

  const operational = normalized.filter((entry) => entry.operational !== false);
  const independentKeys = new Set(operational.map(independenceKey).filter(Boolean));
  const unknownIndependence = operational.filter((entry) => !independenceKey(entry)).map((entry) => entry.id);
  const testedFallbacks = operational.filter((entry) => entry.testedFallback === true && independenceKey(entry)).length;

  const violations = [];
  const warnings = [];
  if (largestProvider.share > policy.maxSingleProviderShare + 1e-12) violations.push('single-provider-concentration-exceeded');
  if (largestJurisdiction.share > policy.maxSingleJurisdictionShare + 1e-12) violations.push('single-jurisdiction-concentration-exceeded');
  if (largestControlGroup.share > policy.maxSingleControlGroupShare + 1e-12) violations.push('single-control-group-concentration-exceeded');
  if (independentKeys.size < policy.minimumIndependentSubstitutes) violations.push('insufficient-independent-substitutes');
  if (testedFallbacks < policy.minimumTestedExternalFallbacks) violations.push('insufficient-tested-fallbacks');
  if (unknownIndependence.length) warnings.push('unknown-dependency-is-not-counted-as-independent');
  if (largestCorrelated.share > largestControlGroup.share + 1e-12) warnings.push('shared-upstream-increases-correlated-concentration');

  return {
    ok: violations.length === 0,
    domain,
    violations,
    warnings,
    policy,
    metrics: {
      dependencyCount: normalized.length,
      operationalCount: operational.length,
      independentSubstituteCount: independentKeys.size,
      testedFallbackCount: testedFallbacks,
      unknownIndependenceIds: unknownIndependence,
      largestProvider,
      largestJurisdiction,
      largestControlGroup,
      largestCorrelatedFailureDomain: largestCorrelated,
      providerHhi: hhi(providerShares),
      jurisdictionHhi: hhi(jurisdictionShares),
      controlGroupHhi: hhi(controlShares),
      correlatedFailureHhi: hhi(correlatedShares),
      providerShares: compactMap(providerShares),
      jurisdictionShares: compactMap(jurisdictionShares),
      controlGroupShares: compactMap(controlShares),
    },
  };
}

export function evaluateDependencyPortfolio(entries = [], { thresholdsByDomain = {}, defaultThresholds = {} } = {}) {
  const grouped = new Map();
  for (const entry of entries) {
    validateDependency(entry);
    if (!grouped.has(entry.domain)) grouped.set(entry.domain, []);
    grouped.get(entry.domain).push(entry);
  }
  const domains = {};
  const violations = [];
  for (const [domain, domainEntries] of grouped) {
    const result = evaluateDependencyDomain(domainEntries, { ...defaultThresholds, ...(thresholdsByDomain[domain] ?? {}) });
    domains[domain] = result;
    for (const violation of result.violations) violations.push(`${domain}:${violation}`);
  }
  return {
    ok: violations.length === 0,
    domains,
    violations,
    domainCount: grouped.size,
  };
}

export function simulateFailure(entries = [], failure = {}, options = {}) {
  const selectors = {
    providerId: failure.providerId,
    jurisdiction: failure.jurisdiction,
    controlGroup: failure.controlGroup,
    upstreamCloud: failure.upstreamCloud,
    upstreamBank: failure.upstreamBank,
    upstreamModelProvider: failure.upstreamModelProvider,
    upstreamRegistry: failure.upstreamRegistry,
    rootCredentialAuthority: failure.rootCredentialAuthority,
    energySourceGroup: failure.energySourceGroup,
    networkCarrierGroup: failure.networkCarrierGroup,
  };
  const activeSelectors = Object.entries(selectors).filter(([, value]) => value != null && value !== '');
  if (!activeSelectors.length) throw new Error('at least one failure selector is required');

  const affectedIds = [];
  const survivors = [];
  for (const entry of entries) {
    validateDependency(entry);
    const affected = activeSelectors.some(([key, value]) => entry[key] === value);
    if (affected) affectedIds.push(entry.id);
    else survivors.push(entry);
  }
  return {
    failure: structuredClone(failure),
    affectedIds,
    survivorIds: survivors.map((entry) => entry.id),
    postFailure: evaluateDependencyPortfolio(survivors, options),
  };
}

export class DependencyResilienceGovernor {
  constructor({ thresholdsByDomain = {}, defaultThresholds = {} } = {}) {
    this.thresholdsByDomain = structuredClone(thresholdsByDomain);
    this.defaultThresholds = normalizeThresholds(defaultThresholds);
    this.entries = new Map();
  }

  upsert(entry) {
    validateDependency(entry);
    this.entries.set(entry.id, structuredClone(entry));
    return this.get(entry.id);
  }

  remove(id) {
    return this.entries.delete(id);
  }

  get(id) {
    const entry = this.entries.get(id);
    return entry ? structuredClone(entry) : null;
  }

  list() {
    return [...this.entries.values()].map((entry) => structuredClone(entry));
  }

  evaluate() {
    return evaluateDependencyPortfolio(this.list(), {
      thresholdsByDomain: this.thresholdsByDomain,
      defaultThresholds: this.defaultThresholds,
    });
  }

  simulateFailure(failure) {
    return simulateFailure(this.list(), failure, {
      thresholdsByDomain: this.thresholdsByDomain,
      defaultThresholds: this.defaultThresholds,
    });
  }

  assertCriticalReady(requiredDomains = []) {
    const result = this.evaluate();
    const missing = requiredDomains.filter((domain) => !result.domains[domain]);
    const failed = requiredDomains.filter((domain) => result.domains[domain] && !result.domains[domain].ok);
    if (missing.length || failed.length) {
      const error = new Error(`dependency resilience gate failed: missing=${missing.join(',') || '-'} failed=${failed.join(',') || '-'}`);
      error.code = 'DEPENDENCY_RESILIENCE_GATE_FAILED';
      error.missingDomains = missing;
      error.failedDomains = failed;
      error.snapshot = result;
      throw error;
    }
    return result;
  }
}

export const DEPENDENCY_RESILIENCE_DEFAULTS = DEFAULT_THRESHOLDS;
