/** Public, bounded generative-state contract integration example.
 * This exact integer-affine family is not the historical U64 benchmark and
 * does not implement arbitrary dense states, tensor workloads or private logic.
 */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';import {join,resolve} from 'node:path';
import {AtomStore,InstructionFabric,PinnedWorkerDriver,compileAtomTree,executeAtomGraph} from '../lib/instruction-fabric.mjs';
import {createFederationRuntime} from '../lib/runtime.mjs';import {createSqliteFederationState} from '../lib/sqlite-state.mjs';
import {sha256,sha256Json as digest} from '../lib/canonical.mjs';
import {decodeRange,reconstructCell,affineRangeSummary} from '../worker/generative-range-operators.mjs';
const out=resolve(process.argv[2]??'.deus/instruction-generative');mkdirSync(out,{recursive:true});
const startTime=new Date().toISOString(),usage0=process.resourceUsage();
const make=(start,count)=>({schema:'affine-integer-range/1',start:String(start),count:String(count),lanes:Array.from({length:8},(_,i)=>({a:String(i-3),b:String(17-i)})),exceptions:[]});
// Independent endpoint-average formula rather than the worker's ordinal formula.
function oracle(d){const s=BigInt(d.start),n=BigInt(d.count);const sums=d.lanes.map(x=>(BigInt(x.a)*s+BigInt(x.b)+BigInt(x.a)*(s+n-1n)+BigInt(x.b))*n/2n);for(const e of d.exceptions)sums[e.lane]+=BigInt(e.value)-BigInt(d.lanes[e.lane].a)*BigInt(e.index)-BigInt(d.lanes[e.lane].b);return {schema:'affine-range-summary/1',start:d.start,count:d.count,laneSums:sums.map(String),sum:String(sums.reduce((a,b)=>a+b,0n)),semantics:'EXACT_INTEGER_AFFINE_PLUS_SPARSE_EXCEPTIONS_NOT_DENSE_ARBITRARY_STATE'};}
function reduceOracle(p){const a=Object.values(p.upstream).sort((a,b)=>BigInt(a.start)<BigInt(b.start)?-1:1);let end=BigInt(a[0].start),n=0n;const sums=Array(8).fill(0n);for(const x of a){assert.equal(BigInt(x.start),end);end+=BigInt(x.count);n+=BigInt(x.count);for(let l=0;l<8;l++)sums[l]+=BigInt(x.laneSums[l]);}return {...a[0],count:String(n),laneSums:sums.map(String),sum:String(sums.reduce((a,b)=>a+b,0n))};}
const n=1000000000000n,part=n/8n,ds=Array.from({length:8},(_,i)=>make(BigInt(i)*part,part));
const sample=make(0,16),pinUrl=new URL('../worker/generative-range-operators.mjs',import.meta.url).href,pinHash=sha256(readFileSync(new URL(pinUrl)));
const cinput={value:sample,upstream:{},sourceDigest:digest(sample)},crinput={value:null,upstream:{one:oracle(sample)},sourceDigest:null};
const env=digest({node:process.version,arithmetic:'EXACT_BIGINT_UNBOUNDED_INTEGER_AFFINE_V1'});
const ops=[{id:'affine',programDigest:pinHash,verificationDigest:sha256(oracle.toString()),environmentDigest:env,inputValidationDigest:sha256(decodeRange.toString()),validateInput:p=>{decodeRange(p.value);return true;},canary:{input:cinput,expected:oracle(sample)},verify:(v,p)=>digest(v)===digest(oracle(p.value))},
{id:'affine-reduce',programDigest:pinHash,verificationDigest:sha256(reduceOracle.toString()),environmentDigest:env,canary:{input:crinput,expected:reduceOracle(crinput)},verify:(v,p)=>digest(v)===digest(reduceOracle(p))}];
const authority={consentRef:'CURRENT_PROJECT_TEST_PUBLIC_ARITHMETIC_ONLY',tenantId:'deus',allowedDataClasses:['public'],zeroSpend:true,expiresAt:new Date(Date.now()+180000).toISOString()};
const bindings=ops.map(o=>({routeId:'local-'+o.id,poolId:'one-allocated-host',slots:2,maxLeaseMs:10000,operatorIds:[o.id],authority,driver:new PinnedWorkerDriver({moduleUrl:pinUrl,moduleDigest:pinHash,exportName:o.id==='affine'?'affineRangeSummary':'reduceAffineRanges',dependencyPins:[],allowedBuiltins:[]})}));
const graph=(runId,descs=ds)=>compileAtomTree({graphId:'generative-contract-example',runId,leaves:descs.map(value=>({value,sourceDigest:digest(value)})),leafOperator:'affine',reducerOperator:'affine-reduce',logicalCells:String(n),fanIn:4});
function open(){const store=new AtomStore(join(out,'atoms.sqlite')),state=createSqliteFederationState(join(out,'queue.sqlite')),fabric=new InstructionFabric({store,bindings,operators:ops});const runtime=createFederationRuntime({state,providers:bindings.map(x=>fabric.provider(x.routeId))});runtime.executor.adapters.set('instruction-atom',fabric.adapter());return {store,state,fabric,runtime};}
let f=open(),t=performance.now();const cold=await executeAtomGraph({...f,graph:graph('cold'),maxParallel:2});const coldMs=performance.now()-t;
assert.equal(digest(cold.root),digest(oracle(make(0,n))));f.state.close();f.store.close();f=open();
t=performance.now();const resume=await executeAtomGraph({...f,graph:graph('cold'),maxParallel:2});const resumeMs=performance.now()-t;assert.equal(resume.executions,0);
t=performance.now();const warm=await executeAtomGraph({...f,graph:graph('warm'),maxParallel:2});const warmMs=performance.now()-t;assert.equal(warm.executions,0);assert.equal(warm.reuses,11);
const deltaDs=structuredClone(ds);deltaDs[0].exceptions=[{index:'7',lane:3,value:'15'}];const delta=await executeAtomGraph({...f,graph:graph('delta',deltaDs),maxParallel:2});
assert.equal(BigInt(delta.root.sum),BigInt(cold.root.sum)+1n);assert.equal(delta.executions,3);assert.equal(delta.reuses,8);
const samples=['0','7','999999999999'].map(i=>{const d=deltaDs.find(d=>BigInt(i)>=BigInt(d.start)&&BigInt(i)<BigInt(d.start)+BigInt(d.count));const v=reconstructCell(d,i);const expected=d.lanes.map((x,l)=>d.exceptions.find(e=>e.index===i&&e.lane===l)?.value??String(BigInt(x.a)*BigInt(i)+BigInt(x.b)));assert.deepEqual(v,expected);return {index:i,values:v};});
assert.throws(()=>decodeRange({...sample,denseValues:[1,2]}),/UNSUPPORTED_DESCRIPTOR/);
const state=f.store.snapshot();assert.equal(state.active,0);const usage=process.resourceUsage();
const receipt={schema:'instruction-generative-contract-example/1',verdict:'PASS_EXACT_AFFINE_SPARSE_CONTRACT_ONLY',startedAt:startTime,finishedAt:new Date().toISOString(),
 logicalCells:String(n),lanes:8,logicalStateValues:String(n*8n),materializedDescriptors:8,materializedGraphNodes:11,maxWorkerThreads:2,
 cold:{elapsedMs:coldMs,graphExecutions:cold.executions,resultDigest:digest(cold.root)},restart:{elapsedMs:resumeMs,newExecutions:resume.executions},warm:{elapsedMs:warmMs,newExecutions:warm.executions,reuses:warm.reuses},
 delta:{executions:delta.executions,reuses:delta.reuses,sumDifference:'1',sourceDescriptorSha256:digest(deltaDs)},reconstruction:samples,
 result:cold.root,leaseState:state,code:{controllerSha256:sha256(readFileSync(new URL('../lib/instruction-fabric.mjs',import.meta.url))),operatorSha256:pinHash,pinMode:'DECLARED_ESM_CLOSURE'},
 resources:{processUserCpuMicroseconds:usage.userCPUTime-usage0.userCPUTime,processSystemCpuMicroseconds:usage.systemCPUTime-usage0.systemCPUTime,maxRssKiB:usage.maxRSS,newRemoteCalls:0,newGpuAllocation:0},
 limitation:'Affine integer positive control plus bounded sparse exceptions only. Finite exhaustive reconstruction is unit-tested; trillion-range result uses exact arithmetic oracle, not a trillion-cell dense execution. Aggregated equal sums do not identify states; full descriptor digests and reconstruction retain distinctions. No claim of historical U64 benchmark reproduction, private kernel deployment, global consensus, physical cores or universal speedup.'};
f.state.close();f.store.close();writeFileSync(join(out,'generative-receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify({verdict:receipt.verdict,logicalCells:receipt.logicalCells,materializedNodes:11,cold:cold.executions,warm:warm.executions,delta:receipt.delta,active:state.active}));
