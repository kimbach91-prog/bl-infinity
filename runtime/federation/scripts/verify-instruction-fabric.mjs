/** Bounded, reproducible integration workload. Never contacts source IPs. */
import assert from 'node:assert/strict';
import { readFileSync,writeFileSync,mkdirSync,realpathSync } from 'node:fs';
import { resolve,join,dirname,basename } from 'node:path';
import { cpus,availableParallelism,totalmem } from 'node:os';
import { createHash } from 'node:crypto';
import { AtomStore,InstructionFabric,PinnedWorkerDriver,compileAtomTree,executeAtomGraph,lowerAtomGraph } from '../lib/instruction-fabric.mjs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { createSqliteFederationState } from '../lib/sqlite-state.mjs';
import { sha256,sha256Json,canonicalize } from '../lib/canonical.mjs';
const args=process.argv.slice(2),arg=k=>{const i=args.indexOf(k);return i<0?null:args[i+1];};
const out=resolve(arg('--out')??'.deus/instruction-verification');mkdirSync(out,{recursive:true});
const cas=join(out,'cas');mkdirSync(cas,{recursive:true});
const inputPath=arg('--input');const inputBytes=inputPath?readFileSync(inputPath):null;
const rows=inputBytes?JSON.parse(inputBytes):Array.from({length:16000},(_,i)=>({source:'SYNTHETIC_'+(i%4),prefix:`10.${Math.floor(i/256)%256}.${i%256}.0/24`,tag:'fixture-'+i}));
assert(Array.isArray(rows)&&rows.length>0&&rows.length<=250000);
const started=new Date().toISOString();const usageBefore=process.resourceUsage();
// Independent controller reference, separate from the worker implementation.
function reference(items){const bySource=Object.fromEntries([...new Set(items.map(x=>x.source))].sort().map(s=>[s,items.filter(x=>x.source===s).length]));
 const ipv6=items.filter(x=>x.prefix.includes(':')).length;
 const sum=items.map(x=>BigInt('0x'+createHash('sha256').update(canonicalize(x)).digest('hex'))).reduce((a,b)=>(a+b)%(1n<<256n),0n);
 return {schema:'atlas-range-summary/1',count:items.length,ipv4:items.length-ipv6,ipv6,bySource,contentSum256:sum.toString(16).padStart(64,'0'),classification:'PUBLISHED_DATA_NOT_EXECUTION_AUTHORITY'};}
function combine(input){const v=Object.values(input.upstream);const bySource={};let sum=0n;
 for(const x of v){for(const [s,n]of Object.entries(x.bySource))bySource[s]=(bySource[s]??0)+n;sum=(sum+BigInt('0x'+x.contentSum256))%(1n<<256n);}
 return {schema:'atlas-range-summary/1',count:v.reduce((a,x)=>a+x.count,0),ipv4:v.reduce((a,x)=>a+x.ipv4,0),ipv6:v.reduce((a,x)=>a+x.ipv6,0),bySource,contentSum256:sum.toString(16).padStart(64,'0'),classification:'PUBLISHED_DATA_NOT_EXECUTION_AUTHORITY'};}
function blob(part){const raw=Buffer.from(JSON.stringify(part));const hash=sha256(raw),p=join(cas,hash+'.json');writeFileSync(p,raw);return {value:{blobPath:p,blobSha256:hash},sourceDigest:hash};}
const leaves=[];for(let i=0;i<rows.length;i+=8000)leaves.push(blob(rows.slice(i,i+8000)));
const moduleUrl=new URL('../worker/instruction-operators.mjs',import.meta.url).href,moduleDigest=sha256(readFileSync(new URL(moduleUrl)));
const canaryInput={value:{rows:[{source:'CANARY',prefix:'192.0.2.0/24'}]},upstream:{},sourceDigest:null};
const canaryExpected=reference(canaryInput.value.rows);
const validInput=x=>{if(x.value?.rows)return sha256Json(x)===sha256Json(canaryInput);
 const v=x.value;if(!v||!/^\w{64}$/.test(v.blobSha256)||basename(v.blobPath)!==v.blobSha256+'.json')return false;
 return dirname(realpathSync(v.blobPath))===realpathSync(cas)&&sha256(readFileSync(v.blobPath))===v.blobSha256;};
