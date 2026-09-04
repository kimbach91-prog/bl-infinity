const ALLOWED_TENANT_KINDS = new Set(['enterprise', 'government']);
const STRONG_AUTH_METHODS = new Set([
  'enterprise_sso',
  'federated_oidc',
  'saml',
  'passkey',
  'mfa',
  'hardware_key',
  'smartcard',
]);
const PHISHING_RESISTANT_METHODS = new Set(['passkey', 'hardware_key', 'smartcard']);

const PROTECTED_PREFIXES = [
  '/core',
  '/internal',
  '/prompts',
  '/evolution',
  '/router',
  '/lineage',
  '/traces',
  '/secrets',
  '/topology',
  '/corpora',
  '/canonical/raw',
];

const DEFAULT_SURFACE_SCOPES = new Map([
  ['/workspace', 'hmi:workspace:read'],
  ['/tasks', 'hmi:tasks:read'],
  ['/evidence', 'hmi:evidence:read'],
  ['/results', 'hmi:results:read'],
  ['/actions', 'hmi:actions:invoke'],
  ['/admin/audit', 'hmi:audit:read'],
]);

const CLASSIFICATION_RANK = Object.freeze({
  public: 0,
  internal: 1,
  confidential: 2,
  restricted: 3,
  sovereign: 4,
});

const SAFE_PROJECTION_KEYS = new Set([
  'workspace',
  'task',
  'status',
  'evidence',
  'results',
  'availableActions',
  'warnings',
  'unknowns',
  'userMessages',
  'timestamps',
]);

const SENSITIVE_KEY = /(prompt|system.?message|chain.?of.?thought|raw.?trace|secret|credential|api.?key|token|router.?policy|evolution|lineage|topology|canonical.?internal|private.?corpus)/i;

function deny(code) {
  return { ok: false, code };
}

function normalizePath(value) {
  if (typeof value !== 'string' || !value.startsWith('/')) return null;
  const path = value.split('?')[0].replace(/\/+$/, '') || '/';
  return path;
}

function under(path, prefix) {
  return path === prefix || path.startsWith(`${prefix}/`);
}

function parseTime(value) {
  if (typeof value === 'number') return value;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function resolveSurfaceScope(path, surfaceScopes = DEFAULT_SURFACE_SCOPES) {
  const prefixes = [...surfaceScopes.keys()].sort((a, b) => b.length - a.length);
  const prefix = prefixes.find((candidate) => under(path, candidate));
  return prefix ? surfaceScopes.get(prefix) : null;
}

function hasStrongAuthentication(session, tenant) {
  const methods = new Set(Array.isArray(session?.authMethods) ? session.authMethods : []);
  const hasStrong = [...methods].some((method) => STRONG_AUTH_METHODS.has(method));
  if (!hasStrong) return false;
  if (tenant?.requirePhishingResistantAuth === true) {
    return [...methods].some((method) => PHISHING_RESISTANT_METHODS.has(method));
  }
  return true;
}

function clearanceAllows(session, request) {
  const requested = request?.dataClass ?? 'internal';
  const granted = session?.clearance ?? 'internal';
  if (!(requested in CLASSIFICATION_RANK) || !(granted in CLASSIFICATION_RANK)) return false;
  return CLASSIFICATION_RANK[granted] >= CLASSIFICATION_RANK[requested];
}

/**
 * HMI authorization boundary.
 *
 * This function is intentionally unable to grant any direct core read. Even a
 * break-glass administrator remains confined to HMI projections and separately
 * audited operational actions.
 */
export function authorizeHmiRequest({ session, tenant, request, now = Date.now(), surfaceScopes = DEFAULT_SURFACE_SCOPES }) {
  const path = normalizePath(request?.path);
  if (!path) return deny('INVALID_SURFACE');

  // Absolute boundary: authentication or role can never override core isolation.
  if (PROTECTED_PREFIXES.some((prefix) => under(path, prefix))) return deny('CORE_ISOLATION');

  if (!session || session.authenticated !== true || !session.identityId) return deny('AUTHENTICATION_REQUIRED');
  if (session.guest === true || session.anonymous === true || session.signupMode === 'self-service') return deny('NON_ENTERPRISE_ENTRY_FORBIDDEN');

  if (!tenant || tenant.status !== 'active' || !ALLOWED_TENANT_KINDS.has(tenant.kind)) return deny('TENANT_NOT_ELIGIBLE');
  if (!tenant.id || session.tenantId !== tenant.id) return deny('TENANT_MEMBERSHIP_REQUIRED');
  if (request?.tenantId && request.tenantId !== tenant.id) return deny('CROSS_TENANT_ACCESS');

  const expiresAt = parseTime(session.expiresAt);
  if (!Number.isFinite(expiresAt) || expiresAt <= now) return deny('SESSION_EXPIRED');
  if (!hasStrongAuthentication(session, tenant)) return deny('STRONG_AUTH_REQUIRED');

  if (!Array.isArray(session.roles) || session.roles.length === 0 || !session.policyVersion) return deny('ROLE_POLICY_REQUIRED');
  if (!clearanceAllows(session, request)) return deny('DATA_CLASSIFICATION_DENIED');

  const requiredScope = resolveSurfaceScope(path, surfaceScopes);
  if (!requiredScope) return deny('SURFACE_NOT_EXPOSED');
  const scopes = new Set(Array.isArray(session.scopes) ? session.scopes : []);
  if (!scopes.has(requiredScope)) return deny('INSUFFICIENT_SCOPE');

  return {
    ok: true,
    code: 'HMI_ACCESS_GRANTED',
    principal: session.identityId,
    tenantId: tenant.id,
    requiredScope,
    projectionOnly: true,
  };
}

function sanitizeProjectionValue(value, depth = 0) {
  if (depth > 10) return '[REDACTED_DEPTH_LIMIT]';
  if (Array.isArray(value)) return value.map((item) => sanitizeProjectionValue(item, depth + 1));
  if (!value || typeof value !== 'object') return value;

  const output = {};
  for (const [key, child] of Object.entries(value)) {
    if (SENSITIVE_KEY.test(key)) continue;
    output[key] = sanitizeProjectionValue(child, depth + 1);
  }
  return output;
}

/**
 * Defense-in-depth projection sanitizer.
 * Input must already be a user-facing projection candidate; this is not an
 * authorization mechanism and must never be wired directly to raw core state.
 */
export function projectHmiEnvelope(candidate = {}) {
  const projected = {};
  for (const key of SAFE_PROJECTION_KEYS) {
    if (Object.hasOwn(candidate, key)) projected[key] = sanitizeProjectionValue(candidate[key]);
  }
  return projected;
}

export const hmiPolicyConstants = Object.freeze({
  allowedTenantKinds: [...ALLOWED_TENANT_KINDS],
  protectedPrefixes: [...PROTECTED_PREFIXES],
  safeProjectionKeys: [...SAFE_PROJECTION_KEYS],
});
