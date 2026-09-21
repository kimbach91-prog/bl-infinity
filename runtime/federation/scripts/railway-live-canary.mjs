import fs from 'node:fs';
import { createFederationRuntime } from '../lib/runtime.mjs';
import { TaskGraphBroker } from '../lib/task-graph-broker.mjs';

const railway=JSON.parse(fs.readFileSync(new URL('../config/providers.railway-live.json',import.meta.url),'utf8'));
const localReducer={
  manifestVersion:'bl-cf-provider/v1',
  id:'local-reducer',
  kind:'local',
  status:'enabled',
  capabilities:['compute.echo'],
  authorization:{
    consentRef:'owner-directive:local-reducer:20260921',
    grantor:'owner',
    grantedAt:'2026-09-21T00:00:00.000Z',
    expiresAt:'2027-09-21T00:00:00.000Z',
    allowedDataClasses:['public'],
    allowSideEffects:false,
    maxTaskCostUsd:0
  },
  limits:{maxConcurrency:1,maxCostPerTaskUsd:0,maxExecutionMs:5000},
  telemetry:{trust:1,availability:1,p95LatencyMs:1,costPerUnitUsd:0,inFlight:0},
  dataPolicy:{privateDataAllowed:false,internalDataAllowed:false,retention:'none'},
  regions:['local'],
  dataLocations:['local'],
  tags:['local','reducer']
};

const runtime=createFederationRuntime({
  providers:[...railway,localReducer],
  localHandlers:{
    'compute.echo': async (payload)=>payload,
  },
});
const broker=new TaskGraphBroker({
  graphId:'railway-ab-live-graph',
  dataClass:'public',
  nodes:[
    {id:'railway-a',capability:'compute.railway.loop.a',payload:{loops:50001},tags:['scatter','railway-a']},
    {id:'railway-b',capability:'compute.railway.loop.b',payload:{loops:50002},tags:['scatter','railway-b']},
    {id:'reduce',capability:'compute.echo',deps:['railway-a','railway-b'],payload:{operation:'collect'},tags:['reduce']},
  ],
});

const startedAt=Date.now();
const first=await broker.materializeReady(runtime.orchestrator);
if(first.length!==2) throw new Error(`expected 2 initial graph nodes, got ${first.length}`);

const roots=await Promise.all([
  runtime.orchestrator.runOnce({coordinatorId:'railway-live-coordinator-1'}),
  runtime.orchestrator.runOnce({coordinatorId:'railway-live-coordinator-2'}),
]);
await broker.refresh(runtime.orchestrator);

const unlocked=await broker.materializeReady(runtime.orchestrator);
if(unlocked.length!==1 || unlocked[0].nodeId!=='reduce') throw new Error('reducer did not unlock after both Railway receipts');
const reduced=await runtime.orchestrator.runOnce({coordinatorId:'railway-live-reducer'});
await broker.refresh(runtime.orchestrator);
const snapshot=broker.snapshot();
const endedAt=Date.now();

const rootProviders=roots.map((r)=>r?.execution?.providerId).filter(Boolean).sort();
const expectedProviders=['railway-cpu-a-live','railway-cpu-b-live'].sort();
if(JSON.stringify(rootProviders)!==JSON.stringify(expectedProviders)) {
  throw new Error(`unexpected root providers: ${JSON.stringify(rootProviders)}`);
}
if(snapshot.verdict!=='SUCCEEDED') throw new Error(`graph verdict ${snapshot.verdict}`);
const reduceState=snapshot.states.reduce;
if(!reduceState?.result?.upstream?.['railway-a'] || !reduceState?.result?.upstream?.['railway-b']) {
  throw new Error('reducer output missing upstream Railway results');
}

const receipt={
  schema:'deus-federation-railway-ab-task-graph-canary/1',
  verdict:'PASS',
  startedAt,
  endedAt,
  elapsedMs:endedAt-startedAt,
  initialMaterialized:first,
  rootExecutions:roots.map((r)=>({
    taskId:r?.job?.id,
    providerId:r?.execution?.providerId,
    measuredLatencyMs:r?.execution?.measuredLatencyMs,
    result:r?.execution?.result,
    attempts:r?.execution?.attempts,
  })),
  reducerExecution:{
    taskId:reduced?.job?.id,
    providerId:reduced?.execution?.providerId,
    result:reduced?.execution?.result,
  },
  graph:snapshot,
  truthBoundary:'TASK_GRAPH_BROKER_EXECUTED_TWO_LIVE_RAILWAY_LOGICAL_EXECUTORS_PLUS_LOCAL_REDUCER__SAME_RAILWAY_PROVIDER_FAILURE_DOMAIN__BOUNDED_PUBLIC_LOOP_CAPABILITY'
};
console.log(JSON.stringify(receipt,null,2));
