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

test('projection identifiers reject delimiter/control injection that could alias tenant keys', () => {
  const store = new TenantProjectionStore();
  assert.throws(() => store.put(record('tenant-a\u0000shadow', { status: 'bad' }), NOW), /unsupported characters/);
  assert.throws(() => store.put(record('tenant-a', { status: 'bad' }, { projectionId: 'task-42\u0000shadow' }), NOW), /unsupported characters/);
  assert.throws(() => store.get({ tenantId: 'tenant-a\u0000shadow', projectionId: 'task-42', now: NOW }), /unsupported characters/);
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

test('stored projection state cannot be mutated through the put receipt', () => {
  const store = new TenantProjectionStore();
  const stored = store.put(record('tenant-a', {
    status: 'ready',
    workspace: { title: 'original' },
    results: [{ answer: 42 }],
  }), NOW);

  assert.equal(Object.isFrozen(stored.value), true);
  assert.equal(Object.isFrozen(stored.value.workspace), true);
  assert.equal(Object.isFrozen(stored.value.results), true);
  assert.equal(Object.isFrozen(stored.value.results[0]), true);
  assert.throws(() => { stored.value.workspace.title = 'tampered'; }, TypeError);
  assert.throws(() => { stored.value.results[0].answer = 999; }, TypeError);

  const reread = store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW });
  assert.equal(reread.value.workspace.title, 'original');
  assert.equal(reread.value.results[0].answer, 42);
});

test('unknown projection schema versions fail closed', () => {
  const store = new TenantProjectionStore();
  assert.throws(
    () => store.put(record('tenant-a', {}, { schemaVersion: 'hmi-projection/v0' }), NOW),
    /unsupported schemaVersion/,
  );
});

test('stale replay cannot replace a fresher projection', () => {
  const store = new TenantProjectionStore();
  store.put(record('tenant-a', { status: 'fresh' }, { createdAt: NOW, expiresAt: NOW + 120_000 }), NOW);

  assert.throws(
    () => store.put(record('tenant-a', { status: 'stale' }, { createdAt: NOW - 1_000, expiresAt: NOW + 120_000 }), NOW),
    /stale projection replay rejected/,
  );
  assert.equal(store.get({ tenantId: 'tenant-a', projectionId: 'task-42', now: NOW }).value.status, 'fresh');
});

test('same-version retries are idempotent but conflicting same-version writes fail closed', () => {
  const store = new TenantProjectionStore();
  const candidate = record('tenant-a', { status: 'same' });
  const first = store.put(candidate, NOW);
  const retry = store.put(candidate, NOW);
  assert.deepEqual(retry, first);

  assert.throws(
    () => store.put(record('tenant-a', { status: 'conflict' }), NOW),
    /projection version conflict/,
  );
});

test('implausible future creation timestamps fail closed', () => {
  const store = new TenantProjectionStore({ maxFutureSkewMs: 30_000 });
  assert.throws(
    () => store.put(record('tenant-a', {}, { createdAt: NOW + 30_001, expiresAt: NOW + 90_000 }), NOW),
    /createdAt exceeds allowed clock skew/,
  );
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

test('invalid classification and invalid temporal bounds are rejected', () => {
  const store = new TenantProjectionStore();
  assert.throws(() => store.put(record('tenant-a', {}, { dataClass: 'unknown' }), NOW));
  assert.throws(() => store.put(record('tenant-a', {}, { expiresAt: NOW }), NOW));
  assert.throws(() => store.put(record('tenant-a', {}, { createdAt: undefined }), NOW));
  assert.throws(() => store.put(record('tenant-a', {}, { createdAt: NOW + 1_000, expiresAt: NOW + 500 }), NOW));
});
