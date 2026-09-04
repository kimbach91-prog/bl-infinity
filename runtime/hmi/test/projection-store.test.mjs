import test from 'node:test';
import assert from 'node:assert/strict';
import { TenantProjectionStore } from '../lib/projection-store.mjs';

const NOW = 1_800_000_000_000;

function record(tenantId, value, overrides = {}) {
  return {
    tenantId,
    projectionId: 'task-42',
    schemaVersion: 'hmi-projection/v1',
    dataClass: 'internal',
    policyVersion: 'policy-1',
    sourceReceiptRefs: ['receipt:opaque:1'],
    createdAt: NOW,
    expiresAt: NOW + 60_000,
    value,
    ...overrides,
  };
}

test('same projection id remains isolated between tenants', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', { status: 'A' }), NOW);
  store.put(record('tenant-b', { status: 'B' }), NOW);

  assert.equal(store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW }).value.status, 'A');
  assert.equal(store.get({ tenantId: 'tenant-b', projectionId: 'task-42', now: NOW }).value.status, 'B');
  assert.equal(store.size(), 2);
});

test('unknown tenant has no global or neighboring fallback', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', { status: 'private-a' }), NOW);
  assert.equal(store.get({ tenantId: 'tenant-b', projectionId: 'task-42', now: NOW }), null);
});

test('protected fields are stripped before projection storage', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', {
    status: 'ok',
    workspace: { title: 'visible', systemPrompt: 'secret', routerPolicy: 'secret' },
    core: { lineage: 'secret' },
  }), NOW);

  const stored = store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW });
  assert.equal(stored.value.status, 'ok');
  assert.equal(stored.value.workspace.title, 'visible');
  assert.equal(stored.value.workspace.systemPrompt, undefined);
  assert.equal(stored.value.workspace.routerPolicy, undefined);
  assert.equal(stored.value.core, undefined);
});

test('expired projections fail closed and are purged', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', { status: 'fresh' }), NOW);
  assert.equal(store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW + 60_001 }), null);
  assert.equal(store.size(), 0);
});

test('tenant purge cannot remove another tenant records', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', { status: 'A' }), NOW);
  store.put(record('tenant-b', { status: 'B' }), NOW);
  assert.equal(store.purgeTenant('tenant-a'), 1);
  assert.equal(store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW }), null);
  assert.equal(store.get({ tenantId: 'tenant-b', projectionId: 'task-42', now: NOW }).value.status, 'B');
});

test('invalid classification and non-future expiry are rejected', () => {
  const store = new TenantProjectionStore();
  assert.throws(() => store.put(record('tenant-a', {}, { dataClass: 'unknown' }), NOW));
  assert.throws(() => store.put(record('tenant-a', {}, { expiresAt: NOW }), NOW));
});
