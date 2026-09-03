import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresProviderDeltaView } from '../lib/registry-sync.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 8, application_name: 'bl-cf-registry-benchmark' });
    await openPostgresFederationState({ pool, applySchema: true });
  });
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE federation_provider_heartbeat_nonces,federation_providers RESTART IDENTITY CASCADE');
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

pgtest('10k-provider registry reads one snapshot then only changed rows', async () => {
  const providerCount = 10_000;
  const changedCount = 10;
  await pool.query(`
    WITH source AS (
      SELECT gs, 'bench-' || lpad(gs::text, 5, '0') AS id
      FROM generate_series(1, $1::int) AS gs
    )
    INSERT INTO federation_providers(
      id,grant_json,grant_hash,consent_ref,status,source,revision,telemetry_json,
      registered_at,updated_at,grant_expires_at,heartbeat_seq
    )
    SELECT
      id,
      jsonb_build_object(
        'manifestVersion','bl-cf-provider/v1',
        'id',id,
        'kind','http-worker',
        'endpoint','https://' || id || '.example.test',
        'capabilities',jsonb_build_array('compute.echo'),
        'authorization',jsonb_build_object(
          'consentRef','grant:' || id,
          'grantor','benchmark',
          'grantedAt','2026-01-01T00:00:00.000Z',
          'expiresAt','2099-01-01T00:00:00.000Z',
          'allowedDataClasses',jsonb_build_array('public'),
          'maxTaskCostUsd',1
        ),
        'limits',jsonb_build_object('maxConcurrency',2,'maxCostPerTaskUsd',1,'maxExecutionMs',5000),
        'dataPolicy',jsonb_build_object('privateDataAllowed',false,'internalDataAllowed',false,'retention','none'),
        'regions',jsonb_build_array('benchmark'),
        'dataLocations',jsonb_build_array('shared')
      ),
      md5(id),
      'grant:' || id,
      'active',
      'benchmark',
      1,
      '{"inFlight":0,"trust":0.5,"availability":1,"p95LatencyMs":10,"costPerUnitUsd":0}'::jsonb,
      now(),now(),'2099-01-01T00:00:00Z'::timestamptz,0
    FROM source
  `, [providerCount]);

  const view = new PostgresProviderDeltaView({ pool }, { batchSize: 500 });
  const snapshotStarted = performance.now();
  const snapshot = await view.snapshot();
  const snapshotMs = performance.now() - snapshotStarted;
  assert.equal(snapshot.items.length, providerCount);
  assert.equal(snapshot.rowsRead, providerCount);
  assert.equal(snapshot.queries, 1);

  await pool.query(`
    UPDATE federation_providers
    SET telemetry_json = telemetry_json || '{"trust":0.9}'::jsonb,
        updated_at = clock_timestamp()
    WHERE id IN (
      SELECT 'bench-' || lpad(gs::text, 5, '0')
      FROM generate_series(1, $1::int) AS gs
    )
  `, [changedCount]);

  const deltaStarted = performance.now();
  const delta = await view.changesSince(snapshot.cursor, { limit: 500 });
  const deltaMs = performance.now() - deltaStarted;
  assert.equal(delta.items.length, changedCount);
  assert.equal(delta.rowsRead, changedCount);
  assert.equal(delta.queries, 1);
  assert.equal(delta.hasMore, false);

  const rowReduction = snapshot.rowsRead / delta.rowsRead;
  assert.ok(rowReduction >= 1000, `expected >=1000x row reduction, got ${rowReduction}`);
  console.log(`# registry-scale-benchmark ${JSON.stringify({ providerCount, changedCount, snapshotRows: snapshot.rowsRead, deltaRows: delta.rowsRead, rowReduction, snapshotMs: Number(snapshotMs.toFixed(2)), deltaMs: Number(deltaMs.toFixed(2)) })}`);
});
