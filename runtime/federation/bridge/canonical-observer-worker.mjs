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

export class BoundedCanonicalObserver {
  constructor({
    bridge,
    instanceId='unknown-instance',
    sourceRev='unknown-rev',
    activeJobScanMaxRows=250,
    checkpointScanMaxRows=500,
  }={}){
    if(!bridge||typeof bridge.readRange!=='function'||typeof bridge.appendRows!=='function') throw new Error('bridge with readRange and appendRows required');
    this.bridge=bridge;
    this.instanceId=sanitizedLabel(instanceId,'unknown-instance');
    this.sourceRev=sanitizedLabel(sourceRev,'unknown-rev');
    this.activeJobScanMaxRows=boundedRows(activeJobScanMaxRows,'activeJobScanMaxRows',{fallback:250,max:2000});
    this.checkpointScanMaxRows=boundedRows(checkpointScanMaxRows,'checkpointScanMaxRows',{fallback:500,max:5000});
    this.activeJobsRange=`11_ACTIVE_JOBS!A1:X${this.activeJobScanMaxRows}`;
    this.checkpointScanRange=`53_FLOW_CHECKPOINTS!A1:L${this.checkpointScanMaxRows}`;
  }

  async runOnce(){
    const [bootRead,jobsRead,checkpointRead]=await Promise.all([
      this.bridge.readRange(BOOT_RANGE),
      this.bridge.readRange(this.activeJobsRange),
      this.bridge.readRange(this.checkpointScanRange),
    ]);
    const bootTable=parseTable(bootRead.values,{name:'10_LIGHT_BOOT',requiredHeaders:BOOT_HEADERS});
    if(bootTable.rows.length!==1) throw machineError('BOOT_ROW_CARDINALITY',`10_LIGHT_BOOT must expose exactly one boot row, found ${bootTable.rows.length}`);
    const boot=bootTable.rows[0];
    const primaryJobId=normalizeCell(boot.PRIMARY_JOB_ID);
    if(!primaryJobId) throw machineError('PRIMARY_JOB_MISSING','10_LIGHT_BOOT PRIMARY_JOB_ID is empty');

    const jobs=parseTable(jobsRead.values,{name:'11_ACTIVE_JOBS',requiredHeaders:JOB_HEADERS});
    const matches=jobs.rows.filter((row)=>row.JOB_ID===primaryJobId);
    if(matches.length!==1) throw machineError('PRIMARY_JOB_CARDINALITY',`PRIMARY_JOB_ID must match exactly one bounded active-job row, found ${matches.length}`);
    const job=matches[0];

    const checkpoints=parseTable(checkpointRead.values,{name:'53_FLOW_CHECKPOINTS',requiredHeaders:CHECKPOINT_HEADERS});
    if(checkpointRead.values.length>=this.checkpointScanMaxRows){
      throw machineError('CHECKPOINT_SCAN_SATURATED','bounded checkpoint scan is saturated; operator must compact or raise the explicit limit');
    }

    const fingerprint=sha256({
      schema:'deus-canonical-primary-job-fingerprint/1',
      boot:{
        bootId:boot.BOOT_ID,
        version:boot.VERSION,
        canonRevBundle:boot.CANON_REV_BUNDLE,
        primaryJobId,
        invalidationFingerprint:boot.INVALIDATION_FINGERPRINT,
        lastEventId:boot.LAST_EVENT_ID,
        lastReceipt:boot.LAST_RECEIPT,
        updatedAtUtc:boot.UPDATED_AT_UTC,
        truthBoundary:boot.TRUTH_BOUNDARY,
      },
      job:{
        jobId:job.JOB_ID,
        projectId:job.PROJECT_ID,
        dataClass:job.DATA_CLASS,
        state:job.STATE,
        phase:job.PHASE,
        contextDigest:job.CONTEXT_DIGEST,
        executionMode:job.EXECUTION_MODE,
        leaseOwner:job.LEASE_OWNER,
        leaseUntilUtc:job.LEASE_UNTIL_UTC,
        lastHeartbeatUtc:job.LAST_HEARTBEAT_UTC,
        lastReceipt:job.LAST_RECEIPT,
        updatedAtUtc:job.UPDATED_AT_UTC,
        resultRef:job.RESULT_REF,
      },
    });
    const checkpointRef=`sha256:${fingerprint}`;
    const row=[
      FLOW_ID,
      NODE_ID,
      'OBSERVE',
      `job=${primaryJobId};state=${job.STATE};phase=${job.PHASE}`,
      'OBSERVED_ONLY__NO_TASK_EXECUTION',
      'KEEP',
      checkpointRef,
      'LiveBus:10_LIGHT_BOOT;11_ACTIVE_JOBS',
      'RE_READ_CANONICAL_STATE__DO_NOT_AUTONOMOUSLY_SPEND_OR_CROSS_PRIVILEGE_BOUNDARIES',
      'CONDITIONAL_PASS_ON_EXACT_READBACK',
      'WAIT_FOR_MATERIAL_CANONICAL_DELTA',
      `schema=deus-bounded-canonical-observer/1;instance=${this.instanceId};source=${this.sourceRev};boot_updated=${boot.UPDATED_AT_UTC};job_updated=${job.UPDATED_AT_UTC};raw_job_text_not_copied=true`,
    ];
    const expected=Object.fromEntries(CHECKPOINT_HEADERS.map((header,index)=>[header,normalizeCell(row[index])]));
    const existing=checkpoints.rows.find((candidate)=>candidate.FLOW_ID===FLOW_ID&&candidate.NODE_ID===NODE_ID&&candidate.CHECKPOINT_REF===checkpointRef);
    if(existing){
      for(const header of CHECKPOINT_HEADERS.filter((name)=>name!=='NOTES')){
        if(existing[header]!==expected[header]) throw machineError('CHECKPOINT_CONFLICT',`matching checkpoint fingerprint has conflicting ${header}`);
      }
      return Object.freeze({
        schema:'deus-bounded-canonical-observer-receipt/1',
        state:'UNCHANGED',
        ready:true,
        primaryJobId,
        observedJobState:job.STATE,
        observedJobPhase:job.PHASE,
        checkpointRef,
        checkpointUpdatedRange:null,
        truthBoundary:'OBSERVED_CANONICAL_STATE_AND_READ_BACK_AN_EXISTING_MATCHING_CHECKPOINT__NO_JOB_ACTION_PROVIDER_ACTION_SPEND_OR_PRIVILEGE_WAS_EXECUTED',
      });
    }

    const append=await this.bridge.appendRows({range:CHECKPOINT_APPEND_RANGE,rows:[row]});
    if(append.updatedRows!==1||!append.updatedRange) throw machineError('CHECKPOINT_APPEND_FAILED','checkpoint append did not update exactly one attributable row');
    const readback=await this.bridge.readRange(append.updatedRange);
    if(readback.values.length!==1||!sameRow(readback.values[0],row)) throw machineError('CHECKPOINT_READBACK_FAILED','checkpoint exact readback did not match the appended row');

    return Object.freeze({
      schema:'deus-bounded-canonical-observer-receipt/1',
      state:'CHECKPOINT_APPENDED',
      ready:true,
      primaryJobId,
      observedJobState:job.STATE,
      observedJobPhase:job.PHASE,
      checkpointRef,
      checkpointUpdatedRange:append.updatedRange,
      truthBoundary:'READ_CANONICAL_BOOT_AND_EXACT_PRIMARY_JOB_THEN_APPENDED_AND_READ_BACK_ONE_DEDUPLICATED_CHECKPOINT__NO_JOB_ACTION_PROVIDER_ACTION_SPEND_OR_PRIVILEGE_WAS_EXECUTED',
    });
  }
}

export const canonicalObserverContract=Object.freeze({
  bootRange:BOOT_RANGE,
  checkpointAppendRange:CHECKPOINT_APPEND_RANGE,
  flowId:FLOW_ID,
  nodeId:NODE_ID,
});
