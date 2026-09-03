import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { BudgetGovernor } from '../lib/budget.mjs';
import { CircuitBreakerBook } from '../lib/circuit.mjs';
import { MemoryResultCache } from '../lib/cache.mjs';
import { isRestrictedIp, validateWorkerEndpoint } from '../lib/network-policy.mjs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { TokenBucketLimiter } from '../lib/rate-limit.mjs';
import { secureTokenEqual } from '../lib/control-auth.mjs';
import { safeDefaultHandlers } from '../worker/handlers.mjs';
import { createWorkerServer } from '../worker/server.mjs';
import { HttpWorkerAdapter } from '../adapters/http-worker.mjs';

function provider(overrides = {}) {
  const base = {
    manifestVersion: 'bl-cf-provider/v1', id: 'owner-local', kind: 'local', capabilities: ['compute.echo'],
    authorization: { consentRef: 'owner:self', grantor: 'owner', grantedAt: '2026-01-01T00:00:00.000Z', expiresAt: '2099-01-01T00:00:00.000Z', allowedDataClasses: ['public','private'], maxTaskCostUsd: 1 },
    limits: { maxConcurrency: 2, maxCostPerTaskUsd: 1, maxExecutionMs: 5000 },
    telemetry: { trust: 1, availability: 1, p95LatencyMs: 1, costPerUnitUsd: 0, inFlight: 0 },
    dataPolicy: { privateDataAllowed: true, internalDataAllowed: true, retention: 'none' }, dataLocations: ['local'], regions: ['local']
  };
  return { ...base, ...overrides };
}

test('budget reservations prevent overcommit and release safely', () => {
  const b = new BudgetGovernor({ totalUsd: 1, perTenantUsd: { a: 0.6 } });
  const r = b.reserve({ amountUsd: 0.5, tenantId: 'a' }); assert.equal(r.ok, true);
  assert.equal(b.reserve({ amountUsd: 0.2, tenantId: 'a' }).reason, 'tenant-budget-exceeded');
  b.release(r.reservation.id); assert.equal(b.reserve({ amountUsd: 0.6, tenantId: 'a' }).ok, true);
});

test('circuit opens after failures and permits half-open probe after cooldown', () => {
  const c = new CircuitBreakerBook({ failureThreshold: 2, cooldownMs: 10 });
  c.failure('p', 100); c.failure('p', 101); assert.equal(c.allow('p', 105).ok, false);
  assert.equal(c.allow('p', 112).state, 'half-open'); assert.equal(c.allow('p', 112).ok, false);
  c.success('p'); assert.equal(c.state('p', 113).state, 'closed');
});

test('private and side-effect tasks are not cached by default', () => {
  const c = new MemoryResultCache();
  assert.equal(c.set({ id:'a', capability:'x', dataClass:'private' }, { x:1 }), null);
  assert.equal(c.set({ id:'b', capability:'x', sideEffect:true }, { x:1 }), null);
  c.set({ id:'c', capability:'x', dataClass:'public', cachePolicy:'public' }, { x:1 });
  assert.equal(c.get({ id:'d', capability:'x', dataClass:'public', cachePolicy:'public' }).value.x, 1);
});

test('network policy blocks metadata, loopback and RFC1918 unless explicitly allowed', async () => {
  assert.equal(isRestrictedIp('169.254.169.254'), true); assert.equal(isRestrictedIp('10.0.0.1'), true); assert.equal(isRestrictedIp('8.8.8.8'), false);
  await assert.rejects(() => validateWorkerEndpoint('https://169.254.169.254', { resolveDns: false }), /private\/link-local\/reserved/);
  await assert.doesNotReject(() => validateWorkerEndpoint('https://10.0.0.1', { resolveDns: false, allowPrivateNetwork: true }));
});

