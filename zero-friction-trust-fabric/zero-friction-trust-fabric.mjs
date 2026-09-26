export const DECISIONS = Object.freeze([
  'MACHINE_CONTINUE',
  'STEP_UP_REQUIRED',
  'DENY'
]);

export const IDENTITY_KINDS = Object.freeze([
  'OWNER_USER',
  'OWNER_DEVICE',
  'WORKLOAD',
  'SERVICE_ACCOUNT',
  'FEDERATED_PRINCIPAL',
  'CONNECTED_ACCOUNT'
]);

export const CREDENTIAL_STRATEGIES = Object.freeze([
  'SHORT_LIVED_TOKEN',
  'OAUTH_REFRESH',
  'OIDC_TOKEN_EXCHANGE',
  'WORKLOAD_FEDERATION',
  'MTLS',
  'SIGNED_CAPABILITY',
  'PROVIDER_SESSION'
]);

export const PROVIDER_CONSTRAINTS = Object.freeze([
  'NONE',
  'USER_PRESENCE_REQUIRED',
  'PROVIDER_CONSENT_REQUIRED',
  'KYC_REQUIRED',
  'LEGAL_SIGNATURE_REQUIRED'
]);

function req(v, name) {
  if (typeof v !== 'string' || !v.trim()) throw new Error(`INVALID_${name}`);
  return v.trim();
}

function num(v, name, min = 0, max = 1) {
  const n = Number(v);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`INVALID_${name}`);
  return n;
}

function nowSeconds(nowMs) {
  return Math.floor(nowMs / 1000);
}

export class DelegatedMachineIdentityFabric {
  constructor({ now = () => Date.now() } = {}) {
    this.now = now;
    this.principals = new Map();
    this.revoked = new Set();
  }

  registerPrincipal({
    principal_id,
    identity_kind,
    owner_delegated = false,
    provider,
    account_ref,
    allowed_actions = [],
    max_risk = 0.5,
    standing_mandates = [],
    credential_strategy = 'SHORT_LIVED_TOKEN',
    expires_at = null
  }) {
    const id = req(principal_id, 'PRINCIPAL_ID');
    const kind = req(identity_kind, 'IDENTITY_KIND');
    if (!IDENTITY_KINDS.includes(kind)) throw new Error('IDENTITY_KIND_NOT_ALLOWED');
    if (!CREDENTIAL_STRATEGIES.includes(credential_strategy)) throw new Error('CREDENTIAL_STRATEGY_NOT_ALLOWED');
    if (this.principals.has(id)) throw new Error('PRINCIPAL_EXISTS');

    const p = Object.freeze({
      principal_id: id,
      identity_kind: kind,
      owner_delegated: owner_delegated === true,
      provider: provider ? req(provider, 'PROVIDER') : null,
      account_ref: account_ref ? req(account_ref, 'ACCOUNT_REF') : null,
      allowed_actions: Object.freeze([...new Set(allowed_actions.map((x) => req(x, 'ACTION')))]),
      max_risk: num(max_risk, 'MAX_RISK'),
      standing_mandates: Object.freeze([...new Set(standing_mandates.map((x) => req(x, 'MANDATE')))]),
      credential_strategy,
      expires_at: expires_at == null ? null : Number(expires_at)
    });
    this.principals.set(id, p);
    return p;
  }

  revoke(principalId) {
    this.revoked.add(req(principalId, 'PRINCIPAL_ID'));
  }

  isActive(p) {
    if (this.revoked.has(p.principal_id)) return false;
    if (p.expires_at != null && this.now() >= p.expires_at) return false;
    return true;
  }

