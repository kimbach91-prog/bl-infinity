import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ShadowTargetFence } from '../lib/shadow-target-fence.mjs';

const sha = s => createHash('sha256').update(s).digest('hex');
function fixture(t) {
  const dir=mkdtempSync(join(tmpdir(),'fence-shadow-'));
  t.after(()=>rmSync(dir,{recursive:true,force:true}));
  return join(dir,'fence.db');
}
// Verifier deliberately does not call production module's digest/canonical helpers.
function verifyIndependent(s) {
  let prev='0'.repeat(64);
  for(const event of s.events) {
    if(event.prev_hash!==prev || event.hash!==sha([prev,event.kind,event.body_json].join('\n'))) return false;
    prev=event.hash;
  }
  for(const effect of s.effects) {
    const rec=JSON.parse(effect.receipt_json);
    const {receiptHash,...core}=rec;
    if(rec.effectSeq!==effect.effect_seq || rec.payloadHash!==effect.payload_hash) return false;
    const raw='{'+Object.keys(core).sort().map(k=>JSON.stringify(k)+':'+JSON.stringify(core[k])).join(',')+'}';
    if(sha(raw)!==receiptHash) return false;
  }
  return true;
}
test('independent verifier accepts fresh target-side fenced receipt',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:400,now:100});
  const x=d.apply({resource:'r',owner:'A',epoch:1,requestId:'j1',payload:{y:2,x:1},now:110});
  assert.equal(x.reused,false);
  assert.equal(x.receipt.epoch,1);
  assert.equal(verifyIndependent(d.snapshot()),true);
  d.close();
});
test('stale worker denied after newer epoch; only successor effect persists',t=>{
  const path=fixture(t),a=new ShadowTargetFence(path),b=new ShadowTargetFence(path);
  a.claim({resource:'r',owner:'A',epoch:1,expiresAt:400,now:100});
  b.claim({resource:'r',owner:'B',epoch:2,expiresAt:450,now:130});
  assert.throws(()=>a.apply({resource:'r',owner:'A',epoch:1,requestId:'old',payload:1,now:140}),{code:'STALE_FENCE_AT_TARGET'});
  b.apply({resource:'r',owner:'B',epoch:2,requestId:'new',payload:2,now:140});
  assert.deepEqual(b.snapshot().effects.map(e=>e.request_id),['new']);
  assert.equal(verifyIndependent(b.snapshot()),true);
  a.close();b.close();
});
test('idempotent replay never repeats an effect; altered payload rejected',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:300,now:100});
  const a=d.apply({resource:'r',owner:'A',epoch:1,requestId:'same',payload:{k:1},now:110});
  const b=d.apply({resource:'r',owner:'A',epoch:1,requestId:'same',payload:{k:1},now:120});
  assert.equal(b.reused,true);
  assert.deepEqual(a.receipt,b.receipt);
  assert.throws(()=>d.apply({resource:'r',owner:'A',epoch:1,requestId:'same',payload:{k:2},now:120}),{code:'IDEMPOTENCY_CONFLICT'});
  assert.equal(d.snapshot().effects.length,1);
  d.close();
});
test('wrong owner, stale epoch and expiry are negative controls',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:3,expiresAt:200,now:100});
  assert.throws(()=>d.apply({resource:'r',owner:'X',epoch:3,requestId:'bad1',payload:1,now:150}),{code:'STALE_FENCE_AT_TARGET'});
  assert.throws(()=>d.apply({resource:'r',owner:'A',epoch:2,requestId:'bad2',payload:1,now:150}),{code:'STALE_FENCE_AT_TARGET'});
  assert.throws(()=>d.apply({resource:'r',owner:'A',epoch:3,requestId:'bad3',payload:1,now:200}),{code:'EXPIRED_FENCE_AT_TARGET'});
  assert.equal(d.snapshot().effects.length,0);
  d.close();
});
test('monotonic lease and malformed proposed lease fail closed',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:3,expiresAt:300,now:100});
  for(const epoch of [1,2,3])
    assert.throws(()=>d.claim({resource:'r',owner:'X',epoch,expiresAt:400,now:100}),{code:'STALE_OR_DUPLICATE_EPOCH'});
  assert.throws(()=>d.claim({resource:'r',owner:'X',epoch:4,expiresAt:100,now:100}),{code:'INVALID_OR_EXPIRED_LEASE'});
  assert.equal(d.snapshot().leases[0].epoch,3);
  d.close();
});
test('cold reopen recovers exact receipt and does not double-effect',t=>{
  const path=fixture(t);
  let d=new ShadowTargetFence(path);
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:300,now:100});
  const before=d.apply({resource:'r',owner:'A',epoch:1,requestId:'job',payload:'x',now:110}).receipt;
  d.close();
  d=new ShadowTargetFence(path);
  assert.equal(verifyIndependent(d.snapshot()),true);
  const r=d.apply({resource:'r',owner:'A',epoch:1,requestId:'job',payload:'x',now:120});
  assert.equal(r.reused,true); assert.deepEqual(r.receipt,before);
  assert.equal(d.snapshot().effects.length,1);
  d.close();
});
test('tampering audit event invalidates independently verified chain',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:300,now:100});
  d.db.prepare("UPDATE shadow_events SET body_json='{}' WHERE seq=1").run();
  assert.equal(verifyIndependent(d.snapshot()),false);
  d.close();
});
test('rejected target effect leaves neither partial write nor event',t=>{
  const d=new ShadowTargetFence(fixture(t));
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:300,now:100});
  const events=d.snapshot().events.length;
  assert.throws(()=>d.apply({resource:'r',owner:'X',epoch:1,requestId:'bad',payload:1,now:110}),{code:'STALE_FENCE_AT_TARGET'});
  assert.equal(d.snapshot().events.length,events);
  assert.equal(d.snapshot().effects.length,0);
  d.close();
});
test('invalid identifiers and non-finite/oversized payloads fail closed',t=>{
  const d=new ShadowTargetFence(fixture(t));
  assert.throws(()=>d.claim({resource:'bad id',owner:'A',epoch:1,expiresAt:300,now:100}),{code:'INVALID_ID'});
  d.claim({resource:'r',owner:'A',epoch:1,expiresAt:300,now:100});
  assert.throws(()=>d.apply({resource:'r',owner:'A',epoch:1,requestId:'NaN',payload:{x:Infinity},now:110}),{code:'INVALID_PAYLOAD'});
  assert.throws(()=>d.apply({resource:'r',owner:'A',epoch:1,requestId:'huge',payload:'x'.repeat(70000),now:110}),{code:'PAYLOAD_TOO_LARGE'});
  d.close();
});