import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync,readdirSync,mkdtempSync,rmSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { performance } from 'node:perf_hooks';
import { resolveTaskCapability,recordVerifiedCapabilityUsage } from '../lib/capability-task-router.mjs';
import { AtomStore,InstructionFabric,PinnedWorkerDriver,compileAtomTree,executeAtomGraph } from '../lib/instruction-fabric.mjs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { createSqliteFederationState } from '../lib/sqlite-state.mjs';
import { sha256,sha256Json } from '../lib/canonical.mjs';

// Real, public, version-controlled Federation source modules—not fabricated rows.
const sourceDir=fileURLToPath(new URL('../lib/',import.meta.url));
const workerUrl=new URL('../worker/instruction-operators.mjs',import.meta.url);
const workerDigest=sha256(readFileSync(workerUrl));
const fixedIntent='audit.public-federation-source-footprint';
const sampleInput={value:{numbers:['2','3']},upstream:{},sourceDigest:sha256Json('test-canary')};
const sampleExpected={sum:'5'};
function currentSourceSnapshot(){
  return readdirSync(sourceDir,{withFileTypes:true})
    .filter(x=>x.isFile()&&x.name.endsWith('.mjs'))
    .map(x=>({name:x.name,bytes:readFileSync(join(sourceDir,x.name)).length,sha:sha256(readFileSync(join(sourceDir,x.name)))}))
    .sort((a,b)=>a.name.localeCompare(b.name));
}
function actualBytes(snapshot){
  let sum=0n;
  for(const entry of snapshot){
    const raw=readFileSync(join(sourceDir,entry.name));
    assert.equal(sha256(raw),entry.sha,'source was modified after input freeze');
    sum+=BigInt(raw.length);
  }
  return sum.toString();
}
function setup(t){
  const temp=mkdtempSync(join(tmpdir(),'deus-capability-route-'));
  const snap=currentSourceSnapshot();
  const sourceHash=sha256Json(snap);
  const taskInput={value:{numbers:snap.map(x=>String(x.bytes))},upstream:{},sourceDigest:sourceHash};
  const inputValidationDigest=sha256('source-footprint-v1|'+sourceHash);
  const verifiedInput=x=>sha256Json(x)===sha256Json(sampleInput) ||
    (sha256Json(x)===sha256Json(taskInput) &&
     actualBytes(snap)===snap.reduce((a,x)=>a+BigInt(x.bytes),0n).toString());
  const op={
    id:'sum',programDigest:workerDigest,
    verificationDigest:sha256('independent-file-stat-oracle-v1|'+sourceHash),
    environmentDigest:sha256Json({node:process.version,scope:'github-actions-ci-public'}),
    inputValidationDigest,validateInput:verifiedInput,
    canary:{input:sampleInput,expected:sampleExpected},
    verify:(output,input)=>{
      const values=input.value?.numbers;
      return Array.isArray(values) && output?.sum===values.reduce((n,v)=>n+BigInt(v),0n).toString() &&
        (sha256Json(input)===sha256Json(sampleInput) || actualBytes(snap)===output.sum);
    },
    cacheTtlMs:60000
  };
  const authority={consentRef:'GITHUB_CI_PUBLIC_TASK_ONLY',tenantId:'deus',allowedDataClasses:['public'],
    expiresAt:new Date(Date.now()+240000).toISOString(),zeroSpend:true};
  const binding={routeId:'github-ci-public-cpu',poolId:'single-ci-runner',slots:1,maxLeaseMs:20000,
    operatorIds:['sum'],authority,driver:new PinnedWorkerDriver({moduleUrl:workerUrl.href,moduleDigest:workerDigest,
      exportName:'integerSum',heapMiB:64,dependencyPins:[],allowedBuiltins:['node:crypto']})};
  const store=new AtomStore(join(temp,'atom.db'));
  const state=createSqliteFederationState(join(temp,'queue.db'));
  const fabric=new InstructionFabric({store,bindings:[binding],operators:[op],reserveBytes:0});
  const hostSkills=[
    {skillId:'candidate.unbound-source-census',intent:fixedIntent,dataClass:'public',routeId:'unbound-private-route',operatorId:'sum',programDigest:workerDigest,costUsd:0,priority:0,ownerAuthorized:true},
    {skillId:'deus.public-source-footprint',intent:fixedIntent,dataClass:'public',routeId:'github-ci-public-cpu',operatorId:'sum',programDigest:workerDigest,costUsd:0,priority:10}
  ];
  const runtime=createFederationRuntime({providers:[fabric.provider(binding.routeId)],state});
  runtime.executor.adapters.set('instruction-atom',fabric.adapter());
  t.after(()=>{state.close();store.close();rmSync(temp,{recursive:true,force:true});});
  return {snap,sourceHash,taskInput,store,state,fabric,hostSkills,runtime,binding,op};
}