  evaluate({
    principal_id,
    action,
    action_risk = 0,
    provider_constraint = 'NONE',
    device_trust = 1,
    session_trust = 1,
    anomaly_score = 0,
    standing_mandate = null
  }) {
    const p = this.principals.get(req(principal_id, 'PRINCIPAL_ID'));
    if (!p || !this.isActive(p)) {
      return Object.freeze({ decision: 'DENY', reason: 'PRINCIPAL_INACTIVE_OR_UNKNOWN' });
    }

    const act = req(action, 'ACTION');
    const providerConstraint = req(provider_constraint, 'PROVIDER_CONSTRAINT');
    if (!PROVIDER_CONSTRAINTS.includes(providerConstraint)) throw new Error('PROVIDER_CONSTRAINT_NOT_ALLOWED');

    if (!p.allowed_actions.includes(act) && !p.allowed_actions.includes('*')) {
      return Object.freeze({ decision: 'DENY', reason: 'ACTION_OUTSIDE_DELEGATION' });
    }

    if (providerConstraint !== 'NONE') {
      return Object.freeze({
        decision: 'STEP_UP_REQUIRED',
        reason: providerConstraint,
        principal_id: p.principal_id,
        auto_resume: true
      });
    }

    const ar = num(action_risk, 'ACTION_RISK');
    const dt = num(device_trust, 'DEVICE_TRUST');
    const st = num(session_trust, 'SESSION_TRUST');
    const anomaly = num(anomaly_score, 'ANOMALY_SCORE');
    const effectiveRisk = Math.min(1, ar + (1 - dt) * 0.25 + (1 - st) * 0.25 + anomaly * 0.5);

    const mandateCovered = standing_mandate && p.standing_mandates.includes(standing_mandate);
    const threshold = mandateCovered ? Math.min(1, p.max_risk + 0.25) : p.max_risk;

    if (effectiveRisk > threshold) {
      return Object.freeze({
        decision: 'STEP_UP_REQUIRED',
        reason: 'RISK_THRESHOLD_EXCEEDED',
        effective_risk: Number(effectiveRisk.toFixed(6)),
        threshold,
        auto_resume: true
      });
    }

    return Object.freeze({
      decision: 'MACHINE_CONTINUE',
      principal_id: p.principal_id,
      action: act,
      effective_risk: Number(effectiveRisk.toFixed(6)),
      threshold,
      credential_strategy: p.credential_strategy,
      owner_delegated: p.owner_delegated
    });
  }

  issueCapability({
    principal_id,
    action,
    resource,
    ttl_seconds = 300,
    risk_context = {}
  }) {
    const decision = this.evaluate({ principal_id, action, ...risk_context });
    if (decision.decision !== 'MACHINE_CONTINUE') return decision;

    const ttl = Number(ttl_seconds);
    if (!Number.isInteger(ttl) || ttl < 1 || ttl > 3600) throw new Error('INVALID_TTL');

    const issued = nowSeconds(this.now());
    return Object.freeze({
      decision: 'MACHINE_CONTINUE',
      capability: Object.freeze({
        type: 'DEUS_SHORT_LIVED_CAPABILITY',
        principal_id,
        action,
        resource: req(resource, 'RESOURCE'),
        issued_at: issued,
        expires_at: issued + ttl,
        raw_secret_embedded: false,
        transferable: false,
        revocation_checked: true
      })
    });
  }
}

export const ZERO_FRICTION_TRUST_MODEL = Object.freeze({
  default_security_primitive: 'DELEGATED_MACHINE_IDENTITY',
  user_consent_model: 'CONSENT_ONCE_THEN_POLICY_DRIVEN_EXECUTION',
  credential_model: 'SHORT_LIVED_OR_REFRESHABLE_OR_FEDERATED',
  authorization_model: 'CONTINUOUS_RISK_ADAPTIVE_POLICY',
  human_prompt_default: false,
  user_presence: 'EDGE_CASE_ONLY_WHEN_PROVIDER_OR_POLICY_REQUIRES',
  password_centric_security: false,
  cryptographic_identity_first: true,
  revocation_first_class: true,
  audit_receipts_required: true,
  provider_constraints_are_external_protocol_facts: true
});
