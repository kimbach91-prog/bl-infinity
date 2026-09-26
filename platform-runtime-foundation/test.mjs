import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PlatformRuntimeFoundation,
  PLATFORM_FOUNDATION_VERSION
} from './index.mjs';

function make() {
  const p = new PlatformRuntimeFoundation({
    availability_target: 0.75,
    latency_target_ms: 500,
    webhook_max_attempts: 3
  });

  p.tenants.createTenant({
    tenant_id: 't-a',
    org_id: 'org-a',
    name: 'Tenant A',
    region: 'APAC',
    data_residency: 'APAC',
    plan: {
      plan_id: 'PRO',
      currency: 'USD',
      quotas: { api_requests: 5, compute_ms: 1000 },
      prices: { api_requests: 0.01, compute_ms: 0.001 },
      monthly_credit: 0.02
    }
  });

  p.tenants.createTenant({
    tenant_id: 't-b',
    org_id: 'org-b',
    name: 'Tenant B',
    region: 'EU',
    data_residency: 'EU',
    plan: { plan_id: 'FREE', quotas: { api_requests: 2 } }
  });

  p.tenants.registerPrincipal({
    principal_id: 'pa',
    tenant_id: 't-a',
    kind: 'SERVICE_ACCOUNT',
    roles: ['admin'],
    scopes: ['jobs.run', 'events.publish'],
    credential_ref: 'vault://tenant-a/pa'
  });

  p.tenants.registerPrincipal({
    principal_id: 'pb',
    tenant_id: 't-b',
    kind: 'ORG_USER',
    roles: ['viewer'],
    scopes: ['jobs.read']
  });

  return p;
}

test('version is stable', () => {
  assert.equal(PLATFORM_FOUNDATION_VERSION, '1.0.0');
});

test('cross-tenant access is denied', () => {
  const p = make();
  const r = p.tenants.authorize({
    principal_id: 'pa',
    tenant_id: 't-b',
    required_scope: 'jobs.run'
  });
  assert.equal(r.allowed, false);
  assert.equal(r.reason, 'CROSS_TENANT_DENIED');
});

test('data residency is enforced independently of auth', () => {
  const p = make();
  const r = p.tenants.authorize({
    principal_id: 'pa',
    tenant_id: 't-a',
    required_scope: 'jobs.run',
    target_region: 'EU'
  });
  assert.equal(r.allowed, false);
  assert.equal(r.reason, 'DATA_RESIDENCY_DENIED');
});

test('quota blocks before execution and usage commits idempotently', () => {
  const p = make();
  for (let i = 0; i < 5; i++) {
    const reserve = p.authorizeAndReserve({
      principal_id: 'pa',
      tenant_id: 't-a',
      scope: 'jobs.run',
      metric: 'api_requests',
      quantity: 1
    });
    assert.equal(reserve.allowed, true);
    p.commitUsage({ reservation: reserve, event_id: `usage-${i}`, source_ref: `rcp-${i}` });
  }

  const blocked = p.authorizeAndReserve({
    principal_id: 'pa',
    tenant_id: 't-a',
    scope: 'jobs.run',
    metric: 'api_requests',
    quantity: 1
  });
  assert.equal(blocked.allowed, false);
  assert.equal(blocked.reason, 'QUOTA_EXCEEDED');

  const before = p.usage.total('t-a', 'api_requests');
  p.usage.append({
    event_id: 'usage-0',
    tenant_id: 't-a',
    metric: 'api_requests',
    quantity: 1,
    source_ref: 'duplicate-should-not-count'
  });
  assert.equal(p.usage.total('t-a', 'api_requests'), before);
});

test('billing derives from usage ledger and verified credits', () => {
  const p = make();
  const reserve = p.authorizeAndReserve({
    principal_id: 'pa',
    tenant_id: 't-a',
    scope: 'jobs.run',
    metric: 'compute_ms',
    quantity: 100
  });
  assert.equal(reserve.allowed, true);
  p.commitUsage({ reservation: reserve, event_id: 'c1', source_ref: 'receipt-c1' });
  p.billing.addCredit({
    tenant_id: 't-a',
    amount: 0.03,
    reason: 'verified-promo',
    receipt_ref: 'credit-r1'
  });
  const invoice = p.billing.previewInvoice('t-a');
  assert.equal(invoice.currency, 'USD');
  assert.equal(invoice.subtotal, 0.1);
  assert.equal(invoice.credits, 0.05);
  assert.equal(invoice.total, 0.05);
  assert.equal(invoice.settlement_required, true);
});

test('event outbox is tenant isolated and idempotent', () => {
  const p = make();
  p.events.subscribe({
    subscription_id: 'sub-a',
    tenant_id: 't-a',
    event_types: ['job.completed'],
    endpoint_ref: 'https://example.invalid/a',
    signing_secret_ref: 'vault://t-a/webhook-signing'
  });
  p.events.publish({
    event_id: 'e1',
    tenant_id: 't-a',
    type: 'job.completed',
    payload: { job_id: 'j1' },
    source_ref: 'receipt-j1'
  });
  const eligible = p.events.eligibleSubscriptions('e1');
  assert.equal(eligible.length, 1);
  const d = p.events.planDelivery({ event_id: 'e1', subscription_id: 'sub-a', attempt: 1 });
  assert.equal(d.state, 'READY');
  assert.equal(d.idempotency_key, 'e1::sub-a');
  assert.equal(d.signing_secret_ref, 'vault://t-a/webhook-signing');
});

test('webhook delivery dead-letters after bounded retries', () => {
  const p = make();
  p.events.subscribe({
    subscription_id: 'sub-a',
    tenant_id: 't-a',
    endpoint_ref: 'https://example.invalid/a'
  });
  p.events.publish({
    event_id: 'e2',
    tenant_id: 't-a',
    type: 'x',
    payload: {},
    source_ref: 'receipt-x'
  });
  const d = p.events.planDelivery({ event_id: 'e2', subscription_id: 'sub-a', attempt: 4 });
  assert.equal(d.state, 'DEAD_LETTER');
  assert.equal(d.attempts, 3);
});

test('SLO tracker exposes availability, latency and error budget truthfully', () => {
  const p = make();
  p.slo.record({ tenant_id: 't-a', service: 'api', success: true, latency_ms: 100 });
  p.slo.record({ tenant_id: 't-a', service: 'api', success: true, latency_ms: 200 });
  p.slo.record({ tenant_id: 't-a', service: 'api', success: true, latency_ms: 300 });
  p.slo.record({ tenant_id: 't-a', service: 'api', success: false, latency_ms: 700 });

  const s = p.slo.summarize({ tenant_id: 't-a', service: 'api' });
  assert.equal(s.sample_count, 4);
  assert.equal(s.availability, 0.75);
  assert.equal(s.availability_met, true);
  assert.equal(s.latency_met, false);
  assert.equal(s.status, 'SLO_AT_RISK');
});

test('suspended tenant cannot execute even with valid principal', () => {
  const p = make();
  p.tenants.updateTenantState('t-a', 'SUSPENDED');
  const r = p.authorizeAndReserve({
    principal_id: 'pa',
    tenant_id: 't-a',
    scope: 'jobs.run',
    metric: 'api_requests',
    quantity: 1
  });
  assert.equal(r.allowed, false);
  assert.equal(r.reason, 'TENANT_INACTIVE_OR_UNKNOWN');
});
