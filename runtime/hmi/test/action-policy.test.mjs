import test from 'node:test';
import assert from 'node:assert/strict';
import { authorizeHmiAction } from '../lib/action-policy.mjs';

const NOW = 1_800_000_000_000;
const tenant = { id: 'org-a', kind: 'enterprise', status: 'active', requirePhishingResistantAuth: true };

function session(overrides = {}) {
  return {
    authenticated: true,
    identityId: 'user-a',
    tenantId: tenant.id,
    roles: ['operator'],
    scopes: [
      'hmi:actions:invoke',
      'hmi:task:create',
      'hmi:task:cancel',
      'hmi:evidence:attach',
      'hmi:result:export',
      'hmi:workflow:approve',
    ],
    policyVersion: 'p1',
    clearance: 'confidential',
    authMethods: ['enterprise_sso', 'passkey'],
    expiresAt: NOW + 60_000,
    stepUpAt: NOW - 30_000,
    ...overrides,
  };
}

function authorize(action, sessionValue = session()) {
  return authorizeHmiAction({ session: sessionValue, tenant, action: { tenantId: tenant.id, ...action }, now: NOW });
}

test('protected/core action families are denied before role privilege', () => {
  const admin = session({ roles: ['root-admin'], clearance: 'sovereign', scopes: ['hmi:actions:invoke', '*'] });
  for (const id of ['core.read', 'evolution.mutate', 'router.override', 'lineage.rewrite', 'canonical/raw', 'secret.export']) {
    assert.equal(authorize({ id, payload: {} }, admin).code, 'CORE_ACTION_FORBIDDEN', id);
  }
});

test('unknown user actions fail closed', () => {
  assert.equal(authorize({ id: 'tool.execute-arbitrary', payload: {} }).code, 'ACTION_NOT_EXPOSED');
});

test('allowlisted task create produces tenant-bound bounded command', () => {
  const verdict = authorize({ id: 'task.create', payload: { title: 'Audit', objective: 'Verify boundary' } });
  assert.equal(verdict.ok, true);
  assert.equal(verdict.command.tenantId, tenant.id);
  assert.equal(verdict.command.principal, 'user-a');
  assert.equal(verdict.command.actionId, 'task.create');
  assert.deepEqual(verdict.command.payload, { title: 'Audit', objective: 'Verify boundary' });
});

test('unexpected payload fields are rejected', () => {
  const verdict = authorize({ id: 'task.create', payload: { title: 'x', rawCoreQuery: 'SELECT *' } });
  assert.equal(verdict.code, 'ACTION_FIELD_NOT_ALLOWED');
});

test('material actions require explicit confirmation and recent step-up', () => {
  assert.equal(authorize({ id: 'workflow.approve', payload: { workflowRef: 'w1', decision: 'approve' } }).code, 'EXPLICIT_CONFIRMATION_REQUIRED');
  assert.equal(authorize({ id: 'workflow.approve', confirmed: true, payload: { workflowRef: 'w1', decision: 'approve' } }, session({ stepUpAt: NOW - 600_000 })).code, 'RECENT_STEP_UP_REQUIRED');
  assert.equal(authorize({ id: 'workflow.approve', confirmed: true, payload: { workflowRef: 'w1', decision: 'approve' } }).ok, true);
});

test('cross-tenant action cannot be authorized', () => {
  const verdict = authorizeHmiAction({
    session: session(),
    tenant,
    action: { id: 'task.create', tenantId: 'org-b', payload: { title: 'x' } },
    now: NOW,
  });
  assert.equal(verdict.code, 'CROSS_TENANT_ACCESS');
});
