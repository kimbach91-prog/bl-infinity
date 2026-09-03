import { randomUUID } from 'node:crypto';
import { rankCandidates } from './fabric.mjs';
import { TelemetryBook } from './telemetry.mjs';
import { CircuitBreakerBook } from './circuit.mjs';

export class FederationExecutor {
  constructor({ registry, adapters = {}, telemetry = new TelemetryBook(), circuit = new CircuitBreakerBook(), audit = null } = {}) {
    if (!registry) throw new Error('registry is required');
    this.registry = registry; this.adapters = new Map(Object.entries(adapters)); this.telemetry = telemetry; this.circuit = circuit; this.audit = audit;
  }
  async execute(task, { maxProviders = 3, weights = {}, providerGuard = null, onProviderSuccess = null, onProviderFailure = null } = {}) {
    const executionId = randomUUID();
    const ranked = rankCandidates(this.registry, task, { weights });
    if (!ranked.length) throw new Error('no eligible provider');
    const attempts = [];
    await this.audit?.append('task.accepted', { executionId, taskId: task.id, capability: task.capability, dataClass: task.dataClass ?? 'public' });
    let attemptedProviders = 0;
    for (const { provider, score } of ranked) {
      if (attemptedProviders >= Math.max(1, maxProviders)) break;
      const circuitVerdict = this.circuit.allow(provider.id);
      if (!circuitVerdict.ok) { attempts.push({ providerId: provider.id, ok: false, skipped: true, error: circuitVerdict.reason }); continue; }
      const adapter = this.adapters.get(provider.kind) ?? this.adapters.get('*');
      if (!adapter) { attempts.push({ providerId: provider.id, ok: false, error: `no adapter for kind ${provider.kind}` }); this.circuit.failure(provider.id); continue; }
      const guardVerdict = providerGuard ? await providerGuard(provider, task) : { ok: true };
      if (!guardVerdict?.ok) { attempts.push({ providerId: provider.id, ok: false, skipped: true, error: guardVerdict?.reason ?? 'provider-guard-rejected' }); continue; }
      attemptedProviders += 1;
      const started = performance.now(); this.telemetry.begin(provider.id);
      let result;
      try {
        await this.audit?.append('task.dispatched', { executionId, taskId: task.id, providerId: provider.id, consentRef: provider.authorization.consentRef });
        result = await adapter.execute(provider, task);
      } catch (error) {
        const latencyMs = performance.now() - started;
        this.telemetry.failure(provider.id, { latencyMs }); this.circuit.failure(provider.id); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
        try { await onProviderFailure?.({ provider, task, guard: guardVerdict, error, latencyMs, executionId }); }
        catch (settlementError) {
          const failure = new Error(`provider failure settlement failed: ${settlementError.message}`);
          failure.executionId = executionId;
          failure.attempts = [...attempts, { providerId: provider.id, ok: false, latencyMs: Math.round(latencyMs), error: error.message, settlementError: settlementError.message }];
          failure.nonRetryable = true;
          throw failure;
        }
        attempts.push({ providerId: provider.id, ok: false, latencyMs: Math.round(latencyMs), error: error.message });
        await this.audit?.append('task.failed-attempt', { executionId, taskId: task.id, providerId: provider.id, error: error.message });
        continue;
      }
      const latencyMs = performance.now() - started;
      this.telemetry.success(provider.id, { latencyMs, costUsd: task.estimatedCostUsd ?? 0 }); this.circuit.success(provider.id); this.registry.updateTelemetry(provider.id, this.telemetry.snapshot(provider.id));
      try { await onProviderSuccess?.({ provider, task, guard: guardVerdict, result, latencyMs, executionId }); }
      catch (settlementError) {
        const failure = new Error(`provider succeeded but settlement failed: ${settlementError.message}`);
        failure.executionId = executionId;
        failure.attempts = [...attempts, { providerId: provider.id, ok: false, executed: true, settlementError: settlementError.message, latencyMs: Math.round(latencyMs) }];
        failure.nonRetryable = true;
        await this.audit?.append('task.settlement-failed', { executionId, taskId: task.id, providerId: provider.id, error: settlementError.message });
        throw failure;
      }
      attempts.push({ providerId: provider.id, ok: true, latencyMs: Math.round(latencyMs), score: Number(score.toFixed(4)) });
      await this.audit?.append('task.completed', { executionId, taskId: task.id, providerId: provider.id, latencyMs: Math.round(latencyMs) });
      return { executionId, taskId: task.id, providerId: provider.id, result, attempts, measuredLatencyMs: latencyMs, provenance: { consentRef: provider.authorization.consentRef, providerKind: provider.kind, executedAt: new Date().toISOString() } };
    }
    const failure = new Error('all eligible providers failed'); failure.executionId = executionId; failure.attempts = attempts; throw failure;
  }
}
