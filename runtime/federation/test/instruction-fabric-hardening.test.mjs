/** Regression evidence for observed pre-start leakage and concurrent journal writes.
 * These exercise trusted local operators only; no network requests or provider leases.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {Worker} from 'node:worker_threads';
import {AtomStore,InstructionFabric,PinnedWorkerDriver} from '../lib/instruction-fabric.mjs';
import {sha256,sha256Json as h} from '../lib/canonical.mjs';
const operatorsUrl=new URL('../worker/instruction-operators.mjs',import.meta.url).href;
const moduleDigest=sha256(readFileSync(new URL(operatorsUrl)));
const payload=n=>({value:{numbers:n},upstream:{},sourceDigest:h(n)});
function fixture(t,{verify=(v,p)=>v.sum===p.value.numbers.reduce((s,n)=>s+BigInt(n),0n).toString(),validateInput=null}={}){
 const dir=mkdtempSync(join(tmpdir(),'atom-hardening-'));const store=new AtomStore(join(dir,'atoms.sqlite'));
 const op={id:'sum',programDigest:moduleDigest,verificationDigest:h('hardening-exact-sum'),environmentDigest:h(process.version),canary:{input:payload([1,2]),expected:{sum:'3'}},verify,...(validateInput?{validateInput,inputValidationDigest:h('dynamic-test-validation')}: {})};
 const b={routeId:'local',poolId:'local-host',slots:1,operatorIds:['sum'],maxLeaseMs:3000,
 authority:{consentRef:'LOCAL_TEST_INVOCATION_ONLY',tenantId:'deus',allowedDataClasses:['public'],zeroSpend:true,expiresAt:new Date(Date.now()+60000).toISOString()},
 driver:new PinnedWorkerDriver({moduleUrl:operatorsUrl,moduleDigest,exportName:'integerSum',dependencyPins:[],allowedBuiltins:['node:crypto']})};
 const f=new InstructionFabric({store,operators:[op],bindings:[b],reserveBytes:0});
 t.after(()=>{store.close();rmSync(dir,{recursive:true,force:true});});return {f,store,dir,b,op};
}
async function leased(f){await f.PROBE('local','sum');return f.LEASE('local','sum',payload([8]));}
test('revocation between LEASE and RUN releases known-never-started work',async t=>{const {f,store}=fixture(t);const l=await leased(f);f.bindings.get('local').authority.revoked=true;await assert.rejects(f.RUN(l),/REVOKED/);assert.equal(store.snapshot().active,0);assert.equal(store.get(l).state,'FAILED');});
test('authority expiry before RUN cannot leak STARTING reservation',async t=>{const {f,store}=fixture(t);const l=await leased(f);f.bindings.get('local').authority.expiresAt='2000-01-01T00:00:00Z';await assert.rejects(f.RUN(l),/EXPIRED/);assert.equal(store.snapshot().active,0);});
test('binding change before RUN is rejected and cleaned',async t=>{const {f,store}=fixture(t);const l=await leased(f);f.bindings.get('local').bindingHash=h('changed');await assert.rejects(f.RUN(l),/BINDING_CHANGED/);assert.equal(store.snapshot().active,0);});
test('input validation runs again before starting executor',async t=>{let good=true;const {f,store}=fixture(t,{validateInput:()=>good});const l=await leased(f);good=false;await assert.rejects(f.RUN(l),/INPUT_VALIDATION/);assert.equal(store.snapshot().active,0);});
test('authority is checked after asynchronous verification',async t=>{let f;({f}=fixture(t,{verify:async(v,p)=>{if(p.value.numbers[0]===8)f.bindings.get('local').authority.revoked=true;return true;}}));await assert.rejects(f.invoke('local','sum',payload([8])),/REVOKED/);assert.equal(f.store.snapshot().active,0);assert.equal(f.store.snapshot().cached,0);});
test('late stop cannot overwrite a released VERIFIED outcome',async t=>{const {f,store}=fixture(t);const r=await f.invoke('local','sum',payload([8]));const l={id:r.receipt.leaseId,fence:r.receipt.fence};assert.equal(store.stopped(l,'CANCELLED'),false);assert.equal(store.get(l).state,'VERIFIED');});
test('released checkpoint is immutable',async t=>{const {f}=fixture(t);const r=await f.invoke('local','sum',payload([8]));assert.throws(()=>f.CHECKPOINT({id:r.receipt.leaseId,fence:r.receipt.fence},{cursor:999}),/RELEASED/);});
test('closure mode is included in attributable result receipt',async t=>{const {f}=fixture(t);const r=await f.invoke('local','sum',payload([8]));assert.equal(r.receipt.codePinMode,'DECLARED_ESM_CLOSURE');assert.equal(r.value.sum,'8');});
test('nested journal event is rolled back with its state transaction',t=>{const {store}=fixture(t);const before=store.verifyEvents();assert.throws(()=>store.tx(()=>{store.event('MUST_ROLL_BACK',{n:1});throw Error('fixture');}),/fixture/);assert.deepEqual(store.verifyEvents(),before);});
test('nested transactions never commit their parent early',t=>{const {store}=fixture(t);assert.throws(()=>store.tx(()=>{store.tx(()=>store.event('CHILD',{}));throw Error('rollback');}),/rollback/);assert.equal(store.verifyEvents().count,0);});
test('four concurrent SQLite connections preserve one journal chain',async t=>{
 const {store,dir}=fixture(t);const moduleUrl=new URL('../lib/instruction-fabric.mjs',import.meta.url).href;
 const workerSource=`const {workerData,parentPort}=require('node:worker_threads');(async()=>{const {AtomStore}=await import(workerData.moduleUrl);const s=new AtomStore(workerData.db);parentPort.postMessage('READY');parentPort.once('message',()=>{try{for(let i=0;i<150;i++)s.event('PARALLEL',{writer:workerData.writer,i});s.close();parentPort.postMessage('DONE');}catch(e){throw e;}});})().catch(e=>{throw e});`;
 const workers=Array.from({length:4},(_,writer)=>new Worker(workerSource,{eval:true,workerData:{moduleUrl,db:join(dir,'atoms.sqlite'),writer}}));
 t.after(async()=>{await Promise.all(workers.map(w=>w.terminate()));});
 await Promise.all(workers.map(w=>new Promise((resolve,reject)=>{w.once('message',m=>m==='READY'?resolve():reject(Error('BAD_READY')));w.once('error',reject);}))); 
 const done=workers.map(w=>new Promise((resolve,reject)=>{w.once('message',m=>m==='DONE'?resolve():reject(Error('BAD_DONE')));w.once('error',reject);}));
 for(const w of workers)w.postMessage('START');await Promise.all(done);assert.equal(store.verifyEvents().count,600);
});
function closure(t,entry="import {n} from './dep.mjs';export function f(){return {n}};",deps=true,builtins=[]){
 const dir=mkdtempSync(join(tmpdir(),'pin-closure-')),path=join(dir,'entry.mjs'),dep=join(dir,'dep.mjs');writeFileSync(path,entry);writeFileSync(dep,'export const n=4;');
 const config={moduleUrl:pathToFileURL(path).href,moduleDigest:sha256(readFileSync(path)),exportName:'f',dependencyPins:deps?[{url:pathToFileURL(dep).href,sha256:sha256(readFileSync(dep))}]:[],allowedBuiltins:builtins};
 t.after(()=>rmSync(dir,{recursive:true,force:true}));return {dir,path,dep,config,driver:new PinnedWorkerDriver(config)};
}
async function result(driver){const x=driver.start({});try{await x.ack;x.run();return await x.result;}finally{await x.cancel();await x.stopped;}}
test('declared local ESM dependency executes pinned bytes',async t=>{const {driver}=closure(t);assert.deepEqual(await result(driver),{n:4});});
test('missing declaration fails before task execution',async t=>{const {driver}=closure(t,undefined,false);await assert.rejects(result(driver),/UNDECLARED_IMPORT/);});
test('dependency modification before invocation fails closed',t=>{const {driver,dep}=closure(t);writeFileSync(dep,'export const n=5;');assert.throws(()=>driver.start({}),/DEPENDENCY_CODE_TAMPER/);});
test('load hook uses frozen bytes for delayed dynamic imports',async t=>{const {driver,dep}=closure(t,"export async function f(){const {n}=await import('./dep.mjs');return {n};}");const x=driver.start({});await x.ack;writeFileSync(dep,'export const n=999;');x.run();assert.deepEqual(await x.result,{n:4});await x.stopped;});
test('new dependency revision changes driver binding identity',t=>{const {config,dep,driver}=closure(t);writeFileSync(dep,'export const n=5;');const other=new PinnedWorkerDriver({...config,dependencyPins:[{url:pathToFileURL(dep).href,sha256:sha256(readFileSync(dep))}]});assert.notEqual(driver.identity,other.identity);});
test('undeclared built-in cannot be imported',async t=>{const {driver}=closure(t,"import fs from 'node:fs';export const f=()=>({ok:!!fs});",false);await assert.rejects(result(driver),/UNDECLARED_BUILTIN/);});
test('allowed built-in is normalized across node alias',async t=>{const {driver}=closure(t,"import {createHash} from 'crypto';export const f=()=>({n:createHash('sha256').update('a').digest('hex').length});",false,['node:crypto']);assert.deepEqual(await result(driver),{n:64});});
for(const target of ['https://example.invalid/never-contact.mjs','data:text/javascript,export default 1'])test('nonlocal import is rejected without retrieval: '+target.split(':')[0],async t=>{const {driver}=closure(t,`export const f=()=>import(${JSON.stringify(target)});`,false);await assert.rejects(result(driver),/UNDECLARED_IMPORT/);});
test('dependency URL queries cannot create unpinned variants',async t=>{const {driver}=closure(t,"export const f=()=>import('./dep.mjs?rev=2');");await assert.rejects(result(driver),/UNDECLARED_IMPORT/);});
test('duplicate and invalid dependency pins are rejected',t=>{const {config}=closure(t);assert.throws(()=>new PinnedWorkerDriver({...config,dependencyPins:[config.dependencyPins[0],config.dependencyPins[0]]}),/DUPLICATE_DEPENDENCY/);assert.throws(()=>new PinnedWorkerDriver({...config,dependencyPins:[{url:'https://example.invalid/x.mjs',sha256:h(1)}]}),/LOCAL_ESM/);});
test('legacy driver is honestly labeled entry-only',t=>{const {config}=closure(t);assert.equal(new PinnedWorkerDriver({...config,dependencyPins:null}).pinMode,'ENTRY_ONLY');});
test('changed dependency rejects even a previously cached result',async t=>{
 const c=closure(t),{store}=fixture(t);const f=new InstructionFabric({store,reserveBytes:0,operators:[{id:'f',programDigest:c.config.moduleDigest,verificationDigest:h('n4'),environmentDigest:h(process.version),verify:v=>v.n===4,canary:{input:{},expected:{n:4}}}],bindings:[{routeId:'closure',poolId:'closure-host',slots:1,operatorIds:['f'],authority:{consentRef:'LOCAL_TEST_ONLY',tenantId:'deus',allowedDataClasses:['public'],zeroSpend:true,expiresAt:new Date(Date.now()+60000).toISOString()},driver:c.driver}]});
 await f.invoke('closure','f',{a:1});writeFileSync(c.dep,'export const n=5;');await assert.rejects(f.invoke('closure','f',{a:1}),/DEPENDENCY_CODE_TAMPER/);
});

test('failed Accord admission journaling rolls back never-issued reservation',async t=>{const {f,store}=fixture(t);await f.PROBE('local','sum');const original=store.event.bind(store);store.event=(type,data)=>{if(type==='ACCORD_ADMIT')throw Error('INJECTED_JOURNAL_FAILURE');return original(type,data);};assert.throws(()=>f.LEASE('local','sum',payload([8])),/INJECTED/);assert.equal(store.snapshot().active,0);store.event=original;const r=await f.invoke('local','sum',payload([8]));assert.equal(r.value.sum,'8');assert.equal(store.snapshot().active,0);});
test('pool capacity conflict cannot silently change shared allocation',t=>{const {store,dir}=fixture(t);const other=new AtomStore(join(dir,'atoms.sqlite'));try{assert.throws(()=>other.pool('local-host',2),/CAPACITY_CONFLICT/);assert.equal(store.db.prepare('SELECT slots FROM atom_pools WHERE id=?').get('local-host').slots,1);}finally{other.close();}});
