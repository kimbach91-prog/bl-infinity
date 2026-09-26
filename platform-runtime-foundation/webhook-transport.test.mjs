import test from 'node:test';
import assert from 'node:assert/strict';
import {createSignedWebhook,verifySignedWebhook,deliverSignedWebhook} from './webhook-transport.mjs';

const secret='synthetic-test-secret-32-bytes-minimum';
const event={event_id:'e1',tenant_id:'t1',type:'job.completed',data:{job_id:'j1'},source_ref:'rcp://j1'};

test('signature verifies with exact raw body',()=>{
  const signed=createSignedWebhook({event,secret,timestamp_seconds:1_800_000_000});
  const v=verifySignedWebhook({
    rawBody:signed.rawBody,headers:signed.headers,secret,
    now_ms:1_800_000_000_000,tolerance_seconds:10
  });
  assert.equal(v.ok,true);
  assert.equal(v.event_id,'e1');
});

test('tampered body fails',()=>{
  const signed=createSignedWebhook({event,secret,timestamp_seconds:1_800_000_000});
  const v=verifySignedWebhook({
    rawBody:signed.rawBody+'x',headers:signed.headers,secret,
    now_ms:1_800_000_000_000,tolerance_seconds:10
  });
  assert.equal(v.ok,false);
  assert.equal(v.reason,'SIGNATURE_MISMATCH');
});

test('old timestamp fails before action',()=>{
  const signed=createSignedWebhook({event,secret,timestamp_seconds:1_700_000_000});
  const v=verifySignedWebhook({
    rawBody:signed.rawBody,headers:signed.headers,secret,
    now_ms:1_800_000_000_000,tolerance_seconds:300
  });
  assert.equal(v.ok,false);
  assert.equal(v.reason,'TIMESTAMP_OUTSIDE_TOLERANCE');
});

test('replay store rejects same delivery twice',()=>{
  const signed=createSignedWebhook({event,secret,timestamp_seconds:1_800_000_000});
  const store=new Set();
  const args={rawBody:signed.rawBody,headers:signed.headers,secret,now_ms:1_800_000_000_000,tolerance_seconds:10,replayStore:store};
  assert.equal(verifySignedWebhook(args).ok,true);
  assert.equal(verifySignedWebhook(args).reason,'REPLAY');
});

test('delivery uses HTTPS POST and result never renders secret',async()=>{
  let seen=null;
  const fakeFetch=async(url,options)=>{
    seen={url,options};
    return {ok:true,status:200,text:async()=>JSON.stringify({ok:true})};
  };
  const r=await deliverSignedWebhook({
    url:'https://example.invalid/hook',event,secret,fetchImpl:fakeFetch,
    timestamp_seconds:1_800_000_000
  });
  assert.equal(seen.options.method,'POST');
  assert.match(seen.options.headers['x-deus-signature'],/^v1=[a-f0-9]{64}$/);
  assert.equal(r.ok,true);
  assert.equal(r.secret_rendered,false);
  assert.equal(JSON.stringify(r).includes(secret),false);
});

test('non-HTTPS URL is rejected',async()=>{
  await assert.rejects(
    ()=>deliverSignedWebhook({url:'http://example.invalid',event,secret,fetchImpl:async()=>{}}),
    /WEBHOOK_URL_MUST_BE_HTTPS/
  );
});
