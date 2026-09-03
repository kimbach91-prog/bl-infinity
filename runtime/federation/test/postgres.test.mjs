import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { assertPostgresSchema } from '../lib/postgres-readiness.mjs';
import { PostgresProviderStore, syncProviderRegistry } from '../lib/provider-store.mjs';
import { ProviderRegistry } from '../lib/fabric.mjs';
import { signProviderManifest, verifyProviderManifest } from '../lib/manifest.mjs';
import { verifyAuditChain } from '../lib/audit.mjs';
import { verifyContributionLedger } from '../lib/ledger.mjs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { safeDefaultHandlers } from '../worker/handlers.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;
const testKeys = generateKeyPairSync('ed25519');
const privateKeyPem = testKeys.privateKey.export({ type: 'pkcs8', format: 'pem' });
const publicKeyPem = testKeys.publicKey.export({ type: 'spki', format: 'pem' });
const trustStore = { 'test-provider-key': publicKeyPem };
const manifestVerifier = (manifest) => verifyProviderManifest(manifest, trustStore, { requireSignature: true });

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 20, application_name: 'bl-cf-test' });
    const state = await openPostgresFederationState({ pool, applySchema: true });
    await state.close();
  });

  beforeEach(async () => {
    await resetDatabase(pool);
  });

  after(async () => {
    await pool?.end();
  });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

function localProvider(id = 'pg-local', overrides = {}) {
  const base = {
    manifestVersion: 'bl-cf-provider/v1', id, kind: 'local', capabilities: ['compute.echo'],
    authorization: { consentRef: `owner:${id}`, grantor: 'owner', grantedAt: '2026-01-01T00:00:00.000Z', expiresAt: '2099-01-01T00:00:00.000Z', allowedDataClasses: ['public'], maxTaskCostUsd: 1 },
    limits: { maxConcurrency: 4, maxCostPerTaskUsd: 1, maxExecutionMs: 5000 },
    telemetry: { trust: 1, availability: 1, p95LatencyMs: 1, costPerUnitUsd: 0, inFlight: 0 },
    dataPolicy: { privateDataAllowed: false, internalDataAllowed: false, retention: 'none' },
    dataLocations: ['local'], regions: ['local']
  };
  return { ...base, ...overrides };
}

function signedHeartbeatProvider(id = 'shared-provider', overrides = {}) {
  const manifest = localProvider(id, {
    telemetry: { trust: 0.4, availability: 0.5, p95LatencyMs: 40, costPerUnitUsd: 0.01, inFlight: 0 },
    liveness: { heartbeatRequired: true, heartbeatTtlMs: 60_000 },
    ...overrides,
  });
  return signProviderManifest(manifest, privateKeyPem, 'test-provider-key');
}

pgtest('postgres tenant idempotency permits same explicit key across tenants', async () => {
  const state = await openPostgresFederationState({ pool });
  const a = await state.queue.enqueue({ id: 'a1', tenantId: 'A', capability: 'compute.echo', dataClass: 'public' }, { idempotencyKey: 'same' });
  const b = await state.queue.enqueue({ id: 'b1', tenantId: 'B', capability: 'compute.echo', dataClass: 'public' }, { idempotencyKey: 'same' });
  const a2 = await state.queue.enqueue({ id: 'a2', tenantId: 'A', capability: 'compute.echo', dataClass: 'public' }, { idempotencyKey: 'same' });
  assert.equal(a.deduplicated, false); assert.equal(b.deduplicated, false); assert.equal(a2.deduplicated, true); assert.equal(a2.job.id, 'a1');
});

pgtest('postgres SKIP LOCKED lets concurrent coordinators claim different jobs', async () => {
  const state = await openPostgresFederationState({ pool });
  await state.queue.enqueue({ id: 'claim-1', capability: 'compute.echo', payload: { n: 1 }, dataClass: 'public' }, { idempotencyKey: 'claim-1' });
  await state.queue.enqueue({ id: 'claim-2', capability: 'compute.echo', payload: { n: 2 }, dataClass: 'public' }, { idempotencyKey: 'claim-2' });
  const [one, two] = await Promise.all([
    state.queue.claim('coordinator-1', ['compute.echo'], { leaseMs: 10_000 }),
    state.queue.claim('coordinator-2', ['compute.echo'], { leaseMs: 10_000 }),
  ]);
  assert.ok(one); assert.ok(two); assert.notEqual(one.id, two.id);
  assert.deepEqual(new Set([one.lease.workerId, two.lease.workerId]), new Set(['coordinator-1', 'coordinator-2']));
});

