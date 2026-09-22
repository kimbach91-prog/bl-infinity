import test from 'node:test';
import assert from 'node:assert/strict';
import { BoundedCanonicalObserver, canonicalObserverContract } from '../bridge/canonical-observer-worker.mjs';

const BOOT_HEADERS=[
  'BOOT_ID','VERSION','MODE','CANON_REV_BUNDLE','ACTIVE_JOB_COUNT','RUNNABLE_JOB_COUNT','PRIMARY_JOB_ID','NEXT_ACTION',
  'COMPUTE_ROUTER_STATE','WARM_ROUTE_POINTERS','INVALIDATION_FINGERPRINT','LAST_EVENT_ID','LAST_RECEIPT','UPDATED_AT_UTC','TRUTH_BOUNDARY',
];
const JOB_HEADERS=[
  'JOB_ID','CONTINUITY_ID','PARENT_JOB_ID','PROJECT_ID','OBJECTIVE','DATA_CLASS','PRIORITY','STATE','PHASE','NEXT_ACTION',
  'DEFINITION_OF_DONE','CANON_POINTERS','SOURCE_REV_BUNDLE','CONTEXT_DIGEST','EXECUTION_MODE','LEASE_OWNER','LEASE_UNTIL_UTC',
  'LAST_HEARTBEAT_UTC','LAST_RECEIPT','FALLBACK_ROUTES','STOP_REASON','UPDATED_AT_UTC','RESULT_REF','NOTES',
];
const CHECKPOINT_HEADERS=[
  'FLOW_ID','NODE_ID','PHASE','UPSTREAM_STATE','EXECUTION_STATE','KEEP_OR_REDO','CHECKPOINT_REF','ARTIFACT_REF',
  'RECOVERY_ACTION','ACCEPTANCE_STATE','NEXT_ACTION','NOTES',
];

function row(headers,values){return headers.map((header)=>values[header]??'');}

function fixture({duplicateJob=false,checkpointRows=[]}={}){
  const bootHeaders=[...BOOT_HEADERS];
  const jobHeaders=[...JOB_HEADERS];
  const checkpointHeaders=[...CHECKPOINT_HEADERS];
  const primaryJobId='JOB-PRIMARY-001';
  const boot=row(bootHeaders,{
    BOOT_ID:'BOOT-V4',VERSION:'4.0',CANON_REV_BUNDLE:'REVSET-1',PRIMARY_JOB_ID:primaryJobId,
    NEXT_ACTION:'sensitive next action that must not escape',INVALIDATION_FINGERPRINT:'LB4|STATE1',LAST_EVENT_ID:'EV-1',
    LAST_RECEIPT:'RCP-1',UPDATED_AT_UTC:'2026-09-22T00:00:00Z',TRUTH_BOUNDARY:'verified boundary',
  });
  const job=row(jobHeaders,{
    JOB_ID:primaryJobId,PROJECT_ID:'PROJECT-1',OBJECTIVE:'TOP SECRET OBJECTIVE',DATA_CLASS:'BL-S1_CONTROL',STATE:'IN_PROGRESS',
    PHASE:'BOUNDED',NEXT_ACTION:'TOP SECRET NEXT ACTION',CONTEXT_DIGEST:'CTX-1',EXECUTION_MODE:'MACHINE_OBSERVER',
    LAST_HEARTBEAT_UTC:'2026-09-22T00:00:00Z',LAST_RECEIPT:'RCP-1',UPDATED_AT_UTC:'2026-09-22T00:00:00Z',RESULT_REF:'RESULT-1',
  });
  const jobs=duplicateJob?[job,[...job]]:[job];
  return {
    primaryJobId,
    tables:new Map([
      ['10_LIGHT_BOOT!A1:O2',[bootHeaders,boot]],
      ['11_ACTIVE_JOBS!A1:X250',[jobHeaders,...jobs]],
      ['53_FLOW_CHECKPOINTS!A1:L500',[checkpointHeaders,...checkpointRows]],
    ]),
  };
}

