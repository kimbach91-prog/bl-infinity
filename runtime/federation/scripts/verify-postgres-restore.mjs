import assert from 'node:assert/strict';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresProviderStore } from '../lib/provider-store.mjs';
import { PostgresProviderDeltaView } from '../lib/registry-sync.mjs';
import { rateLimitScopeKey } from '../lib/rate-limit.mjs';
import { assertPostgresSchema, assertProviderDeltaSchema } from '../lib/postgres-readiness.mjs';
import { verifyAuditChain } from '../lib/audit.mjs';
import { verifyContributionLedger } from '../lib/ledger.mjs';

const connectionString = process.env.BL_RESTORE_VERIFY_URL;
if (!connectionString) throw new Error('BL_RESTORE_VERIFY_URL is required');

const state = await openPostgresFederationState({ connectionString, budget: { totalUsd: 10, perProviderUsd: { 'restore-active': 10 } } });
const store = new PostgresProviderStore(state.pool);

try {
  assert.equal((await assertPostgresSchema(state.pool)).ok, true);
  assert.equal((await assertProviderDeltaSchema(state.pool)).ok, true);

  const audit = await state.audit.list();
  const ledger = await state.ledger.list();
  assert.equal(verifyAuditChain(audit).ok, true);
  assert.equal(verifyContributionLedger(ledger).ok, true);
  assert.ok(audit.some((entry) => entry.type === 'restore.fixture-created' && entry.data?.marker === 'bl-cf-restore-v1'));
  assert.equal(ledger.length, 1);
  assert.equal(ledger[0].providerId, 'restore-active');

  const active = await store.get('restore-active');
  const revoked = await store.get('restore-revoked');
  assert.equal(active.status, 'active');
  assert.equal(revoked.status, 'disabled');
  assert.ok(revoked.authorization.revokedAt);
  assert.equal(revoked.runtime.revokeReason, 'restore-drill-revocation');
  await assert.rejects(() => store.heartbeat('restore-revoked', { inFlight: 0 }), (error) => error.code === 'PROVIDER_REVOKED');

  const pending = await state.queue.get('restore-pending-job');
  assert.equal(pending.state, 'pending');
  assert.equal(pending.task.payload.marker, 'restore-fixture');

  const budget = await state.budget.snapshot();
  assert.equal(budget.spent.totalUsd, 0.2);
  assert.equal(budget.spent.perProviderUsd['restore-active'], 0.2);
  assert.equal(budget.reserved.totalUsd, 0);

  const nonce = await state.pool.query(`SELECT COUNT(*)::int AS n FROM federation_provider_heartbeat_nonces WHERE provider_id='restore-active' AND nonce='restore-nonce-0001'`);
  assert.equal(Number(nonce.rows[0].n), 1);

  const restoreRateKey = rateLimitScopeKey({ principalId: 'restore-principal', routeGroup: 'task-submit' });
  const restoredRate = await state.pool.query('SELECT tokens,expires_at FROM federation_rate_limit_buckets WHERE scope_key=$1', [restoreRateKey]);
  assert.equal(restoredRate.rowCount, 1);
  assert.equal(Number(restoredRate.rows[0].tokens), 3);
  assert.ok(new Date(restoredRate.rows[0].expires_at).getTime() > Date.now());

  const view = new PostgresProviderDeltaView(store);
  const snapshot = await view.snapshot();
  assert.equal(snapshot.items.length, 2);
  assert.ok(snapshot.cursor > 0);
  const beforeSeq = snapshot.items.find((item) => item.provider.id === 'restore-active').changeSeq;
  await store.updateMeasuredTelemetry('restore-active', { trust: 0.66 });
  const delta = await view.changesSince(snapshot.cursor);
  assert.equal(delta.items.length, 1);
  assert.equal(delta.items[0].provider.id, 'restore-active');
  assert.ok(delta.items[0].changeSeq > beforeSeq);

  console.log(JSON.stringify({
    ok: true,
    fixture: 'bl-cf-restore-v1',
    auditRecords: audit.length,
    ledgerRecords: ledger.length,
    providers: snapshot.items.length,
    restoredRevocation: true,
    restoredBudgetUsd: budget.spent.totalUsd,
    restoredRateLimitTokens: Number(restoredRate.rows[0].tokens),
    deltaCursorContinues: true,
  }));
} finally {
  await state.close();
}
