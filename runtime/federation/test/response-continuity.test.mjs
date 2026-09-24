import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ResponseContinuityGuard,
  buildResponseCheckpoint,
  responseContinuityDecision,
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

test('verified checkpoint at soft turn budget emits partial and stops same-turn continuation', () => {
  const d = responseContinuityDecision({
    turnElapsedMs: 36_000,
    checkpointVerified: true,
    hasUserVisibleReply: true,
  });
  assert.equal(d.action, 'EMIT_PARTIAL_REPLY_NOW');
  assert.equal(d.reason, 'SOFT_TURN_BUDGET_EXCEEDED');
  assert.equal(d.shouldContinueAfterVisibleUpdate, false);
  assert.equal(d.turnEndAllowed, true);
});

test('visible progress does not reset total turn budget', () => {
  const g = new ResponseContinuityGuard({ now: 1_000 });
  g.markUserVisible({ now: 20_000 });
  const d = g.decide({ checkpointVerified: true }, { now: 37_000 });
  assert.equal(d.action, 'EMIT_PARTIAL_REPLY_NOW');
  assert.equal(d.reason, 'SOFT_TURN_BUDGET_EXCEEDED');
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
