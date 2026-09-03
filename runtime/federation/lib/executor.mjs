import { randomUUID } from 'node:crypto';
import { rankCandidates } from './fabric.mjs';
import { TelemetryBook } from './telemetry.mjs';
import { CircuitBreakerBook } from './circuit.mjs';

export class FederationExecutor {
  constructor({ registry, adapters = {}, telemetry = new TelemetryBook(), circuit = new CircuitBreakerBook(), audit = null } = {}) {
    if (!registry) throw new Error('registry is required');
    this.registry = registry; this.adapters = new Map(Object.entries(adapters)); this.telemetry = telemetry; this.circuit = circuit; this.audit = audit;
  }
  async execute(task, { maxProviders = 3, weights = {}, providerGuard = null } = {}) {
    const executionId = randomUUID();
    const ranked = rankCandidates(this.registry, task, { weights });
    if (!ranked.length) throw new Error('no eligible provider');
    const attempts = [];
    await this.audit?.append('task.accepted', { executionId, taskId: task.id, capability: task.capability, dataClass: task.dataClass ?? 'public' });
    let attemptedProviders = 0;
    for (const { provider, score } of ranked) {
      if (attemptedProviders >= Math.max(1, maxProviders)) break;
      const guardVerdict = providerGuard ? providerGuard(provider, task) : { ok: true };
      if (!guardVerdict?.ok) { attempts.push({ providerId: provider.id, ok: false, skipped: true, error: guardVerdict?.reason ?? 'provider-guard-rejected' }); continue; }
      const circuitVerdict = this.circuit.allow(provider.id);
      if (!circuitVerdict.ok) { attempts.push({ providerId: provider.id, ok: false, skipped: true, error: circuitVerdict.reason }); continue; }
      attemptedProviders += 1;
      const adapter = this.adapters.get(provider.kind) ?? this.adapters.get('*');
      if (!adapter) { attempts.push({ providerId: provider.id, ok: false, error: `no adapter for kind ${provider.kind}` }); this.circuit.failure(provider.id); continue; }
      const started = performance.now(); this.telemetry.begin(provider.id);
      try {
        await this.audit?.append('task.dispatched', { executionId, taskId: task.id, providerId: provider.id, consentRef: provider.authorization.consentRef });
        const result = await adapter.execute(provider, task); const latencyMs = performance.now() - started;
        this.telemetry.success(provider.id, { latencyMs, costUsd: task.estimatedCostUsd ?? 0 }); this.circuit.success(provider.id); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
        attempts.push({ providerId: provider.id, ok: true, latencyMs: Math.round(latencyMs), score: Number(score.toFixed(4)) });
        await this.audit?.append('task.completed', { executionId, taskId: task.id, providerId: provider.id, latencyMs: Math.round(latencyMs) });
        return { executionId, taskId: task.id, providerId: provider.id, result, attempts, measuredLatencyMs: latencyMs, provenance: { consentRef: provider.authorization.consentRef, providerKind: provider.kind, executedAt: new Date().toISOString() } };
      } catch (error) {
        const latencyMs = performance.now() - started; this.telemetry.failure(provider.id, { latencyMs }); this.circuit.failure(provider.id); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
        attempts.push({ providerId: provider.id, ok: false, latencyMs: Math.round(latencyMs), error: error.message }); await this.audit?.append('task.failed-attempt', { executionId, taskId: task.id, providerId: provider.id, error: error.message });
      }
    }
    const failure = new Error('all eligible providers failed'); failure.executionId = executionId; failure.attempts = attempts; throw failure;
  }
}
