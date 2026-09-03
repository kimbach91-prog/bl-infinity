import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresProviderStore } from '../lib/provider-store.mjs';
import { PostgresTokenBucketLimiter, rateLimitScopeKey } from '../lib/rate-limit.mjs';

const connectionString = process.env.BL_RESTORE_SOURCE_URL || process.env.BL_TEST_POSTGRES_URL;
if (!connectionString) throw new Error('BL_RESTORE_SOURCE_URL or BL_TEST_POSTGRES_URL is required');

const state = await openPostgresFederationState({ connectionString, applySchema: true, budget: { totalUsd: 10, perProviderUsd: { 'restore-active': 10 } } });
const store = new PostgresProviderStore(state.pool);

try {
  await state.pool.query(`
    TRUNCATE TABLE
      federation_provider_heartbeat_nonces,
      federation_jobs,
      federation_result_cache,
      federation_rate_limit_buckets,
      federation_budget_reservations,
      federation_contribution_ledger,
      federation_audit,
      federation_providers
    RESTART IDENTITY CASCADE
  `);

  await store.put(provider('restore-active'));
  await store.put(provider('restore-revoked'));
  await store.revoke('restore-revoked', 'restore-drill-revocation');

  await state.queue.enqueue({
    id: 'restore-pending-job',
    tenantId: 'restore-tenant',
    capability: 'compute.echo',
    payload: { marker: 'restore-fixture' },
    dataClass: 'public',
    estimatedCostUsd: 0.2,
  }, { idempotencyKey: 'restore-pending-job' });

  const reservation = await state.budget.reserve({
    amountUsd: 0.2,
    tenantId: 'restore-tenant',
    providerId: 'restore-active',
    taskId: 'restore-accounted-task',
  });
  if (!reservation.ok) throw new Error(`restore fixture budget reservation rejected: ${reservation.reason}`);
  await state.budget.commit(reservation.reservation.id, 0.2);

  await state.ledger.record({
    taskId: 'restore-accounted-task',
    providerId: 'restore-active',
    consentRef: 'grant:restore-active',
    tenantId: 'restore-tenant',
    measuredLatencyMs: 12,
    billedCostUsd: 0.2,
    inputBytes: 100,
    outputBytes: 200,
    status: 'succeeded',
  });
  await state.audit.append('restore.fixture-created', { marker: 'bl-cf-restore-v1' });
  await state.audit.append('provider.revoked', { providerId: 'restore-revoked', reason: 'restore-drill-revocation' });

  await state.pool.query(`
    INSERT INTO federation_provider_heartbeat_nonces(provider_id,nonce,seen_at,expires_at)
    VALUES('restore-active','restore-nonce-0001',now(),now()+interval '1 hour')
  `);

  const restoreRateKey = rateLimitScopeKey({ principalId: 'restore-principal', routeGroup: 'task-submit' });
  const restoreLimiter = new PostgresTokenBucketLimiter(state.pool, { capacity: 5, refillPerSecond: 1, idleTtlMs: 60 * 60_000, cleanupEvery: 10000 });
  const rate = await restoreLimiter.take(restoreRateKey, 2);
  if (!rate.ok || rate.remaining !== 3) throw new Error('failed to seed restore rate-limit bucket');

  console.log(JSON.stringify({ ok: true, fixture: 'bl-cf-restore-v1', restoreRateKey }));
} finally {
  await state.close();
}

function provider(id) {
  return {
    manifestVersion: 'bl-cf-provider/v1',
    id,
    kind: 'http-worker',
    endpoint: `https://${id}.example.test`,
    capabilities: ['compute.echo'],
    authorization: {
      consentRef: `grant:${id}`,
      grantor: 'restore-drill',
      grantedAt: '2026-01-01T00:00:00.000Z',
      expiresAt: '2099-01-01T00:00:00.000Z',
      allowedDataClasses: ['public'],
      maxTaskCostUsd: 1,
    },
    limits: { maxConcurrency: 2, maxCostPerTaskUsd: 1, maxExecutionMs: 5000 },
    dataPolicy: { privateDataAllowed: false, internalDataAllowed: false, retention: 'none' },
    regions: ['restore'],
    dataLocations: ['shared'],
  };
}
