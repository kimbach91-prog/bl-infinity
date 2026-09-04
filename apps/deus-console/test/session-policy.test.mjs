import test from 'node:test';
import assert from 'node:assert/strict';
import {
  canAccessSurface,
  validateIdentityAdapterCandidate,
} from '../lib/session-policy.mjs';

const NOW = Date.parse('2026-09-05T00:00:00+07:00');

function candidate(overrides = {}) {
  const base = {
    verified: true,
    tenant: {
      id: 'org-acme',
      kind: 'enterprise',
      status: 'active',
      requirePhishingResistantAuth: true,
    },
    session: {
      authenticated: true,
      identityId: 'user-1',
      tenantId: 'org-acme',
      tenantKind: 'enterprise',
      roles: ['operator'],
      scopes: ['hmi:workspace:read'],
      policyVersion: '2026-09-05',
      clearance: 'confidential',
      authMethods: ['enterprise_sso', 'passkey'],
      expiresAt: new Date(NOW + 60_000).toISOString(),
    },
  };

  return {
    ...base,
    ...overrides,
    tenant: { ...base.tenant, ...(overrides.tenant || {}) },
    session: { ...base.session, ...(overrides.session || {}) },
  };
}

test('verified enterprise context with phishing-resistant auth is accepted', () => {
  const verdict = validateIdentityAdapterCandidate(candidate(), { now: NOW });
  assert.equal(verdict.ok, true);
  assert.equal(canAccessSurface(verdict, 'hmi:workspace:read'), true);
});

test('public/consumer tenant and cross-tenant context fail closed', () => {
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ tenant: { kind: 'consumer' } }), { now: NOW }).code,
    'TENANT_NOT_ELIGIBLE',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { tenantId: 'org-other' } }), { now: NOW }).code,
    'TENANT_CONTEXT_MISMATCH',
  );
});

test('anonymous guest and self-service entry are rejected', () => {
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { guest: true } }), { now: NOW }).code,
    'NON_ENTERPRISE_ENTRY_FORBIDDEN',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { anonymous: true } }), { now: NOW }).code,
    'NON_ENTERPRISE_ENTRY_FORBIDDEN',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { signupMode: 'self-service' } }), { now: NOW }).code,
    'NON_ENTERPRISE_ENTRY_FORBIDDEN',
  );
});

test('weak auth and missing phishing-resistant factor are rejected', () => {
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { authMethods: ['password'] } }), { now: NOW }).code,
    'STRONG_AUTH_REQUIRED',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { authMethods: ['enterprise_sso'] } }), { now: NOW }).code,
    'PHISHING_RESISTANT_AUTH_REQUIRED',
  );
});

test('expired, role-less, policy-less and malformed clearance contexts fail closed', () => {
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { expiresAt: new Date(NOW).toISOString() } }), { now: NOW }).code,
    'SESSION_EXPIRED',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { roles: [] } }), { now: NOW }).code,
    'ROLE_POLICY_REQUIRED',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { policyVersion: '' } }), { now: NOW }).code,
    'ROLE_POLICY_REQUIRED',
  );
  assert.equal(
    validateIdentityAdapterCandidate(candidate({ session: { clearance: 'root' } }), { now: NOW }).code,
    'INVALID_CLEARANCE',
  );
});

test('workspace rendering requires explicit workspace scope', () => {
  const verdict = validateIdentityAdapterCandidate(candidate({ session: { scopes: ['hmi:tasks:read'] } }), { now: NOW });
  assert.equal(verdict.ok, true);
  assert.equal(canAccessSurface(verdict, 'hmi:workspace:read'), false);
});