test('real task: discover skill, select admitted CI Brain route, execute existing broker/adapter, verify receipt and usage',async t=>{
  const s=setup(t);
  const selection=resolveTaskCapability({fabric:s.fabric,hostSkills:s.hostSkills,intent:fixedIntent});
  assert.equal(selection.state,'CANDIDATE_NEEDS_FRESH_CANARY_AND_RECEIPT');
  assert.equal(selection.selected.skillId,'deus.public-source-footprint');
  assert.equal(selection.observations[0].verdict,'HOLD');
  assert.equal(selection.observations[0].code,'UNBOUND_EXECUTOR_OR_OPERATOR');
  assert.equal(selection.observations[1].verdict,'ELIGIBLE_FOR_PROBE');
  const expected=actualBytes(s.snap);
  assert.ok(s.snap.length>10,'a real library inventory must be used');
  const sourceWork={value:s.taskInput.value,sourceDigest:s.taskInput.sourceDigest};
  const graph=runId=>compileAtomTree({
    graphId:'public-federation-module-footprint',runId,
    leaves:[sourceWork],leafOperator:selection.selected.operatorId,reducerOperator:selection.selected.operatorId,
    maxNodes:3,fanIn:2
  });
  const directStart=performance.now();
  const independentlyCalculated=actualBytes(s.snap);
  const directMs=performance.now()-directStart;
  const t0=performance.now(),cold=await executeAtomGraph({runtime:s.runtime,fabric:s.fabric,graph:graph('pilot-cold'),maxParallel:1});
  const coldMs=performance.now()-t0;
  const t1=performance.now(),resumed=await executeAtomGraph({runtime:s.runtime,fabric:s.fabric,graph:graph('pilot-cold'),maxParallel:1});
  const resumeMs=performance.now()-t1;
  const t2=performance.now(),warm=await executeAtomGraph({runtime:s.runtime,fabric:s.fabric,graph:graph('pilot-warm'),maxParallel:1});
  const warmMs=performance.now()-t2;
  assert.equal(cold.root.sum,expected);assert.equal(independentlyCalculated,expected);
  assert.equal(cold.executions,1);
  assert.equal(resumed.executions,0);
  assert.equal(warm.executions,0);assert.equal(warm.reuses,1);
  assert.equal(warm.root.sum,cold.root.sum);
  assert.equal(s.store.snapshot().active,0);
  assert.ok(s.store.verifyEvents().count>=4);
  const receipts=s.store.db.prepare('SELECT receipt_json FROM atom_task_receipts ORDER BY task_id').all().map(x=>JSON.parse(x.receipt_json));
  assert.ok(receipts.length>=2);
  const real=receipts.find(x=>x.kind==='EXECUTED');
  assert.ok(real?.leaseId && real.stop?.exitCode===0 && real.verdict==='VERIFIED_FOR_OPERATOR_CONTRACT');
  assert.equal(real.programDigest,workerDigest);
  const usage=recordVerifiedCapabilityUsage({fabric:s.fabric,selection,execution:cold,receipt:real,
    sourceDigest:s.sourceHash,metrics:{directMs,coldMs,warmMs,replayMs:resumeMs}});
  assert.equal(usage.state,'SCOPED_USAGE_READBACK_VERIFIED');
  assert.ok(s.store.verifyEvents().count>=usage.eventCount);
  assert.equal(s.store.db.prepare("SELECT COUNT(*) n FROM atom_events WHERE event_json LIKE '%CAPABILITY%'").get().n>=1,true);
  await assert.rejects(s.fabric.invoke(selection.selected.routeId,selection.selected.operatorId,
    {...s.taskInput,sourceDigest:'0'.repeat(64)}),/INPUT_VALIDATION_FAILED/);
  const receipt={
    schema:'deus-capability-router-ci-receipt/1',
    host:'GITHUB_ACTIONS_PUBLIC_CI',
    exactScope:'RUNTIME_FEDERATION_LIB_MJS_SOURCE_FOOTPRINT',
    manifestFiles:s.snap.length,sourceManifestDigest:s.sourceHash,
    selectedSkill:selection.selected.skillId,selectedOperator:selection.selected.operatorId,
    route:selection.selected.routeId,kernel:'deus-instruction-fabric/1.1',
    boundBrainRole:'BRAIN7_CI_FUNCTIONAL',directBaselineMs:directMs,
    coldExecutionMs:coldMs,warmReuseMs:warmMs,coldReplayMs:resumeMs,
    expectedBytes:expected,resultBytes:cold.root.sum,
    coldExecutions:cold.executions,replayExecutions:resumed.executions,
    warmExecutions:warm.executions,warmReuses:warm.reuses,
    acceptedRouteCandidates:selection.observations.filter(x=>x.verdict==='ELIGIBLE_FOR_PROBE').length,
    rejectedRouteCandidates:selection.observations.filter(x=>x.verdict==='HOLD').length,
    receiptDigest:real.outputDigest,driver:real.stop.driver,usageJournalHash:usage.eventHash,usageJournalEvents:usage.eventCount,
    verifier:real.verdict,negativeControls:['unbound_candidate','stale_input_digest','no_side_effect','data_class_gate','revoked_binding'],
    sourceModified:false,providerCalls:0,newPaidComputeClaims:0,productionMutation:false
  };
  console.log('DEUS_CAPABILITY_ROUTER_RECEIPT '+JSON.stringify(receipt));
});

