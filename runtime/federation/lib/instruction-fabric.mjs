/** Opt-in instruction adapter for the existing Federation runtime and DAG broker.
 * Trust boundary: bindings/operators are installed by the authorized host, NEVER
 * from Atlas records or worker output. SQLite fencing covers one shared local DB;
 * it is not global consensus. Worker threads isolate lifecycle, not hostile code.
 */
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { Worker } from 'node:worker_threads';
import { fileURLToPath } from 'node:url';
import { freemem } from 'node:os';
import { canonicalize, sha256, sha256Json } from './canonical.mjs';
import { evaluateComputeOffer } from './compute-accord-gate.mjs';
import { registerParticipationIdentity, promoteRegistrationWithAccord, buildParticipationLease } from './universal-participation-registry.mjs';
import { TaskGraphBroker, normalizeTaskGraph } from './task-graph-broker.mjs';
import { compileLogicalResourcePlan } from './logical-resource-compiler.mjs';

export const INSTRUCTION_FABRIC_VERSION = 'deus-instruction-fabric/1.0';
export const ATOM_VERBS = Object.freeze(['PROBE','LEASE','RUN','CHECKPOINT','RESULT','CANCEL','RELEASE']);
const HEX = /^[a-f0-9]{64}$/;
function need(x, code) { if (!x) { const e=new Error(code); e.code=code; throw e; } }
function jsonValue(x, maxBytes=8*1024*1024) {
  function visit(v){need(v===null||['string','number','boolean','object'].includes(typeof v),'NON_JSON_OR_NONFINITE_VALUE');if(typeof v==='number')need(Number.isFinite(v),'NON_JSON_OR_NONFINITE_VALUE');if(v&&typeof v==='object'){need(Array.isArray(v)||Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null,'NON_JSON_OBJECT');for(const a of Object.values(v))visit(a);}}
  visit(x);const raw=JSON.stringify(x); need(typeof raw==='string' && Buffer.byteLength(raw)<=maxBytes,'PACKET_SIZE_OR_TYPE');
  const v=JSON.parse(raw); need(canonicalize(x)===canonicalize(v),'NON_JSON_OR_NONFINITE_VALUE'); return v;
}
function int(x, lo, hi, name) { need(Number.isSafeInteger(x)&&x>=lo&&x<=hi,name); return x; }
function checkedHash(x) { need(HEX.test(x),'HASH_REQUIRED'); return x; }
function fail(code) { const e=new Error(code); e.code=code; return e; }

/** Persisted resource reservations are distinct from the existing task queue lease.
 * Expiry alone NEVER releases a possibly running resource. stop_observed is only
 * written by the host after the driver lifecycle resolves or before it starts.
 */