const operators=[{id:'atlas',programDigest:moduleDigest,verificationDigest:sha256(reference.toString()),environmentDigest:sha256Json({node:process.version,program:'atlas-1'}),
 inputValidationDigest:sha256(validInput.toString()),validateInput:validInput,canary:{input:canaryInput,expected:canaryExpected},
 verify:(value,input)=>sha256Json(value)===sha256Json(reference(input.value.rows??JSON.parse(readFileSync(input.value.blobPath))))},
 {id:'reduce-atlas',programDigest:moduleDigest,verificationDigest:sha256(combine.toString()),environmentDigest:sha256Json({node:process.version,program:'atlas-1'}),
 canary:{input:{value:null,sourceDigest:null,upstream:{a:canaryExpected,b:canaryExpected}},expected:combine({upstream:{a:canaryExpected,b:canaryExpected}})},verify:(value,input)=>sha256Json(value)===sha256Json(combine(input))}];
const authority={consentRef:'CURRENT_AUTHORIZED_INVOCATION_PUBLIC_DATA_ONLY',tenantId:'deus',allowedDataClasses:['public'],expiresAt:new Date(Date.now()+300000).toISOString(),zeroSpend:true};
const bindings=operators.map(op=>({routeId:'host-'+op.id,poolId:'same-allocated-host',slots:2,maxLeaseMs:30000,operatorIds:[op.id],authority,
 driver:new PinnedWorkerDriver({dependencyPins:[],allowedBuiltins:['node:crypto','node:fs','node:path'],moduleUrl,moduleDigest,exportName:op.id==='atlas'?'atlasBlobSummary':'reduceAtlas',heapMiB:96})}));
function open(index){const store=new AtomStore(join(out,`atoms-${index}.sqlite`)),state=createSqliteFederationState(join(out,`queue-${index}.sqlite`));
 const fabric=new InstructionFabric({store,bindings,operators}),runtime=createFederationRuntime({providers:bindings.map(b=>fabric.provider(b.routeId)),state});
 runtime.executor.adapters.set('instruction-atom',fabric.adapter());return {store,state,fabric,runtime};}
