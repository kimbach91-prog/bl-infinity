const ALLOWED_TENANT_KINDS = new Set(['enterprise', 'government']);
const ALLOWED_CLEARANCE = new Set(['public', 'internal', 'confidential', 'restricted', 'sovereign']);
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

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function stringArray(value, { nonEmpty = false } = {}) {
  return Array.isArray(value)
    && (!nonEmpty || value.length > 0)
    && value.every((item) => nonEmptyString(item));
}

function deny(code) {
  return { ok: false, code };
}

/**
 * Validate the trusted identity-adapter response before any web surface renders.
 * Client-controlled headers/body/localStorage are deliberately not inputs here.
 */
export function validateIdentityAdapterCandidate(candidate, { now = Date.now() } = {}) {
  if (!candidate || typeof candidate !== 'object' || candidate.verified !== true) {
    return deny('IDENTITY_NOT_VERIFIED');
  }

  const tenant = candidate.tenant;
  const session = candidate.session;
  if (!tenant || typeof tenant !== 'object' || !session || typeof session !== 'object') {
    return deny('IDENTITY_CONTEXT_INCOMPLETE');
  }

  if (!nonEmptyString(tenant.id)
      || tenant.status !== 'active'
      || !ALLOWED_TENANT_KINDS.has(tenant.kind)) {
    return deny('TENANT_NOT_ELIGIBLE');
  }

  if (session.authenticated !== true
      || !nonEmptyString(session.identityId)
      || !nonEmptyString(session.tenantId)) {
    return deny('AUTHENTICATION_REQUIRED');
  }

  if (session.guest === true || session.anonymous === true || session.signupMode === 'self-service') {
    return deny('NON_ENTERPRISE_ENTRY_FORBIDDEN');
  }

  if (session.tenantId !== tenant.id || session.tenantKind !== tenant.kind) {
    return deny('TENANT_CONTEXT_MISMATCH');
  }

  if (!stringArray(session.roles, { nonEmpty: true })
      || !stringArray(session.scopes)
      || !nonEmptyString(session.policyVersion)) {
    return deny('ROLE_POLICY_REQUIRED');
  }

  if (!ALLOWED_CLEARANCE.has(session.clearance)) {
    return deny('INVALID_CLEARANCE');
  }

  if (!stringArray(session.authMethods, { nonEmpty: true })) {
    return deny('STRONG_AUTH_REQUIRED');
  }
  const methods = new Set(session.authMethods);
  if (![...methods].some((method) => STRONG_AUTH_METHODS.has(method))) {
    return deny('STRONG_AUTH_REQUIRED');
  }
  if (tenant.requirePhishingResistantAuth === true
      && ![...methods].some((method) => PHISHING_RESISTANT_METHODS.has(method))) {
    return deny('PHISHING_RESISTANT_AUTH_REQUIRED');
  }

  const expiresAt = Date.parse(session.expiresAt);
  if (!Number.isFinite(expiresAt) || expiresAt <= now) {
    return deny('SESSION_EXPIRED');
  }

  return {
    ok: true,
    code: 'IDENTITY_CONTEXT_VERIFIED',
    session,
    tenant,
  };
}

export function canAccessSurface(context, requiredScope) {
  if (!context?.session || !nonEmptyString(requiredScope)) return false;
  return Array.isArray(context.session.scopes) && context.session.scopes.includes(requiredScope);
}

export const webSessionPolicyConstants = Object.freeze({
  allowedTenantKinds: [...ALLOWED_TENANT_KINDS],
  allowedClearance: [...ALLOWED_CLEARANCE],
  strongAuthMethods: [...STRONG_AUTH_METHODS],
  phishingResistantMethods: [...PHISHING_RESISTANT_METHODS],
});
