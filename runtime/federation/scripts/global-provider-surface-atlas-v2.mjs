import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const PROVIDERS=[["GITHUB_ACTIONS","https://docs.github.com/actions","CI_COMPUTE","CONNECTED_OR_AUTH_REQUIRED"],["RAILWAY","https://docs.railway.com/","APP_RUNTIME","CONNECTED_OR_AUTH_REQUIRED"],["VERCEL","https://vercel.com/docs","SERVERLESS_EDGE","CONNECTED_OR_AUTH_REQUIRED"],["HF_JOBS","https://huggingface.co/docs/huggingface_hub/guides/jobs","JOBS_COMPUTE","AUTH_REQUIRED"],["AKASH","https://akash.network/docs/","OPT_IN_MARKET","PUBLIC_MARKET"],["AI_HORDE","https://aihorde.net/","VOLUNTEER_AI","PUBLIC_SERVICE"],["GOLEM","https://docs.golem.network/","OPT_IN_MARKET","PUBLIC_MARKET"],["BOINC","https://boinc.berkeley.edu/","VOLUNTEER_COMPUTE","PUBLIC_PROJECT_NETWORK"],["BACALHAU","https://docs.bacalhau.org/","DISTRIBUTED_COMPUTE","PUBLIC_OR_NODE_PARTICIPATION"],["RUNPOD","https://docs.runpod.io/","GPU_CLOUD","AUTH_REQUIRED"],["VAST_AI","https://docs.vast.ai/","GPU_MARKET","AUTH_REQUIRED"],["SALAD","https://docs.salad.com/","DISTRIBUTED_GPU","AUTH_REQUIRED"],["IO_NET","https://docs.io.net/","GPU_NETWORK","AUTH_REQUIRED"],["REPLICATE","https://replicate.com/docs","MODEL_INFERENCE_TRAINING","AUTH_REQUIRED"],["GROQ","https://console.groq.com/docs","INFERENCE_ACCELERATOR","AUTH_REQUIRED"],["MODAL","https://modal.com/docs","SERVERLESS_CPU_GPU","AUTH_REQUIRED"],["TOGETHER_AI","https://docs.together.ai/","INFERENCE_TRAINING","AUTH_REQUIRED"],["FIREWORKS_AI","https://docs.fireworks.ai/","INFERENCE_FINE_TUNING","AUTH_REQUIRED"],["CEREBRAS","https://inference-docs.cerebras.ai/","INFERENCE_ACCELERATOR","AUTH_REQUIRED"],["LAMBDA_CLOUD","https://docs.lambda.ai/","GPU_CLOUD","AUTH_REQUIRED"],["FLY_IO","https://fly.io/docs/machines/api/","MACHINES_API","AUTH_REQUIRED"],["RENDER","https://api-docs.render.com/","APP_RUNTIME","AUTH_REQUIRED"],["GOOGLE_CLOUD_RUN","https://cloud.google.com/run/docs","SERVERLESS_CONTAINER","AUTH_REQUIRED"],["GOOGLE_VERTEX_AI","https://cloud.google.com/vertex-ai/docs","AI_TRAINING_INFERENCE","AUTH_REQUIRED"],["CLOUDFLARE_WORKERS","https://developers.cloudflare.com/workers/","EDGE_COMPUTE","AUTH_REQUIRED"],["AWS_BATCH","https://docs.aws.amazon.com/batch/","BATCH_COMPUTE","AUTH_REQUIRED"],["AWS_LAMBDA","https://docs.aws.amazon.com/lambda/","SERVERLESS_COMPUTE","AUTH_REQUIRED"],["AZURE_CONTAINER_APPS","https://learn.microsoft.com/azure/container-apps/","CONTAINER_COMPUTE","AUTH_REQUIRED"],["AZURE_ML","https://learn.microsoft.com/azure/machine-learning/","AI_TRAINING_INFERENCE","AUTH_REQUIRED"],["OCI_FUNCTIONS","https://docs.oracle.com/en-us/iaas/Content/Functions/home.htm","SERVERLESS_COMPUTE","AUTH_REQUIRED"],["OCI_CONTAINER_INSTANCES","https://docs.oracle.com/en-us/iaas/Content/container-instances/home.htm","CONTAINER_COMPUTE","AUTH_REQUIRED"],["IBM_CODE_ENGINE","https://cloud.ibm.com/docs/codeengine","SERVERLESS_CONTAINER","AUTH_REQUIRED"],["DIGITALOCEAN_FUNCTIONS","https://docs.digitalocean.com/products/functions/","SERVERLESS_COMPUTE","AUTH_REQUIRED"],["COREWEAVE","https://docs.coreweave.com/","GPU_CLOUD","AUTH_REQUIRED"],["CRUSOE_CLOUD","https://docs.crusoecloud.com/","GPU_CLOUD","AUTH_REQUIRED"],["VULTR","https://docs.vultr.com/","CLOUD_GPU","AUTH_REQUIRED"],["TENSORDOCK","https://docs.tensordock.com/","GPU_MARKET","AUTH_REQUIRED"],["FAL_AI","https://docs.fal.ai/","MODEL_INFERENCE","AUTH_REQUIRED"],["BASETEN","https://docs.baseten.co/","MODEL_SERVING","AUTH_REQUIRED"],["ANYSCALE","https://docs.anyscale.com/","DISTRIBUTED_AI","AUTH_REQUIRED"],["NVIDIA_NIM","https://docs.nvidia.com/nim/","INFERENCE_CONTAINERS","AUTH_REQUIRED"]];
const OUT='.deus/global-provider-surface-atlas/v2';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Provider-Atlas/2.0','accept':'text/html,application/json,text/plain,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function probe([provider,url,capability,access]){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(12000)});
    const b=Buffer.from(await r.arrayBuffer());
    const sourceReachable=r.status<500 && r.status!==404;
    return {provider,url,capability,access,sourceReachable,status:r.status,finalUrl:r.url,contentType:r.headers.get('content-type'),bytes:b.length,sha256:sha(b),ms:Date.now()-started,error:null};
  }catch(e){
    return {provider,url,capability,access,sourceReachable:false,status:null,finalUrl:null,contentType:null,bytes:0,sha256:null,ms:Date.now()-started,error:String(e?.message||e)};
  }
}
const results=[];
for(const p of PROVIDERS) results.push(await probe(p));

