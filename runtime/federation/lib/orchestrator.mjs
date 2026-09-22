import { MemoryLeaseQueue } from './queue.mjs';
import { BudgetGovernor } from './budget.mjs';
import { MemoryResultCache } from './cache.mjs';
import { ContributionLedger } from './ledger.mjs';
import { ValuePolicyGovernor } from './value-policy.mjs';
import { chooseComputeTier } from './resource-envelope.mjs';

export class FederationOrchestrator {
  constructor({ registry, executor, queue = new MemoryLeaseQueue(), budget = new BudgetGovernor(), resourceEnvelope = null, cache = new MemoryResultCache(), ledger = new ContributionLedger(), audit = null, allowedStateDataClasses = null, valuePolicy = new ValuePolicyGovernor(), treasury = null } = {}) {
    if (!registry || !executor) throw new Error('registry and executor are required');
    this.registry = registry;
    this.executor = executor;
    this.queue = queue;
    this.budget = budget;
    this.resourceEnvelope = resourceEnvelope;
    this.cache = cache;
    this.ledger = ledger;
    this.audit = audit;
    this.valuePolicy = valuePolicy;
    this.treasury = treasury;
    this.allowedStateDataClasses = allowedStateDataClasses ? new Set(allowedStateDataClasses) : null;
  }

  async submit(task, options = {}) {
    const dataClass = task.dataClass ?? 'public';
    if (this.allowedStateDataClasses && !this.allowedStateDataClasses.has(dataClass)) {
      const error = new Error(`state backend rejects dataClass: ${dataClass}`);
      error.code = 'STATE_DATA_CLASS_REJECTED';
      throw error;
    }

    const admission = this.valuePolicy?.admit?.(task) ?? { ok: true, legacy: true, priority: 0 };
    if (!admission.ok) {
      const error = new Error(`value policy rejected task: ${admission.reason ?? 'unknown'}`);
      error.code = 'VALUE_POLICY_REJECTED';
      error.nonRetryable = true;
      error.admission = admission;
      await this.audit?.append('task.admission-rejected', { taskId: task.id, reason: admission.reason ?? 'unknown' });
      throw error;
    }

    if (this.resourceEnvelope && task.computeEnvelope) this.#ensureResourceTask(task);

    const effective = { ...options };
    if (!admission.legacy) effective.priority = admission.priority;
    if (task.sideEffect === true && !(task.idempotencyKey && task.retrySafe === true)) effective.maxAttempts = 1;
    const enqueued = await this.queue.enqueue(task, effective);
    await this.audit?.append(enqueued.deduplicated ? 'queue.deduplicated' : 'queue.enqueued', {
      taskId: enqueued.job.id,
      idempotencyKey: enqueued.job.idempotencyKey,
      workloadClass: admission.workloadClass ?? null,
      utility: admission.utility ?? null,
      strategicReinvestmentRequested: admission.strategicReinvestmentRequested ?? admission.commonBenefitRequested ?? false,
      commonBenefitRequested: admission.commonBenefitRequested ?? false,
      derivedPriority: admission.legacy ? null : admission.priority,
      computeEnvelope: task.computeEnvelope ? true : false,
    });
    return { ...enqueued, admission };
  }

