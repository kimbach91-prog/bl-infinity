import { createHash, timingSafeEqual } from 'node:crypto';

const PRINCIPAL_ID_RE = /^[a-zA-Z0-9._:-]{2,128}$/;
const TENANT_ID_RE = /^(\*|[a-zA-Z0-9._:-]{1,128})$/;
const SCOPE_RE = /^(\*|[a-z][a-z0-9.-]*:[a-z][a-z0-9.-]*)$/;
const GLOBAL_ONLY_SCOPES = new Set([
  'provider:read',
  'provider:admin',
  'provider:heartbeat',
  'route:read',
  'runtime:read',
  'runtime:operate',
  'runtime:execute',
  'ledger:read',
  'audit:read',
  'search:read',
  'search:write',
]);

export function bearerToken(req) {
  const value = req.headers?.authorization || '';
  return value.startsWith('Bearer ') ? value.slice(7) : null;
}

export function secureTokenEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const aa = Buffer.from(a), bb = Buffer.from(b);
  return aa.length === bb.length && timingSafeEqual(aa, bb);
}

export function hasControlAccess(req, configuredToken) {
  return Boolean(configuredToken && secureTokenEqual(bearerToken(req), configuredToken));
}

export function parseControlPrincipals(raw, env = process.env) {
  if (raw == null || raw === '') return [];
  const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
  if (!Array.isArray(parsed)) throw new Error('BL_CONTROL_PRINCIPALS_JSON must be an array');
  const ids = new Set();
  const tokenHashes = new Set();
  return parsed.map((input, index) => {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error(`control principal ${index} must be an object`);
    if ('token' in input || 'secret' in input || 'tokenHash' in input) throw new Error(`control principal ${index} must reference tokenEnv, not embed a token/secret`);
    const id = String(input.id ?? '');
    const tenantId = String(input.tenantId ?? '');
    const tokenEnv = String(input.tokenEnv ?? '');
    const scopes = Array.isArray(input.scopes) ? [...new Set(input.scopes.map(String))] : [];
    if (!PRINCIPAL_ID_RE.test(id)) throw new Error(`control principal ${index} has invalid id`);
    if (!TENANT_ID_RE.test(tenantId)) throw new Error(`control principal ${id} has invalid tenantId`);
    if (!/^[A-Z][A-Z0-9_]{2,127}$/.test(tokenEnv)) throw new Error(`control principal ${id} has invalid tokenEnv`);
    if (!scopes.length) throw new Error(`control principal ${id} must have at least one scope`);
    for (const scope of scopes) {
      if (!SCOPE_RE.test(scope)) throw new Error(`control principal ${id} has invalid scope: ${scope}`);
      if ((scope === '*' || GLOBAL_ONLY_SCOPES.has(scope)) && tenantId !== '*') throw new Error(`scope ${scope} requires tenantId=*`);
    }
    if (ids.has(id)) throw new Error(`duplicate control principal id: ${id}`);
    ids.add(id);
    const token = env[tokenEnv];
    if (typeof token !== 'string' || token.length < 24) throw new Error(`control principal ${id} token env ${tokenEnv} must contain at least 24 characters`);
    const tokenHash = fingerprintToken(token);
    if (tokenHashes.has(tokenHash)) throw new Error('control principals must not share the same bearer token');
    tokenHashes.add(tokenHash);
    return Object.freeze({ id, tenantId, tokenEnv, scopes: Object.freeze(scopes), tokenHash });
  });
}

export class ControlAuthenticator {
  constructor({ legacyToken = null, principals = [], env = process.env } = {}) {
    this.entries = new Map();
    this.configured = false;
    if (legacyToken) {
      if (typeof legacyToken !== 'string' || legacyToken.length < 16) throw new Error('BL_CONTROL_TOKEN must contain at least 16 characters when configured');
      this.entries.set(fingerprintToken(legacyToken), Object.freeze({ id: 'legacy-root', tenantId: '*', scopes: Object.freeze(['*']), authType: 'legacy-root' }));
      this.configured = true;
    }
    const resolved = principals.length && principals[0]?.tokenHash
      ? principals
      : parseControlPrincipals(principals, env);
    for (const principal of resolved) {
      if (this.entries.has(principal.tokenHash)) throw new Error('duplicate bearer token across legacy/principal control auth');
      this.entries.set(principal.tokenHash, Object.freeze({ id: principal.id, tenantId: principal.tenantId, scopes: principal.scopes, authType: 'principal' }));
      this.configured = true;
    }
  }

  authenticate(req) {
    const token = bearerToken(req);
    if (!token) return null;
    return this.entries.get(fingerprintToken(token)) ?? null;
  }

  authorize(req, scope) {
    const principal = this.authenticate(req);
    if (!principal) return { ok: false, status: this.configured ? 401 : 503, reason: this.configured ? 'unauthorized' : 'control-auth-not-configured' };
    if (!principal.scopes.includes('*') && !principal.scopes.includes(scope)) return { ok: false, status: 403, reason: 'scope-denied', principal };
    return { ok: true, principal };
  }

  optionalAuthorize(req, scope) {
    if (!this.configured) return { ok: true, principal: null, authOptional: true };
    return this.authorize(req, scope);
  }
}

export function bindTaskToPrincipalTenant(task, principal) {
  if (!task || typeof task !== 'object') throw new Error('task is required for tenant binding');
  if (!principal || principal.tenantId === '*') return structuredClone(task);
  const requested = task.tenantId ?? principal.tenantId;
  if (requested !== principal.tenantId) {
    const error = new Error(`task tenant ${requested} is outside principal tenant ${principal.tenantId}`);
    error.code = 'TENANT_SCOPE_VIOLATION';
    throw error;
  }
  return { ...structuredClone(task), tenantId: principal.tenantId };
}

export function fingerprintToken(token) {
  if (typeof token !== 'string' || !token) throw new Error('token is required');
  return createHash('sha256').update(`bl-cf-control-v1\0${token}`).digest('hex');
}

export { GLOBAL_ONLY_SCOPES };