const registryInputs=results.map(x=>({
  type:'service',
  value:'provider-surface:'+x.provider,
  evidenceClass:x.sourceReachable?'DATA_ONLY':'UNKNOWN',
  authorityClass:'UNKNOWN',
  computeHint:true,
  serviceHint:true,
  source:'GLOBAL_PROVIDER_SURFACE_ATLAS_V2',
  sourceEvidenceRef:x.url,
  observedAt:new Date().toISOString(),
  freshnessState:x.sourceReachable?'SOURCE_REACHABLE':'SOURCE_HOLD',
  metadata:{
    provider:x.provider,capability:x.capability,access:x.access,
    sourceReachable:x.sourceReachable,status:x.status,finalUrl:x.finalUrl,
    offerState:x.access==='PUBLIC_MARKET'||x.access==='PUBLIC_SERVICE'||x.access==='PUBLIC_PROJECT_NETWORK'||x.access==='PUBLIC_OR_NODE_PARTICIPATION'
      ?'SOURCE_MAPPED_PUBLIC_OR_OPT_IN':'HOLD_AUTH_OR_CONTRACT',
  }
}));
const batch=registerParticipationBatch(registryInputs);
const reachable=results.filter(x=>x.sourceReachable);
const held=results.filter(x=>!x.sourceReachable);
const byAccess={};
const byCapability={};
for(const x of results){
  byAccess[x.access]=(byAccess[x.access]??0)+1;
  byCapability[x.capability]=(byCapability[x.capability]??0)+1;
}
const manifest={
  schema:'deus-global-provider-surface-atlas/2',
  generatedAt:new Date().toISOString(),
  providers:results.length,
  reachable:reachable.length,
  held:held.length,
  byAccess,byCapability,
  registrations:batch.counts,
  batchDigest:batch.batchDigest,
  results,
  truthBoundary:'PROVIDER_SOURCE_REACHABLE_NE_CONNECTED_ACCOUNT__DOCS_NE_OFFER__OFFER_NE_LEASE__NO_SPEND_OR_JOB_CREATION',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/provider-surfaces.jsonl',results.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',batch.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
if(results.length<35) throw new Error('provider atlas unexpectedly small');
if(reachable.length<25) throw new Error('fewer than 25 provider source roots reachable: '+reachable.length);
if(batch.counts.executionAdmitted!==0) throw new Error('provider atlas must not admit execution');
console.log(JSON.stringify({verdict:'PASS',providers:results.length,reachable:reachable.length,held:held.length,registrations:batch.counts,digest:manifest.digest}));