test('orchestrator closes queue-execute-cache-ledger-budget loop', async () => {
  const runtime = createFederationRuntime({ providers: [provider()], localHandlers: safeDefaultHandlers, budgetConfig: { totalUsd: 1 } });
  await runtime.orchestrator.submit({ id:'job1', capability:'compute.echo', payload:{ hello:'world' }, dataClass:'public', cachePolicy:'public', estimatedCostUsd:0.1, tenantId:'t1' });
  const first = await runtime.orchestrator.runOnce(); assert.equal(first.job.state, 'succeeded'); assert.equal(first.execution.result.hello, 'world');
  await runtime.orchestrator.submit({ id:'job2', capability:'compute.echo', payload:{ hello:'world' }, dataClass:'public', cachePolicy:'public', estimatedCostUsd:0.1, tenantId:'t1', idempotencyKey:'distinct-key' });
  const second = await runtime.orchestrator.runOnce(); assert.equal(second.cacheHit, true);
  const status = await runtime.orchestrator.status(); assert.equal(status.ledger['owner-local'].tasks, 1); assert.equal(status.budget.spent.totalUsd, 0.1);
});

test('dedupe and cache boundaries do not collapse tenant-scoped work', async () => {
  const runtime = createFederationRuntime({ providers: [provider()], localHandlers: safeDefaultHandlers });
  const a = await runtime.orchestrator.submit({ id:'ta', tenantId:'A', capability:'compute.echo', payload:{x:1}, dataClass:'internal' });
  const b = await runtime.orchestrator.submit({ id:'tb', tenantId:'B', capability:'compute.echo', payload:{x:1}, dataClass:'internal' });
  assert.equal(a.deduplicated, false); assert.equal(b.deduplicated, false);
  const c = new MemoryResultCache();
  c.set({ id:'ca', tenantId:'A', capability:'x', payload:1, dataClass:'internal', cachePolicy:'tenant' }, { tenant:'A' });
  assert.equal(c.get({ id:'cb', tenantId:'B', capability:'x', payload:1, dataClass:'internal', cachePolicy:'tenant' }), null);
});

test('side effects require explicit provider grant and unsafe retries collapse to one attempt', async () => {
  const runtime = createFederationRuntime({ providers: [provider()], localHandlers: safeDefaultHandlers });
  const out = await runtime.orchestrator.submit({ id:'side1', capability:'compute.echo', payload:{x:1}, dataClass:'public', sideEffect:true });
  assert.equal(out.job.maxAttempts, 1);
  const run = await runtime.orchestrator.runOnce(); assert.match(run.error, /no eligible provider/);
});

test('control auth uses exact token equality and rate limiter enforces burst', () => {
  assert.equal(secureTokenEqual('abc', 'abc'), true); assert.equal(secureTokenEqual('abc', 'abd'), false); assert.equal(secureTokenEqual('abc', 'ab'), false);
  const l = new TokenBucketLimiter({ capacity: 2, refillPerSecond: 1 });
  assert.equal(l.take('ip', 1, 1000).ok, true); assert.equal(l.take('ip', 1, 1000).ok, true); assert.equal(l.take('ip', 1, 1000).ok, false); assert.equal(l.take('ip', 1, 2000).ok, true);
});

test('worker idempotency key replays stored result without rerunning handler', async (t) => {
  let calls = 0; const secret = 'idem-secret';
  const server = createWorkerServer({ handlers: { 'test.count': async () => ({ calls: ++calls }) }, sharedSecret: secret, requireAuth: true });
  server.listen(0, '127.0.0.1'); await once(server, 'listening'); t.after(() => server.close());
  const address = server.address();
  const p = provider({ id:'idem-http', kind:'http-worker', endpoint:`http://127.0.0.1:${address.port}`, capabilities:['test.count'], transport:{auth:'hmac-env',secretEnv:'IDEM_SECRET'} });
  const adapter = new HttpWorkerAdapter({ env:{IDEM_SECRET:secret} });
  const task = { id:'first', idempotencyKey:'same-op', capability:'test.count', payload:null, dataClass:'public' };
  assert.equal((await adapter.execute(p, task)).calls, 1);
  assert.equal((await adapter.execute(p, { ...task, id:'retry' })).calls, 1);
  assert.equal(calls, 1);
});
