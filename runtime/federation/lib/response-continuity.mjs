import { createHash } from 'node:crypto';

export const DEFAULT_RESPONSE_CONTINUITY_POLICY = Object.freeze({
  maxSilenceMs: 8_000,
  maxToolCallsWithoutVisibleUpdate: 2,
  preemptionMarginMs: 15_000,
  softTurnBudgetMs: 35_000,
  maxCriticalSectionMs: 20_000,
  foregroundHardCapMs: 45_000,
  maxTotalToolCallsPerTurn: 8,
  fastForegroundAckMs: 3_000,
  heavyForegroundPlannedToolThreshold: 2,
  heavyForegroundPlanStepThreshold: 4,
  preferDurableOffloadForHeavy: true,
  requireVerifiedCheckpointBeforeNonterminalYield: true,
  continueAfterCheckpointedTimeout: true,
  yieldForegroundOnHardCap: true,
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

export function deriveResponseStepIdempotencyKey({
  jobId,
  runId,
  phaseId,
  stepId,
  inputDigest = null,
} = {}) {
  if (!jobId) throw new Error('jobId is required');
  if (!runId) throw new Error('runId is required');
  if (!phaseId) throw new Error('phaseId is required');
  if (!stepId) throw new Error('stepId is required');
  return responseCheckpointDigest({
    schema: 'deus-response-step-idempotency/1',
    jobId: String(jobId),
    runId: String(runId),
    phaseId: String(phaseId),
    stepId: String(stepId),
    inputDigest: inputDigest == null ? null : String(inputDigest),
  });
}

export function buildTransactionalResponseCheckpoint({
  jobId,
  runId,
  continuityId = null,
  phaseId,
  stepId,
  stepStatus = 'PENDING',
  state = 'CHECKPOINTED_RUNNABLE',
  attempt = 1,
  inputDigest = null,
  outputRefs = [],
  verifiedFacts = [],
  latestReceipt = null,
  blocker = null,
  nextAction,
  idempotencyKey = null,
  sourceRevision = null,
  timestamp = new Date().toISOString(),
} = {}) {
  if (!jobId) throw new Error('jobId is required');
  if (!runId) throw new Error('runId is required');
  if (!phaseId) throw new Error('phaseId is required');
  if (!stepId) throw new Error('stepId is required');
  if (!nextAction) throw new Error('nextAction is required');
  const normalizedAttempt = Math.max(1, Math.trunc(boundedNumber(attempt, 1, { min: 1 })));
  const key = idempotencyKey == null
    ? deriveResponseStepIdempotencyKey({ jobId, runId, phaseId, stepId, inputDigest })
    : String(idempotencyKey);
  const envelope = Object.freeze({
    schema: 'deus-response-transaction-checkpoint/2',
    jobId: String(jobId),
    runId: String(runId),
    continuityId: continuityId == null ? null : String(continuityId),
    phaseId: String(phaseId),
    stepId: String(stepId),
    stepStatus: String(stepStatus),
    state: String(state),
    attempt: normalizedAttempt,
    idempotencyKey: key,
    inputDigest: inputDigest == null ? null : String(inputDigest),
    outputRefs: Object.freeze([...outputRefs].map(String)),
    verifiedFacts: Object.freeze([...verifiedFacts].map(String)),
    latestReceipt: latestReceipt == null ? null : String(latestReceipt),
    blocker: blocker == null ? null : String(blocker),
    nextAction: String(nextAction),
    sourceRevision: sourceRevision == null ? null : String(sourceRevision),
    timestamp: String(timestamp),
    resumeContract: 'EXACT_STEP_IDEMPOTENT_REPLAY_OR_KEEP_VERIFIED_OUTPUT',
    responseObligation: 'CHECKPOINT_THEN_EMIT_VISIBLE_UPDATE; FOREGROUND_HARD_CAP_HANDS_OFF_DURABLY_INSTEAD_OF_HOLDING_UI_ANALYSIS_OPEN',
    truthBoundary: 'TRANSACTION_CHECKPOINT_LIMITS_WORK_LOSS_AND_DUPLICATE_REPLAY__IT_DOES_NOT_CONTROL_PLATFORM_UI_DELIVERY_OR_EXTERNAL_SIDE_EFFECT_IDEMPOTENCY',
  });
  return Object.freeze({ ...envelope, digest: responseCheckpointDigest(envelope) });
}

export function transactionResumePlan(checkpoint = {}, {
  completedIdempotencyKeys = [],
} = {}) {
  if (!checkpoint?.jobId || !checkpoint?.runId || !checkpoint?.phaseId || !checkpoint?.stepId || !checkpoint?.idempotencyKey) {
    throw new Error('transactional checkpoint fields are required');
  }
  const completed = new Set([...completedIdempotencyKeys].map(String));
  const status = String(checkpoint.stepStatus ?? 'PENDING').toUpperCase();
  const keyAlreadyCompleted = completed.has(String(checkpoint.idempotencyKey));
  let action = 'RESUME_EXACT_STEP';
  let reason = 'STEP_NOT_VERIFIED';
  let replayExactStep = true;

  if (status === 'VERIFIED' || keyAlreadyCompleted) {
    action = 'KEEP_VERIFIED_STEP_AND_ADVANCE';
    reason = status === 'VERIFIED' ? 'CHECKPOINT_STEP_VERIFIED' : 'IDEMPOTENCY_KEY_ALREADY_COMPLETED';
    replayExactStep = false;
  } else if (status === 'EXECUTED' || status === 'WRITTEN') {
    action = 'VERIFY_EXISTING_OUTPUT_BEFORE_RETRY';
    reason = 'SIDE_EFFECT_MAY_ALREADY_EXIST';
    replayExactStep = false;
  }

  return Object.freeze({
    schema: 'deus-response-transaction-resume-plan/2',
    jobId: String(checkpoint.jobId),
    runId: String(checkpoint.runId),
    phaseId: String(checkpoint.phaseId),
    stepId: String(checkpoint.stepId),
    idempotencyKey: String(checkpoint.idempotencyKey),
    action,
    reason,
    replayExactStep,
    nextAction: checkpoint.nextAction == null ? null : String(checkpoint.nextAction),
    truthBoundary: 'RESUME_PLAN_PREVENTS_BLIND_REPLAY__EXTERNAL_SIDE_EFFECTS_STILL_REQUIRE_PROVIDER_SPECIFIC_READBACK_OR_IDEMPOTENCY_SUPPORT',
  });
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
  const totalToolCalls = Math.trunc(boundedNumber(input.totalToolCalls, toolCallsSinceVisibleUpdate));
  const plannedToolCalls = Math.trunc(boundedNumber(input.plannedToolCalls, 0));
  const plannedSteps = Math.trunc(boundedNumber(input.plannedSteps, 0));
  const foregroundComplexityClass = String(input.foregroundComplexityClass ?? 'NORMAL').toUpperCase();
  const durableExecutorAvailable = input.durableExecutorAvailable === true;
  const deadlineRemaining = input.uiDeadlineMsRemaining == null
    ? null
    : boundedNumber(input.uiDeadlineMsRemaining, 0);
  const turnElapsedMs = boundedNumber(input.turnElapsedMs, 0);
  const criticalSectionElapsedMs = boundedNumber(input.criticalSectionElapsedMs, 0);
  const predictablePreemption = deadlineRemaining != null && deadlineRemaining <= p.preemptionMarginMs;
  const softTurnBudgetExceeded = turnElapsedMs >= p.softTurnBudgetMs;
  const criticalSectionExceeded = criticalSectionElapsedMs >= p.maxCriticalSectionMs;
  const timeoutRisk = predictablePreemption || softTurnBudgetExceeded || criticalSectionExceeded;
  const foregroundHardCapExceeded = turnElapsedMs >= p.foregroundHardCapMs;
  const totalToolCallBudgetExceeded = totalToolCalls >= p.maxTotalToolCallsPerTurn;
  const analysisStallRisk = foregroundHardCapExceeded || totalToolCallBudgetExceeded;
  const explicitHeavyClass = new Set(['HEAVY', 'LONG', 'MULTI_STEP', 'TOOL_HEAVY', 'DEUS_MATERIAL']).has(foregroundComplexityClass);
  const heavyForegroundTask = explicitHeavyClass
    || plannedToolCalls > p.heavyForegroundPlannedToolThreshold
    || plannedSteps > p.heavyForegroundPlanStepThreshold;
  const fastForegroundOffload = p.preferDurableOffloadForHeavy === true
    && heavyForegroundTask
    && durableExecutorAvailable;
  const fastAckOverdue = !hasUserVisibleReply && turnElapsedMs >= p.fastForegroundAckMs;
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
  } else if (fastForegroundOffload && !checkpointVerified) {
    action = 'CHECKPOINT_FAST_ACK_AND_HANDOFF_NOW';
    reason = fastAckOverdue
      ? 'HEAVY_FOREGROUND_FAST_ACK_BUDGET_EXCEEDED_WITHOUT_CHECKPOINT'
      : 'HEAVY_FOREGROUND_REQUIRES_DURABLE_HANDOFF_CHECKPOINT';
  } else if (fastForegroundOffload) {
    action = hasUserVisibleReply
      ? 'HANDOFF_DURABLE_AND_RETURN_PARTIAL_NOW'
      : 'EMIT_FAST_ACK_AND_HANDOFF_DURABLE_NOW';
    reason = 'HEAVY_FOREGROUND_OFFLOADED_TO_DURABLE_EXECUTOR';
  } else if (analysisStallRisk && !checkpointVerified) {
    action = 'CHECKPOINT_THEN_HANDOFF_REPLY_NOW';
    reason = foregroundHardCapExceeded
      ? 'FOREGROUND_HARD_CAP_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT'
      : 'TOTAL_TOOL_CALL_BUDGET_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT';
  } else if (analysisStallRisk) {
    action = 'HANDOFF_AND_EMIT_PARTIAL_NOW';
    reason = foregroundHardCapExceeded
      ? 'FOREGROUND_HARD_CAP_EXCEEDED'
      : 'TOTAL_TOOL_CALL_BUDGET_EXCEEDED';
  } else if (timeoutRisk && !checkpointVerified) {
    action = 'CHECKPOINT_THEN_REPLY_NOW';
    reason = predictablePreemption
      ? 'PREDICTABLE_UI_PREEMPTION_WITHOUT_VERIFIED_CHECKPOINT'
      : softTurnBudgetExceeded
        ? 'SOFT_TURN_BUDGET_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT'
        : 'CRITICAL_SECTION_BUDGET_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT';
  } else if (timeoutRisk) {
    action = 'EMIT_PARTIAL_REPLY_NOW';
    reason = predictablePreemption
      ? 'PREDICTABLE_UI_PREEMPTION'
      : softTurnBudgetExceeded
        ? 'SOFT_TURN_BUDGET_EXCEEDED'
        : 'CRITICAL_SECTION_BUDGET_EXCEEDED';
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
  const checkpointRisk = waitingOrBlocked || timeoutRisk || analysisStallRisk || fastForegroundOffload;
  const timeoutMayYield = timeoutRisk && p.continueAfterCheckpointedTimeout !== true;
  const foregroundMustYield = (analysisStallRisk && p.yieldForegroundOnHardCap === true) || fastForegroundOffload;
  const yieldCondition = waitingOrBlocked || timeoutMayYield || foregroundMustYield;
  const solverContinuationRequired = nonterminal
    && !waitingOrBlocked
    && !foregroundMustYield
    && (!timeoutRisk || p.continueAfterCheckpointedTimeout === true);
  const turnEndAllowed = terminal || ownerStop || (
    nonterminal
    && yieldCondition
    && (!p.requireVerifiedCheckpointBeforeNonterminalYield || checkpointVerified)
    && hasUserVisibleReply
  );
  const actionWillEmitVisibleHandoff = new Set([
    'EMIT_FAST_ACK_AND_HANDOFF_DURABLE_NOW',
    'HANDOFF_DURABLE_AND_RETURN_PARTIAL_NOW',
    'HANDOFF_AND_EMIT_PARTIAL_NOW',
  ]).has(action);
  const turnEndAllowedAfterAction = turnEndAllowed || Boolean(
    nonterminal
    && checkpointVerified
    && yieldCondition
    && actionWillEmitVisibleHandoff
  );

  return Object.freeze({
    schema: 'deus-response-continuity-decision/1',
    action,
    reason,
    mustEmitUserVisible: action !== 'CONTINUE_WORK',
    checkpointRequiredBeforeYield: nonterminal
      && checkpointRisk
      && p.requireVerifiedCheckpointBeforeNonterminalYield
      && !checkpointVerified,
    turnEndAllowed,
    turnEndAllowedAfterAction,
    shouldContinueAfterVisibleUpdate: solverContinuationRequired,
    solverContinuationRequired,
    platformPreemptionSafe: checkpointVerified,
    timeoutContainmentTriggered: timeoutRisk,
    analysisStallContained: analysisStallRisk,
    fastForegroundOffload,
    heavyForegroundTask,
    fastAckOverdue,
    foregroundComplexityClass,
    plannedToolCalls,
    plannedSteps,
    durableExecutorAvailable,
    foregroundHardCapExceeded,
    totalToolCallBudgetExceeded,
    totalToolCalls,
    turnElapsedMs,
    criticalSectionElapsedMs,
    nextAction: input.nextAction == null ? null : String(input.nextAction),
    blocker: input.blocker == null ? null : String(input.blocker),
    policy: Object.freeze({
      maxSilenceMs: p.maxSilenceMs,
      maxToolCallsWithoutVisibleUpdate: p.maxToolCallsWithoutVisibleUpdate,
      preemptionMarginMs: p.preemptionMarginMs,
      softTurnBudgetMs: p.softTurnBudgetMs,
      maxCriticalSectionMs: p.maxCriticalSectionMs,
      foregroundHardCapMs: p.foregroundHardCapMs,
      maxTotalToolCallsPerTurn: p.maxTotalToolCallsPerTurn,
      fastForegroundAckMs: p.fastForegroundAckMs,
      heavyForegroundPlannedToolThreshold: p.heavyForegroundPlannedToolThreshold,
      heavyForegroundPlanStepThreshold: p.heavyForegroundPlanStepThreshold,
      preferDurableOffloadForHeavy: p.preferDurableOffloadForHeavy === true,
      requireVerifiedCheckpointBeforeNonterminalYield: p.requireVerifiedCheckpointBeforeNonterminalYield,
      continueAfterCheckpointedTimeout: p.continueAfterCheckpointedTimeout === true,
      yieldForegroundOnHardCap: p.yieldForegroundOnHardCap === true,
    }),
    truthBoundary: 'FAST_FOREGROUND_REDUCES_DEUS_SIDE_LONG_REASONING_AND_TOOL_CHAINS_BY_OFFLOADING_HEAVY_WORK__IT_CANNOT_DISABLE_OR_OVERRIDE_CHATGPT_PLATFORM_AUTOMATIC_REASONING_BEFORE_THIS_KERNEL_EXECUTES',
  });
}

export class ResponseContinuityGuard {
  constructor({ policy = {}, now = Date.now() } = {}) {
    this.policy = Object.freeze({ ...DEFAULT_RESPONSE_CONTINUITY_POLICY, ...policy });
    this.turnStartedAt = Number(now);
    this.criticalSectionStartedAt = Number(now);
    this.lastVisibleAt = Number(now);
    this.toolCallsSinceVisibleUpdate = 0;
    this.totalToolCalls = 0;
    this.materialProgressSinceVisible = false;
    this.hasUserVisibleReply = false;
    this.hasUserVisibleFinal = false;
  }

  markToolCall() {
    this.toolCallsSinceVisibleUpdate += 1;
    this.totalToolCalls += 1;
  }

  markMaterialProgress() {
    this.materialProgressSinceVisible = true;
  }

  markCriticalSectionStart({ now = Date.now() } = {}) {
    this.criticalSectionStartedAt = Number(now);
  }

  markCriticalSectionEnd({ now = Date.now() } = {}) {
    this.criticalSectionStartedAt = Number(now);
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
      turnElapsedMs: Math.max(0, Number(now) - this.turnStartedAt),
      criticalSectionElapsedMs: Math.max(0, Number(now) - this.criticalSectionStartedAt),
      toolCallsSinceVisibleUpdate: this.toolCallsSinceVisibleUpdate,
      totalToolCalls: this.totalToolCalls,
      materialProgressSinceVisible: this.materialProgressSinceVisible,
      hasUserVisibleReply: this.hasUserVisibleReply,
      hasUserVisibleFinal: this.hasUserVisibleFinal,
    }, this.policy);
  }
}
