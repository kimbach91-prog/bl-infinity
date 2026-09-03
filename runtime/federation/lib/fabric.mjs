import { evaluateProvider, validateTask } from './policy.mjs';

const nowMs = () => Date.now();

export class ProviderRegistry {
  constructor(providers = [], { manifestVerifier = null } = {}) { this.providers = new Map(); this.manifestVerifier = manifestVerifier; for (const p of providers) this.register(p); }
  register(provider) { validateProvider(provider); if (this.manifestVerifier) { const verdict = this.manifestVerifier(provider); if (!verdict?.ok) throw new Error(`provider manifest rejected: ${verdict?.reason ?? 'unknown'}`); } this.providers.set(provider.id, structuredClone(provider)); return this.get(provider.id); }
  updateTelemetry(providerId, telemetry) { const p = this.providers.get(providerId); if (!p) throw new Error(`unknown provider: ${providerId}`); p.telemetry = { ...p.telemetry, ...structuredClone(telemetry) }; return this.get(providerId); }
  disable(providerId) { const p = this.providers.get(providerId); if (!p) throw new Error(`unknown provider: ${providerId}`); p.status = 'disabled'; }
  get(providerId) { const p = this.providers.get(providerId); return p ? structuredClone(p) : null; }
  list() { return [...this.providers.values()].map((p) => structuredClone(p)); }
}

function validateProvider(p) {
  const required = ['id', 'kind', 'capabilities', 'authorization', 'limits', 'telemetry'];
  for (const k of required) if (p?.[k] == null) throw new Error(`provider.${k} is required`);
  if (!p.authorization.consentRef) throw new Error('provider.authorization.consentRef is required');
  if (p.authorization.expiresAt && Date.parse(p.authorization.expiresAt) <= nowMs()) throw new Error('provider authorization is expired');
  if (!Array.isArray(p.capabilities) || p.capabilities.length === 0) throw new Error('provider.capabilities must be non-empty');
}
export function eligible(provider, task) { return evaluateProvider(provider, task).ok; }
export function score(provider, task, weights = {}) {
  const w = { trust: 2, locality: 1.5, availability: 1.2, latency: 1, cost: 1, carbon: 0.15, ...weights };
  const trust = clamp01(provider.telemetry.trust ?? 0.5), availability = clamp01(provider.telemetry.availability ?? 0.5), locality = task.dataLocation && provider.dataLocations?.includes(task.dataLocation) ? 1 : 0.4;
  const latencyPenalty = Math.log10(10 + Math.max(0, provider.telemetry.p95LatencyMs ?? 1000)), costPenalty = Math.log10(1 + 100 * Math.max(0, provider.telemetry.costPerUnitUsd ?? 0)), carbonPenalty = Math.log10(1 + Math.max(0, provider.telemetry.carbonIntensity ?? 0));
  return w.trust * trust + w.locality * locality + w.availability * availability - w.latency * latencyPenalty - w.cost * costPenalty - w.carbon * carbonPenalty;
}
export function rankCandidates(registry, task, options = {}) {
  validateTask(task);
  return registry.list().map((provider) => ({ provider, policy: evaluateProvider(provider, task) })).filter((x) => x.policy.ok).map(({ provider }) => ({ provider, score: score(provider, task, options.weights) })).sort((a, b) => b.score - a.score || a.provider.id.localeCompare(b.provider.id));
}
export function planRoute(registry, task, options = {}) {
  const candidates = rankCandidates(registry, task, options), selected = candidates.slice(0, Math.max(1, options.replicas ?? 1));
  return { taskId: task.id, generatedAt: new Date().toISOString(), selected: selected.map(({ provider, score: candidateScore }) => ({ providerId: provider.id, kind: provider.kind, endpoint: provider.endpoint ?? null, score: Number(candidateScore.toFixed(4)), consentRef: provider.authorization.consentRef })), rejectedCount: registry.list().length - candidates.length, policy: { authorizationRequired: true, noUnauthorizedCompute: true, dataClass: task.dataClass ?? 'public' } };
}
function clamp01(x) { return Math.max(0, Math.min(1, Number(x))); }