pgtest('postgres advisory budget lock prevents concurrent global overcommit', async () => {
  const state = await openPostgresFederationState({ pool, budget: { totalUsd: 1, perProviderUsd: { p: 1 } } });
  const [a, b] = await Promise.all([
    state.budget.reserve({ amountUsd: 0.7, tenantId: 'A', providerId: 'p', taskId: 'budget-a' }),
    state.budget.reserve({ amountUsd: 0.7, tenantId: 'B', providerId: 'p', taskId: 'budget-b' }),
  ]);
  const accepted = [a, b].filter((x) => x.ok), rejected = [a, b].filter((x) => !x.ok);
  assert.equal(accepted.length, 1); assert.equal(rejected.length, 1); assert.equal(rejected[0].reason, 'global-budget-exceeded');
  assert.equal((await state.budget.snapshot()).reserved.totalUsd, 0.7);
  await state.budget.release(accepted[0].reservation.id, 'test-cleanup');
});

pgtest('postgres ledger and audit chains remain valid under concurrent appenders', async () => {
  const state = await openPostgresFederationState({ pool });
  await Promise.all(Array.from({ length: 16 }, (_, i) => state.ledger.record({ taskId: `ledger-${i}`, providerId: `p-${i % 3}`, consentRef: 'test:grant', tenantId: `t-${i % 2}`, measuredLatencyMs: i + 1, billedCostUsd: 0.001, inputBytes: 10, outputBytes: 20, status: 'succeeded' })));
  await Promise.all(Array.from({ length: 16 }, (_, i) => state.audit.append('concurrent.test', { i })));
  const ledger = await state.ledger.list(), audit = await state.audit.list();
  assert.equal(ledger.length, 16); assert.equal(audit.length, 16);
  assert.equal(verifyContributionLedger(ledger).ok, true); assert.equal(verifyAuditChain(audit).ok, true);
});

pgtest('postgres chain verifier accepts sequence gaps caused by rolled-back nextval', async () => {
  const state = await openPostgresFederationState({ pool });
  await state.ledger.record({ taskId: 'before-gap', providerId: 'p', consentRef: 'g', tenantId: 't' });
  const client = await pool.connect();
  try { await client.query('BEGIN'); await client.query("SELECT nextval(pg_get_serial_sequence('federation_contribution_ledger','seq'))"); await client.query('ROLLBACK'); }
  finally { client.release(); }
  await state.ledger.record({ taskId: 'after-gap', providerId: 'p', consentRef: 'g', tenantId: 't' });
  const ledger = await state.ledger.list();
  assert.ok(ledger[1].seq > ledger[0].seq + 1); assert.equal(verifyContributionLedger(ledger).ok, true);
});

pgtest('postgres cache write starts at zero hits and increments atomically on read', async () => {
  const state = await openPostgresFederationState({ pool });
  const task = { id: 'cache-pg', tenantId: 'A', capability: 'compute.echo', payload: { x: 1 }, dataClass: 'public', cachePolicy: 'public' };
  const written = await state.cache.set(task, { ok: true }, { ttlMs: 60_000 }); assert.equal(written.hits, 0);
  const [r1, r2] = await Promise.all([state.cache.get(task), state.cache.get(task)]); assert.ok(r1 && r2);
  assert.equal((await state.cache.stats()).hits, 2);
});

pgtest('runtime shared-state policy rejects private data before it reaches Postgres', async () => {
  const state = await openPostgresFederationState({ pool });
  const runtime = createFederationRuntime({ providers: [localProvider()], localHandlers: safeDefaultHandlers, state, allowedStateDataClasses: ['public'] });
  await assert.rejects(() => runtime.orchestrator.submit({ id: 'private-rejected', tenantId: 'tenant', capability: 'compute.echo', payload: { secret: true }, dataClass: 'private' }), (error) => error.code === 'STATE_DATA_CLASS_REJECTED');
  assert.equal(await state.queue.get('private-rejected'), null);
});

pgtest('postgres readiness gate detects a missing required relation', async () => {
  assert.equal((await assertPostgresSchema(pool)).ok, true);
  await pool.query('DROP TABLE federation_result_cache');
  try { await assert.rejects(() => assertPostgresSchema(pool), (error) => error.code === 'POSTGRES_SCHEMA_MISSING'); }
  finally { const schema = await readFile(new URL('../storage/postgres/schema.sql', import.meta.url), 'utf8'); await pool.query(schema); }
});