const serialStart=performance.now(),expected=reference(rows),serialMs=performance.now()-serialStart;
const graph=(runId,ls=leaves)=>compileAtomTree({graphId:'atlas-instruction-acceptance',runId,leaves:ls,leafOperator:'atlas',reducerOperator:'reduce-atlas',fanIn:4});
const results=[];let f;
for(let i=0;i<3;i++){
 f=open(i);const coldGraph=graph('cold-'+i);const plan=lowerAtomGraph(coldGraph,{vcpuEquivalent:2,provenSimultaneousVcpuLowerBound:0,hostRamGiBPortfolio:192/1024,verifiedGpuCount:0,verifiedVramGiB:0});assert.equal(plan.summary.hold,0);
 let t=performance.now();const cold=await executeAtomGraph({...f,graph:coldGraph,maxParallel:2});const coldMs=performance.now()-t;assert.equal(sha256Json(cold.root),sha256Json(expected));
 f.state.close();f.store.close();f=open(i);
 t=performance.now();const resume=await executeAtomGraph({...f,graph:coldGraph,maxParallel:2});const resumeMs=performance.now()-t;assert.equal(resume.executions,0);
 t=performance.now();const warm=await executeAtomGraph({...f,graph:graph('warm-'+i),maxParallel:2});const warmMs=performance.now()-t;
 assert.equal(warm.executions,0);assert.equal(warm.reuses,coldGraph.nodes.length);assert.equal(sha256Json(warm.root),sha256Json(expected));assert.equal(f.store.snapshot().active,0);
 results.push({coldMs,warmMs,resumeMs,coldExecutions:cold.executions,warmExecutions:warm.executions,warmReuses:warm.reuses,resultDigest:sha256Json(warm.root),events:f.store.verifyEvents()});
 if(i<2){f.state.close();f.store.close();}
}
const changedRows=rows.slice(0,8000).map((r,i)=>i? r:{...r,testOnlyRevision:'CONTROLLED_DELTA_FIXTURE'});
const changedLeaves=[blob(changedRows),...leaves.slice(1)];const changedExpected=reference([...changedRows,...rows.slice(8000)]);
const delta=await executeAtomGraph({...f,graph:graph('delta',changedLeaves),maxParallel:2});assert.equal(sha256Json(delta.root),sha256Json(changedExpected));
const depth=graph('shape').metadata.depth;assert.equal(delta.executions,1+depth);assert.equal(delta.executions+delta.reuses,graph('shape').nodes.length);
const classifications=[...new Map(rows.map(r=>[r.source,r])).values()].map(r=>f.fabric.classifyAtlas({type:'cidr',value:r.prefix,source:r.source,ownerAuthorized:true,currentLease:true}));
assert(classifications.every(x=>!x.executionAdmitted&&!x.offerEligible));
const usageAfter=process.resourceUsage(),median=xs=>[...xs].sort((a,b)=>a-b)[Math.floor(xs.length/2)];
const coldMedian=median(results.map(r=>r.coldMs)),warmMedian=median(results.map(r=>r.warmMs));
const receipt={schema:'deus-instruction-fabric-acceptance/1',verdict:'PASS_FOR_SCOPED_INTEGRATION',startedAt:started,finishedAt:new Date().toISOString(),
 source:inputPath?{kind:'REAL_PUBLIC_ATLAS_SNAPSHOT',inputSha256:sha256(inputBytes),rows:rows.length}:{kind:'SYNTHETIC_CI_FIXTURE',rows:rows.length},
 graph:{logicalDomain:'1000000000000',materializedNodes:graph('shape').nodes.length,leafShards:leaves.length,fanIn:4,depth,maxParallelWorkers:2},
 expected,resultDigest:sha256Json(expected),rounds:results,baseline:{directSerialReferenceMs:serialMs,includesInputRead:false},
 matched:{coldMedianMs:coldMedian,warmMedianMs:warmMedian,reuseRatio:coldMedian/warmMedian,scope:'SAME_OUTPUT_AND_CONTRACT_COLD_GRAPH_VS_VERIFIED_REUSE_WITH_RETAINED_STATE; NOT_UNIVERSAL_SPEEDUP'},
 controlledDelta:{newExecutions:delta.executions,reused:delta.reuses,expectedAffectedCone:1+depth,resultDigest:sha256Json(delta.root),realAtlasSourceUnchanged:true},
 resources:{node:process.version,osCpuThreadsVisible:cpus().length,osAvailableParallelism:availableParallelism(),hostMemoryVisibleBytes:totalmem(),maxConcurrentWorkerThreads:2,
 processUserCpuMicroseconds:usageAfter.userCPUTime-usageBefore.userCPUTime,processSystemCpuMicroseconds:usageAfter.systemCPUTime-usageBefore.systemCPUTime,maxRssKiB:usageAfter.maxRSS,
 newGpuAllocation:0,newExternalLease:0,moneySpentByThisScript:0,energyJoules:null},
 classifier:{sourceFamilies:classifications.length,indexOnly:classifications.length,fromAtlasExecutionAdmitted:0},
 finalResourceState:f.store.snapshot(),codePinModes:[...new Set(f.store.db.prepare("SELECT receipt_json FROM atom_leases WHERE receipt_json IS NOT NULL").all().map(x=>JSON.parse(x.receipt_json).codePinMode))],code:{operatorModuleSha256:moduleDigest,controllerSha256:sha256(readFileSync(new URL('../lib/instruction-fabric.mjs',import.meta.url)))},
 limitations:['Two threads are on one allocated host, not two independent physical nodes.','Local SQLite fencing is not cross-host consensus.','No arbitrary provider, GPU or Windows production deployment was performed.','Worker threads are not a sandbox for untrusted code.','Public range data gives no third-party execution permission.','Existing V5 predecessor benchmark and hardware-history scopes are not overwritten.']};
f.state.close();f.store.close();writeFileSync(join(out,'acceptance.json'),JSON.stringify(receipt,null,2));
console.log(JSON.stringify({verdict:receipt.verdict,source:receipt.source,graph:receipt.graph,matched:receipt.matched,controlledDelta:receipt.controlledDelta,resourceLeasesRemaining:receipt.finalResourceState.active,resultDigest:receipt.resultDigest}));
