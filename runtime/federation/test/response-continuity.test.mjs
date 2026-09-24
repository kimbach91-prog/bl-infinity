import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ResponseContinuityGuard,
  buildResponseCheckpoint,
  buildTransactionalResponseCheckpoint,
  deriveResponseStepIdempotencyKey,
  responseContinuityDecision,
  transactionResumePlan,
} from '../lib/response-continuity.mjs';

test('material progress cannot remain silent to the user', () => {
  const d = responseContinuityDecision({
    materialProgressSinceVisible: true,
    hasUserVisibleReply: false,
  });
  assert.equal(d.action, 'EMIT_PROGRESS_UPDATE');
  assert.equal(d.mustEmitUserVisible, true);
});

test('tool-call budget triggers a visible progress update', () => {
  const d = responseContinuityDecision({
    toolCallsSinceVisibleUpdate: 3,
    hasUserVisibleReply: false,
  });
  assert.equal(d.action, 'EMIT_PROGRESS_UPDATE');
  assert.equal(d.reason, 'MAX_TOOL_CALLS_WITHOUT_VISIBLE_UPDATE_EXCEEDED');
});

test('predictable preemption requires checkpoint before reply/yield', () => {
  const d = responseContinuityDecision({
    uiDeadlineMsRemaining: 5000,
    checkpointVerified: false,
    hasUserVisibleReply: false,
    nextAction: 'resume exact job',
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_REPLY_NOW');
  assert.equal(d.checkpointRequiredBeforeYield, true);
  assert.equal(d.turnEndAllowed, false);
});

test('verified checkpoint plus visible partial allows a genuine wait yield', () => {
  const d = responseContinuityDecision({
    criticalPathWaiting: true,
    checkpointVerified: true,
    hasUserVisibleReply: true,
  });
  assert.equal(d.action, 'CONTINUE_WORK');
  assert.equal(d.turnEndAllowed, true);
});

test('nonterminal blocker without checkpoint cannot silently end turn', () => {
  const d = responseContinuityDecision({
    hardBlocker: true,
    checkpointVerified: false,
    hasUserVisibleReply: false,
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_REPLY_NOW');
  assert.equal(d.turnEndAllowed, false);
});

test('verified done requires final reply before turn can close cleanly', () => {
  const d = responseContinuityDecision({
    jobState: 'VERIFIED_DONE',
    finalReady: true,
    hasUserVisibleFinal: false,
  });
  assert.equal(d.action, 'EMIT_FINAL_REPLY_NOW');
  assert.equal(d.mustEmitUserVisible, true);
});

test('guard resets silence/tool counters after visible update', () => {
  const g = new ResponseContinuityGuard({ now: 1000 });
  g.markToolCall();
  g.markToolCall();
  g.markMaterialProgress();
  assert.equal(g.decide({}, { now: 2000 }).action, 'EMIT_PROGRESS_UPDATE');
  g.markUserVisible({ now: 2000 });
  const d = g.decide({}, { now: 2500 });
  assert.equal(d.action, 'CONTINUE_WORK');
});

test('checkpoint envelope is deterministic and preserves exact next action', () => {
  const a = buildResponseCheckpoint({
    jobId: 'J1',
    nextAction: 'resume Vercel receipt readback',
    verifiedFacts: ['runtime pass'],
    timestamp: '2026-09-24T00:00:00Z',
  });
  const b = buildResponseCheckpoint({
    jobId: 'J1',
    nextAction: 'resume Vercel receipt readback',
    verifiedFacts: ['runtime pass'],
    timestamp: '2026-09-24T00:00:00Z',
  });
  assert.equal(a.digest, b.digest);
  assert.equal(a.nextAction, 'resume Vercel receipt readback');
  assert.match(a.responseObligation, /MUST_EMIT_USER_VISIBLE_REPLY/);
});


test('soft turn budget checkpoints even when platform deadline telemetry is unavailable', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 36_000,
    checkpointVerified: false,
    hasUserVisibleReply: true,
    nextAction: 'resume exact bounded unit',
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_REPLY_NOW');
  assert.equal(d.reason, 'SOFT_TURN_BUDGET_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT');
  assert.equal(d.timeoutContainmentTriggered, true);
  assert.equal(d.turnEndAllowed, false);
});

test('verified checkpoint at soft turn budget emits partial but keeps same-turn solver active', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 36_000,
    checkpointVerified: true,
    hasUserVisibleReply: true,
  });
  assert.equal(d.action, 'EMIT_PARTIAL_REPLY_NOW');
  assert.equal(d.reason, 'SOFT_TURN_BUDGET_EXCEEDED');
  assert.equal(d.shouldContinueAfterVisibleUpdate, true);
  assert.equal(d.solverContinuationRequired, true);
  assert.equal(d.turnEndAllowed, false);
});

test('visible progress does not reset total turn budget', () => {
  const g = new ResponseContinuityGuard({ now: 1_000 });
  g.markUserVisible({ now: 20_000 });
  const d = g.decide({ checkpointVerified: true }, { now: 37_000 });
  assert.equal(d.action, 'EMIT_PARTIAL_REPLY_NOW');
  assert.equal(d.reason, 'SOFT_TURN_BUDGET_EXCEEDED');
  assert.equal(d.shouldContinueAfterVisibleUpdate, true);
  assert.equal(d.turnEndAllowed, false);
  assert.ok(d.turnElapsedMs >= 36_000);
});

