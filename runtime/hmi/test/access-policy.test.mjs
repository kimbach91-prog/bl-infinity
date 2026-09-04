import test from 'node:test';
import assert from 'node:assert/strict';
import { authorizeHmiRequest, projectHmiEnvelope } from '../lib/access-policy.mjs';

const NOW = Date.parse('2026-09-04T18:00:00+07:00');
const tenant = {
  id: 'org-acme',
  kind: 'enterprise',
  status: 'active',
  requirePhishingResistantAuth: true,
};

function session(overrides = {}) {
  return {
    authenticated: true,
    identityId: 'user-1',
    tenantId: tenant.id,
    roles: ['operator'],
    scopes: ['hmi:workspace:read', 'hmi:tasks:read', 'hmi:evidence:read', 'hmi:results:read', 'hmi:actions:invoke'],
    policyVersion: '2026-09-04',
    clearance: 'confidential',
    authMethods: ['enterprise_sso', 'passkey'],
    expiresAt: NOW + 60_000,
    ...overrides,
  };
}

function authorize({ path = '/workspace', request = {}, session: sessionValue = session(), tenant: tenantValue = tenant } = {}) {
  return authorizeHmiRequest({
    session: sessionValue,
    tenant: tenantValue,
    request: { path, tenantId: tenant.id, dataClass: 'internal', ...request },
    now: NOW,
  });
}

test('valid enterprise user receives projection-only HMI access', () => {
  const verdict = authorize();
  assert.equal(verdict.ok, true);
  assert.equal(verdict.projectionOnly, true);
});

test('anonymous, guest and public self-signup sessions are denied', () => {
  assert.equal(authorize({ session: null }).code, 'AUTHENTICATION_REQUIRED');
  assert.equal(authorize({ session: session({ guest: true }) }).code, 'NON_ENTERPRISE_ENTRY_FORBIDDEN');
  assert.equal(authorize({ session: session({ anonymous: true }) }).code, 'NON_ENTERPRISE_ENTRY_FORBIDDEN');
  assert.equal(authorize({ session: session({ signupMode: 'self-service' }) }).code, 'NON_ENTERPRISE_ENTRY_FORBIDDEN');
});

test('consumer/public tenant kind is rejected', () => {
  const verdict = authorize({ tenant: { ...tenant, kind: 'consumer' } });
  assert.equal(verdict.code, 'TENANT_NOT_ELIGIBLE');
});

test('government tenant is eligible', () => {
  const gov = { ...tenant, id: 'agency-1', kind: 'government' };
  const verdict = authorizeHmiRequest({
    session: session({ tenantId: gov.id }),
    tenant: gov,
    request: { path: '/workspace', tenantId: gov.id, dataClass: 'internal' },
    now: NOW,
  });
  assert.equal(verdict.ok, true);
});

test('cross-tenant access fails closed', () => {
  assert.equal(authorize({ request: { tenantId: 'org-other' } }).code, 'CROSS_TENANT_ACCESS');
  assert.equal(authorize({ session: session({ tenantId: 'org-other' }) }).code, 'TENANT_MEMBERSHIP_REQUIRED');
});

test('expired or weakly authenticated sessions are denied', () => {
  assert.equal(authorize({ session: session({ expiresAt: NOW }) }).code, 'SESSION_EXPIRED');
  assert.equal(authorize({ session: session({ authMethods: ['enterprise_sso'] }) }).code, 'STRONG_AUTH_REQUIRED');
});

test('role, policy, scope and data clearance gates are independent', () => {
  assert.equal(authorize({ session: session({ roles: [] }) }).code, 'ROLE_POLICY_REQUIRED');
  assert.equal(authorize({ session: session({ policyVersion: null }) }).code, 'ROLE_POLICY_REQUIRED');
  assert.equal(authorize({ session: session({ scopes: [] }) }).code, 'INSUFFICIENT_SCOPE');
  assert.equal(authorize({ request: { dataClass: 'restricted' } }).code, 'DATA_CLASSIFICATION_DENIED');
});

test('protected core paths are denied even to a maximally scoped administrator', () => {
  const admin = session({
    roles: ['root-admin'],
    clearance: 'sovereign',
    scopes: ['*', 'hmi:workspace:read', 'hmi:tasks:read', 'hmi:evidence:read', 'hmi:results:read', 'hmi:actions:invoke', 'hmi:audit:read'],
  });
  for (const path of ['/core', '/core/prompts', '/prompts/system', '/evolution/state', '/router/policy', '/lineage/raw', '/traces/1', '/secrets/x', '/topology', '/corpora/private', '/canonical/raw']) {
    assert.equal(authorize({ path, session: admin }).code, 'CORE_ISOLATION', path);
  }
});

test('unregistered surfaces fail closed', () => {
  assert.equal(authorize({ path: '/debug' }).code, 'SURFACE_NOT_EXPOSED');
  assert.equal(authorize({ path: '/api/raw-state' }).code, 'SURFACE_NOT_EXPOSED');
});

test('projection envelope drops dangerous top-level and nested keys', () => {
  const projected = projectHmiEnvelope({
    workspace: {
      title: 'Mission',
      internal: {
        systemPrompt: 'DO NOT LEAK',
        safeSummary: 'visible',
      },
    },
    status: 'running',
    core: { evolutionaryLogic: 'hidden' },
    rawTrace: 'hidden',
    results: [{ answer: 42, credential: 'hidden' }],
  });
  assert.equal(projected.status, 'running');
  assert.equal(projected.core, undefined);
  assert.equal(projected.rawTrace, undefined);
  assert.equal(projected.workspace.internal.systemPrompt, undefined);
  assert.equal(projected.workspace.internal.safeSummary, 'visible');
  assert.equal(projected.results[0].credential, undefined);
  assert.equal(projected.results[0].answer, 42);
});