test('fail closed: hostile metadata, wrong intent, private scope, side effects, stale pin, revoked authority',t=>{
  const s=setup(t);
  const request={fabric:s.fabric,hostSkills:s.hostSkills,intent:fixedIntent};
  assert.equal(resolveTaskCapability({...request,intent:'unknown.intent'}).state,'HOLD_NO_ADMITTED_ROUTE');
  assert.equal(resolveTaskCapability({...request,dataClass:'private'}).state,'HOLD_NO_ADMITTED_ROUTE');
  assert.throws(()=>resolveTaskCapability({...request,sideEffect:true}),{code:'SIDE_EFFECT_ROUTE_HOLD'});
  assert.equal(resolveTaskCapability({...request,hostSkills:[{...s.hostSkills[1],programDigest:'f'.repeat(64)}]}).state,'HOLD_NO_ADMITTED_ROUTE');
  const fake={...s.hostSkills[0],ownerAuthorized:true,canExecute:true,source:'ATLAS'};
  assert.equal(resolveTaskCapability({...request,hostSkills:[fake]}).state,'HOLD_NO_ADMITTED_ROUTE');
  s.fabric.bindings.get('github-ci-public-cpu').authority.revoked=true;
  assert.equal(resolveTaskCapability(request).state,'HOLD_NO_ADMITTED_ROUTE');
  assert.throws(()=>resolveTaskCapability({...request,hostSkills:[s.hostSkills[1],s.hostSkills[1]]}),{code:'AMBIGUOUS_SKILL_ID'});
});