class FakeBridge{
  constructor(tables){this.tables=tables;this.appended=[];this.readbacks=new Map();}
  async readRange(range){
    const values=this.readbacks.get(range)||this.tables.get(range);
    if(!values) throw new Error(`unexpected range ${range}`);
    return {range,values:structuredClone(values)};
  }
  async appendRows({range,rows}){
    assert.equal(range,canonicalObserverContract.checkpointAppendRange);
    this.appended.push(...structuredClone(rows));
    const table=this.tables.get('53_FLOW_CHECKPOINTS!A1:L500');
    table.push(...structuredClone(rows));
    const updatedRange=`'53_FLOW_CHECKPOINTS'!A${table.length}:L${table.length}`;
    this.readbacks.set(updatedRange,structuredClone(rows));
    return {updatedRows:rows.length,updatedColumns:12,updatedRange};
  }
}

test('observer appends one exact checkpoint, reads it back, and deduplicates the same state',async()=>{
  const data=fixture();
  const bridge=new FakeBridge(data.tables);
  const observer=new BoundedCanonicalObserver({bridge,instanceId:'service-1',sourceRev:'abc123'});

  const first=await observer.runOnce();
  assert.equal(first.state,'CHECKPOINT_APPENDED');
  assert.equal(first.primaryJobId,data.primaryJobId);
  assert.equal(bridge.appended.length,1);
  assert.equal(bridge.appended[0].length,12);
  assert.match(bridge.appended[0][6],/^sha256:[a-f0-9]{64}$/);
  assert.doesNotMatch(JSON.stringify(bridge.appended[0]),/TOP SECRET|sensitive next action/i);

  const second=await observer.runOnce();
  assert.equal(second.state,'UNCHANGED');
  assert.equal(second.checkpointRef,first.checkpointRef);
  assert.equal(bridge.appended.length,1);
});

test('observer fails closed when the primary job is ambiguous',async()=>{
  const data=fixture({duplicateJob:true});
  const observer=new BoundedCanonicalObserver({bridge:new FakeBridge(data.tables)});
  await assert.rejects(()=>observer.runOnce(),(error)=>error.code==='PRIMARY_JOB_CARDINALITY');
});

test('observer fails closed when a required canonical header disappears',async()=>{
  const data=fixture();
  data.tables.get('10_LIGHT_BOOT!A1:O2')[0][6]='RENAMED_PRIMARY_JOB_ID';
  const observer=new BoundedCanonicalObserver({bridge:new FakeBridge(data.tables)});
  await assert.rejects(()=>observer.runOnce(),(error)=>error.code==='CANONICAL_HEADER_MISSING');
});

test('observer rejects a conflicting row that reuses the same fingerprint',async()=>{
  const data=fixture();
  const bridge=new FakeBridge(data.tables);
  const observer=new BoundedCanonicalObserver({bridge});
  await observer.runOnce();
  data.tables.get('53_FLOW_CHECKPOINTS!A1:L500').at(-1)[4]='EXECUTED_WITHOUT_AUTHORITY';
  await assert.rejects(()=>observer.runOnce(),(error)=>error.code==='CHECKPOINT_CONFLICT');
});

test('observer stops before append when its bounded checkpoint scan is saturated',async()=>{
  const filler=Array.from({length:4},(_,index)=>row(CHECKPOINT_HEADERS,{FLOW_ID:`FLOW-${index}`,NODE_ID:'NODE',CHECKPOINT_REF:`RCP-${index}`}));
  const data=fixture({checkpointRows:filler});
  data.tables.set('53_FLOW_CHECKPOINTS!A1:L5',[CHECKPOINT_HEADERS,...filler]);
  const bridge=new FakeBridge(data.tables);
  const observer=new BoundedCanonicalObserver({bridge,checkpointScanMaxRows:5});
  await assert.rejects(()=>observer.runOnce(),(error)=>error.code==='CHECKPOINT_SCAN_SATURATED');
  assert.equal(bridge.appended.length,0);
});
