import test from 'node:test';
import assert from 'node:assert/strict';
import { loadPlatformPostgresSchema, openPostgresPlatformRuntime, PostgresPlatformRuntime } from './postgres.mjs';

class ScriptedPool {
  constructor(steps = []) { this.steps = [...steps]; this.calls = []; }
  async query(sql, params = []) {
    this.calls.push({ sql: String(sql), params });
    const step = this.steps.shift();
    if (!step) return { rowCount: 0, rows: [] };
    if (step.match && !step.match.test(String(sql))) throw new Error('unexpected SQL: ' + String(sql));
    return step.result;
  }
}

test('schema is additive and includes all platform persistence relations', async () => {
  const sql = await loadPlatformPostgresSchema();
  for (const table of [
    'deus_platform_tenants',
    'deus_platform_principals',
    'deus_platform_usage_events',
    'deus_platform_billing_credits',
    'deus_platform_webhook_subscriptions',
    'deus_platform_outbox',
    'deus_platform_webhook_deliveries',
    'deus_platform_slo_samples',
  ]) assert.match(sql, new RegExp('CREATE TABLE IF NOT EXISTS ' + table));
  assert.match(sql, /PRIMARY KEY\(event_id, subscription_id\)/);
  assert.doesNotMatch(sql, /DROP TABLE|TRUNCATE TABLE|DELETE FROM federation_/i);
});

test('open runtime performs a non-mutating readiness query when applySchema=false', async () => {
  const pool = new ScriptedPool([{ match: /SELECT 1/, result: { rowCount: 1, rows: [{ '?column?': 1 }] } }]);
  const opened = await openPostgresPlatformRuntime({ pool, applySchema: false });
  assert.ok(opened.runtime instanceof PostgresPlatformRuntime);
  assert.equal(pool.calls.length, 1);
});

test('authorize fails closed when principal is not bound to requested tenant', async () => {
  const pool = new ScriptedPool([{ match: /FROM deus_platform_principals/, result: { rowCount: 0, rows: [] } }]);
  const runtime = new PostgresPlatformRuntime(pool);
  const verdict = await runtime.authorize({ principal_id: 'pA', tenant_id: 'tenantB', required_scope: 'jobs.run' });
  assert.deepEqual(verdict, { allowed: false, reason: 'CROSS_TENANT_OR_PRINCIPAL_DENIED' });
});

test('authorize enforces scope and data residency after tenant binding', async () => {
  const row = {
    principal_id: 'pA', tenant_id: 'tenantA', roles: ['admin'], scopes: ['jobs.run'],
    active: true, principal_region: 'APAC', tenant_state: 'ACTIVE', tenant_region: 'APAC',
    data_residency: 'APAC', plan: {},
  };
  const pool = new ScriptedPool([
    { match: /FROM deus_platform_principals/, result: { rowCount: 1, rows: [row] } },
    { match: /FROM deus_platform_principals/, result: { rowCount: 1, rows: [row] } },
  ]);
  const runtime = new PostgresPlatformRuntime(pool);
  assert.equal((await runtime.authorize({ principal_id: 'pA', tenant_id: 'tenantA', required_scope: 'jobs.run' })).allowed, true);
  assert.equal((await runtime.authorize({ principal_id: 'pA', tenant_id: 'tenantA', required_scope: 'jobs.run', target_region: 'EU' })).reason, 'DATA_RESIDENCY_DENIED');
});

test('usage event idempotency returns existing row rather than double-counting', async () => {
  const existing = {
    event_id: 'e1', tenant_id: 't1', metric: 'api_requests', quantity: '1',
    source_ref: 'r1', workload_family: 'GENERAL', metadata: {}, occurred_at: '2026-09-27T00:00:00.000Z',
  };
  const pool = new ScriptedPool([
    { match: /INSERT INTO deus_platform_usage_events/, result: { rowCount: 0, rows: [] } },
    { match: /SELECT \* FROM deus_platform_usage_events/, result: { rowCount: 1, rows: [existing] } },
  ]);
  const runtime = new PostgresPlatformRuntime(pool);
  const result = await runtime.recordUsage({ event_id: 'e1', tenant_id: 't1', metric: 'api_requests', quantity: 1, source_ref: 'r1' });
  assert.equal(result.deduplicated, true);
  assert.equal(result.event.quantity, 1);
});

test('quota check uses persisted usage and fails before new execution', async () => {
  const pool = new ScriptedPool([
    { match: /SELECT state,plan/, result: { rowCount: 1, rows: [{ state: 'ACTIVE', plan: { quotas: { api_requests: 5 } } }] } },
    { match: /SUM\(quantity\)/, result: { rowCount: 1, rows: [{ total: '5' }] } },
  ]);
  const runtime = new PostgresPlatformRuntime(pool);
  const verdict = await runtime.quotaCheck({ tenant_id: 't1', metric: 'api_requests', requested_quantity: 1 });
  assert.equal(verdict.allowed, false);
  assert.equal(verdict.reason, 'QUOTA_EXCEEDED');
});

test('publish event materializes tenant-matching delivery rows only through SQL join', async () => {
  const event = { event_id: 'e1', tenant_id: 't1', type: 'job.completed', payload: {}, source_ref: 'r1', sequence: 1 };
  const pool = new ScriptedPool([
    { match: /INSERT INTO deus_platform_outbox/, result: { rowCount: 1, rows: [event] } },
    { match: /INSERT INTO deus_platform_webhook_deliveries/, result: { rowCount: 1, rows: [] } },
  ]);
  const runtime = new PostgresPlatformRuntime(pool);
  const published = await runtime.publishEvent({ event_id: 'e1', tenant_id: 't1', type: 'job.completed', payload: {}, source_ref: 'r1' });
  assert.equal(published.tenant_id, 't1');
  assert.match(pool.calls[1].sql, /s\.tenant_id=\$2/);
});

test('SLO summary reports risk when availability or latency target is missed', async () => {
  const pool = new ScriptedPool([
    { match: /percentile_cont/, result: { rowCount: 1, rows: [{ samples: '4', success_count: '3', p95: '700' }] } },
  ]);
  const runtime = new PostgresPlatformRuntime(pool);
  const s = await runtime.summarizeSlo({ tenant_id: 't1', service: 'api', availability_target: 0.75, latency_target_ms: 500 });
  assert.equal(s.availability, 0.75);
  assert.equal(s.availability_met, true);
  assert.equal(s.latency_met, false);
  assert.equal(s.status, 'SLO_AT_RISK');
});
