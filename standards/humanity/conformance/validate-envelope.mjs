import { verifyIntegrityDigestHcs, HCS_CANONICALIZATION_PROFILE, HCS_INTEGRITY_TARGET_PROFILE } from '../runtime/canonicalize-hcs.mjs';

const ACTION_STATES = new Set(['PROPOSED','AUTHORIZED','ATTEMPTED','OBSERVED_COMPLETE','INFERRED_OUTCOME','FAILED','REVOKED']);
const EPISTEMIC = new Set(['OBSERVED','REPORTED','INFERRED','ASSUMED','PREDICTED','UNKNOWN','DISPUTED']);
const TOP_LEVEL = new Set(['hcsVersion','messageId','issuedAt','expiresAt','requiredProfiles','actor','authority','action','epistemic','provenance','dataPolicy','payload','payloadRef','evidenceRefs','extensions','integrity']);

function object(value) { return Boolean(value && typeof value === 'object' && !Array.isArray(value)); }
function nonEmptyString(value) { return typeof value === 'string' && value.length > 0; }
function validDate(value) { return typeof value === 'string' && Number.isFinite(Date.parse(value)); }

export function validateHcsEnvelope(envelope, options = {}) {
  const errors = [];
  const fail = (code, path = '$') => errors.push({ code, path });

  if (!object(envelope)) return { valid: false, errors: [{ code: 'ENVELOPE_OBJECT_REQUIRED', path: '$' }] };

  for (const key of Object.keys(envelope)) if (!TOP_LEVEL.has(key)) fail('UNKNOWN_TOP_LEVEL_FIELD', `$.${key}`);

  if (envelope.hcsVersion !== '0.1') fail('UNSUPPORTED_HCS_VERSION', '$.hcsVersion');
  if (!nonEmptyString(envelope.messageId) || envelope.messageId.length < 8 || envelope.messageId.length > 256) fail('INVALID_MESSAGE_ID', '$.messageId');
  if (!validDate(envelope.issuedAt)) fail('INVALID_ISSUED_AT', '$.issuedAt');
  if (envelope.expiresAt != null && !validDate(envelope.expiresAt)) fail('INVALID_EXPIRES_AT', '$.expiresAt');

  if (options.referenceTime != null && envelope.expiresAt && validDate(envelope.expiresAt)) {
    if (Date.parse(envelope.expiresAt) <= Date.parse(options.referenceTime)) fail('ENVELOPE_EXPIRED', '$.expiresAt');
  }

  if (!object(envelope.actor)) fail('ACTOR_REQUIRED', '$.actor');
  else {
    if (!nonEmptyString(envelope.actor.subjectId)) fail('SUBJECT_ID_REQUIRED', '$.actor.subjectId');
    if (!nonEmptyString(envelope.actor.identityRef)) fail('IDENTITY_REF_REQUIRED', '$.actor.identityRef');
  }

  if (!object(envelope.authority)) fail('AUTHORITY_REQUIRED', '$.authority');
  else {
    if (!nonEmptyString(envelope.authority.basis)) fail('AUTHORITY_BASIS_REQUIRED', '$.authority.basis');
    if (!Array.isArray(envelope.authority.scope) || envelope.authority.scope.length === 0 || envelope.authority.scope.some((v) => !nonEmptyString(v))) fail('AUTHORITY_SCOPE_REQUIRED', '$.authority.scope');
    if (!nonEmptyString(envelope.authority.revocationRef)) fail('REVOCATION_REF_REQUIRED', '$.authority.revocationRef');
    if (options.revokedRefs?.has?.(envelope.authority.revocationRef)) fail('AUTHORITY_REVOKED', '$.authority.revocationRef');
  }

  if (!object(envelope.action)) fail('ACTION_REQUIRED', '$.action');
  else {
    if (!nonEmptyString(envelope.action.type)) fail('ACTION_TYPE_REQUIRED', '$.action.type');
    if (!ACTION_STATES.has(envelope.action.state)) fail('INVALID_ACTION_STATE', '$.action.state');
    if (envelope.action.state === 'OBSERVED_COMPLETE' && (!Array.isArray(envelope.evidenceRefs) || envelope.evidenceRefs.length === 0)) fail('OBSERVED_COMPLETE_REQUIRES_EVIDENCE', '$.evidenceRefs');
  }

  if (!object(envelope.epistemic) || !EPISTEMIC.has(envelope.epistemic.class)) fail('INVALID_EPISTEMIC_CLASS', '$.epistemic.class');
  if (object(envelope.epistemic) && envelope.epistemic.confidence != null && (typeof envelope.epistemic.confidence !== 'number' || envelope.epistemic.confidence < 0 || envelope.epistemic.confidence > 1)) fail('INVALID_CONFIDENCE', '$.epistemic.confidence');

  if (!object(envelope.provenance) || !Array.isArray(envelope.provenance.sourceRefs) || envelope.provenance.sourceRefs.length === 0) fail('PROVENANCE_SOURCE_REQUIRED', '$.provenance.sourceRefs');

  if (envelope.requiredProfiles != null) {
    if (!Array.isArray(envelope.requiredProfiles) || envelope.requiredProfiles.some((v) => !nonEmptyString(v))) fail('INVALID_REQUIRED_PROFILES', '$.requiredProfiles');
    else if (options.supportedProfiles) {
      for (const profile of envelope.requiredProfiles) if (!options.supportedProfiles.has(profile)) fail('REQUIRED_PROFILE_UNSUPPORTED', '$.requiredProfiles');
    }
  }

  if (envelope.extensions != null) {
    if (!object(envelope.extensions)) fail('INVALID_EXTENSIONS', '$.extensions');
    else for (const key of Object.keys(envelope.extensions)) if (!(key.startsWith('https://') || key.startsWith('urn:'))) fail('INVALID_EXTENSION_NAMESPACE', `$.extensions.${key}`);
  }

  if (!object(envelope.integrity)) fail('INTEGRITY_REQUIRED', '$.integrity');
  else {
    const i = envelope.integrity;
    if (!nonEmptyString(i.mechanism)) fail('INTEGRITY_MECHANISM_REQUIRED', '$.integrity.mechanism');
    if (!nonEmptyString(i.evidenceRef)) fail('INTEGRITY_EVIDENCE_REF_REQUIRED', '$.integrity.evidenceRef');
    if (i.targetProfile !== HCS_INTEGRITY_TARGET_PROFILE) fail('UNSUPPORTED_INTEGRITY_TARGET', '$.integrity.targetProfile');
    if (i.canonicalization !== HCS_CANONICALIZATION_PROFILE) fail('UNSUPPORTED_CANONICALIZATION', '$.integrity.canonicalization');
    if (i.digestAlgorithm !== 'sha-256') fail('UNSUPPORTED_DIGEST_ALGORITHM', '$.integrity.digestAlgorithm');
    if (typeof i.digestValue !== 'string' || !/^[a-f0-9]{64}$/.test(i.digestValue)) fail('INVALID_DIGEST_VALUE', '$.integrity.digestValue');
    else {
      try { if (!verifyIntegrityDigestHcs(envelope)) fail('INTEGRITY_DIGEST_MISMATCH', '$.integrity.digestValue'); }
      catch { fail('INTEGRITY_CANONICALIZATION_FAILED', '$.integrity'); }
    }
  }

  return { valid: errors.length === 0, errors };
}
