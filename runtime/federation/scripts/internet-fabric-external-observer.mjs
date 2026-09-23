import fs from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const providers=[
  {id:'railway-cpu-a-live',endpoint:'https://deus-cpu-executor-a-production.up.railway.app'},
  {id:'railway-cpu-b-live',endpoint:'https://deus-cpu-executor-b-production.up.railway.app'},
];

async function probe(provider){
  const out={id:provider.id,endpoint:provider.endpoint,httpReachable:false,computeContract:false,health:null,compute:null};
  for(const [kind,path] of [['health','/health'],['compute','/compute?loops=1000']]){
    const started=Date.now();
    try{
      const response=await fetch(new URL(path,provider.endpoint),{
        method:'GET',
        headers:{accept:'application/json,text/plain','user-agent':'DEUS-Internet-Fabric-Observer/1.0'},
        signal:AbortSignal.timeout(10000),
        redirect:'error',
      });
      const text=await response.text();
      let body=null;
      try{body=text?JSON.parse(text):null;}catch{body={raw:text.slice(0,256)};}
      out[kind]={status:response.status,elapsedMs:Date.now()-started,body};
      if(response.ok) out.httpReachable=true;
      if(kind==='compute' && response.ok && body?.state==='EXECUTED' && Number.isFinite(Number(body?.checksum))) out.computeContract=true;
    }catch(error){
      out[kind]={error:String(error?.message??error),elapsedMs:Date.now()-started};
    }
    await sleep(25);
  }
  out.state=out.computeContract?'COMPUTE_CONTRACT_AVAILABLE':(out.httpReachable?'HTTP_REACHABLE_COMPUTE_CONTRACT_HOLD':'UNREACHABLE');
  return out;
}

const results=[];
for(const provider of providers) results.push(await probe(provider));
const receipt={
  schema:'deus-internet-fabric-external-route-observer/1',
  observedAt:new Date().toISOString(),
  results,
  summary:{
    reachable:results.filter(x=>x.httpReachable).length,
    computeContractAvailable:results.filter(x=>x.computeContract).length,
    held:results.filter(x=>x.httpReachable&&!x.computeContract).length,
    unreachable:results.filter(x=>!x.httpReachable).length,
  },
  verdict:'PASS_ROUTE_STATE_CLASSIFIED',
  truthBoundary:'HTTP_REACHABLE_NE_COMPUTE_CONTRACT__ROUTE_FAILURE_OR_REPURPOSING_NE_TASK_FAILURE__NO_EXTERNAL_COMPUTE_CREDIT_WITHOUT_EXECUTED_CONTRACT_RECEIPT'
};
fs.mkdirSync('.deus/internet-fabric',{recursive:true});
fs.writeFileSync('.deus/internet-fabric/external-route-observer.json',JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt,null,2));
