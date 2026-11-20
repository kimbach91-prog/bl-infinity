import { createHash } from 'node:crypto';

const BOOT_RANGE='10_LIGHT_BOOT!A1:O2';
const CHECKPOINT_APPEND_RANGE='53_FLOW_CHECKPOINTS!A:L';
const FLOW_ID='DEUS-MACHINE-CONTINUITY';
const NODE_ID='PRIMARY-JOB-STATE';
const BOOT_HEADERS=[
  'BOOT_ID','VERSION','CANON_REV_BUNDLE','PRIMARY_JOB_ID','INVALIDATION_FINGERPRINT',
  'LAST_EVENT_ID','LAST_RECEIPT','UPDATED_AT_UTC','TRUTH_BOUNDARY',
];
const JOB_HEADERS=[
  'JOB_ID','PROJECT_ID','DATA_CLASS','STATE','PHASE','CONTEXT_DIGEST','EXECUTION_MODE',
  'LEASE_OWNER','LEASE_UNTIL_UTC','LAST_HEARTBEAT_UTC','LAST_RECEIPT','UPDATED_AT_UTC','RESULT_REF',
];
const CHECKPOINT_HEADERS=[
  'FLOW_ID','NODE_ID','PHASE','UPSTREAM_STATE','EXECUTION_STATE','KEEP_OR_REDO','CHECKPOINT_REF','ARTIFACT_REF',
  'RECOVERY_ACTION','ACCEPTANCE_STATE','NEXT_ACTION','NOTES',
];

function machineError(code,message){
  const error=new Error(message);
  error.code=code;
  return error;
}

function boundedRows(value,name,{fallback,max}){
  const rows=value==null?fallback:Number(value);
  if(!Number.isSafeInteger(rows)||rows<2||rows>max) throw new Error(`${name} must be an integer between 2 and ${max}`);
  return rows;
}

function normalizeCell(value){return value==null?'':String(value).trim();}

function parseTable(values,{name,requiredHeaders}){
  if(!Array.isArray(values)||values.length<1) throw machineError('CANONICAL_TABLE_EMPTY',`${name} returned no header row`);
  const headers=values[0].map(normalizeCell);
  const positions=new Map();
  headers.forEach((header,index)=>{
    if(!header) return;
    if(positions.has(header)) throw machineError('CANONICAL_HEADER_DUPLICATE',`${name} contains duplicate header ${header}`);
    positions.set(header,index);
  });
  for(const header of requiredHeaders){
    if(!positions.has(header)) throw machineError('CANONICAL_HEADER_MISSING',`${name} missing required header ${header}`);
  }
  const rows=values.slice(1)
    .filter((row)=>Array.isArray(row)&&row.some((cell)=>normalizeCell(cell)!==''))
    .map((row)=>Object.fromEntries(headers.filter(Boolean).map((header)=>[header,normalizeCell(row[positions.get(header)])])));
  return {headers,positions,rows};
}

