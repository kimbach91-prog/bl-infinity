import { createHash } from 'node:crypto';

export const UAC_V1_VERSION = '1.0.0';

export const UAC_EFFECT_CLASSES = Object.freeze([
  'READ_ONLY',
  'REVERSIBLE_WRITE',
  'IRREVERSIBLE',
  'FINANCIAL',
  'PROTECTED',
]);

export const UAC_DATA_CLASSES = Object.freeze([
  'BL-S0_PUBLIC',
  'BL-S1_CONTROL',
  'PUBLIC',
  'CONTROL',
  'PRIVATE',
  'SEALED',
  'TASK_SPECIFIC',
]);

export const UAC_LANGUAGE_BOUNDARIES = Object.freeze([
  'INTERNAL_TEXTLESS',
  'TEXT_REQUIRED',
  'OWNER_UI',
  'HUMAN_DOC',
  'EXTERNAL_LANGUAGE_INTERFACE',
]);

const HARD_EDGE_EFFECTS = new Set(['IRREVERSIBLE', 'FINANCIAL', 'PROTECTED']);

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isNonEmptyObject(value) {
  return isObject(value) && Object.keys(value).length > 0;
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function checkFiniteNonNegativeObject(value, path, errors) {
  if (!isNonEmptyObject(value)) {
    errors.push(`${path}: required non-empty object`);
    return;
  }
  let hasFiniteCeiling = false;
  for (const [key, raw] of Object.entries(value)) {
    if (raw === null || raw === undefined) continue;
    if (typeof raw === 'number') {
      if (!Number.isFinite(raw) || raw < 0) errors.push(`${path}.${key}: must be finite and nonnegative`);
      else hasFiniteCeiling = true;
    }
  }
  if (!hasFiniteCeiling) errors.push(`${path}: must contain at least one finite nonnegative numeric ceiling`);
}

function normalizeContext(context = {}) {
  return {
    longHorizon: context.longHorizon === true,
    internalHandoff: context.internalHandoff === true,
    optimizedHandoff: context.optimizedHandoff === true,
    accelerationRequested: context.accelerationRequested === true,
    hardEdgeReceiptRef: context.hardEdgeReceiptRef ?? null,
  };
}

export function validateUacV1(envelope, context = {}) {
  const c = normalizeContext(context);
  const errors = [];
  if (!isObject(envelope)) return { ok: false, errors: ['envelope: required object'] };

  if (envelope.contract_version !== UAC_V1_VERSION) errors.push('contract_version: must equal 1.0.0');
  if (!nonEmptyString(envelope.principal_id)) errors.push('principal_id: required non-empty string');
  if (!isNonEmptyObject(envelope.capability_descriptor)) errors.push('capability_descriptor: required non-empty object');
  if (!isNonEmptyObject(envelope.input_schema)) errors.push('input_schema: required non-empty object');
  if (!isNonEmptyObject(envelope.output_schema)) errors.push('output_schema: required non-empty object');

  if (!UAC_EFFECT_CLASSES.includes(envelope.effect_class)) {
    errors.push(`effect_class: unknown value ${String(envelope.effect_class)}`);
  }
  if (!UAC_DATA_CLASSES.includes(envelope.data_class)) {
    errors.push(`data_class: unknown value ${String(envelope.data_class)}`);
  }

  const hasEffect = UAC_EFFECT_CLASSES.includes(envelope.effect_class) && envelope.effect_class !== 'READ_ONLY';
  if (hasEffect && !nonEmptyString(envelope.authority_ref)) {
    errors.push('authority_ref: required for effects');
  }
  if (envelope.effect_class === 'REVERSIBLE_WRITE' && !isNonEmptyObject(envelope.rollback_contract)) {
    errors.push('rollback_contract: required for reversible write');
  }
  if (HARD_EDGE_EFFECTS.has(envelope.effect_class) && !nonEmptyString(c.hardEdgeReceiptRef)) {
    errors.push('hard_edge_receipt_ref: explicit protected-boundary receipt required');
  }

  checkFiniteNonNegativeObject(envelope.budget, 'budget', errors);

  if (!isNonEmptyObject(envelope.freshness)) errors.push('freshness: required non-empty object');
  if (!isNonEmptyObject(envelope.receipt_contract)) errors.push('receipt_contract: required non-empty object');
  if (!isNonEmptyObject(envelope.quality_gate)) errors.push('quality_gate: required non-empty object');

  if (c.longHorizon && !isNonEmptyObject(envelope.handoff_state)) {
    errors.push('handoff_state: required for long-horizon work');
  }
  if (c.internalHandoff && !(isNonEmptyObject(envelope.internal_representation) || nonEmptyString(envelope.internal_representation))) {
    errors.push('internal_representation: required for internal handoff');
  }
  if (!UAC_LANGUAGE_BOUNDARIES.includes(envelope.language_boundary)) {
    errors.push(`language_boundary: unknown value ${String(envelope.language_boundary)}`);
  }
  if (!(isNonEmptyObject(envelope.output_plane_contract) || nonEmptyString(envelope.output_plane_contract))) {
    errors.push('output_plane_contract: required');
  }
  if (c.optimizedHandoff && !(isNonEmptyObject(envelope.context_codec) || nonEmptyString(envelope.context_codec))) {
    errors.push('context_codec: required for optimized handoff');
  }
  if (c.accelerationRequested && !(isNonEmptyObject(envelope.output_acceleration_plan) || nonEmptyString(envelope.output_acceleration_plan))) {
    errors.push('output_acceleration_plan: required when acceleration is requested');
  }

  return { ok: errors.length === 0, errors };
}

export function assertUacV1(envelope, context = {}) {
  const verdict = validateUacV1(envelope, context);
  if (!verdict.ok) {
    const error = new Error(`UAC_V1_INVALID: ${verdict.errors.join('; ')}`);
    error.code = 'UAC_V1_INVALID';
    error.validationErrors = verdict.errors;
    throw error;
  }
  return envelope;
}

export function compileLegacyTaskToUacV1({
  task,
  principalId,
  capabilityDescriptor,
  inputSchema,
  outputSchema,
  effectClass = 'READ_ONLY',
  dataClass = null,
  authorityRef = null,
  budget,
  freshness,
  receiptContract,
  rollbackContract = null,
  qualityGate,
  handoffState = null,
  internalRepresentation = null,
  languageBoundary = 'INTERNAL_TEXTLESS',
  outputPlaneContract = 'INTERNAL_COMMAND',
  contextCodec = null,
  outputAccelerationPlan = null,
  context = {},
} = {}) {
  if (!isObject(task)) throw new Error('UAC_V1_COMPILE: task object required');
  const envelope = {
    contract_version: UAC_V1_VERSION,
    principal_id: principalId,
    capability_descriptor: capabilityDescriptor ?? { capability: task.capability },
    input_schema: inputSchema,
    output_schema: outputSchema,
    effect_class: effectClass,
    data_class: dataClass ?? task.dataClass,
    authority_ref: authorityRef,
    budget,
    freshness,
    receipt_contract: receiptContract,
    rollback_contract: rollbackContract,
    quality_gate: qualityGate,
    handoff_state: handoffState,
    internal_representation: internalRepresentation,
    language_boundary: languageBoundary,
    output_plane_contract: outputPlaneContract,
    context_codec: contextCodec,
    output_acceleration_plan: outputAccelerationPlan,
    task: structuredClone(task),
  };
  assertUacV1(envelope, context);
  return envelope;
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (!isObject(value)) return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
}

export function uacV1Digest(envelope, context = {}) {
  assertUacV1(envelope, context);
  return createHash('sha256').update(JSON.stringify(canonicalize(envelope))).digest('hex');
}