  async runOnce({ coordinatorId = 'coordinator', leaseMs = 60_000, retryDelayMs = 1000 } = {}) {
    const capabilities = [...new Set(this.registry.list().flatMap((p) => p.capabilities ?? []))];
    const job = await this.queue.claim(coordinatorId, capabilities, { leaseMs });
    if (!job) return null;
    const task = job.task;
    const token = job.lease.token;
    try {
      const cached = await this.cache.get(task);
      if (cached) {
        const value = { ...structuredClone(cached.value), cache: { hit: true, key: cached.key } };
        await this.queue.complete(job.id, token, value);
        await this.audit?.append('task.cache-hit', { taskId: task.id, cacheKey: cached.key });
        this.#closeResourceTask(task, 'cache-hit');
        return { job: await this.queue.get(job.id), execution: value, cacheHit: true };
      }
      const estimated = Number(task.estimatedCostUsd ?? 0);
      const tenantId = task.tenantId ?? 'default';
      if (this.resourceEnvelope && task.computeEnvelope) this.#ensureResourceTask(task);
      const execution = await this.executor.execute(task, {
        providerGuard: async (provider) => {
          let resourceReservation = null;
          if (this.resourceEnvelope && task.computeEnvelope) {
            const tier = task.computeTier ?? chooseComputeTier(task.computeRouting ?? {}).tier;
            const resourceEstimate = estimateResources(task, provider);
            const resourceVerdict = this.resourceEnvelope.authorize(task.id, resourceEstimate, {
              tier,
              explicitHpcAuthorization: task.explicitHpcAuthorization === true,
            });
            if (!resourceVerdict.ok) return resourceVerdict;
            resourceReservation = resourceVerdict.reservation;
          }

          const budgetVerdict = await this.budget.reserve({ amountUsd: estimated, tenantId, providerId: provider.id, taskId: task.id });
          if (!budgetVerdict.ok) {
            if (resourceReservation?.id) this.resourceEnvelope.release(resourceReservation.id, 'usd-budget-rejected');
            return budgetVerdict;
          }
          return {
            ok: true,
            reservation: budgetVerdict.reservation,
            budgetReservation: budgetVerdict.reservation,
            resourceReservation,
          };
        },
        onProviderSuccess: async ({ guard }) => {
          if (guard?.budgetReservation?.id) await this.budget.commit(guard.budgetReservation.id, estimated);
          if (guard?.resourceReservation?.id) this.resourceEnvelope.commit(guard.resourceReservation.id, guard.resourceReservation.estimate);
        },
        onProviderFailure: async ({ guard }) => {
          if (guard?.budgetReservation?.id) await this.budget.release(guard.budgetReservation.id, 'execution-failed');
          if (guard?.resourceReservation?.id) this.resourceEnvelope.release(guard.resourceReservation.id, 'execution-failed');
        },
      });
      await this.cache.set(task, execution, { ttlMs: task.cacheTtlMs });
      const provider = this.registry.get(execution.providerId);
      for (const attempt of execution.attempts ?? []) {
        if (!attempt.ok) {
          await this.ledger.record({
            taskId: task.id,
            providerId: attempt.providerId,
            consentRef: this.registry.get(attempt.providerId)?.authorization?.consentRef ?? null,
            tenantId,
            measuredLatencyMs: attempt.latencyMs ?? 0,
            billedCostUsd: 0,
            inputBytes: byteSize(task.payload),
            outputBytes: 0,
            status: 'failed',
          });
        }
      }
      await this.ledger.record({
        taskId: task.id,
        providerId: execution.providerId,
        consentRef: provider?.authorization?.consentRef ?? null,
        tenantId,
        measuredLatencyMs: execution.measuredLatencyMs,
        billedCostUsd: estimated,
        inputBytes: byteSize(task.payload),
        outputBytes: byteSize(execution.result),
        status: 'succeeded',
      });
      await this.queue.complete(job.id, token, execution);
      this.#closeResourceTask(task, 'completed');
      return { job: await this.queue.get(job.id), execution, cacheHit: false };
    } catch (error) {
      for (const attempt of error.attempts ?? []) {
        await this.ledger.record({
          taskId: task.id,
          providerId: attempt.providerId,
          consentRef: this.registry.get(attempt.providerId)?.authorization?.consentRef ?? null,
          tenantId: task.tenantId ?? 'default',
          measuredLatencyMs: attempt.latencyMs ?? 0,
          billedCostUsd: 0,
          inputBytes: byteSize(task.payload),
          outputBytes: 0,
          status: 'failed',
        });
      }
      await this.queue.fail(job.id, token, error, { retryDelayMs, terminal: error.nonRetryable === true });
      await this.audit?.append('queue.execution-failed', { taskId: task.id, error: error.message, nonRetryable: error.nonRetryable === true });
      return { job: await this.queue.get(job.id), error: error.message };
    }
  }