pgtest('runtime persists queue budget and ledger across separate Postgres pools', async () => {
  const firstState = await openPostgresFederationState({ pool, budget: { totalUsd: 1 } });
  const runtime = createFederationRuntime({ providers: [localProvider()], localHandlers: safeDefaultHandlers, state: firstState, allowedStateDataClasses: ['public'] });
  await runtime.orchestrator.submit({ id: 'pg-e2e', tenantId: 'tenant', capability: 'compute.echo', payload: { hello: 'postgres' }, dataClass: 'public', estimatedCostUsd: 0.1 });
  const run = await runtime.orchestrator.runOnce({ coordinatorId: 'coordinator-A' });
  assert.equal(run.job.state, 'succeeded'); assert.equal(run.execution.result.hello, 'postgres');
  const secondPool = new Pool({ connectionString, max: 4, application_name: 'bl-cf-reopen-test' });
  try {
    const secondState = await openPostgresFederationState({ pool: secondPool, budget: { totalUsd: 1 } });
    assert.equal((await secondState.queue.get('pg-e2e')).state, 'succeeded');
    assert.equal((await secondState.ledger.summary())['pg-local'].tasks, 1);
    assert.equal((await secondState.budget.snapshot()).spent.totalUsd, 0.1);
  } finally { await secondPool.end(); }
});

pgtest('shared provider liveness cannot mutate signed authority and revocation propagates', async () => {
  const store = new PostgresProviderStore(pool, { manifestVerifier });
  const signed = signedHeartbeatProvider('shared-live');
  const stored = await store.put(signed, { source: 'test-bootstrap' });
  assert.equal(stored.status, 'disabled');
  assert.equal(stored.runtime.heartbeatRequired, true);
  const grantHash = stored.runtime.grantHash;

  const heartbeat = await store.heartbeat('shared-live', { inFlight: 2, trust: 1 });
  assert.equal(heartbeat.status, 'active');
  assert.equal(heartbeat.telemetry.inFlight, 2);
  assert.equal(heartbeat.telemetry.trust, 0.4);
  assert.equal(heartbeat.runtime.grantHash, grantHash);
  assert.deepEqual(heartbeat.capabilities, ['compute.echo']);

  const a = new ProviderRegistry([], { manifestVerifier });
  const b = new ProviderRegistry([], { manifestVerifier });
  await syncProviderRegistry(a, store); await syncProviderRegistry(b, store);
  assert.equal(a.get('shared-live').status, 'active'); assert.equal(b.get('shared-live').status, 'active');

  const revoked = await store.revoke('shared-live', 'owner-request');
  assert.equal(revoked.authorization.revokedAt != null, true);
  await syncProviderRegistry(a, store); await syncProviderRegistry(b, store);
  assert.equal(a.get('shared-live').status, 'disabled'); assert.equal(b.get('shared-live').status, 'disabled');
  await assert.rejects(() => store.heartbeat('shared-live', { inFlight: 0 }), (error) => error.code === 'PROVIDER_REVOKED');
  await assert.rejects(() => store.put(signed), (error) => error.code === 'PROVIDER_REVOKED');
});

pgtest('explicit new signed grant revision is required to replace revoked authority', async () => {
  const store = new PostgresProviderStore(pool, { manifestVerifier });
  const first = signedHeartbeatProvider('shared-revision');
  await store.put(first); await store.revoke('shared-revision', 'rotate-grant');
  const second = signedHeartbeatProvider('shared-revision', {
    capabilities: ['compute.echo', 'compute.hash'],
    authorization: { ...first.authorization, consentRef: 'owner:shared-revision:v2' },
  });
  const replaced = await store.put(second, { replace: true, source: 'operator-regrant' });
  assert.equal(replaced.runtime.revision, 2);
  assert.equal(replaced.status, 'disabled');
  assert.deepEqual(replaced.capabilities, ['compute.echo', 'compute.hash']);
  const activated = await store.heartbeat('shared-revision', { inFlight: 0 });
  assert.equal(activated.status, 'active');
});

async function resetDatabase(targetPool) {
  await targetPool.query(`
    TRUNCATE TABLE
      federation_jobs,
      federation_result_cache,
      federation_budget_reservations,
      federation_contribution_ledger,
      federation_audit,
      federation_providers
    RESTART IDENTITY
  `);
}
