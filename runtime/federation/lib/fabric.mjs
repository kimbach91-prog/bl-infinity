const nowMs = () => Date.now();

export class ProviderRegistry {
  constructor(providers = []) {
    this.providers = new Map();
    for (const p of providers) this.register(p);
  }

  register(provider) {
    validateProvider(provider);
    this.providers.set(provider.id, structuredClone(provider));
    return this.providers.get(provider.id);
  }

  list() {
    return [...this.providers.values()].map((p) => structuredClone(p));
  }
}

function validateProvider(p) {
  const required = ["id", "kind", "capabilities", "authorization", "limits", "telemetry"];
  for (const k of required) if (p?.[k] == null) throw new Error(`provider.${k} is required`);
  if (!p.authorization.consentRef) throw new Error("provider.authorization.consentRef is required");
  if (p.authorization.expiresAt && Date.parse(p.authorization.expiresAt) <= nowMs()) {
    throw new Error("provider authorization is expired");
  }
  if (!Array.isArray(p.capabilities) || p.capabilities.length === 0) {
    throw new Error("provider.capabilities must be non-empty");
  }
}

export function eligible(provider, task) {
  if (provider.status === "disabled") return false;
  if (provider.authorization.expiresAt && Date.parse(provider.authorization.expiresAt) <= nowMs()) return false;
  if (!provider.capabilities.includes(task.capability)) return false;
  if ((provider.limits.maxConcurrency ?? 0) <= (provider.telemetry.inFlight ?? 0)) return false;
  if ((task.estimatedCostUsd ?? 0) > (provider.limits.maxCostPerTaskUsd ?? Infinity)) return false;
  if (task.dataClass === "private" && provider.dataPolicy?.privateDataAllowed !== true) return false;
  if (task.region && provider.regions?.length && !provider.regions.includes(task.region)) return false;
  return true;
}

export function score(provider, task, weights = {}) {
  const w = {
    trust: 2.0,
    locality: 1.5,
    availability: 1.2,
    latency: 1.0,
    cost: 1.0,
    carbon: 0.15,
    ...weights,
  };

  const trust = clamp01(provider.telemetry.trust ?? 0.5);
  const availability = clamp01(provider.telemetry.availability ?? 0.5);
  const locality = task.dataLocation && provider.dataLocations?.includes(task.dataLocation) ? 1 : 0.4;
  const latencyPenalty = Math.log10(10 + Math.max(0, provider.telemetry.p95LatencyMs ?? 1000));
  const costPenalty = Math.log10(1 + 100 * Math.max(0, provider.telemetry.costPerUnitUsd ?? 0));
  const carbonPenalty = Math.log10(1 + Math.max(0, provider.telemetry.carbonIntensity ?? 0));

  return (
    w.trust * trust +
    w.locality * locality +
    w.availability * availability -
    w.latency * latencyPenalty -
    w.cost * costPenalty -
    w.carbon * carbonPenalty
  );
}

export function planRoute(registry, task, options = {}) {
  validateTask(task);
  const candidates = registry.list()
    .filter((p) => eligible(p, task))
    .map((p) => ({ provider: p, score: score(p, task, options.weights) }))
    .sort((a, b) => b.score - a.score);

  const selected = candidates.slice(0, Math.max(1, options.replicas ?? 1));
  return {
    taskId: task.id,
    generatedAt: new Date().toISOString(),
    selected: selected.map(({ provider, score }) => ({
      providerId: provider.id,
      kind: provider.kind,
      endpoint: provider.endpoint ?? null,
      score: Number(score.toFixed(4)),
      consentRef: provider.authorization.consentRef,
    })),
    rejectedCount: registry.list().length - candidates.length,
    policy: {
      authorizationRequired: true,
      noUnauthorizedCompute: true,
      dataClass: task.dataClass ?? "public",
    },
  };
}

function validateTask(task) {
  if (!task?.id) throw new Error("task.id is required");
  if (!task?.capability) throw new Error("task.capability is required");
  if (!["public", "internal", "private"].includes(task.dataClass ?? "public")) {
    throw new Error("task.dataClass must be public, internal, or private");
  }
}

function clamp01(x) {
  return Math.max(0, Math.min(1, Number(x)));
}
