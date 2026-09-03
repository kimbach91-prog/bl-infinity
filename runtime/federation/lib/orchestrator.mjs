import { MemoryLeaseQueue } from './queue.mjs';
import { BudgetGovernor } from './budget.mjs';
import { MemoryResultCache } from './cache.mjs';
import { ContributionLedger } from './ledger.mjs';

export class FederationOrchestrator {
  constructor({ registry, executor, queue = new MemoryLeaseQueue(), budget = new BudgetGovernor(), cache = new MemoryResultCache(), ledger = new ContributionLedger(), audit = null } = {}) {
    if (!registry || !executor) throw new Error('registry and executor are required');
    this.registry = registry; this.executor = executor; this.queue = queue; this.budget = budget; this.cache = cache; this.ledger = ledger; this.audit = audit;
  }
  async submit(task, options = {}) {
    const effective = { ...options };
    if (task.sideEffect === true && !(task.idempotencyKey && task.retrySafe === true)) effective.maxAttempts = 1;
    const enqueued = this.queue.enqueue(task, effective);
    await this.audit?.append(enqueued.deduplicated ? 'queue.deduplicated' : 'queue.enqueued', { taskId: enqueued.job.id, idempotencyKey: enqueued.job.idempotencyKey });
    return enqueued;
  }
  async runOnce({ coordinatorId = 'coordinator', leaseMs = 60_000, retryDelayMs = 1000 } = {}) {
    const capabilities = [...new Set(this.registry.list().flatMap((p) => p.capabilities ?? []))];
    const job = this.queue.claim(coordinatorId, capabilities, { leaseMs }); if (!job) return null;
    const task = job.task, token = job.lease.token;
    try {
      const cached = this.cache.get(task);
      if (cached) { const value = { ...structuredClone(cached.value), cache: { hit: true, key: cached.key } }; this.queue.complete(job.id, token, value); await this.audit?.append('task.cache-hit', { taskId: task.id, cacheKey: cached.key }); return { job: this.queue.get(job.id), execution: value, cacheHit: true }; }
      const estimated = Number(task.estimatedCostUsd ?? 0);
      const reserve = this.budget.reserve({ amountUsd: estimated, tenantId: task.tenantId ?? 'default', taskId: task.id }); if (!reserve.ok) throw new Error(`budget rejected: ${reserve.reason}`);
      let execution;
      try { execution = await this.executor.execute(task, { providerGuard: (provider) => this.budget.canSpend({ amountUsd: estimated, tenantId: task.tenantId ?? 'default', providerId: provider.id }) }); this.budget.commit(reserve.reservation.id, estimated); }
      catch (error) { this.budget.release(reserve.reservation.id, 'execution-failed'); throw error; }
      this.cache.set(task, execution, { ttlMs: task.cacheTtlMs });
      const provider = this.registry.get(execution.providerId);
      for (const attempt of execution.attempts ?? []) if (!attempt.ok) this.ledger.record({ taskId: task.id, providerId: attempt.providerId, consentRef: this.registry.get(attempt.providerId)?.authorization?.consentRef ?? null, tenantId: task.tenantId ?? 'default', measuredLatencyMs: attempt.latencyMs ?? 0, billedCostUsd: 0, inputBytes: byteSize(task.payload), outputBytes: 0, status: 'failed' });
      this.ledger.record({ taskId: task.id, providerId: execution.providerId, consentRef: provider?.authorization?.consentRef ?? null, tenantId: task.tenantId ?? 'default', measuredLatencyMs: execution.measuredLatencyMs, billedCostUsd: estimated, inputBytes: byteSize(task.payload), outputBytes: byteSize(execution.result), status: 'succeeded' });
      this.queue.complete(job.id, token, execution); return { job: this.queue.get(job.id), execution, cacheHit: false };
    } catch (error) {
      for (const attempt of error.attempts ?? []) this.ledger.record({ taskId: task.id, providerId: attempt.providerId, consentRef: this.registry.get(attempt.providerId)?.authorization?.consentRef ?? null, tenantId: task.tenantId ?? 'default', measuredLatencyMs: attempt.latencyMs ?? 0, billedCostUsd: 0, inputBytes: byteSize(task.payload), outputBytes: 0, status: 'failed' });
      this.queue.fail(job.id, token, error, { retryDelayMs }); await this.audit?.append('queue.execution-failed', { taskId: task.id, error: error.message }); return { job: this.queue.get(job.id), error: error.message };
    }
  }
  status() { return { queue: { pending: this.queue.list({ state: 'pending' }).length, running: this.queue.list({ state: 'running' }).length, succeeded: this.queue.list({ state: 'succeeded' }).length, deadletter: this.queue.list({ state: 'deadletter' }).length }, budget: this.budget.snapshot(), cache: this.cache.stats(), ledger: this.ledger.summary(), circuits: this.executor.circuit?.snapshot?.() ?? {} }; }
}
function byteSize(value) { return Buffer.byteLength(typeof value === 'string' ? value : JSON.stringify(value ?? null)); }