export class AtomStore {
  constructor(path) {
    this.db=new DatabaseSync(path);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS atom_pools(id TEXT PRIMARY KEY, slots INTEGER NOT NULL, next_fence INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS atom_leases(id TEXT PRIMARY KEY, pool TEXT NOT NULL, route TEXT NOT NULL,
        fence INTEGER NOT NULL, job_key TEXT NOT NULL, binding_hash TEXT NOT NULL, packet_json TEXT NOT NULL,
        state TEXT NOT NULL, expires INTEGER NOT NULL, released INTEGER NOT NULL DEFAULT 0,
        stop_observed INTEGER NOT NULL DEFAULT 0, checkpoint_json TEXT, receipt_json TEXT);
      CREATE UNIQUE INDEX IF NOT EXISTS atom_active_key ON atom_leases(job_key) WHERE released=0;
      CREATE TABLE IF NOT EXISTS atom_cache(cache_key TEXT PRIMARY KEY, output_json TEXT NOT NULL,
        output_hash TEXT NOT NULL, receipt_json TEXT NOT NULL, expires INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS atom_task_receipts(task_id TEXT PRIMARY KEY, task_hash TEXT NOT NULL,
        output_hash TEXT NOT NULL, receipt_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS atom_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_json TEXT NOT NULL,
        prev_hash TEXT NOT NULL, hash TEXT NOT NULL);`);
  }
  tx(fn) { this.db.exec('BEGIN IMMEDIATE'); try { const r=fn(); this.db.exec('COMMIT'); return r; } catch(e) { this.db.exec('ROLLBACK'); throw e; } }
  pool(id, slots) {
    int(slots,1,64,'POOL_SLOTS');
    const old=this.db.prepare('SELECT * FROM atom_pools WHERE id=?').get(id);
    need(!old||old.slots===slots,'POOL_ALIAS_CAPACITY_CONFLICT');
    this.db.prepare('INSERT OR IGNORE INTO atom_pools(id,slots) VALUES(?,?)').run(id,slots);
  }
  event(type, data) {
    const previous=this.db.prepare('SELECT hash FROM atom_events ORDER BY seq DESC LIMIT 1').get()?.hash??'0'.repeat(64);
    const e={type,at:new Date().toISOString(),data:jsonValue(data)}; const hash=sha256Json({previous,event:e});
    this.db.prepare('INSERT INTO atom_events(event_json,prev_hash,hash) VALUES(?,?,?)').run(JSON.stringify(e),previous,hash);
    return hash;
  }
  reserve({pool,route,key,bindingHash,packet,expires,now=Date.now()}) {
    need(expires>now,'LEASE_EXPIRED');
    return this.tx(()=>{
      const p=this.db.prepare('SELECT * FROM atom_pools WHERE id=?').get(pool); need(p,'POOL_UNKNOWN');
      const active=this.db.prepare('SELECT COUNT(*) n FROM atom_leases WHERE pool=? AND released=0').get(pool).n;
      need(active<p.slots,'POOL_BUSY_OR_UNCONFIRMED_STOP');
      need(!this.db.prepare('SELECT id FROM atom_leases WHERE job_key=? AND released=0').get(key),'DUPLICATE_ACTIVE_WORK');
      const id=randomUUID(), fence=p.next_fence+1; need(Number.isSafeInteger(fence),'FENCE_EXHAUSTED');
      this.db.prepare('UPDATE atom_pools SET next_fence=? WHERE id=?').run(fence,pool);
      this.db.prepare('INSERT INTO atom_leases(id,pool,route,fence,job_key,binding_hash,packet_json,state,expires) VALUES(?,?,?,?,?,?,?,?,?)')
        .run(id,pool,route,fence,key,bindingHash,JSON.stringify(packet),'LEASED',expires);
      this.event('LEASE',{id,pool,route,fence,key,expires}); return {id,fence};
    });
  }
  get(l) { const r=this.db.prepare('SELECT * FROM atom_leases WHERE id=?').get(l.id); need(r&&r.fence===l.fence,'STALE_FENCE'); return r; }
  current(l, now=Date.now()) { const r=this.get(l); need(!r.released&&r.expires>now,'EXPIRED_OR_RELEASED_LEASE'); return r; }
  claimStart(l) { return this.tx(()=>{ const r=this.current(l); need(r.state==='LEASED','ALREADY_STARTED'); this.db.prepare("UPDATE atom_leases SET state='STARTING' WHERE id=?").run(l.id); return r; }); }
  ack(l, ack) { const r=this.current(l); need(r.state==='STARTING','ACK_STATE'); this.db.prepare("UPDATE atom_leases SET state='EXECUTING' WHERE id=?").run(l.id); this.event('EXECUTOR_ACK',{...l,ack}); }
  checkpoint(l, value) { this.current(l); const raw=JSON.stringify(jsonValue(value,256*1024)); this.db.prepare('UPDATE atom_leases SET checkpoint_json=? WHERE id=?').run(raw,l.id); this.event('CHECKPOINT',{...l,hash:sha256(raw)}); }
  stopped(l, state) { this.get(l); this.db.prepare('UPDATE atom_leases SET stop_observed=1,state=? WHERE id=?').run(state,l.id); this.event('STOP_OBSERVED',{...l,state}); }
  release(l) { return this.tx(()=>{ const r=this.get(l); need(r.stop_observed===1,'STOP_NOT_CONFIRMED'); if(r.released) return false; this.db.prepare('UPDATE atom_leases SET released=1 WHERE id=?').run(l.id); this.event('RELEASE',l); return true; }); }
  cache(key, now=Date.now()) {
    const r=this.db.prepare('SELECT * FROM atom_cache WHERE cache_key=?').get(key); if(!r||r.expires<=now) return null;
    const value=JSON.parse(r.output_json),receipt=JSON.parse(r.receipt_json);
    need(sha256Json(value)===r.output_hash&&receipt.outputDigest===r.output_hash&&receipt.key===key,'CACHE_TAMPER');
    return {value,receipt};
  }
  accept(l, receipt, value, ttlMs) {
    this.tx(()=>{
      const r=this.current(l); need(r.stop_observed===1&&r.state==='RESULT_RETURNED','RESULT_WITHOUT_STOP');
      need(receipt.key===r.job_key,'RECEIPT_BINDING');
      this.db.prepare("UPDATE atom_leases SET state='VERIFIED',receipt_json=? WHERE id=?").run(JSON.stringify(receipt),l.id);
      if(ttlMs>0)this.db.prepare('INSERT OR REPLACE INTO atom_cache VALUES(?,?,?,?,?)').run(receipt.key,JSON.stringify(value),receipt.outputDigest,JSON.stringify(receipt),Date.now()+ttlMs);
      this.event('VERIFIED',{...l,key:receipt.key,outputDigest:receipt.outputDigest});
    });
  }
  taskReceipt(task, value, receipt) { this.db.prepare('INSERT OR REPLACE INTO atom_task_receipts VALUES(?,?,?,?)').run(task.id,sha256Json(task),sha256Json(value),JSON.stringify(receipt)); }
  result(l) { const r=this.get(l); return r.receipt_json?JSON.parse(r.receipt_json):null; }
  verifyEvents() {
    let previous='0'.repeat(64),count=0;
    for(const r of this.db.prepare('SELECT * FROM atom_events ORDER BY seq').all()) { need(r.prev_hash===previous&&r.hash===sha256Json({previous,event:JSON.parse(r.event_json)}),'EVENT_CHAIN_TAMPER'); previous=r.hash; count++; }
    return {count,hash:previous};
  }
  snapshot() { return {active:this.db.prepare('SELECT COUNT(*) n FROM atom_leases WHERE released=0').get().n,
    leases:this.db.prepare('SELECT state,COUNT(*) n FROM atom_leases GROUP BY state').all(),
    cached:this.db.prepare('SELECT COUNT(*) n FROM atom_cache').get().n,events:this.verifyEvents()}; }
  close() { this.db.close(); }
}

// Fixed bootstrap; module path, source hash and export are trusted host bindings.
const BOOTSTRAP=`const {parentPort,workerData,threadId}=require('node:worker_threads');
const fs=require('node:fs'),crypto=require('node:crypto');
(async()=>{const b=fs.readFileSync(new URL(workerData.moduleUrl));
if(crypto.createHash('sha256').update(b).digest('hex')!==workerData.moduleDigest)throw Error('WORKER_CODE_TAMPER');
const mod=await import(workerData.moduleUrl);if(typeof mod[workerData.exportName]!=='function')throw Error('OPERATOR_EXPORT_MISSING');
parentPort.postMessage({type:'ACK',threadId,pid:process.pid});
parentPort.once('message',async m=>{if(m.type!=='RUN')throw Error('RUN_REQUIRED');
try{const result=await mod[workerData.exportName](workerData.input,{checkpoint:v=>parentPort.postMessage({type:'CHECKPOINT',value:v})});
parentPort.postMessage({type:'RESULT',value:result});parentPort.close();}
catch(e){parentPort.postMessage({type:'ERROR',error:String(e.message)});parentPort.close();}});
})().catch(e=>{parentPort.postMessage({type:'ERROR',error:String(e.message)});parentPort.close();});`;

export class PinnedWorkerDriver {
  constructor({moduleUrl,moduleDigest,exportName,heapMiB=96}) {
    const u=new URL(moduleUrl); need(u.protocol==='file:','LOCAL_PINNED_MODULE_REQUIRED'); checkedHash(moduleDigest);
    need(/^[A-Za-z_$][\w$]*$/.test(exportName),'INVALID_EXPORT'); int(heapMiB,16,512,'HEAP_LIMIT');
    this.config=Object.freeze({moduleUrl:u.href,moduleDigest,exportName,heapMiB});
    this.identity=sha256Json({kind:'pinned-worker-thread',...this.config});
  }
  start(input,onCheckpoint=()=>{}) {
    need(sha256(readFileSync(fileURLToPath(this.config.moduleUrl)))===this.config.moduleDigest,'OPERATOR_CODE_TAMPER');
    const worker=new Worker(BOOTSTRAP,{eval:true,workerData:{...this.config,input},resourceLimits:{maxOldGenerationSizeMb:this.config.heapMiB}});
    const workerThreadId=worker.threadId;
    let ackResolve,ackReject,resultResolve,resultReject,stopResolve,resultSeen=false,error=null,resultValue;
    const ack=new Promise((a,b)=>{ackResolve=a;ackReject=b;});ack.catch(()=>{});
    const result=new Promise((a,b)=>{resultResolve=a;resultReject=b;});result.catch(()=>{});
    const stopped=new Promise(a=>{stopResolve=a;});
    worker.on('message',m=>{
      if(m.type==='ACK')ackResolve({threadId:m.threadId,pid:m.pid,driver:this.identity});
      else if(m.type==='RESULT'){resultSeen=true;resultValue=m.value;}
      else if(m.type==='ERROR'){error=fail(m.error);}
      else if(m.type==='CHECKPOINT'){try{onCheckpoint(m.value);}catch(e){error=e;void worker.terminate();}}
    });
    worker.on('error',e=>{error=e;ackReject(e);});
    worker.on('exit',code=>{const proof={driver:this.identity,exitCode:code,observedAt:new Date().toISOString(),threadId:workerThreadId};stopResolve(proof);
      if(error||code!==0||!resultSeen){const e=error??fail('WORKER_STOPPED_WITHOUT_RESULT');ackReject(e);resultReject(e);}else resultResolve(resultValue);});
    return {ack,result,stopped,run:()=>worker.postMessage({type:'RUN'}),cancel:async()=>{await worker.terminate();return stopped;}};
  }
}

export class InstructionFabric {
  constructor({store,bindings,operators,freshnessMs=300000,reserveBytes=256*1024*1024}) {
    need(store instanceof AtomStore,'ATOM_STORE_REQUIRED'); this.store=store;
    this.bindings=new Map();this.operators=new Map();this.probes=new Map();this.inflight=new Map();this.probing=new Map();
    this.freshnessMs=int(freshnessMs,1,3600000,'FRESHNESS_LIMIT');this.reserveBytes=int(reserveBytes,0,2**40,'RESERVE_BYTES');
    for(const op of operators??[]){need(op.id&&typeof op.verify==='function'&&op.canary,'OPERATOR_CONTRACT_REQUIRED');
      for(const k of ['programDigest','verificationDigest','environmentDigest'])checkedHash(op[k]);
      if(op.validateInput)checkedHash(op.inputValidationDigest);
      need(!this.operators.has(op.id),'DUPLICATE_OPERATOR');this.operators.set(op.id,Object.freeze({...op,canary:jsonValue(op.canary)}));}
    for(const b of bindings??[]){need(b.routeId&&b.poolId&&b.driver?.start&&b.driver.identity&&b.authority?.consentRef,'TRUSTED_BINDING_REQUIRED');
      need(!this.bindings.has(b.routeId),'DUPLICATE_ROUTE');need(Array.isArray(b.operatorIds)&&b.operatorIds.every(id=>this.operators.has(id)),'BINDING_OPERATORS');
      const data=jsonValue({routeId:b.routeId,poolId:b.poolId,operatorIds:b.operatorIds,authority:b.authority,maxLeaseMs:b.maxLeaseMs??30000,slots:b.slots??1,driverIdentity:b.driver.identity});
      int(data.maxLeaseMs,100,300000,'MAX_LEASE_MS'); this.store.pool(data.poolId,data.slots);
      this.bindings.set(data.routeId,{...data,driver:b.driver,bindingHash:sha256Json(data)});}
  }
  authorize(routeId,opId,context={}) {
    const b=this.bindings.get(routeId),op=this.operators.get(opId);need(b&&op&&b.operatorIds.includes(opId),'UNBOUND_EXECUTOR_OR_OPERATOR');
    const a=b.authority;need(a.revoked!==true&&Number.isFinite(Date.parse(a.expiresAt))&&Date.parse(a.expiresAt)>Date.now(),'AUTHORITY_EXPIRED_OR_REVOKED');
    need(context.sideEffect!==true,'SIDE_EFFECT_NOT_SUPPORTED');
    need(a.tenantId===(context.tenantId??'deus'),'TENANT_OUTSIDE_GRANT');
    need(a.allowedDataClasses?.includes(context.dataClass??'public'),'DATA_OUTSIDE_GRANT');
    need(a.zeroSpend===true,'EXPLICIT_ZERO_SPEND_BINDING_REQUIRED');return {b,op};
  }
  classifyAtlas(record) {
    // Ignore all source-supplied authority, liveness, lease and endpoint claims.
    const type=String(record.type??'generic').toLowerCase();const value=record.value??record.prefix;
    const registration=registerParticipationIdentity({type,value,evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',source:record.source??'ATLAS',sourceEvidenceRef:record.sourceEvidenceRef??null});
    return {...registration,callableBindingCandidate:this.bindings.has(String(record.routeId??'')),executionAdmitted:false};
  }
  key(routeId,opId,input,context={}) {
    const {b,op}=this.authorize(routeId,opId,context);
    return sha256Json({schema:INSTRUCTION_FABRIC_VERSION,op:opId,input:jsonValue(input),program:op.programDigest,verifier:op.verificationDigest,
      environment:op.environmentDigest,inputValidation:op.inputValidationDigest??null,binding:b.bindingHash,tenant:context.tenantId??'deus',dataClass:context.dataClass??'public'});
  }
  async PROBE(routeId,opId,context={}) {
    const {b,op}=this.authorize(routeId,opId,context),probeKey=b.bindingHash+'|'+opId+'|'+op.programDigest+'|'+op.verificationDigest+'|'+op.environmentDigest;
    const old=this.probes.get(probeKey);if(old&&Date.now()-old.at<this.freshnessMs)return old;
    if(this.probing.has(probeKey))return this.probing.get(probeKey);
    const promise=(async()=>{
      const l=this.LEASE(routeId,opId,op.canary.input,context,{probe:true});
      const value=await this.RUN(l);need(sha256Json(value)===sha256Json(op.canary.expected),'CANARY_EXPECTATION_FAIL');
      const receipt={at:Date.now(),binding:b.bindingHash,program:op.programDigest,receipt:this.RESULT(l)};
      this.probes.set(probeKey,receipt);this.store.event('PROBE_PASS',{routeId,opId,outputDigest:sha256Json(value)});return receipt;
    })();this.probing.set(probeKey,promise);try{return await promise;}finally{this.probing.delete(probeKey);}
  }
  LEASE(routeId,opId,input,context={}, {probe=false,leaseMs=null}={}) {
    const {b,op}=this.authorize(routeId,opId,context);if(op.validateInput)need(op.validateInput(input)===true,'INPUT_VALIDATION_FAILED');need(freemem()>=this.reserveBytes,'MEMORY_RESERVE_HOLD');
    const probeKey=b.bindingHash+'|'+opId+'|'+op.programDigest+'|'+op.verificationDigest+'|'+op.environmentDigest;const evidence=this.probes.get(probeKey);
    if(probe)need(sha256Json(input)===sha256Json(op.canary.input),'PROBE_INPUT_NOT_CANARY');
    need(probe||(evidence&&Date.now()-evidence.at<this.freshnessMs),'FRESH_CANARY_REQUIRED');
    const ttl=leaseMs??b.maxLeaseMs;int(ttl,100,b.maxLeaseMs,'LEASE_TTL');
    const packet={routeId,opId,input:jsonValue(input),context:jsonValue(context),probe};
    const key=this.key(routeId,opId,packet.input,context)+(probe?':probe':'');
    const l=this.store.reserve({pool:b.poolId,route:routeId,key,bindingHash:b.bindingHash,packet,expires:Math.min(Date.now()+ttl,Date.parse(b.authority.expiresAt))});
    // These booleans are derived here from host-bound authority + fresh local receipt,
    // never passed through from Atlas or provider output.
    const accord=evaluateComputeOffer({offerId:l.id,routeId,provider:routeId,authorityClass:'OWNER_AUTHORIZED',ownerAuthorized:true,
      capabilityClass:opId,dataClassMax:context.dataClass??'public',freshnessMs:0,receiptPath:true,canaryPassed:!probe,currentLease:true,expectedUsefulValue:1});
    need(probe||accord.decision==='ADMIT_CURRENT','ACCORD_NOT_ADMITTED');
    if(!probe){const reg=registerParticipationIdentity({type:'service',value:routeId,authorityClass:'OWNER_AUTHORIZED',ownerAuthorized:true,computeHint:true,evidenceClass:'DATA_ONLY'});
      const admitted=promoteRegistrationWithAccord(reg,accord);const r=this.store.get(l);
      const lease=buildParticipationLease({registration:admitted,leaseId:l.id,issuedAt:new Date().toISOString(),expiresAt:new Date(r.expires).toISOString(),capacity:{pool:b.poolId,slots:1}});
      this.store.event('ACCORD_ADMIT',{id:l.id,lease,sourceConsentRef:b.authority.consentRef});}
    return l;
  }
  CHECKPOINT(l, value) { return this.store.checkpoint(l,value); }
  RESULT(l) { return this.store.result(l); }
  RELEASE(l) { return this.store.release(l); }
  async CANCEL(l) {
    const r=this.store.get(l);if(r.released)return {state:'ALREADY_RELEASED'};
    const h=this.inflight.get(l.id);
    if(h){h.cancelled=true;await h.handle.cancel();await h.handle.stopped;this.store.stopped(l,'CANCELLED');this.RELEASE(l);return {state:'CANCELLED_STOP_VERIFIED'};}
    if(r.state==='LEASED'){this.store.stopped(l,'CANCELLED_NOT_STARTED');this.RELEASE(l);return {state:'CANCELLED_NOT_STARTED'};}
    if(r.stop_observed){this.RELEASE(l);return {state:'RELEASED_AFTER_OBSERVED_STOP'};}
    throw fail('UNKNOWN_EXECUTOR_STOP_HOLD');
  }
  async RUN(l) {
    const r=this.store.claimStart(l),p=JSON.parse(r.packet_json);const {b,op}=this.authorize(p.routeId,p.opId,p.context);
    need(b.bindingHash===r.binding_hash,'BINDING_CHANGED');let h,timer;const started=performance.now();
    try{
      h={cancelled:false,handle:b.driver.start(p.input,v=>this.CHECKPOINT(l,v))};this.inflight.set(l.id,h);
      const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{h.cancelled=true;void h.handle.cancel();reject(fail('LEASE_DEADLINE'));},Math.max(1,r.expires-Date.now()));});
      const ack=await Promise.race([h.handle.ack,deadline]);this.store.ack(l,ack);h.handle.run();
      const raw=await Promise.race([h.handle.result,deadline]);const stop=await h.handle.stopped;
      need(!h.cancelled,'CANCELLED_RESULT_REJECTED');this.store.current(l);this.authorize(p.routeId,p.opId,p.context);
      const value=jsonValue(raw);this.store.stopped(l,'RESULT_RETURNED');
      need(await op.verify(value,p.input)===true,'RESULT_VERIFIER_REJECTED');
      if(p.probe)need(sha256Json(value)===sha256Json(op.canary.expected),'CANARY_EXPECTATION_FAIL');
      this.store.current(l);
      const receipt={schema:INSTRUCTION_FABRIC_VERSION,kind:p.probe?'CANARY':'EXECUTED',key:r.job_key,leaseId:l.id,fence:l.fence,
        routeId:p.routeId,poolId:b.poolId,operator:p.opId,inputDigest:sha256Json(p.input),outputDigest:sha256Json(value),
        programDigest:op.programDigest,verificationDigest:op.verificationDigest,environmentDigest:op.environmentDigest,
        bindingDigest:b.bindingHash,stop,elapsedMs:performance.now()-started,verifiedAt:new Date().toISOString(),
        physicalCapacityClaimed:false,verdict:'VERIFIED_FOR_OPERATOR_CONTRACT'};
      this.store.accept(l,receipt,value,p.probe?0:int(op.cacheTtlMs??600000,0,86400000,'CACHE_TTL'));
      this.RELEASE(l);return value;
    }catch(e){
      if(h){await h.handle.cancel();await h.handle.stopped;}
      // Only known built-in driver termination / never-started work closes a lease.
      this.store.stopped(l,h?.cancelled?'CANCELLED':'FAILED');this.RELEASE(l);this.store.event('SCAR',{...l,code:e.code??e.message});throw e;
    }finally{clearTimeout(timer);this.inflight.delete(l.id);}
  }
  async invoke(routeId,opId,input,context={}) {
    const {op}=this.authorize(routeId,opId,context);input=jsonValue(input);if(op.validateInput)need(op.validateInput(input)===true,'INPUT_VALIDATION_FAILED');const key=this.key(routeId,opId,input,context);
    const cached=this.store.cache(key);
    if(cached){need(cached.receipt.inputDigest===sha256Json(input)&&cached.receipt.programDigest===op.programDigest&&cached.receipt.verificationDigest===op.verificationDigest&&cached.receipt.environmentDigest===op.environmentDigest&&cached.receipt.verdict==='VERIFIED_FOR_OPERATOR_CONTRACT','CACHE_CONTRACT_MISMATCH');this.store.event('REUSE',{key,originalLease:cached.receipt.leaseId});return {value:cached.value,receipt:{...cached.receipt,kind:'VERIFIED_REUSE',reusedAt:new Date().toISOString()}};}
    await this.PROBE(routeId,opId,context);const l=this.LEASE(routeId,opId,input,context);const value=await this.RUN(l);return {value,receipt:this.RESULT(l)};
  }
  provider(routeId) {
    const b=this.bindings.get(routeId);need(b,'UNKNOWN_BINDING');
    return {id:routeId,kind:'instruction-atom',status:'active',capabilities:b.operatorIds.map(x=>'atom.'+x),
      authorization:{consentRef:b.authority.consentRef,expiresAt:b.authority.expiresAt,allowedDataClasses:b.authority.allowedDataClasses,maxTaskCostUsd:0,allowSideEffects:false},
      limits:{maxConcurrency:b.slots,maxCostPerTaskUsd:0},telemetry:{trust:1,availability:1,p95LatencyMs:100,costPerUnitUsd:0}};
  }
  adapter() { return {execute:async(provider,task)=>{
    need(task.capability.startsWith('atom.'),'ATOM_CAPABILITY_REQUIRED');need(!task.cachePolicy,'LEGACY_CACHE_MUST_BE_DISABLED');
    const opId=task.capability.slice(5);const p=task.payload;const input=p?.graph?{value:p.input?.value??null,upstream:p.upstream??{},sourceDigest:p.input?.sourceDigest??null}:p;
    const result=await this.invoke(provider.id,opId,input,{tenantId:task.tenantId??'deus',dataClass:task.dataClass??'public',sideEffect:task.sideEffect===true});
    this.store.taskReceipt(task,result.value,result.receipt);return result.value;
  }}; }
  verifyPersistedTask(job) {
    if(job.state!=='succeeded')return;
    const row=this.store.db.prepare('SELECT * FROM atom_task_receipts WHERE task_id=?').get(job.id);
    const value=job.result?.result;need(row&&row.task_hash===sha256Json(job.task)&&row.output_hash===sha256Json(value),'QUEUE_RESULT_WITHOUT_VERIFIED_ATOM_RECEIPT');
    const receipt=JSON.parse(row.receipt_json),p=job.task.payload;
    need(receipt.outputDigest===row.output_hash&&receipt.verdict==='VERIFIED_FOR_OPERATOR_CONTRACT','PERSISTED_RECEIPT_MISMATCH');
    const input=p?.graph?{value:p.input?.value??null,upstream:p.upstream??{},sourceDigest:p.input?.sourceDigest??null}:p;
    const context={tenantId:job.task.tenantId??'deus',dataClass:job.task.dataClass??'public',sideEffect:job.task.sideEffect===true};
    need(receipt.key===this.key(receipt.routeId,job.task.capability.slice(5),input,context),'PERSISTED_CONTRACT_CHANGED');
    const {op}=this.authorize(receipt.routeId,job.task.capability.slice(5),context);
    if(op.validateInput)need(op.validateInput(input)===true,'PERSISTED_INPUT_VALIDATION_FAILED');
  }
}

/** Cold descriptor may address 1T; materialized graph is explicitly bounded. */
export function compileAtomTree({graphId,runId=graphId,leaves,leafOperator,reducerOperator,fanIn=4,logicalCells='1000000000000',maxNodes=10000}={}) {
  int(fanIn,2,64,'FANIN');int(maxNodes,2,10000,'MAX_NODES');need(Array.isArray(leaves)&&leaves.length>0&&leaves.length<maxNodes,'BOUNDED_LEAVES_REQUIRED');
  need(/^\d+$/.test(String(logicalCells))&&BigInt(logicalCells)>0n&&BigInt(logicalCells)<=1000000000000n,'LOGICAL_DOMAIN');
  let nodes=leaves.map((x,i)=>({id:'leaf-'+i,capability:'atom.'+leafOperator,payload:{value:jsonValue(x.value),sourceDigest:checkedHash(x.sourceDigest)},deps:[]}));
  let layer=nodes.map(x=>x.id),depth=0;
  while(layer.length>1){const next=[];for(let i=0;i<layer.length;i+=fanIn){const id=`reduce-${depth}-${i/fanIn}`;
      nodes.push({id,capability:'atom.'+reducerOperator,payload:{value:null,sourceDigest:null},deps:layer.slice(i,i+fanIn)});need(nodes.length<=maxNodes,'MATERIALIZATION_LIMIT');next.push(id);}layer=next;depth++;}
  return normalizeTaskGraph({graphId,runId,nodes,dataClass:'public',metadata:{logicalCells:String(logicalCells),materializedNodes:nodes.length,leafCount:leaves.length,fanIn,depth,root:layer[0],physicalExecutorCount:null,semantics:'BOUNDED_HOT_DAG_NOT_ONE_EXECUTOR_PER_LOGICAL_CELL'}});
}

/** Uses the unchanged broker/orchestrator, with verification before every restore. */
export async function executeAtomGraph({runtime,fabric,graph,maxParallel=2,deadlineMs=120000}) {
  int(maxParallel,1,16,'PARALLEL_LIMIT');int(deadlineMs,100,300000,'GRAPH_DEADLINE');
  const broker=new TaskGraphBroker(graph),orch=runtime.orchestrator;const deadline=Date.now()+deadlineMs;
  for(const id of graph.order){const job=await orch.queue.get(broker.taskIdForNode(id));if(job)fabric.verifyPersistedTask(job);}
  await broker.restoreFromQueue(orch);let executions=0,reuses=0;
  while(broker.snapshot().verdict==='IN_PROGRESS'){
    need(Date.now()<deadline,'GRAPH_CHECKPOINT_DEADLINE');await broker.materializeReady(orch,{maxTasks:maxParallel});
    const results=await Promise.all(Array.from({length:maxParallel},(_,i)=>orch.runOnce({coordinatorId:'atom-'+i,leaseMs:Math.min(deadlineMs,300000),retryDelayMs:50})));
    for(const r of results){if(r?.job?.state==='succeeded'){fabric.verifyPersistedTask(r.job);const rr=fabric.store.db.prepare('SELECT receipt_json FROM atom_task_receipts WHERE task_id=?').get(r.job.id);JSON.parse(rr.receipt_json).kind==='VERIFIED_REUSE'?reuses++:executions++;}}
    await broker.refresh(orch);if(!results.some(Boolean)&&broker.snapshot().verdict==='IN_PROGRESS')await new Promise(r=>setTimeout(r,50));
  }
  const snapshot=broker.snapshot();need(snapshot.verdict==='SUCCEEDED','GRAPH_FAILED');
  return {snapshot,root:snapshot.states[graph.metadata.root].result,executions,reuses,resourceState:fabric.store.snapshot()};
}

/** Reducer contracts are explicit, not a universal majority vote. */
export function reduceTyped(kind,values,{verifyItem=()=>false,score=()=>NaN,key=x=>sha256Json(x)}={}) {
  need(Array.isArray(values)&&values.length>0,'REDUCER_INPUT');need(values.every(x=>verifyItem(x)===true),'REDUCER_ITEM_REJECTED');
  if(kind==='exact')return {kind,items:values,orderedDigest:sha256Json(values)};
  if(kind==='optimization') { const scored=values.map(v=>({v,s:score(v),k:key(v)}));need(scored.every(x=>Number.isFinite(x.s)),'SCORE_REQUIRED');scored.sort((a,b)=>b.s-a.s||a.k.localeCompare(b.k));return {kind,best:scored[0].v,score:scored[0].s}; }
  if(kind==='simulation') { let n=0,mean=0,m2=0;for(const v of values){need(Number.isSafeInteger(v.n)&&v.n>0&&Number.isFinite(v.mean)&&Number.isFinite(v.m2)&&v.m2>=0,'STATISTICS_CONTRACT');const total=n+v.n;need(Number.isSafeInteger(total),'STATISTICS_OVERFLOW');const delta=v.mean-mean;m2+=v.m2+delta*delta*n*v.n/total;mean+=delta*v.n/total;n=total;}need(Number.isFinite(mean)&&Number.isFinite(m2),'STATISTICS_NONFINITE');return {kind,n,mean,m2}; }
  if(kind==='reasoning') { const claims=new Map();for(const v of values){need(typeof v.claim==='string'&&Array.isArray(v.evidence)&&typeof v.stance==='string','CLAIM_CONTRACT');const a=claims.get(v.claim)??[];a.push(v);claims.set(v.claim,a);}return {kind,truthPromoted:false,claims:[...claims].map(([claim,items])=>({claim,items,conflict:new Set(items.map(x=>x.stance)).size>1,state:'EVIDENCE_REVIEW_REQUIRED'}))}; }
  throw fail('UNKNOWN_REDUCER');
}

/** Existing LRC remains the placement compiler. The vector is a caller-provided
 * planning input; actual admission still needs binding/canary/resource lease. */
export function lowerAtomGraph(graph, resourceVector) {
  need(resourceVector&&typeof resourceVector==='object','RESOURCE_VECTOR_REQUIRED');
  return compileLogicalResourcePlan({taskId:graph.graphId,logicalNamespace:graph.metadata.logicalCells,
    taskLogicalUnits:graph.metadata.logicalCells,resourceVector,dataClass:'BL-S0',
    stages:graph.nodes.map(n=>({id:n.id,deps:n.deps,role:n.deps.length?'REDUCE':'COMPUTE',
      capability:n.capability,cpu:'REQUIRED',gpu:'NONE',ramRole:'WORKING_SET',storageRole:'RESULT_CACHE',cacheable:true})),
    metadata:{instructionFabricVersion:INSTRUCTION_FABRIC_VERSION,graphFingerprint:graph.fingerprint,
      vectorMeaning:'PLACEMENT_INPUT_NOT_NEW_PHYSICAL_CAPACITY',dispatchGate:'FRESH_CANARY_AND_FENCED_RESOURCE_LEASE'}});
}
