import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PLATFORM_API_VERSION,
  platformApiContext,
  platformError,
  platformEnvelope,
  developerReplayMeta,
} from '../lib/developer-api.mjs';

function req(headers={}) { return { headers }; }

test('version header is required and unsupported major returns upgrade status',()=>{
  const missing=platformApiContext(req({}));
  assert.equal(missing.ok,false);
  assert.equal(missing.status,400);
  assert.equal(missing.error.body.error.code,'API_VERSION_REQUIRED');

  const old=platformApiContext(req({'x-deus-api-version':'2.0.0'}));
  assert.equal(old.ok,false);
  assert.equal(old.status,426);
  assert.equal(old.error.body.error.code,'API_VERSION_UNSUPPORTED');
});

test('context generates request and trace ids and requires idempotency on writes',()=>{
  const read=platformApiContext(req({'x-deus-api-version':'1.9.0'}));
  assert.equal(read.ok,true);
  assert.equal(read.api_version,PLATFORM_API_VERSION);
  assert.match(read.request_id,/^req-/);
  assert.match(read.trace_id,/^trace-/);

  const write=platformApiContext(req({'x-deus-api-version':'1.0.0'}),{requireIdempotency:true});
  assert.equal(write.ok,false);
  assert.equal(write.error.body.error.code,'IDEMPOTENCY_KEY_REQUIRED');
});

test('explicit request trace and idempotency headers are preserved',()=>{
  const c=platformApiContext(req({
    'x-deus-api-version':'1.0.0',
    'x-request-id':'request-abc',
    'x-trace-id':'trace-abc',
    'idempotency-key':'idem-12345678',
  }),{requireIdempotency:true});
  assert.equal(c.ok,true);
  assert.equal(c.request_id,'request-abc');
  assert.equal(c.trace_id,'trace-abc');
  assert.equal(c.idempotency_key,'idem-12345678');
});

test('replay metadata distinguishes exact replay from conflict',()=>{
  const task={id:'j1',tenantId:'t1',capability:'compute.echo',payload:{x:1},dataClass:'public'};
  const same=developerReplayMeta({deduplicated:true,job:{task}},task);
  assert.equal(same.replay,true);
  assert.equal(same.conflict,false);

  const changed={...task,payload:{x:2}};
  const conflict=developerReplayMeta({deduplicated:true,job:{task}},changed);
  assert.equal(conflict.replay,false);
  assert.equal(conflict.conflict,true);
  assert.notEqual(conflict.request_hash,conflict.existing_hash);
});

test('structured envelope and error carry version/request/trace',()=>{
  const ctx={api_version:'1.0.0',request_id:'r1',trace_id:'t1'};
  const ok=platformEnvelope(ctx,{value:1},{replay:false});
  assert.equal(ok.api_version,'1.0.0');
  assert.equal(ok.request_id,'r1');
  assert.equal(ok.meta.replay,false);
  const bad=platformError(ctx,'X','bad',{status:409});
  assert.equal(bad.status,409);
  assert.equal(bad.body.error.code,'X');
  assert.equal(bad.body.trace_id,'t1');
});
