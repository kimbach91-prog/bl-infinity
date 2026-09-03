import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createSqliteFederationState } from '../lib/sqlite-state.mjs';
import { verifyAuditChain } from '../lib/audit.mjs';
import { verifyContributionLedger } from '../lib/ledger.mjs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { safeDefaultHandlers } from '../worker/handlers.mjs';
import { MemoryLeaseQueue } from '../lib/queue.mjs';
import { BudgetGovernor } from '../lib/budget.mjs';

async function tempDb(t) { const dir = await mkdtemp(join(tmpdir(), 'blcf-sqlite-')); t.after(() => rm(dir, { recursive: true, force: true })); return join(dir, 'state.db'); }
function localProvider(id = 'local', latency = 1) { return { manifestVersion:'bl-cf-provider/v1', id, kind:'local', capabilities:['compute.echo'], authorization:{consentRef:`owner:${id}`,grantor:'owner',grantedAt:'2026-01-01T00:00:00.000Z',expiresAt:'2099-01-01T00:00:00.000Z',allowedDataClasses:['public'],maxTaskCostUsd:1}, limits:{maxConcurrency:2,maxCostPerTaskUsd:1,maxExecutionMs:5000}, telemetry:{trust:1,availability:1,p95LatencyMs:latency,costPerUnitUsd:0,inFlight:0}, dataPolicy:{privateDataAllowed:false,internalDataAllowed:false,retention:'none'},dataLocations:['local'],regions:['local'] }; }

test('sqlite queue survives restart and preserves idempotency', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path);
  state.queue.enqueue({ id:'j1', tenantId:'a', capability:'compute.echo', payload:{x:1}, dataClass:'public' }); state.close();
  state = createSqliteFederationState(path); assert.equal(state.queue.get('j1').state, 'pending');
  const dup = state.queue.enqueue({ id:'j2', tenantId:'a', capability:'compute.echo', payload:{x:1}, dataClass:'public' }); assert.equal(dup.deduplicated, true); assert.equal(dup.job.id, 'j1'); state.close();
});

