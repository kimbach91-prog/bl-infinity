import { authorizeHmiRequest } from './access-policy.mjs';

const OPAQUE_REF = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const CONTROL_CHAR = /[\u0000-\u001f\u007f]/;
const EXPORT_FORMATS = new Set(['json', 'csv', 'pdf']);
const WORKFLOW_DECISIONS = new Set(['approve', 'reject']);

function isPlainRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function isBoundedText(value, { min = 0, max }) {
  return typeof value === 'string'
    && value.length >= min
    && value.length <= max
    && !CONTROL_CHAR.test(value);
}

function isOptionalText(value, max) {
  return value === undefined || isBoundedText(value, { max });
}

function isOpaqueRef(value) {
  return typeof value === 'string' && OPAQUE_REF.test(value);
}

function isOptionalOpaqueRef(value) {
  return value === undefined || isOpaqueRef(value);
}

function isOpaqueRefList(value) {
  return value === undefined
    || (Array.isArray(value)
      && value.length <= 32
      && value.every(isOpaqueRef));
}

function validateTaskCreate(payload) {
  return isBoundedText(payload.title, { min: 1, max: 200 })
    && isBoundedText(payload.objective, { min: 1, max: 4_000 })
    && isOptionalOpaqueRef(payload.deadlineRef)
    && isOpaqueRefList(payload.evidenceRefs);
}

function validateTaskCancel(payload) {
  return isOpaqueRef(payload.taskRef)
    && isBoundedText(payload.reason, { min: 1, max: 1_000 });
}

function validateEvidenceAttach(payload) {
  return isOpaqueRef(payload.taskRef)
    && isOpaqueRef(payload.evidenceRef)
    && isOptionalText(payload.note, 2_000);
}

function validateResultExport(payload) {
  return isOpaqueRef(payload.resultRef)
    && EXPORT_FORMATS.has(payload.format)
    && isOptionalText(payload.purpose, 512);
}

function validateWorkflowApprove(payload) {
  return isOpaqueRef(payload.workflowRef)
    && WORKFLOW_DECISIONS.has(payload.decision)
    && isOptionalText(payload.note, 2_000);
}

const ACTIONS = new Map([
  ['task.create', {
    scope: 'hmi:task:create',
    allowedKeys: new Set(['title', 'objective', 'deadlineRef', 'evidenceRefs']),
    maxBytes: 16_384,
    stepUp: false,
    validate: validateTaskCreate,
  }],
  ['task.cancel', {
    scope: 'hmi:task:cancel',
    allowedKeys: new Set(['taskRef', 'reason']),
    maxBytes: 4_096,
    stepUp: true,
    validate: validateTaskCancel,
  }],
  ['evidence.attach', {
    scope: 'hmi:evidence:attach',
    allowedKeys: new Set(['taskRef', 'evidenceRef', 'note']),
    maxBytes: 8_192,
    stepUp: false,
    validate: validateEvidenceAttach,
  }],
  ['result.export', {
    scope: 'hmi:result:export',
    allowedKeys: new Set(['resultRef', 'format', 'purpose']),
    maxBytes: 4_096,
    stepUp: true,
    validate: validateResultExport,
  }],
  ['workflow.approve', {
    scope: 'hmi:workflow:approve',
    allowedKeys: new Set(['workflowRef', 'decision', 'note']),
    maxBytes: 4_096,
    stepUp: true,
    validate: validateWorkflowApprove,
  }],
]);

const FORBIDDEN_ACTION = /^(core|internal|prompt|evolution|router|lineage|trace|secret|topology|corpus|canonical)([.:/]|$)/i;
const MAX_STEP_UP_AGE_MS = 5 * 60_000;

function deny(code) {
  return { ok: false, code };
}

function byteLength(value) {
  try {
    const serialized = JSON.stringify(value ?? {});
    return typeof serialized === 'string' ? Buffer.byteLength(serialized, 'utf8') : Number.POSITIVE_INFINITY;
  } catch {
    return Number.POSITIVE_INFINITY;
  }
}

export function authorizeHmiAction({ session, tenant, action, now = Date.now() }) {
  const actionId = typeof action?.id === 'string' ? action.id : '';
  if (!actionId || FORBIDDEN_ACTION.test(actionId)) return deny('CORE_ACTION_FORBIDDEN');

  const base = authorizeHmiRequest({
    session,
    tenant,
    request: {
      path: '/actions',
      tenantId: action?.tenantId ?? tenant?.id,
      dataClass: action?.dataClass ?? 'internal',
    },
    now,
  });
  if (!base.ok) return base;

  const definition = ACTIONS.get(actionId);
  if (!definition) return deny('ACTION_NOT_EXPOSED');

  const scopes = new Set(Array.isArray(session?.scopes) ? session.scopes : []);
  if (!scopes.has(definition.scope)) return deny('ACTION_SCOPE_REQUIRED');

  const payload = action?.payload ?? {};
  if (!isPlainRecord(payload)) return deny('INVALID_ACTION_PAYLOAD');
  if (byteLength(payload) > definition.maxBytes) return deny('ACTION_PAYLOAD_TOO_LARGE');
  for (const key of Object.keys(payload)) {
    if (!definition.allowedKeys.has(key)) return deny('ACTION_FIELD_NOT_ALLOWED');
  }
  if (!definition.validate(payload)) return deny('ACTION_FIELD_VALUE_INVALID');

  if (definition.stepUp) {
    if (action?.confirmed !== true) return deny('EXPLICIT_CONFIRMATION_REQUIRED');
    const stepUpAt = Number(session?.stepUpAt);
    if (!Number.isFinite(stepUpAt) || stepUpAt > now || now - stepUpAt > MAX_STEP_UP_AGE_MS) return deny('RECENT_STEP_UP_REQUIRED');
  }

  return {
    ok: true,
    code: 'HMI_ACTION_AUTHORIZED',
    command: {
      schemaVersion: 'deus-hmi-command/v1',
      tenantId: tenant.id,
      principal: session.identityId,
      actionId,
      payload: structuredClone(payload),
      policyVersion: session.policyVersion,
      authorizedAt: now,
    },
  };
}

export const exposedHmiActionIds = Object.freeze([...ACTIONS.keys()]);
