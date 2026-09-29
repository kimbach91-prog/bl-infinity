import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EVAL_RELEASE_GATE_VERSION,
  evaluateReleasePromotion,
} from '../lib/eval-release-gate.mjs';

const NOW = Date.parse('2026-09-29T10:00:00Z');
const FP = 'sha256:candidate-source-fingerprint';

function passingCandidate(overrides = {}) {
  return {
    candidateId: 'candidate-1',
    sourceFingerprint: FP,
    rollbackRef: 'git:rollback-ref',
    evals: [{
      evalId: 'EVAL-PLATFORM-PARITY-V1',
      status: 'VERIFIED_SCOPED',
      candidateSourceFingerprint: FP,
      backendReceipt: 'RCP-BACKEND-001',
      independentEvidence: true,
      validUntil: '2026-10-29T10:00:00Z',
    }],
    gaps: [
      { gapId: 'P0-INT-001', criticality: 'P0', status: 'VERIFIED_CLOSED' },
      { gapId: 'P1-EXT-001', criticality: 'P1', status: 'OPEN' },
    ],
    ...overrides,
  };
}

test('version is explicit and stable for receipt attribution', () => {
  assert.equal(EVAL_RELEASE_GATE_VERSION, 'eval-release-gate/1.0.0');
});

test('eligible result is review-only and never self-promotes parity', () => {
  const out = evaluateReleasePromotion(passingCandidate(), { now: NOW });
  assert.equal(out.eligible, true);
  assert.equal(out.decision, 'ELIGIBLE_FOR_SCOPED_REVIEW');
  assert.match(out.truthBoundary, /!=PROMOTED_RELEASE!=PLATFORM_PARITY/);
});

test('fails closed on malformed or missing identity/rollback/eval inputs', () => {
  const out = evaluateReleasePromotion({
    sourceFingerprint: FP,
    evals: [],
    gaps: [],
  }, { now: NOW });
  assert.equal(out.eligible, false);
  assert.equal(out.decision, 'HOLD');
  assert.ok(out.reasons.includes('MISSING_CANDIDATE_ID'));
  assert.ok(out.reasons.includes('MISSING_ROLLBACK'));
  assert.ok(out.reasons.includes('MISSING_EVALS'));
});

test('rejects evaluation bound to a different source fingerprint', () => {
  const c = passingCandidate();
  c.evals[0].candidateSourceFingerprint = 'sha256:other';
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('SOURCE_MISMATCH:EVAL-PLATFORM-PARITY-V1'));
});

test('requires an attributable backend receipt', () => {
  const c = passingCandidate();
  c.evals[0].backendReceipt = '';
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('MISSING_BACKEND_RECEIPT:EVAL-PLATFORM-PARITY-V1'));
});

test('requires evidence separation instead of circular self-grade', () => {
  const c = passingCandidate();
  c.evals[0].independentEvidence = false;
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('NON_INDEPENDENT_EVIDENCE:EVAL-PLATFORM-PARITY-V1'));
});

test('invalidates stale evaluation evidence', () => {
  const c = passingCandidate();
  c.evals[0].validUntil = '2026-09-29T09:59:59Z';
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('STALE_OR_INVALID_EVAL:EVAL-PLATFORM-PARITY-V1'));
});

test('blocks an unmitigated internal P0 gap', () => {
  const c = passingCandidate({
    gaps: [{ gapId: 'P0-UAC', criticality: 'P0', status: 'OPEN' }],
  });
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('P0_OPEN:P0-UAC'));
});

test('blocks an unmitigated hard-edge P0 gap without misclassifying it as internal failure', () => {
  const c = passingCandidate({
    gaps: [{ gapId: 'P0-OAUTH', criticality: 'P0_HARD_EDGE', status: 'HOLD_EXTERNAL' }],
  });
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, false);
  assert.ok(out.reasons.includes('P0_OPEN:P0-OAUTH'));
});

test('closed and mitigated P0 gaps can pass when every other gate is valid', () => {
  const c = passingCandidate({
    gaps: [
      { gapId: 'P0-A', criticality: 'P0', status: 'CLOSED' },
      { gapId: 'P0-B', criticality: 'P0', status: 'MITIGATED' },
      { gapId: 'P0-C', criticality: 'P0_HARD_EDGE', status: 'VERIFIED_CLOSED' },
    ],
  });
  const out = evaluateReleasePromotion(c, { now: NOW });
  assert.equal(out.eligible, true);
});
