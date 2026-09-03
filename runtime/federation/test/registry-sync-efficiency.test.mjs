import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresProviderStore } from '../lib/provider-store.mjs';
import { PostgresProviderDeltaView } from '../lib/registry-sync.mjs';
import { readFile } from 'node:fs/promises';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;
let store = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 8, application_name: 'bl-cf-registry-efficiency-test' });
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
  return {
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
    ...overrides,
  };
}

pgtest('delta row hydration is semantically identical to canonical provider-store get', async () => {
  const now = Date.parse('2026-09-04T00:00:00.000Z');
  await store.put(provider('parity', { liveness: { heartbeatRequired: true, heartbeatTtlMs: 60_000 } }), { now });
  await store.heartbeat('parity', { inFlight: 1 }, { now: now + 1000 });
  await store.updateMeasuredTelemetry('parity', { trust: 0.77, p95LatencyMs: 23 }, { now: now + 2000 });

  const view = new PostgresProviderDeltaView(store);
  const snapshot = await view.snapshot({ now: now + 2000 });
  const canonical = await store.get('parity', { now: now + 2000 });
  assert.deepEqual(snapshot.items[0].provider, canonical);
});

pgtest('identical bootstrap grant is write-free and does not emit a fake change cursor', async () => {
  const manifest = provider('idempotent-bootstrap');
  await store.put(manifest, { source: 'bootstrap', seedTelemetry: true });
  const before = await pool.query('SELECT change_seq,updated_at FROM federation_providers WHERE id=$1', [manifest.id]);
  await store.put(manifest, { source: 'bootstrap', seedTelemetry: true });
  const afterRow = await pool.query('SELECT change_seq,updated_at FROM federation_providers WHERE id=$1', [manifest.id]);
  assert.equal(Number(afterRow.rows[0].change_seq), Number(before.rows[0].change_seq));
  assert.equal(new Date(afterRow.rows[0].updated_at).toISOString(), new Date(before.rows[0].updated_at).toISOString());
});

pgtest('snapshot and delta each use one database query regardless of provider count', async () => {
  for (let i = 0; i < 250; i += 1) await store.put(provider(`bulk-${String(i).padStart(4, '0')}`));

  let queryCount = 0;
  const countedStore = {
    pool: {
      query: async (...args) => { queryCount += 1; return pool.query(...args); },
    },
  };
  const view = new PostgresProviderDeltaView(countedStore, { batchSize: 500 });
  const snapshot = await view.snapshot();
  assert.equal(snapshot.items.length, 250);
  assert.equal(snapshot.queries, 1);
  assert.equal(queryCount, 1);

  const cursor = snapshot.cursor;
  await store.updateMeasuredTelemetry('bulk-0007', { trust: 0.9 });
  await store.updateMeasuredTelemetry('bulk-0042', { trust: 0.8 });
  queryCount = 0;
  const delta = await view.changesSince(cursor);
  assert.equal(delta.items.length, 2);
  assert.equal(delta.queries, 1);
  assert.equal(queryCount, 1);
});