test('critical section budget triggers containment before a long blocking operation overruns the turn', () => {
  const d = responseContinuityDecision({
    criticalSectionElapsedMs: 21_000,
    checkpointVerified: false,
    hasUserVisibleReply: true,
    nextAction: 'resume after external call',
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_REPLY_NOW');
  assert.equal(d.reason, 'CRITICAL_SECTION_BUDGET_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT');
});


test('timeout risk requires checkpoint but does not become a solver-stop condition', () => {
  const d = responseContinuityDecision({
    uiDeadlineMsRemaining: 5000,
    checkpointVerified: false,
    hasUserVisibleReply: true,
    nextAction: 'persist exact cursor then continue',
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_REPLY_NOW');
  assert.equal(d.checkpointRequiredBeforeYield, true);
  assert.equal(d.solverContinuationRequired, true);
  assert.equal(d.turnEndAllowed, false);
});

test('transaction checkpoint derives stable idempotency key and exact resume cursor', () => {
  const input = {
    jobId: 'JOB-X',
    runId: 'RUN-7',
    continuityId: 'CONT-X',
    phaseId: 'PHASE-2',
    stepId: 'STEP-3',
    inputDigest: 'input-sha',
    nextAction: 'verify STEP-3 output then advance',
    timestamp: '2026-09-24T06:30:00Z',
  };
  const a = buildTransactionalResponseCheckpoint(input);
  const b = buildTransactionalResponseCheckpoint(input);
  assert.equal(a.digest, b.digest);
  assert.equal(a.idempotencyKey, b.idempotencyKey);
  assert.equal(a.idempotencyKey, deriveResponseStepIdempotencyKey(input));
  assert.equal(a.phaseId, 'PHASE-2');
  assert.equal(a.stepId, 'STEP-3');
  const plan = transactionResumePlan(a);
  assert.equal(plan.action, 'RESUME_EXACT_STEP');
  assert.equal(plan.replayExactStep, true);
});

test('transaction resume verifies possible side effects before retry and keeps verified steps', () => {
  const executed = buildTransactionalResponseCheckpoint({
    jobId: 'JOB-X',
    runId: 'RUN-7',
    phaseId: 'PHASE-2',
    stepId: 'WRITE-1',
    stepStatus: 'EXECUTED',
    latestReceipt: 'RCP-1',
    nextAction: 'read back WRITE-1',
    timestamp: '2026-09-24T06:30:00Z',
  });
  const verify = transactionResumePlan(executed);
  assert.equal(verify.action, 'VERIFY_EXISTING_OUTPUT_BEFORE_RETRY');
  assert.equal(verify.replayExactStep, false);

  const verified = buildTransactionalResponseCheckpoint({
    jobId: 'JOB-X',
    runId: 'RUN-7',
    phaseId: 'PHASE-2',
    stepId: 'WRITE-1',
    stepStatus: 'VERIFIED',
    nextAction: 'advance to WRITE-2',
    timestamp: '2026-09-24T06:31:00Z',
  });
  const keep = transactionResumePlan(verified);
  assert.equal(keep.action, 'KEEP_VERIFIED_STEP_AND_ADVANCE');
  assert.equal(keep.replayExactStep, false);
});


test('foreground hard cap hands off instead of keeping UI in analysis state', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 46_000,
    checkpointVerified: true,
    hasUserVisibleReply: true,
    nextAction: 'durable worker continues exact step',
  });
  assert.equal(d.action, 'HANDOFF_AND_EMIT_PARTIAL_NOW');
  assert.equal(d.reason, 'FOREGROUND_HARD_CAP_EXCEEDED');
  assert.equal(d.analysisStallContained, true);
  assert.equal(d.solverContinuationRequired, false);
  assert.equal(d.shouldContinueAfterVisibleUpdate, false);
  assert.equal(d.turnEndAllowed, true);
});

test('foreground hard cap requires checkpoint before handoff', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 46_000,
    checkpointVerified: false,
    hasUserVisibleReply: true,
    nextAction: 'checkpoint exact cursor then handoff',
  });
  assert.equal(d.action, 'CHECKPOINT_THEN_HANDOFF_REPLY_NOW');
  assert.equal(d.reason, 'FOREGROUND_HARD_CAP_EXCEEDED_WITHOUT_VERIFIED_CHECKPOINT');
  assert.equal(d.checkpointRequiredBeforeYield, true);
  assert.equal(d.turnEndAllowed, false);
});

test('total tool calls trigger foreground handoff even when visible updates reset local counter', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 20_000,
    toolCallsSinceVisibleUpdate: 1,
    totalToolCalls: 8,
    checkpointVerified: true,
    hasUserVisibleReply: true,
  });
  assert.equal(d.action, 'HANDOFF_AND_EMIT_PARTIAL_NOW');
  assert.equal(d.reason, 'TOTAL_TOOL_CALL_BUDGET_EXCEEDED');
  assert.equal(d.totalToolCallBudgetExceeded, true);
  assert.equal(d.solverContinuationRequired, false);
});

test('guard visible updates do not reset total tool-call budget', () => {
  const g = new ResponseContinuityGuard({ now: 1_000 });
  for (let i = 0; i < 4; i += 1) g.markToolCall();
  g.markUserVisible({ now: 5_000 });
  for (let i = 0; i < 4; i += 1) g.markToolCall();
  const d = g.decide({ checkpointVerified: true }, { now: 10_000 });
  assert.equal(d.totalToolCalls, 8);
  assert.equal(d.action, 'HANDOFF_AND_EMIT_PARTIAL_NOW');
  assert.equal(d.turnEndAllowed, true);
});
