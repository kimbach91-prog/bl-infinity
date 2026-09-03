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

async function tempDb(t) { const dir = await mkdtemp(join(tmpdir(), 'blcf-sqlite-')); t.after(() => rm(dir, { recursive: true, force: true })); return join(dir, 'state.db'); }
function localProvider() { return { manifestVersion:'bl-cf-provider/v1', id:'local', kind:'local', capabilities:['compute.echo'], authorization:{consentRef:'owner:self',grantor:'owner',grantedAt:'2026-01-01T00:00:00.000Z',expiresAt:'2099-01-01T00:00:00.000Z',allowedDataClasses:['public'],maxTaskCostUsd:1}, limits:{maxConcurrency:2,maxCostPerTaskUsd:1,maxExecutionMs:5000}, telemetry:{trust:1,availability:1,p95LatencyMs:1,costPerUnitUsd:0,inFlight:0}, dataPolicy:{privateDataAllowed:false,internalDataAllowed:false,retention:'none'},dataLocations:['local'],regions:['local'] }; }

test('sqlite queue survives restart and preserves idempotency', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path);
  state.queue.enqueue({ id:'j1', tenantId:'a', capability:'compute.echo', payload:{x:1}, dataClass:'public' }); state.close();
  state = createSqliteFederationState(path); assert.equal(state.queue.get('j1').state, 'pending');
  const dup = state.queue.enqueue({ id:'j2', tenantId:'a', capability:'compute.echo', payload:{x:1}, dataClass:'public' }); assert.equal(dup.deduplicated, true); assert.equal(dup.job.id, 'j1'); state.close();
});

test('sqlite lease expiration recovers across reopen', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path, { queue:{ defaultLeaseMs:10, maxAttempts:2 } });
  state.queue.enqueue({ id:'j', capability:'compute.echo', dataClass:'public' }, { now:100 }); const claimed = state.queue.claim('w',['compute.echo'],{now:100,leaseMs:10}); assert.equal(claimed.state,'running'); state.close();
  state = createSqliteFederationState(path, { queue:{ defaultLeaseMs:10, maxAttempts:2 } }); assert.deepEqual(state.queue.sweepExpired(111), ['j']); assert.equal(state.queue.get('j').state,'pending'); state.close();
});

test('sqlite cache budget ledger and audit survive restart', async (t) => {
  const path = await tempDb(t); let state = createSqliteFederationState(path, { budget:{ totalUsd:1 } });
  const task={id:'c1',tenantId:'a',capability:'compute.echo',payload:{x:1},dataClass:'public',cachePolicy:'public'};
  state.cache.set(task,{ok:true},{now:100,ttlMs:1000}); const r=state.budget.reserve({amountUsd:0.2,tenantId:'a',taskId:'c1'}); state.budget.commit(r.reservation.id,0.2);
  state.ledger.record({taskId:'c1',providerId:'p1',consentRef:'grant:1',tenantId:'a',measuredLatencyMs:4,billedCostUsd:0.2,inputBytes:2,outputBytes:3,status:'succeeded'}); await state.audit.append('test.event',{x:1}); state.close();
  state=createSqliteFederationState(path,{budget:{totalUsd:1}}); assert.equal(state.cache.get(task,200).value.ok,true); assert.equal(state.budget.snapshot().spent.totalUsd,0.2); assert.equal(state.ledger.summary().p1.tasks,1); assert.equal(verifyContributionLedger(state.ledger.list()).ok,true); assert.equal(verifyAuditChain(state.audit.list()).ok,true); state.close();
});

test('runtime orchestrator uses injected sqlite state end-to-end across reopen', async (t) => {
  const path=await tempDb(t); let state=createSqliteFederationState(path,{budget:{totalUsd:1}}); let runtime=createFederationRuntime({providers:[localProvider()],localHandlers:safeDefaultHandlers,state});
  await runtime.orchestrator.submit({id:'persisted',capability:'compute.echo',payload:{v:1},dataClass:'public',estimatedCostUsd:0.1}); const run=await runtime.orchestrator.runOnce(); assert.equal(run.job.state,'succeeded'); state.close();
  state=createSqliteFederationState(path,{budget:{totalUsd:1}}); runtime=createFederationRuntime({providers:[localProvider()],localHandlers:safeDefaultHandlers,state}); assert.equal(runtime.orchestrator.queue.get('persisted').state,'succeeded'); assert.equal(runtime.orchestrator.ledger.summary().local.tasks,1); assert.equal(runtime.orchestrator.budget.snapshot().spent.totalUsd,0.1); state.close();
});
