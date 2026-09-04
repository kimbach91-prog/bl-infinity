import { authorizeHmiRequest } from './access-policy.mjs';

const ACTIONS = new Map([
  ['task.create', {
    scope: 'hmi:task:create',
    allowedKeys: new Set(['title', 'objective', 'deadlineRef', 'evidenceRefs']),
    maxBytes: 16_384,
    stepUp: false,
  }],
  ['task.cancel', {
    scope: 'hmi:task:cancel',
    allowedKeys: new Set(['taskRef', 'reason']),
    maxBytes: 4_096,
    stepUp: true,
  }],
  ['evidence.attach', {
    scope: 'hmi:evidence:attach',
    allowedKeys: new Set(['taskRef', 'evidenceRef', 'note']),
    maxBytes: 8_192,
    stepUp: false,
  }],
  ['result.export', {
    scope: 'hmi:result:export',
    allowedKeys: new Set(['resultRef', 'format', 'purpose']),
    maxBytes: 4_096,
    stepUp: true,
  }],
  ['workflow.approve', {
    scope: 'hmi:workflow:approve',
    allowedKeys: new Set(['workflowRef', 'decision', 'note']),
    maxBytes: 4_096,
    stepUp: true,
  }],
]);

const FORBIDDEN_ACTION = /^(core|internal|prompt|evolution|router|lineage|trace|secret|topology|corpus|canonical)([.:/]|$)/i;
const MAX_STEP_UP_AGE_MS = 5 * 60_000;

function deny(code) {
  return { ok: false, code };
}

function byteLength(value) {
  return Buffer.byteLength(JSON.stringify(value ?? {}), 'utf8');
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
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return deny('INVALID_ACTION_PAYLOAD');
  if (byteLength(payload) > definition.maxBytes) return deny('ACTION_PAYLOAD_TOO_LARGE');
  for (const key of Object.keys(payload)) {
    if (!definition.allowedKeys.has(key)) return deny('ACTION_FIELD_NOT_ALLOWED');
  }

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