function sha256(value){
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function sanitizedLabel(value,fallback){
  const label=normalizeCell(value).replace(/[^A-Za-z0-9._:-]/g,'_').slice(0,128);
  return label||fallback;
}

function sameRow(actual,expected){
  return expected.every((cell,index)=>normalizeCell(actual?.[index])===normalizeCell(cell));
}


function exactCheckpointRange(value){
  if(value==null) return null;
  const match=String(value).match(/^(?:53_FLOW_CHECKPOINTS|'53_FLOW_CHECKPOINTS')!A([1-9]\d{0,6}):L\1$/);
  if(!match||Number(match[1])<2||Number(match[1])>1_000_000) {
    throw machineError('CHECKPOINT_ROW_REF_REJECTED','checkpoint row reference must be one fixed A:L row in the checkpoint sheet');
  }
  return `53_FLOW_CHECKPOINTS!A${match[1]}:L${match[1]}`;
}
function asCheckpointRow(raw,table){
  return Object.fromEntries(table.headers.filter(Boolean).map((header)=>[header,normalizeCell(raw?.[table.positions.get(header)])]));
}
function checkpointMatches(candidate,ref){
  return candidate.FLOW_ID===FLOW_ID&&candidate.NODE_ID===NODE_ID&&candidate.CHECKPOINT_REF===ref;
}
function verifyCheckpoint(candidate,expected){
  for(const header of CHECKPOINT_HEADERS.filter((name)=>name!=='NOTES')){
    if(candidate[header]!==expected[header]) throw machineError('CHECKPOINT_CONFLICT',`matching checkpoint fingerprint has conflicting ${header}`);
  }
}
function boundedMillis(value){
  const n=Number(value);
  if(!Number.isSafeInteger(n)||n<1000||n>60_000) throw machineError('OBSERVER_TIME_BUDGET_REJECTED','observer time budget must be between 1000 and 60000 milliseconds');
  return n;
}

export class BoundedCanonicalObserver {
  constructor({
    bridge,instanceId='unknown-instance',sourceRev='unknown-rev',
    activeJobScanMaxRows=250,checkpointScanMaxRows=500,
    checkpointPageRows=128,checkpointRowHint=null,timeBudgetMs=10_000,
    clock=()=>performance.now(),
  }={}){
    if(!bridge||typeof bridge.readRange!=='function'||typeof bridge.appendRows!=='function') throw new Error('bridge with readRange and appendRows required');
    if(typeof clock!=='function') throw new Error('clock must be a function');
    this.bridge=bridge;
    this.instanceId=sanitizedLabel(instanceId,'unknown-instance');
    this.sourceRev=sanitizedLabel(sourceRev,'unknown-rev');
    this.activeJobScanMaxRows=boundedRows(activeJobScanMaxRows,'activeJobScanMaxRows',{fallback:250,max:2000});
    this.checkpointScanMaxRows=boundedRows(checkpointScanMaxRows,'checkpointScanMaxRows',{fallback:500,max:5000});
    this.checkpointPageRows=Math.min(boundedRows(checkpointPageRows,'checkpointPageRows',{fallback:128,max:512}),this.checkpointScanMaxRows-1);
    this.checkpointRowHint=exactCheckpointRange(checkpointRowHint);
    this.timeBudgetMs=boundedMillis(timeBudgetMs);
    this.clock=clock;
    this.activeJobsRange=`11_ACTIVE_JOBS!A1:X${this.activeJobScanMaxRows}`;
    this.verifiedCheckpoint=null;
  }

  async runOnce(){
    const started=this.clock();
    const signal=AbortSignal.timeout(this.timeBudgetMs);
    const scan={schema:'deus-observer-checkpoint-lookup/1',maxRows:this.checkpointScanMaxRows,pageRows:this.checkpointPageRows,
      scanRowsRead:0,scanRowsReturned:0,pagesRead:0,exactRowReads:0,knownMatchCount:0,complete:false,saturated:false,mode:'BOUNDED_PAGES'};
    const deadline=()=>{
      if(signal.aborted||this.clock()-started>=this.timeBudgetMs) throw machineError('OBSERVER_DEADLINE_EXCEEDED','bounded observer deadline expired');
    };
    const read=async(range)=>{
      deadline();
      const result=await this.bridge.readRange(range,{signal});
      deadline();
      return result;
    };
    try{
      const [bootRead,jobsRead]=await Promise.all([read(BOOT_RANGE),read(this.activeJobsRange)]);
      const bootTable=parseTable(bootRead.values,{name:'10_LIGHT_BOOT',requiredHeaders:BOOT_HEADERS});
      if(bootTable.rows.length!==1) throw machineError('BOOT_ROW_CARDINALITY',`10_LIGHT_BOOT must expose exactly one boot row, found ${bootTable.rows.length}`);
      const boot=bootTable.rows[0];
      const primaryJobId=normalizeCell(boot.PRIMARY_JOB_ID);
      if(!primaryJobId) throw machineError('PRIMARY_JOB_MISSING','10_LIGHT_BOOT PRIMARY_JOB_ID is empty');
      const jobs=parseTable(jobsRead.values,{name:'11_ACTIVE_JOBS',requiredHeaders:JOB_HEADERS});
      const matches=jobs.rows.filter((row)=>row.JOB_ID===primaryJobId);
      if(matches.length!==1) throw machineError('PRIMARY_JOB_CARDINALITY',`PRIMARY_JOB_ID must match exactly one bounded active-job row, found ${matches.length}`);
      const job=matches[0];
      const fingerprint=sha256({
        schema:'deus-canonical-primary-job-fingerprint/1',
        boot:{bootId:boot.BOOT_ID,version:boot.VERSION,canonRevBundle:boot.CANON_REV_BUNDLE,primaryJobId,
          invalidationFingerprint:boot.INVALIDATION_FINGERPRINT,lastEventId:boot.LAST_EVENT_ID,
          lastReceipt:boot.LAST_RECEIPT,truthBoundary:boot.TRUTH_BOUNDARY},
        job:{jobId:job.JOB_ID,projectId:job.PROJECT_ID,dataClass:job.DATA_CLASS,state:job.STATE,phase:job.PHASE,
          contextDigest:job.CONTEXT_DIGEST,executionMode:job.EXECUTION_MODE,lastReceipt:job.LAST_RECEIPT,resultRef:job.RESULT_REF},
      });
      const checkpointRef=`sha256:${fingerprint}`;
      const row=[FLOW_ID,NODE_ID,'OBSERVE',`job=${primaryJobId};state=${job.STATE};phase=${job.PHASE}`,
        'OBSERVED_ONLY__NO_TASK_EXECUTION','KEEP',checkpointRef,'LiveBus:10_LIGHT_BOOT;11_ACTIVE_JOBS',
        'RE_READ_CANONICAL_STATE__DO_NOT_AUTONOMOUSLY_SPEND_OR_CROSS_PRIVILEGE_BOUNDARIES',
        'CONDITIONAL_PASS_ON_EXACT_READBACK','WAIT_FOR_MATERIAL_CANONICAL_DELTA',
        `schema=deus-bounded-canonical-observer/1;instance=${this.instanceId};source=${this.sourceRev};boot_updated=${boot.UPDATED_AT_UTC};job_updated=${job.UPDATED_AT_UTC};raw_job_text_not_copied=true`];
      const expected=Object.fromEntries(CHECKPOINT_HEADERS.map((header,index)=>[header,normalizeCell(row[index])]));
      const headerRead=await read('53_FLOW_CHECKPOINTS!A1:L1');
      if(!Array.isArray(headerRead.values)||headerRead.values.length!==1) throw machineError('CHECKPOINT_HEADER_CARDINALITY','checkpoint header read must return exactly one row');
      scan.scanRowsRead=1;
      scan.scanRowsReturned=1;
      const table=parseTable(headerRead.values,{name:'53_FLOW_CHECKPOINTS',requiredHeaders:CHECKPOINT_HEADERS});
      const unchanged=(range,mode)=>{
        this.verifiedCheckpoint={ref:checkpointRef,range};
        scan.mode=mode;
        return Object.freeze({schema:'deus-bounded-canonical-observer-receipt/1',state:'UNCHANGED',ready:true,
          primaryJobId,observedJobState:job.STATE,observedJobPhase:job.PHASE,checkpointRef,checkpointUpdatedRange:null,
          checkpointObservedRange:range,checkpointLookup:Object.freeze({...scan}),
          truthBoundary:'EXACT_CHECKPOINT_ROW_REUSE_ONLY__NOT_A_GLOBAL_CHECKPOINT_CENSUS__NO_JOB_ACTION_PROVIDER_ACTION_SPEND_OR_PRIVILEGE_WAS_EXECUTED'});
      };
      const exact=async(range)=>{
        scan.exactRowReads+=1;
        const result=await read(range);
        if(!Array.isArray(result.values)||result.values.length>1) throw machineError('CHECKPOINT_EXACT_READ_CARDINALITY','exact checkpoint read returned too many rows');
        if(result.values.length!==1) return false;
        const candidate=asCheckpointRow(result.values[0],table);
        if(!checkpointMatches(candidate,checkpointRef)) return false;
        scan.knownMatchCount+=1;
        verifyCheckpoint(candidate,expected);
        return true;
      };
      const hints=[this.verifiedCheckpoint?.ref===checkpointRef?this.verifiedCheckpoint.range:null,this.checkpointRowHint].filter(Boolean).map(exactCheckpointRange);
      for(const hint of [...new Set(hints)]){
        if(await exact(hint)) return unchanged(hint,'EXACT_ROW_READBACK');
      }
      this.verifiedCheckpoint=null;
      // The existing total cap includes the header. Pagination changes transport,
      // never the allowed rows. A positive exact match can be reused without
      // claiming global completeness. A saturated no-match window cannot append.
      let start=2;
      while(scan.scanRowsRead<this.checkpointScanMaxRows){
        const remaining=this.checkpointScanMaxRows-scan.scanRowsRead;
        const requested=Math.min(this.checkpointPageRows,remaining);
        const end=start+requested-1;
        const result=await read(`53_FLOW_CHECKPOINTS!A${start}:L${end}`);
        if(!Array.isArray(result.values)||result.values.length>requested) throw machineError('CHECKPOINT_PAGE_BOUND_EXCEEDED','checkpoint page exceeded its declared row bound');
        scan.pagesRead+=1;
        scan.scanRowsRead+=requested;
        scan.scanRowsReturned+=result.values.length;
        const found=[];
        for(let offset=0;offset<result.values.length;offset+=1){
          const candidate=asCheckpointRow(result.values[offset],table);
          if(checkpointMatches(candidate,checkpointRef)) found.push({candidate,range:`53_FLOW_CHECKPOINTS!A${start+offset}:L${start+offset}`});
        }
        scan.knownMatchCount+=found.length;
        if(found.length>1) throw machineError('CHECKPOINT_MATCH_AMBIGUOUS','multiple matching checkpoint rows were found in the same bounded page');
        if(found.length===1){
          verifyCheckpoint(found[0].candidate,expected);
          if(!await exact(found[0].range)) throw machineError('CHECKPOINT_MATCH_CHANGED','matching checkpoint changed before exact readback');
          // knownMatchCount counts distinct discovered rows, not readbacks.
          scan.knownMatchCount-=1;
          return unchanged(found[0].range,'PAGED_EXACT_ROW_READBACK');
        }
        // Never treat a short intermediate page as EOF: later rows can
        // still exist within the same admitted window.
        scan.complete=result.values.length<requested;
        start=end+1;
      }
      if(!scan.complete){
        scan.saturated=true;
        throw machineError('CHECKPOINT_SCAN_SATURATED','bounded checkpoint scan is saturated; exact qualified row hint or admitted index is required');
      }
      deadline();
      const append=await this.bridge.appendRows({range:CHECKPOINT_APPEND_RANGE,rows:[row],signal});
      if(append.updatedRows!==1||!append.updatedRange) throw machineError('CHECKPOINT_APPEND_FAILED','checkpoint append did not update exactly one attributable row');
      const range=exactCheckpointRange(append.updatedRange);
      scan.exactRowReads+=1;
      const readback=await read(range);
      if(!Array.isArray(readback.values)||readback.values.length!==1||!sameRow(readback.values[0],row)) throw machineError('CHECKPOINT_READBACK_FAILED','checkpoint exact readback did not match the appended row');
      this.verifiedCheckpoint={ref:checkpointRef,range};
      return Object.freeze({schema:'deus-bounded-canonical-observer-receipt/1',state:'CHECKPOINT_APPENDED',ready:true,
        primaryJobId,observedJobState:job.STATE,observedJobPhase:job.PHASE,checkpointRef,checkpointUpdatedRange:range,
        checkpointLookup:Object.freeze({...scan}),
        truthBoundary:'BOUNDED_SCAN_THEN_ONE_METADATA_CHECKPOINT_APPEND_AND_EXACT_READBACK__NO_JOB_ACTION_PROVIDER_ACTION_SPEND_OR_PRIVILEGE_WAS_EXECUTED'});
    }catch(error){
      if(signal.aborted&&(error?.name==='AbortError'||error?.name==='TimeoutError')) error=machineError('OBSERVER_DEADLINE_EXCEEDED','bounded observer deadline expired');
      error.diagnostics=Object.freeze({...scan});
      throw error;
    }
  }
}

export const canonicalObserverContract=Object.freeze({
  bootRange:BOOT_RANGE,checkpointAppendRange:CHECKPOINT_APPEND_RANGE,flowId:FLOW_ID,nodeId:NODE_ID,
  checkpointTotalMaxRows:5000,checkpointExactRowMax:1_000_000,checkpointPageMaxRows:512,
  checkpointReuseScope:'EXACT_VALIDATED_ROW_NOT_GLOBAL_CENSUS',
  timeBudgetMaxMs:60_000,authorityExpanded:false,
});

