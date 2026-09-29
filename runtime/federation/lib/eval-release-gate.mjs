const PASS_STATES = new Set(['PASS','VERIFIED','VERIFIED_DONE','VERIFIED_SCOPED','CLOSED']);
const CLOSED_GAP_STATES = new Set(['CLOSED','MITIGATED','VERIFIED_CLOSED']);

export const EVAL_RELEASE_GATE_VERSION = 'eval-release-gate/1.0.0';

function nonEmptyString(v){ return typeof v === 'string' && v.trim().length > 0; }
function hold(reasons, checkedAt){
  return { gateVersion:EVAL_RELEASE_GATE_VERSION, decision:'HOLD', eligible:false, checkedAt, reasons:[...new Set(reasons)] };
}

/**
 * Fail-closed promotion eligibility gate.
 * A passing result means only ELIGIBLE_FOR_SCOPED_REVIEW; it never self-promotes a release.
 */
export function evaluateReleasePromotion(input, { now = Date.now() } = {}) {
  const checkedAt = new Date(now).toISOString();
  if (!input || typeof input !== 'object' || Array.isArray(input)) return hold(['MALFORMED_INPUT'], checkedAt);

  const reasons = [];
  if (!nonEmptyString(input.candidateId)) reasons.push('MISSING_CANDIDATE_ID');
  if (!nonEmptyString(input.sourceFingerprint)) reasons.push('MISSING_SOURCE_FINGERPRINT');
  if (!nonEmptyString(input.rollbackRef)) reasons.push('MISSING_ROLLBACK');
  if (!Array.isArray(input.evals) || input.evals.length === 0) reasons.push('MISSING_EVALS');
  if (!Array.isArray(input.gaps)) reasons.push('MISSING_GAPS');
  if (reasons.length) return hold(reasons, checkedAt);

  for (const ev of input.evals) {
    if (!ev || typeof ev !== 'object' || !nonEmptyString(ev.evalId)) {
      reasons.push('MALFORMED_EVAL');
      continue;
    }
    const id = ev.evalId;
    if (!PASS_STATES.has(ev.status)) reasons.push(`EVAL_NOT_PASS:${id}`);
    if (!nonEmptyString(ev.candidateSourceFingerprint) || ev.candidateSourceFingerprint !== input.sourceFingerprint) {
      reasons.push(`SOURCE_MISMATCH:${id}`);
    }
    if (!nonEmptyString(ev.backendReceipt)) reasons.push(`MISSING_BACKEND_RECEIPT:${id}`);
    if (ev.independentEvidence !== true) reasons.push(`NON_INDEPENDENT_EVIDENCE:${id}`);
    const validUntil = Date.parse(ev.validUntil);
    if (!Number.isFinite(validUntil) || validUntil <= now) reasons.push(`STALE_OR_INVALID_EVAL:${id}`);
  }

  for (const gap of input.gaps) {
    if (!gap || typeof gap !== 'object') {
      reasons.push('MALFORMED_GAP');
      continue;
    }
    const critical = gap.criticality === 'P0' || gap.criticality === 'P0_HARD_EDGE';
    if (critical && !CLOSED_GAP_STATES.has(gap.status)) reasons.push(`P0_OPEN:${gap.gapId || 'UNKNOWN'}`);
  }

  if (reasons.length) return hold(reasons, checkedAt);
  return {
    gateVersion:EVAL_RELEASE_GATE_VERSION,
    decision:'ELIGIBLE_FOR_SCOPED_REVIEW',
    eligible:true,
    checkedAt,
    reasons:[],
    truthBoundary:'ELIGIBLE_FOR_SCOPED_REVIEW!=PROMOTED_RELEASE!=PLATFORM_PARITY'
  };
}
