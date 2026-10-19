
import test from 'node:test';
import assert from 'node:assert/strict';
import { BoundedCanonicalObserver as Candidate } from '../bridge/canonical-observer-worker.mjs';
import { GoogleSheetsCanonicalBridge } from '../bridge/drive-machine-bridge.mjs';

const BH=['BOOT_ID','VERSION','CANON_REV_BUNDLE','PRIMARY_JOB_ID','INVALIDATION_FINGERPRINT','LAST_EVENT_ID','LAST_RECEIPT','UPDATED_AT_UTC','TRUTH_BOUNDARY'];
const BV=['fixture-boot','8.0','fixture-rev','PUBLIC-FIXTURE-JOB','fixture-fingerprint','PUBLIC-EVENT','PUBLIC-RECEIPT','2026-10-14T00:00:00Z','SCOPED_ONLY'];
const JH=['JOB_ID','PROJECT_ID','DATA_CLASS','STATE','PHASE','CONTEXT_DIGEST','EXECUTION_MODE','LEASE_OWNER','LEASE_UNTIL_UTC','LAST_HEARTBEAT_UTC','LAST_RECEIPT','UPDATED_AT_UTC','RESULT_REF'];
const JV=['PUBLIC-FIXTURE-JOB','PUBLIC-FIXTURE','public','READY','OBSERVE','public-digest','ON_DEMAND','','','','PUBLIC-RECEIPT','2026-10-14T00:00:00Z','public-result'];
const CH=['FLOW_ID','NODE_ID','PHASE','UPSTREAM_STATE','EXECUTION_STATE','KEEP_OR_REDO','CHECKPOINT_REF','ARTIFACT_REF','RECOVERY_ACTION','ACCEPTANCE_STATE','NEXT_ACTION','NOTES'];
const clone=(x)=>structuredClone(x);
const blank=()=>Array(12).fill('');
const unrelated=(n)=>['OTHER-FLOW','OTHER-NODE','OBSERVE','public-fixture-'+n,'OBSERVED_ONLY','KEEP','public-ref-'+n,'','','','',''];
class FixtureBridge{
  constructor(rows=[]){
    this.checkpoints=[clone(CH),...clone(rows)];this.boot=[clone(BH),clone(BV)];this.jobs=[clone(JH),clone(JV)];
    this.calls=[];this.appends=[];this.onRead=null;this.mutateReadback=false;this.badAppendRange=false;this.oversizedPage=false;
  }
  async readRange(range,options={}){
    this.calls.push({range,hasSignal:!!options.signal});
    if(this.onRead) this.onRead(range);
    if(range.startsWith('10_LIGHT_BOOT!')) return {values:clone(this.boot)};
    if(range.startsWith('11_ACTIVE_JOBS!')) return {values:clone(this.jobs)};
    const m=range.match(/^(?:53_FLOW_CHECKPOINTS|'53_FLOW_CHECKPOINTS')!A(\d+):L(\d+)$/);
    assert.ok(m,'fixture refused unexpected source range');
    const start=Number(m[1]),end=Number(m[2]);
    let values=clone(this.checkpoints.slice(start-1,end));
    while(values.length&&!(values.at(-1)??[]).some(x=>String(x??'').trim()!=='')) values.pop();
    if(this.mutateReadback&&start===end&&start>1&&this.appends.length) values[0][4]='FORGED_EXECUTION';
    if(this.oversizedPage&&end>start&&start>1) values=Array(end-start+2).fill(unrelated(1));
    return {values};
  }
  async appendRows({range,rows,signal}){
    assert.equal(range,'53_FLOW_CHECKPOINTS!A:L');
    this.appends.push(clone(rows));
    this.checkpoints.push(...clone(rows));
    const r=this.checkpoints.length;
    return {updatedRows:1,updatedRange:this.badAppendRange?'11_ACTIVE_JOBS!A2:L2':`'53_FLOW_CHECKPOINTS'!A${r}:L${r}`};
  }
}
// Frozen public fixture from the unchanged v1 fingerprint and checkpoint contract.
const good=["DEUS-MACHINE-CONTINUITY","PRIMARY-JOB-STATE","OBSERVE","job=PUBLIC-FIXTURE-JOB;state=READY;phase=OBSERVE","OBSERVED_ONLY__NO_TASK_EXECUTION","KEEP","sha256:e2ea09c8373b2924cbd212d63a4d2f2fb89492960be2b8e8d1e5d58c3aa4d51e","LiveBus:10_LIGHT_BOOT;11_ACTIVE_JOBS","RE_READ_CANONICAL_STATE__DO_NOT_AUTONOMOUSLY_SPEND_OR_CROSS_PRIVILEGE_BOUNDARIES","CONDITIONAL_PASS_ON_EXACT_READBACK","WAIT_FOR_MATERIAL_CANONICAL_DELTA","schema=deus-bounded-canonical-observer/1;instance=fixture;source=fixture;boot_updated=2026-10-14T00:00:00Z;job_updated=2026-10-14T00:00:00Z;raw_job_text_not_copied=true"];
const make=(bridge,extra={})=>new Candidate({bridge,instanceId:'fixture',sourceRev:'fixture',checkpointScanMaxRows:9,checkpointPageRows:4,...extra});
const rejectsCode=async(fn,code)=>assert.rejects(fn,e=>e.code===code);

