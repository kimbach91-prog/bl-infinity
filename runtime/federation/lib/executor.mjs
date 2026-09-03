import { rankCandidates } from './fabric.mjs';
import { TelemetryBook } from './telemetry.mjs';

export class FederationExecutor {
  constructor({ registry, adapters = {}, telemetry = new TelemetryBook(), audit = null } = {}) {
    if (!registry) throw new Error('registry is required');
    this.registry = registry; this.adapters = new Map(Object.entries(adapters)); this.telemetry = telemetry; this.audit = audit;
  }
  async execute(task, { maxProviders = 3, weights = {} } = {}) {
    const ranked = rankCandidates(this.registry, task, { weights }).slice(0, Math.max(1, maxProviders));
    if (!ranked.length) throw new Error('no eligible provider');
    const attempts = [];
    await this.audit?.append('task.accepted', { taskId: task.id, capability: task.capability, dataClass: task.dataClass ?? 'public' });
    for (const { provider, score } of ranked) {
      const adapter = this.adapters.get(provider.kind) ?? this.adapters.get('*');
      if (!adapter) { attempts.push({ providerId: provider.id, ok: false, error: `no adapter for kind ${provider.kind}` }); continue; }
      const started = performance.now(); this.telemetry.begin(provider.id);
      try {
        await this.audit?.append('task.dispatched', { taskId: task.id, providerId: provider.id, consentRef: provider.authorization.consentRef });
        const result = await adapter.execute(provider, task); const latencyMs = performance.now() - started;
        this.telemetry.success(provider.id, { latencyMs, costUsd: task.estimatedCostUsd ?? 0 }); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
        attempts.push({ providerId: provider.id, ok: true, latencyMs: Math.round(latencyMs), score: Number(score.toFixed(4)) });
        await this.audit?.append('task.completed', { taskId: task.id, providerId: provider.id, latencyMs: Math.round(latencyMs) });
        return { taskId: task.id, providerId: provider.id, result, attempts, provenance: { consentRef: provider.authorization.consentRef, providerKind: provider.kind, executedAt: new Date().toISOString() } };
      } catch (error) {
        const latencyMs = performance.now() - started; this.telemetry.failure(provider.id, { latencyMs }); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
        attempts.push({ providerId: provider.id, ok: false, latencyMs: Math.round(latencyMs), error: error.message }); await this.audit?.append('task.failed-attempt', { taskId: task.id, providerId: provider.id, error: error.message });
      }
    }
    const failure = new Error('all eligible providers failed'); failure.attempts = attempts; throw failure;
  }
}
