import fs from 'node:fs';
import { createFederationRuntime } from '../lib/runtime.mjs';

const providers=JSON.parse(fs.readFileSync(new URL('../config/providers.railway-live.json',import.meta.url),'utf8'));
const runtime=createFederationRuntime({providers});
const tasks=[
  {id:'railway-a-canary',capability:'compute.railway.loop.a',payload:{loops:50001},dataClass:'public',estimatedCostUsd:0},
  {id:'railway-b-canary',capability:'compute.railway.loop.b',payload:{loops:50002},dataClass:'public',estimatedCostUsd:0},
];
const startedAt=Date.now();
const results=await Promise.all(tasks.map((task)=>runtime.executor.execute(task)));
const endedAt=Date.now();
const receipt={
  schema:'deus-federation-railway-ab-live-canary/1',
  verdict:results.every((r)=>r?.result?.state==='EXECUTED')?'PASS':'FAIL',
  startedAt,
  endedAt,
  elapsedMs:endedAt-startedAt,
  results:results.map((r)=>({
    taskId:r.taskId,
    providerId:r.providerId,
    measuredLatencyMs:r.measuredLatencyMs,
    result:r.result,
    attempts:r.attempts,
  })),
  truthBoundary:'TWO_PUBLIC_RAILWAY_LOGICAL_EXECUTORS__SAME_PROVIDER_FAILURE_DOMAIN__BOUNDED_LOOP_CAPABILITY_ONLY'
};
console.log(JSON.stringify(receipt,null,2));
if(receipt.verdict!=='PASS') process.exit(1);