  async status() {
    const [pending, running, succeeded, deadletter, budget, cache, ledger] = await Promise.all([
      this.queue.list({ state: 'pending' }),
      this.queue.list({ state: 'running' }),
      this.queue.list({ state: 'succeeded' }),
      this.queue.list({ state: 'deadletter' }),
      this.budget.snapshot(),
      this.cache.stats(),
      this.ledger.summary(),
    ]);
    return {
      queue: { pending: pending.length, running: running.length, succeeded: succeeded.length, deadletter: deadletter.length },
      budget,
      resourceEnvelope: this.resourceEnvelope?.snapshot?.() ?? null,
      cache,
      ledger,
      circuits: this.executor.circuit?.snapshot?.() ?? {},
      allowedStateDataClasses: this.allowedStateDataClasses ? [...this.allowedStateDataClasses] : null,
      valuePolicy: this.valuePolicy ? { enabled: true } : { enabled: false },
      treasury: this.treasury?.snapshot?.() ?? null,
    };
  }

  #ensureResourceTask(task) {
    try {
      return this.resourceEnvelope.taskSnapshot(task.id);
    } catch (error) {
      if (!String(error?.message ?? '').startsWith('unknown task:')) throw error;
    }
    const envelope = task.computeEnvelope ?? {};
    return this.resourceEnvelope.openTask({
      taskId: task.id,
      tenantId: task.tenantId ?? 'default',
      purpose: envelope.purpose ?? task.capability,
      authority: envelope.authority ?? task.authority ?? null,
      dataResidency: envelope.dataResidency ?? (task.dataLocation ? [task.dataLocation] : []),
      limits: envelope.limits ?? {},
      tierCeiling: envelope.tierCeiling ?? 'T4',
      assuranceLevel: envelope.assuranceLevel ?? 'medium',
      catastrophicRiskClass: envelope.catastrophicRiskClass ?? 0,
    });
  }

  #closeResourceTask(task, reason) {
    if (!(this.resourceEnvelope && task.computeEnvelope)) return;
    try {
      const snapshot = this.resourceEnvelope.taskSnapshot(task.id);
      if (snapshot.state === 'open') this.resourceEnvelope.closeTask(task.id, reason);
    } catch {
      // Runtime completion must not be converted into failure only because optional envelope cleanup was already completed elsewhere.
    }
  }
}

function estimateResources(task, provider) {
  const workUnits = Number(task.estimatedWorkUnits ?? 0);
  const rawProviderEnergy = provider.telemetry?.energyPerUnitJoules;
  const providerEnergyPerUnit = rawProviderEnergy == null || rawProviderEnergy === '' ? null : Number(rawProviderEnergy);
  const derivedEnergy = Number.isFinite(workUnits) && workUnits > 0 && providerEnergyPerUnit != null && Number.isFinite(providerEnergyPerUnit) && providerEnergyPerUnit >= 0
    ? workUnits * providerEnergyPerUnit
    : 0;
  return {
    energyJoules: Number(task.estimatedEnergyJoules ?? derivedEnergy),
    costUsd: Number(task.estimatedCostUsd ?? 0),
    acceleratorSeconds: Number(task.estimatedAcceleratorSeconds ?? 0),
    tokens: Number(task.estimatedTokens ?? 0),
    wallTimeMs: Number(task.estimatedWallTimeMs ?? provider.telemetry?.p95LatencyMs ?? 0),
  };
}

function byteSize(value) {
  return Buffer.byteLength(typeof value === 'string' ? value : JSON.stringify(value ?? null));
}
