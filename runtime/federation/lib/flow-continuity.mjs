import { createHash } from 'node:crypto';

export const DEFAULT_CONTINUITY_POLICY = Object.freeze({
  leaseMs: 60_000,
  retryBaseMs: 1_000,
  retryMaxMs: 60_000,
  retryFactor: 2,
  retryJitterRatio: 0.20,
  maxDispatchPerTick: 32,
});

function boundedNumber(value, name, { min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${name} out of range`);
  return n;
}

function deterministicUnit(key) {
  const hex = createHash('sha256').update(String(key)).digest('hex').slice(0, 13);
  return Number.parseInt(hex, 16) / 0x1fffffffffffff;
}

export function retryDelayMs(attempt, {
  baseMs = DEFAULT_CONTINUITY_POLICY.retryBaseMs,
  maxMs = DEFAULT_CONTINUITY_POLICY.retryMaxMs,
  factor = DEFAULT_CONTINUITY_POLICY.retryFactor,
  jitterRatio = DEFAULT_CONTINUITY_POLICY.retryJitterRatio,
  key = '',
} = {}) {
  const a = Math.max(1, Math.trunc(boundedNumber(attempt, 'attempt', { min: 1 })));
  const base = boundedNumber(baseMs, 'baseMs', { min: 1 });
  const max = boundedNumber(maxMs, 'maxMs', { min: base });
  const f = boundedNumber(factor, 'factor', { min: 1, max: 16 });
  const jr = boundedNumber(jitterRatio, 'jitterRatio', { min: 0, max: 1 });
  const exponential = Math.min(max, base * (f ** (a - 1)));
  const jitter = (deterministicUnit(`${key}:${a}`) * 2 - 1) * jr;
  return Math.max(0, Math.round(exponential * (1 + jitter)));
}

export function checkpointDigest(snapshot = {}) {
  const payload = {
    schema: 'deus-flow-checkpoint/1',
    graphId: snapshot.graphId ?? null,
    runId: snapshot.runId ?? null,
    graphFingerprint: snapshot.graphFingerprint ?? null,
    verdict: snapshot.verdict ?? null,
    counts: snapshot.counts ?? null,
    ready: snapshot.ready ?? [],
    states: snapshot.states ?? {},
  };
  return createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

export function continuityRecoveryPlan(snapshot = {}) {
  const states = snapshot.states ?? {};
  const resume = [];
  const keep = [];
  const stop = [];
  for (const [nodeId, state] of Object.entries(states)) {
    if (state.state === 'succeeded') keep.push(nodeId);
    else if (state.state === 'pending' || state.state === 'submitted') resume.push(nodeId);
    else if (state.state === 'failed' || state.state === 'blocked') stop.push(nodeId);
  }
  return Object.freeze({
    schema: 'deus-flow-recovery-plan/1',
    graphId: snapshot.graphId ?? null,
    runId: snapshot.runId ?? null,
    keep: Object.freeze(keep),
    resume: Object.freeze(resume),
    stop: Object.freeze(stop),
    canContinue: stop.length === 0,
    truthBoundary: 'KEEP_MEANS_DO_NOT_RECOMPUTE_VERIFIED_SUCCEEDED_NODE__RESUME_MEANS_CONTINUE_FROM_DURABLE_QUEUE_OR_NEXT_READY_NODE__STOP_REQUIRES_REPAIR_OR_NEW_RUN_ID',
  });
}

export class FlowContinuitySupervisor {
  constructor({ broker, orchestrator, policy = {} } = {}) {
    if (!broker?.restoreFromQueue || !broker?.materializeReady || !broker?.snapshot) throw new Error('restart-restorable task graph broker is required');
    if (!orchestrator?.queue) throw new Error('orchestrator with durable queue is required');
    this.broker = broker;
    this.orchestrator = orchestrator;
    this.policy = Object.freeze({ ...DEFAULT_CONTINUITY_POLICY, ...policy });
  }

  async recover({ now = Date.now() } = {}) {
    const restored = await this.broker.restoreFromQueue(this.orchestrator, { now, sweepExpired: true });
    const snapshot = this.broker.snapshot();
    return {
      schema: 'deus-flow-continuity-recovery/1',
      restored,
      snapshot,
      checkpointDigest: checkpointDigest(snapshot),
      recoveryPlan: continuityRecoveryPlan(snapshot),
    };
  }

  async dispatchReady({ now = Date.now(), maxTasks = this.policy.maxDispatchPerTick } = {}) {
    const submitted = await this.broker.materializeReady(this.orchestrator, { now, maxTasks });
    const snapshot = this.broker.snapshot();
    return {
      submitted,
      snapshot,
      checkpointDigest: checkpointDigest(snapshot),
    };
  }

  async tick({ now = Date.now(), maxTasks = this.policy.maxDispatchPerTick } = {}) {
    const recovery = await this.recover({ now });
    if (!recovery.recoveryPlan.canContinue) {
      return {
        state: 'REPAIR_REQUIRED',
        recovery,
        checkpointDigest: recovery.checkpointDigest,
      };
    }
    const dispatch = await this.dispatchReady({ now, maxTasks });
    return {
      state: dispatch.snapshot.verdict === 'SUCCEEDED' ? 'SUCCEEDED' : 'RUNNABLE',
      recovery,
      dispatch,
      checkpointDigest: dispatch.checkpointDigest,
    };
  }

  retryDelay(attempt, key) {
    return retryDelayMs(attempt, {
      baseMs: this.policy.retryBaseMs,
      maxMs: this.policy.retryMaxMs,
      factor: this.policy.retryFactor,
      jitterRatio: this.policy.retryJitterRatio,
      key,
    });
  }
}