test('explicit idempotency keys are tenant scoped in memory and sqlite queues', async (t) => {
  const memory = new MemoryLeaseQueue();
  const a = memory.enqueue({ id:'ma', tenantId:'a', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  const b = memory.enqueue({ id:'mb', tenantId:'b', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  const aDup = memory.enqueue({ id:'ma2', tenantId:'a', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  assert.equal(a.deduplicated, false); assert.equal(b.deduplicated, false); assert.equal(aDup.deduplicated, true); assert.equal(aDup.job.id, 'ma');

  const path = await tempDb(t); const state = createSqliteFederationState(path);
  const sa = state.queue.enqueue({ id:'sa', tenantId:'a', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  const sb = state.queue.enqueue({ id:'sb', tenantId:'b', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  const saDup = state.queue.enqueue({ id:'sa2', tenantId:'a', capability:'compute.echo', dataClass:'public' }, { idempotencyKey:'same' });
  assert.equal(sa.deduplicated, false); assert.equal(sb.deduplicated, false); assert.equal(saDup.deduplicated, true); assert.equal(saDup.job.id, 'sa'); state.close();
});

test('sqlite lease expiration recovers across reopen', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path, { queue:{ defaultLeaseMs:10, maxAttempts:2 } });
  state.queue.enqueue({ id:'j', capability:'compute.echo', dataClass:'public' }, { now:100 }); const claimed = state.queue.claim('w',['compute.echo'],{now:100,leaseMs:10}); assert.equal(claimed.state,'running'); state.close();
  state = createSqliteFederationState(path, { queue:{ defaultLeaseMs:10, maxAttempts:2 } }); assert.deepEqual(state.queue.sweepExpired(111), ['j']); assert.equal(state.queue.get('j').state,'pending'); state.close();
});

test('sqlite cache writes do not count as cache hits', async (t) => {
  const path = await tempDb(t); const state = createSqliteFederationState(path);
  const task = { id:'cache-1', tenantId:'a', capability:'compute.echo', payload:{x:1}, dataClass:'public', cachePolicy:'public' };
  const written = state.cache.set(task, {ok:true}, {now:100, ttlMs:1000});
  assert.equal(written.hits, 0); assert.equal(state.cache.stats().hits, 0);
  const read = state.cache.get(task, 200); assert.equal(read.hits, 1); assert.equal(state.cache.stats().hits, 1); state.close();
});

test('sqlite cache budget ledger and audit survive restart', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path, { budget:{ totalUsd:1 } });
  const task={id:'c1',tenantId:'a',capability:'compute.echo',payload:{x:1},dataClass:'public',cachePolicy:'public'};
  state.cache.set(task,{ok:true},{now:100,ttlMs:1000}); const r=state.budget.reserve({amountUsd:0.2,tenantId:'a',taskId:'c1'}); state.budget.commit(r.reservation.id,0.2);
  state.ledger.record({taskId:'c1',providerId:'p1',consentRef:'grant:1',tenantId:'a',measuredLatencyMs:4,billedCostUsd:0.2,inputBytes:2,outputBytes:3,status:'succeeded'}); await state.audit.append('test.event',{x:1}); state.close();
  state=createSqliteFederationState(path,{budget:{totalUsd:1}}); assert.equal(state.cache.get(task,200).value.ok,true); assert.equal(state.budget.snapshot().spent.totalUsd,0.2); assert.equal(state.ledger.summary().p1.tasks,1); assert.equal(verifyContributionLedger(state.ledger.list()).ok,true); assert.equal(verifyAuditChain(state.audit.list()).ok,true); state.close();
});

test('actual cost above reservation is rejected by memory and sqlite hard budgets', async (t) => {
  const memory = new BudgetGovernor({ totalUsd:0.1, perTenantUsd:{a:0.1}, perProviderUsd:{p:0.1} });
  const mr = memory.reserve({ amountUsd:0.05, tenantId:'a', providerId:'p', taskId:'m' });
  assert.throws(() => memory.commit(mr.reservation.id, 0.2), /actual cost rejected/);
  assert.equal(memory.snapshot().spent.totalUsd, 0); assert.equal(memory.snapshot().reserved.totalUsd, 0.05); memory.release(mr.reservation.id);

  const path = await tempDb(t); const state = createSqliteFederationState(path, { budget:{ totalUsd:0.1, perTenantUsd:{a:0.1}, perProviderUsd:{p:0.1} } });
  const sr = state.budget.reserve({ amountUsd:0.05, tenantId:'a', providerId:'p', taskId:'s' });
  assert.throws(() => state.budget.commit(sr.reservation.id, 0.2), /actual cost rejected/);
  assert.equal(state.budget.snapshot().spent.totalUsd, 0); assert.equal(state.budget.snapshot().reserved.totalUsd, 0.05); state.budget.release(sr.reservation.id); state.close();
});

test('orchestrator reserves provider budget and falls through to provider with capacity', async (t) => {
  const path = await tempDb(t); const state = createSqliteFederationState(path, { budget:{ totalUsd:1, perProviderUsd:{fast:0.1,backup:1} } });
  const runtime = createFederationRuntime({ providers:[localProvider('fast',1), localProvider('backup',100)], localHandlers:safeDefaultHandlers, state });
  await runtime.orchestrator.submit({ id:'budget-route', tenantId:'a', capability:'compute.echo', payload:{v:1}, dataClass:'public', estimatedCostUsd:0.2 });
  const run = await runtime.orchestrator.runOnce();
  assert.equal(run.job.state, 'succeeded'); assert.equal(run.execution.providerId, 'backup');
  const snapshot = state.budget.snapshot(); assert.equal(snapshot.spent.perProviderUsd.backup, 0.2); assert.equal(snapshot.spent.perProviderUsd.fast ?? 0, 0); assert.equal(snapshot.reserved.totalUsd, 0); state.close();
});

test('provider success with settlement failure is non-retryable and deadletters once', async () => {
  const runtime = createFederationRuntime({ providers:[localProvider('only',1)], localHandlers:safeDefaultHandlers });
  runtime.orchestrator.budget = {
    reserve: async () => ({ ok:true, reservation:{ id:'r1' } }),
    commit: async () => { throw new Error('settlement unavailable'); },
    release: async () => {},
    snapshot: async () => ({})
  };
  await runtime.orchestrator.submit({ id:'settlement-fail', tenantId:'a', capability:'compute.echo', payload:{v:1}, dataClass:'public', estimatedCostUsd:0.1 }, { maxAttempts:3 });
  const run = await runtime.orchestrator.runOnce();
  assert.match(run.error, /provider succeeded but settlement failed/); assert.equal(run.job.state, 'deadletter'); assert.equal(run.job.attempts, 1);
});

test('runtime orchestrator uses injected sqlite state end-to-end across reopen', async (t) => {
  const path=await tempDb(t); let state=createSqliteFederationState(path,{budget:{totalUsd:1}}); let runtime=createFederationRuntime({providers:[localProvider()],localHandlers:safeDefaultHandlers,state});
  await runtime.orchestrator.submit({id:'persisted',capability:'compute.echo',payload:{v:1},dataClass:'public',estimatedCostUsd:0.1}); const run=await runtime.orchestrator.runOnce(); assert.equal(run.job.state,'succeeded'); state.close();
  state=createSqliteFederationState(path,{budget:{totalUsd:1}}); runtime=createFederationRuntime({providers:[localProvider()],localHandlers:safeDefaultHandlers,state}); assert.equal(runtime.orchestrator.queue.get('persisted').state,'succeeded'); assert.equal(runtime.orchestrator.ledger.summary().local.tasks,1); assert.equal(runtime.orchestrator.budget.snapshot().spent.totalUsd,0.1); state.close();
});
