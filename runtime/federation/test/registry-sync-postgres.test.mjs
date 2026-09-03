import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresProviderStore } from '../lib/provider-store.mjs';
import { PostgresProviderDeltaView, ProviderRegistrySynchronizer } from '../lib/registry-sync.mjs';
import { ProviderRegistry } from '../lib/fabric.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;
let store = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 16, application_name: 'bl-cf-registry-scale-test' });
    await openPostgresFederationState({ pool, applySchema: true });
    const migration = await readFile(new URL('../storage/postgres/migrations/008_provider_change_seq.sql', import.meta.url), 'utf8');
    await pool.query(migration);
    store = new PostgresProviderStore(pool);
  });
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE federation_provider_heartbeat_nonces,federation_providers RESTART IDENTITY CASCADE');
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

function provider(id, overrides = {}) {
  const base = {
    manifestVersion: 'bl-cf-provider/v1',
    id,
    kind: 'http-worker',
    endpoint: `https://${id}.example.test`,
    capabilities: ['compute.echo'],
    authorization: {
      consentRef: `grant:${id}`,
      grantor: 'test-owner',
      grantedAt: '2026-01-01T00:00:00.000Z',
      expiresAt: '2099-01-01T00:00:00.000Z',
      allowedDataClasses: ['public'],
      maxTaskCostUsd: 1,
    },
    limits: { maxConcurrency: 2, maxCostPerTaskUsd: 1, maxExecutionMs: 5000 },
    dataPolicy: { privateDataAllowed: false, internalDataAllowed: false, retention: 'none' },
    regions: ['test'],
    dataLocations: ['shared'],
  };
  return { ...base, ...overrides };
}

pgtest('provider change trigger emits monotonic cursors and delta reader avoids full snapshot after bootstrap', async () => {
  await store.put(provider('delta-a'));
  await store.put(provider('delta-b'));
  const view = new PostgresProviderDeltaView(store, { batchSize: 10 });
  const snapshot = await view.snapshot();
  assert.equal(snapshot.items.length, 2);
  assert.ok(snapshot.cursor > 0);

  const cursor = snapshot.cursor;
  await store.updateMeasuredTelemetry('delta-a', { trust: 0.8, p95LatencyMs: 25 });
  const delta = await view.changesSince(cursor);
  assert.equal(delta.items.length, 1);
  assert.equal(delta.items[0].provider.id, 'delta-a');
  assert.ok(delta.items[0].changeSeq > cursor);
  assert.equal(delta.providerCount, undefined);
});

pgtest('same provider can change repeatedly without losing a later delta', async () => {
  await store.put(provider('repeat'));
  const view = new PostgresProviderDeltaView(store);
  const snapshot = await view.snapshot();
  await store.updateMeasuredTelemetry('repeat', { trust: 0.6 });
  const first = await view.changesSince(snapshot.cursor);
  assert.equal(first.items.length, 1);
  await store.updateMeasuredTelemetry('repeat', { trust: 0.7 });
  const second = await view.changesSince(first.cursor);
  assert.equal(second.items.length, 1);
  assert.ok(second.cursor > first.cursor);
  assert.equal(second.items[0].provider.telemetry.trust, 0.7);
});

pgtest('two coordinators converge on a revoke using independent cursors', async () => {
  await store.put(provider('shared-revoke'));
  const registryA = new ProviderRegistry();
  const registryB = new ProviderRegistry();
  const syncA = new ProviderRegistrySynchronizer(registryA, new PostgresProviderDeltaView(store));
  const syncB = new ProviderRegistrySynchronizer(registryB, new PostgresProviderDeltaView(store));
  await syncA.bootstrap();
  await syncB.bootstrap();
  assert.equal(registryA.get('shared-revoke').status, 'active');
  assert.equal(registryB.get('shared-revoke').status, 'active');

  await store.revoke('shared-revoke', 'test-revoke');
  const a = await syncA.sync();
  const b = await syncB.sync();
  assert.equal(a.applied, 1);
  assert.equal(b.applied, 1);
  assert.equal(registryA.get('shared-revoke').status, 'disabled');
  assert.equal(registryB.get('shared-revoke').status, 'disabled');
});

pgtest('heartbeat refresh appears as one incremental provider change', async () => {
  const now = Date.parse('2026-09-04T00:00:00.000Z');
  await store.put(provider('hb-delta', { liveness: { heartbeatRequired: true, heartbeatTtlMs: 60_000 } }), { now });
  const view = new PostgresProviderDeltaView(store);
  const snapshot = await view.snapshot({ now });
  assert.equal(snapshot.items[0].provider.status, 'disabled');
  await store.heartbeat('hb-delta', { inFlight: 1 }, { now: now + 1000 });
  const delta = await view.changesSince(snapshot.cursor, { now: now + 1000 });
  assert.equal(delta.items.length, 1);
  assert.equal(delta.items[0].provider.status, 'active');
  assert.equal(delta.items[0].provider.telemetry.inFlight, 1);
});

pgtest('migration trigger bumps cursor for status, telemetry, heartbeat and revoke mutations', async () => {
  const now = Date.parse('2026-09-04T00:00:00.000Z');
  await store.put(provider('all-mutations', { liveness: { heartbeatRequired: true, heartbeatTtlMs: 60_000 } }), { now });
  const seqs = [];
  for (const operation of [
    () => store.heartbeat('all-mutations', { inFlight: 0 }, { now: now + 1000 }),
    () => store.updateMeasuredTelemetry('all-mutations', { trust: 0.65 }, { now: now + 2000 }),
    () => store.setStatus('all-mutations', 'disabled', { now: now + 3000 }),
    () => store.setStatus('all-mutations', 'active', { now: now + 4000 }),
    () => store.revoke('all-mutations', 'done', { now: now + 5000 }),
  ]) {
    await operation();
    const row = await pool.query('SELECT change_seq FROM federation_providers WHERE id=$1', ['all-mutations']);
    seqs.push(Number(row.rows[0].change_seq));
  }
  for (let i = 1; i < seqs.length; i += 1) assert.ok(seqs[i] > seqs[i - 1]);
});
