import { createHash } from 'node:crypto';

export const DEFAULT_RESPONSE_CONTINUITY_POLICY = Object.freeze({
  maxSilenceMs: 15_000,
  maxToolCallsWithoutVisibleUpdate: 3,
  preemptionMarginMs: 8_000,
  requireVerifiedCheckpointBeforeNonterminalYield: true,
});

const TERMINAL_STATES = new Set(['VERIFIED_DONE', 'OWNER_STOP', 'BLOCKED_HARD']);

function boundedNumber(value, fallback, { min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
}

export function responseCheckpointDigest(envelope = {}) {
  return createHash('sha256').update(JSON.stringify(stable(envelope))).digest('hex');
}

export function buildResponseCheckpoint({
  jobId,
  continuityId = null,
  phase = null,
  state = 'CHECKPOINTED_RUNNABLE',
  verifiedFacts = [],
  artifactRefs = [],
  latestReceipt = null,
  blocker = null,
  nextAction,
  sourceRevision = null,
  timestamp = new Date().toISOString(),
} = {}) {
  if (!jobId) throw new Error('jobId is required');
  if (!nextAction) throw new Error('nextAction is required');
  const envelope = Object.freeze({
    schema: 'deus-response-continuity-checkpoint/1',
    jobId: String(jobId),
    continuityId: continuityId == null ? null : String(continuityId),
    phase: phase == null ? null : String(phase),
    state: String(state),
    verifiedFacts: Object.freeze([...verifiedFacts].map(String)),
    artifactRefs: Object.freeze([...artifactRefs].map(String)),
    latestReceipt: latestReceipt == null ? null : String(latestReceipt),
    blocker: blocker == null ? null : String(blocker),
    nextAction: String(nextAction),
    sourceRevision: sourceRevision == null ? null : String(sourceRevision),
    timestamp: String(timestamp),
    responseObligation: 'MUST_EMIT_USER_VISIBLE_REPLY_BEFORE_PREDICTABLE_YIELD',
    truthBoundary: 'CHECKPOINT_PRESERVES_WORK_STATE_BUT_DOES_NOT_PROVE_USER_SAW_A_REPLY',
  });
  return Object.freeze({ ...envelope, digest: responseCheckpointDigest(envelope) });
}

export function responseContinuityDecision(input = {}, policy = {}) {
  const p = { ...DEFAULT_RESPONSE_CONTINUITY_POLICY, ...policy };
  const jobState = String(input.jobState ?? 'RUNNABLE');
  const terminal = input.terminal === true || TERMINAL_STATES.has(jobState);
  const ownerStop = input.ownerStop === true || jobState === 'OWNER_STOP';
  const finalReady = input.finalReady === true || jobState === 'VERIFIED_DONE';
  const hardBlocker = input.hardBlocker === true || jobState === 'BLOCKED_HARD';
  const criticalPathWaiting = input.criticalPathWaiting === true;
  const checkpointVerified = input.checkpointVerified === true;
  const hasUserVisibleFinal = input.hasUserVisibleFinal === true;
  const hasUserVisibleReply = input.hasUserVisibleReply === true || hasUserVisibleFinal;
  const materialProgressSinceVisible = input.materialProgressSinceVisible === true;
  const msSinceVisibleUpdate = boundedNumber(input.msSinceVisibleUpdate, 0);
  const toolCallsSinceVisibleUpdate = Math.trunc(boundedNumber(input.toolCallsSinceVisibleUpdate, 0));
  const deadlineRemaining = input.uiDeadlineMsRemaining == null
    ? null
    : boundedNumber(input.uiDeadlineMsRemaining, 0);
  const predictablePreemption = deadlineRemaining != null && deadlineRemaining <= p.preemptionMarginMs;
  const silenceExceeded = msSinceVisibleUpdate >= p.maxSilenceMs;
  const toolBudgetExceeded = toolCallsSinceVisibleUpdate >= p.maxToolCallsWithoutVisibleUpdate;
  const waitingOrBlocked = criticalPathWaiting || hardBlocker;

  let action = 'CONTINUE_WORK';
  let reason = 'NO_RESPONSE_CONTINUITY_TRIGGER';

  if (finalReady && !hasUserVisibleFinal) {
    action = 'EMIT_FINAL_REPLY_NOW';
    reason = 'FINAL_READY_BUT_NOT_YET_USER_VISIBLE';
  } else if (ownerStop && !hasUserVisibleReply) {
    action = 'EMIT_STOP_ACK_NOW';
    reason = 'OWNER_STOP_REQUIRES_VISIBLE_ACK';
  } else if (predictablePreemption && !checkpointVerified) {
    action = 'CHECKPOINT_THEN_REPLY_NOW';
    reason = 'PREDICTABLE_UI_PREEMPTION_WITHOUT_VERIFIED_CHECKPOINT';
  } else if (predictablePreemption) {
    action = 'EMIT_PARTIAL_REPLY_NOW';
    reason = 'PREDICTABLE_UI_PREEMPTION';
  } else if (waitingOrBlocked && !checkpointVerified) {
    action = 'CHECKPOINT_THEN_REPLY_NOW';
    reason = 'NONTERMINAL_WAIT_OR_BLOCK_WITHOUT_VERIFIED_CHECKPOINT';
  } else if (waitingOrBlocked && !hasUserVisibleReply) {
    action = 'EMIT_PARTIAL_REPLY_NOW';
    reason = 'NONTERMINAL_WAIT_OR_BLOCK_REQUIRES_VISIBLE_STATUS';
  } else if (!hasUserVisibleReply && (silenceExceeded || toolBudgetExceeded || materialProgressSinceVisible)) {
    action = 'EMIT_PROGRESS_UPDATE';
    reason = silenceExceeded
      ? 'MAX_VISIBLE_SILENCE_EXCEEDED'
      : toolBudgetExceeded
        ? 'MAX_TOOL_CALLS_WITHOUT_VISIBLE_UPDATE_EXCEEDED'
        : 'MATERIAL_PROGRESS_NOT_YET_USER_VISIBLE';
  }

  const nonterminal = !terminal;
  const yieldCondition = waitingOrBlocked || predictablePreemption;
  const turnEndAllowed = terminal || ownerStop || (
    nonterminal
    && yieldCondition
    && (!p.requireVerifiedCheckpointBeforeNonterminalYield || checkpointVerified)
    && hasUserVisibleReply
  );

  return Object.freeze({
    schema: 'deus-response-continuity-decision/1',
    action,
    reason,
    mustEmitUserVisible: action !== 'CONTINUE_WORK',
    checkpointRequiredBeforeYield: nonterminal
      && yieldCondition
      && p.requireVerifiedCheckpointBeforeNonterminalYield
      && !checkpointVerified,
    turnEndAllowed,
    shouldContinueAfterVisibleUpdate: !terminal && !waitingOrBlocked,
    nextAction: input.nextAction == null ? null : String(input.nextAction),
    blocker: input.blocker == null ? null : String(input.blocker),
    policy: Object.freeze({
      maxSilenceMs: p.maxSilenceMs,
      maxToolCallsWithoutVisibleUpdate: p.maxToolCallsWithoutVisibleUpdate,
      preemptionMarginMs: p.preemptionMarginMs,
      requireVerifiedCheckpointBeforeNonterminalYield: p.requireVerifiedCheckpointBeforeNonterminalYield,
    }),
    truthBoundary: 'USER_VISIBLE_UPDATE_REQUIRED_IS_A_CONTROL_OBLIGATION__PLATFORM_DELIVERY_ACK_REMAINS_EXTERNAL_TO_THIS_KERNEL',
  });
}

export class ResponseContinuityGuard {
  constructor({ policy = {}, now = Date.now() } = {}) {
    this.policy = Object.freeze({ ...DEFAULT_RESPONSE_CONTINUITY_POLICY, ...policy });
    this.lastVisibleAt = Number(now);
    this.toolCallsSinceVisibleUpdate = 0;
    this.materialProgressSinceVisible = false;
    this.hasUserVisibleReply = false;
    this.hasUserVisibleFinal = false;
  }

  markToolCall() {
    this.toolCallsSinceVisibleUpdate += 1;
  }

  markMaterialProgress() {
    this.materialProgressSinceVisible = true;
  }

  markUserVisible({ final = false, now = Date.now() } = {}) {
    this.lastVisibleAt = Number(now);
    this.toolCallsSinceVisibleUpdate = 0;
    this.materialProgressSinceVisible = false;
    this.hasUserVisibleReply = true;
    if (final) this.hasUserVisibleFinal = true;
  }

  decide(input = {}, { now = Date.now() } = {}) {
    return responseContinuityDecision({
      ...input,
      msSinceVisibleUpdate: Math.max(0, Number(now) - this.lastVisibleAt),
      toolCallsSinceVisibleUpdate: this.toolCallsSinceVisibleUpdate,
      materialProgressSinceVisible: this.materialProgressSinceVisible,
      hasUserVisibleReply: this.hasUserVisibleReply,
      hasUserVisibleFinal: this.hasUserVisibleFinal,
    }, this.policy);
  }
}
