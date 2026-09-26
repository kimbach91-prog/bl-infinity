import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DataPolicyRegistry,
  DataResourceCatalog,
  assertDataGovernanceRuntime
} from './index.mjs';

function fixture(nowIso = '2026-09-27T00:00:00Z') {
  let now = new Date(nowIso).getTime();
  const policies = new DataPolicyRegistry();
  policies.register({
    policy_id: 'p1',
    tenant_id: 't1',
    retention_days: 30,
    deletion_grace_days: 7,
    region: 'APAC',
    export_allowed: true,
    training_use_allowed: false
  });
  policies.register({
    policy_id: 'p2',
    tenant_id: 't2',
    retention_days: 365,
    deletion_grace_days: 0,
    region: 'EU',
    export_allowed: false,
    training_use_allowed: true
  });
  const catalog = new DataResourceCatalog({ policyRegistry: policies, now: () => now });
  return { policies, catalog, setNow: (iso) => { now = new Date(iso).getTime(); } };
}

test('runtime types are valid', () => {
  const { policies, catalog } = fixture();
  assert.equal(assertDataGovernanceRuntime({ policyRegistry: policies, catalog }), true);
});

test('residency mismatch is rejected at write time', () => {
  const { catalog } = fixture();
  assert.throws(() => catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'EU',
    source_ref: 'drive://x'
  }), /DATA_RESIDENCY_MISMATCH/);
});

test('cross-tenant access is denied', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1'
  });
  assert.throws(() => catalog.getForTenant('r1', 't2'), /CROSS_TENANT_DATA_DENIED/);
});

test('retention decision becomes delete-due after expiry', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1',
    created_at: '2026-08-01T00:00:00Z'
  });
  const d = catalog.retentionDecision({ resource_id: 'r1', tenant_id: 't1', at: '2026-09-27T00:00:00Z' });
  assert.equal(d.action, 'DELETE_DUE');
});

test('legal hold blocks deletion and purge', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1'
  });
  catalog.setLegalHold({
    resource_id: 'r1',
    tenant_id: 't1',
    enabled: true,
    authority_ref: 'case://legal/1'
  });
  assert.equal(catalog.requestDeletion({
    resource_id: 'r1',
    tenant_id: 't1',
    authority_ref: 'owner://1'
  }).reason, 'LEGAL_HOLD');
  assert.equal(catalog.purge({
    resource_id: 'r1',
    tenant_id: 't1',
    authority_ref: 'owner://1',
    purge_receipt: 'rcp://purge/1'
  }).reason, 'LEGAL_HOLD');
});

test('soft delete honors grace then purges with receipt', () => {
  const { catalog, setNow } = fixture('2026-09-01T00:00:00Z');
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1',
    content_hash: 'abc'
  });
  const tomb = catalog.requestDeletion({
    resource_id: 'r1',
    tenant_id: 't1',
    authority_ref: 'owner://1'
  });
  assert.equal(tomb.state, 'TOMBSTONED');

  setNow('2026-09-05T00:00:00Z');
  const early = catalog.purge({
    resource_id: 'r1',
    tenant_id: 't1',
    authority_ref: 'owner://1',
    purge_receipt: 'rcp://purge/early'
  });
  assert.equal(early.purged, false);
  assert.equal(early.reason, 'GRACE_PERIOD_ACTIVE');

  setNow('2026-09-10T00:00:00Z');
  const done = catalog.purge({
    resource_id: 'r1',
    tenant_id: 't1',
    authority_ref: 'owner://1',
    purge_receipt: 'rcp://purge/final'
  });
  assert.equal(done.purged, true);
  assert.equal(catalog.getForTenant('r1', 't1').state, 'PURGED');
  assert.equal(catalog.getForTenant('r1', 't1').content_hash, null);
});

test('export manifest is tenant-scoped and hash-addressed', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1',
    content_hash: 'hash-r1'
  });
  const x = catalog.exportManifest({
    tenant_id: 't1',
    authority_ref: 'owner://1',
    generated_at: '2026-09-27T00:00:00Z'
  });
  assert.equal(x.entries.length, 1);
  assert.equal(x.entries[0].resource_id, 'r1');
  assert.equal(typeof x.manifest_hash, 'string');
  assert.equal(x.manifest_hash.length, 64);
});

test('export-disabled policy blocks portability for that resource', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r2',
    tenant_id: 't2',
    policy_id: 'p2',
    region: 'EU',
    source_ref: 'drive://r2'
  });
  assert.throws(() => catalog.exportManifest({
    tenant_id: 't2',
    authority_ref: 'owner://2'
  }), /EXPORT_NOT_ALLOWED/);
});

test('training use is denied by default policy and never inferred from access', () => {
  const { catalog } = fixture();
  catalog.create({
    resource_id: 'r1',
    tenant_id: 't1',
    policy_id: 'p1',
    region: 'APAC',
    source_ref: 'drive://r1'
  });
  const e = catalog.trainingEligibility({ resource_id: 'r1', tenant_id: 't1' });
  assert.equal(e.allowed, false);
  assert.equal(e.training_use_allowed, false);
});