test('regression: saturated positive match must reuse a validated exact row',async()=>{
  const rows=[unrelated(1),good,unrelated(3),unrelated(4),unrelated(5),unrelated(6),unrelated(7),unrelated(8)];
  const b=new FixtureBridge(rows);const r=await make(b).runOnce();
  assert.equal(r.state,'UNCHANGED');assert.equal(r.checkpointRef,good[6]);assert.equal(b.appends.length,0);
  assert.equal(r.checkpointLookup.knownMatchCount,1);assert.ok(r.truthBoundary.includes('NOT_A_GLOBAL_CHECKPOINT_CENSUS'));
});
test('saturated no-match stays closed with no append and exact total request budget',async()=>{
  const b=new FixtureBridge(Array.from({length:20},(_,n)=>unrelated(n)));
  await assert.rejects(()=>make(b).runOnce(),e=>e.code==='CHECKPOINT_SCAN_SATURATED'&&e.diagnostics.maxRows===9&&e.diagnostics.scanRowsRead===9);
  assert.equal(b.appends.length,0);assert.equal(b.calls.filter(x=>x.range.startsWith('53_')).length,3);
});
test('later page positive is reused and directly reread',async()=>{
  const b=new FixtureBridge([unrelated(1),unrelated(2),unrelated(3),unrelated(4),unrelated(5),good,unrelated(7),unrelated(8)]);
  const r=await make(b).runOnce();assert.equal(r.state,'UNCHANGED');assert.equal(r.checkpointObservedRange,'53_FLOW_CHECKPOINTS!A7:L7');assert.equal(r.checkpointLookup.pagesRead,2);assert.equal(b.appends.length,0);
});
test('short intermediate page cannot hide a later in-window checkpoint',async()=>{
  const b=new FixtureBridge([unrelated(1),blank(),blank(),blank(),unrelated(5),good]);
  const r=await make(b).runOnce();assert.equal(r.state,'UNCHANGED');assert.equal(b.appends.length,0);assert.equal(r.checkpointLookup.pagesRead,2);
});
test('matching fingerprint with conflicting execution field is rejected',async()=>{
  const bad=clone(good);bad[4]='EXECUTED';const b=new FixtureBridge([bad]);
  await rejectsCode(()=>make(b).runOnce(),'CHECKPOINT_CONFLICT');assert.equal(b.appends.length,0);
});
test('multiple matches in a page are ambiguous and cannot be promoted',async()=>{
  const b=new FixtureBridge([good,good]);await rejectsCode(()=>make(b).runOnce(),'CHECKPOINT_MATCH_AMBIGUOUS');assert.equal(b.appends.length,0);
});
test('qualified exact-row hint reuses a match outside window without scanning corpus',async()=>{
  const rows=Array.from({length:120},(_,n)=>unrelated(n));rows[119]=good;const b=new FixtureBridge(rows);
  const r=await make(b,{checkpointRowHint:'53_FLOW_CHECKPOINTS!A121:L121'}).runOnce();
  assert.equal(r.state,'UNCHANGED');assert.equal(r.checkpointLookup.mode,'EXACT_ROW_READBACK');assert.equal(r.checkpointLookup.pagesRead,0);assert.equal(b.appends.length,0);
});
test('wrong-sheet, multirow, row1 and oversized hint locators are rejected before reads',()=>{
  for(const hint of ['11_ACTIVE_JOBS!A2:L2','53_FLOW_CHECKPOINTS!A2:L3','53_FLOW_CHECKPOINTS!A1:L1','53_FLOW_CHECKPOINTS!A1000001:L1000001']){
    const b=new FixtureBridge();assert.throws(()=>make(b,{checkpointRowHint:hint}),e=>e.code==='CHECKPOINT_ROW_REF_REJECTED');assert.equal(b.calls.length,0);
  }
});
test('stale hint does not authorize append through saturation',async()=>{
  const b=new FixtureBridge(Array.from({length:20},(_,n)=>unrelated(n)));
  await rejectsCode(()=>make(b,{checkpointRowHint:'53_FLOW_CHECKPOINTS!A20:L20'}).runOnce(),'CHECKPOINT_SCAN_SATURATED');assert.equal(b.appends.length,0);
});
test('a forged memo locator cannot broaden the read scope',async()=>{
  const b=new FixtureBridge([good]);const o=make(b);
  o.verifiedCheckpoint={ref:good[6],range:'11_ACTIVE_JOBS!A2:L2'};
  await rejectsCode(()=>o.runOnce(),'CHECKPOINT_ROW_REF_REJECTED');
  assert.equal(b.calls.filter(x=>x.range==='11_ACTIVE_JOBS!A2:L2').length,0);assert.equal(b.appends.length,0);
});
test('finite empty-tail window appends one metadata row and verifies exact returned locator',async()=>{
  const b=new FixtureBridge([unrelated(1)]);const r=await make(b).runOnce();
  assert.equal(r.state,'CHECKPOINT_APPENDED');assert.equal(b.appends.length,1);assert.deepEqual(b.appends[0][0],good);
  assert.ok(r.checkpointLookup.complete);assert.equal(r.checkpointLookup.scanRowsRead,9);
});
test('memo reuses one exact validated row on unchanged second run',async()=>{
  const b=new FixtureBridge([unrelated(1)]);const o=make(b);await o.runOnce();b.calls=[];
  const r=await o.runOnce();assert.equal(r.state,'UNCHANGED');assert.equal(r.checkpointLookup.pagesRead,0);assert.equal(b.appends.length,1);
});
test('changed job fingerprint invalidates memo and holds on saturated window',async()=>{
  const b=new FixtureBridge([unrelated(1)]);const o=make(b);await o.runOnce();
  while(b.checkpoints.length<20)b.checkpoints.push(unrelated(b.checkpoints.length));b.jobs[1][3]='CHANGED';
  await rejectsCode(()=>o.runOnce(),'CHECKPOINT_SCAN_SATURATED');assert.equal(b.appends.length,1);
});
test('tampered append readback never yields ready receipt',async()=>{
  const b=new FixtureBridge();b.mutateReadback=true;await rejectsCode(()=>make(b).runOnce(),'CHECKPOINT_READBACK_FAILED');assert.equal(b.appends.length,1);
});
test('returned append locator cannot redirect a read to another sheet',async()=>{
  const b=new FixtureBridge();b.badAppendRange=true;await rejectsCode(()=>make(b).runOnce(),'CHECKPOINT_ROW_REF_REJECTED');
  assert.equal(b.calls.filter(x=>x.range==='11_ACTIVE_JOBS!A2:L2').length,0);
});
test('deadline expires before append; no page beyond the declared deadline is requested',async()=>{
  let t=0;const b=new FixtureBridge();b.onRead=(range)=>{if(range==='53_FLOW_CHECKPOINTS!A2:L5')t=2000;};
  await rejectsCode(()=>make(b,{clock:()=>t,timeBudgetMs:1000}).runOnce(),'OBSERVER_DEADLINE_EXCEEDED');assert.equal(b.appends.length,0);
});
test('oversized page fails closed',async()=>{
  const b=new FixtureBridge();b.oversizedPage=true;await rejectsCode(()=>make(b).runOnce(),'CHECKPOINT_PAGE_BOUND_EXCEEDED');assert.equal(b.appends.length,0);
});
test('duplicate canonical job and bad checkpoint headers still reject',async()=>{
  const b=new FixtureBridge();b.jobs.push(clone(JV));await rejectsCode(()=>make(b).runOnce(),'PRIMARY_JOB_CARDINALITY');
  const c=new FixtureBridge();c.checkpoints[0][1]='FLOW_ID';await rejectsCode(()=>make(c).runOnce(),'CANONICAL_HEADER_DUPLICATE');assert.equal(c.appends.length,0);
});
test('row and time configuration remain bounded',()=>{
  for(const n of [1,5001,Infinity,NaN])assert.throws(()=>make(new FixtureBridge(),{checkpointScanMaxRows:n}));
  for(const n of [999,60001,Infinity,NaN])assert.throws(()=>make(new FixtureBridge(),{timeBudgetMs:n}));
});
test('bridge propagates the supplied cancellation signal on reads and metadata append',async()=>{
  const seen=[];const signal=new AbortController().signal;
  const b=new GoogleSheetsCanonicalBridge({spreadsheetId:'PUBLIC_FIXTURE',tokenSource:async()=> 'PUBLIC_FIXTURE_TOKEN',
    fetchImpl:async(url,init)=>{seen.push({url,signal:init.signal,method:init.method??'GET'});return {ok:true,text:async()=>JSON.stringify(init.method==='POST'?{updates:{updatedRows:1,updatedRange:'53_FLOW_CHECKPOINTS!A2:L2'}}:{range:'53_FLOW_CHECKPOINTS!A1:L1',values:[CH]})};}});
  await b.readRange('53_FLOW_CHECKPOINTS!A1:L1',{signal});await b.appendRows({range:'53_FLOW_CHECKPOINTS!A:L',rows:[good],signal});
  assert.ok(seen.every(x=>x.signal===signal));assert.deepEqual(seen.map(x=>x.method),['GET','POST']);
});

