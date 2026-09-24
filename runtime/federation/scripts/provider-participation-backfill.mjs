import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { registerParticipationIdentity, registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const OUT='.deus/provider-participation-backfill/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Provider-Participation-Backfill/1.0','accept':'application/json,text/plain,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function get(url){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,signal:AbortSignal.timeout(20000)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:true,url,status:r.status,bytes:b.length,sha256:sha(b),ms:Date.now()-t,body:b};
  }catch(e){return {ok:false,url,error:String(e?.message||e),ms:Date.now()-t};}
}
function j(r){try{return JSON.parse(r.body.toString('utf8'));}catch{return null;}}
const records=[],receipts=[];

// Akash opt-in marketplace providers.
const ak=await get('https://console-api.akash.network/v1/providers');
receipts.push({...ak,body:undefined,source:'AKASH_PROVIDERS'});
if(ak.ok){
  const data=j(ak);
  const providers=Array.isArray(data)?data:(Array.isArray(data?.providers)?data.providers:(Array.isArray(data?.data)?data.data:[]));
  for(const p of providers){
    const value='akash:provider:'+String(p.owner||p.hostUri||p.name||'unknown');
    records.push({
      type:'service',value,evidenceClass:'PUBLIC_SERVICE',authorityClass:'OPT_IN_MARKET',
      optIn:true,computeHint:true,serviceHint:true,source:'AKASH_PUBLIC_PROVIDER_API',
      sourceEvidenceRef:'https://console-api.akash.network/v1/providers',
      observedAt:new Date().toISOString(),freshnessState:p.isOnline===true?'FRESH_SOURCE_ONLINE':'SOURCE_OBSERVED',
      metadata:{name:p.name??null,owner:p.owner??null,hostUri:p.hostUri??null,isOnline:p.isOnline===true,lastCheckDate:p.lastCheckDate??null,gpuModels:p.gpuModels??[],stats:p.stats??null},
    });
  }
}

// AI Horde public-intended inference/model services.
const hp=await get('https://aihorde.net/api/v2/status/performance');
const hm=await get('https://aihorde.net/api/v2/status/models');
receipts.push({...hp,body:undefined,source:'AIHORDE_PERFORMANCE'},{...hm,body:undefined,source:'AIHORDE_MODELS'});
if(hm.ok){
  const models=j(hm);
  for(const m of (Array.isArray(models)?models:[])){
    const model=String(m.name||m.model||'unknown');
    records.push({
      type:'service',value:'aihorde:model:'+model,evidenceClass:'PUBLIC_SERVICE',
      authorityClass:'PUBLIC_SERVICE_INTENDED',publicIntended:true,computeHint:true,serviceHint:true,
      source:'AI_HORDE_PUBLIC_STATUS_API',sourceEvidenceRef:'https://aihorde.net/api/v2/status/models',
      observedAt:new Date().toISOString(),freshnessState:'FRESH_SOURCE',
      metadata:{model,performance:m.performance??null,queued:m.queued??null,jobs:m.jobs??null},
    });
  }
}

// Global provider/API roots. Registration only: not capacity, not connected-account authority.
const providerRoots=[
  ['RUNPOD','https://api.runpod.io/graphql','GPU_CLOUD_API'],
  ['VAST_AI','https://cloud.vast.ai/api/v1/bundles/','GPU_MARKET_API'],
  ['HF_JOBS','https://huggingface.co/api/jobs','JOBS_API'],
  ['SALAD','https://api.salad.com/','CONTAINER_GPU_API'],
  ['IO_NET','https://cloud.io.net/','GPU_NETWORK_API'],
  ['REPLICATE','https://api.replicate.com/v1/','MODEL_API'],
  ['GROQ','https://api.groq.com/openai/v1/','INFERENCE_API'],
  ['MODAL','https://modal.com/','SERVERLESS_COMPUTE'],
  ['TOGETHER_AI','https://api.together.xyz/v1/','MODEL_API'],
  ['FIREWORKS_AI','https://api.fireworks.ai/inference/v1/','MODEL_API'],
  ['CEREBRAS','https://api.cerebras.ai/v1/','INFERENCE_API'],
  ['LAMBDA_CLOUD','https://cloud.lambdalabs.com/api/v1/','GPU_CLOUD_API'],
  ['FLY_IO','https://api.machines.dev/v1/','MACHINES_API'],
  ['RENDER','https://api.render.com/v1/','CLOUD_API'],
  ['GOOGLE_CLOUD_RUN','https://run.googleapis.com/','SERVERLESS_API'],
  ['CLOUDFLARE_WORKERS','https://api.cloudflare.com/client/v4/','EDGE_COMPUTE_API'],
  ['AWS_BATCH','https://batch.amazonaws.com/','BATCH_COMPUTE_API'],
  ['AZURE_CONTAINER_APPS','https://management.azure.com/','CONTAINER_COMPUTE_API'],
  ['RAILWAY','https://railway.app/','CONNECTED_PLATFORM_SOURCE'],
  ['VERCEL','https://vercel.com/','CONNECTED_PLATFORM_SOURCE'],
  ['GITHUB_ACTIONS','https://api.github.com/','CONNECTED_PLATFORM_SOURCE'],
  ['GOLEM','https://api.stats.golem.network/','OPT_IN_MARKET_SOURCE'],
  ['BOINC','https://boinc.berkeley.edu/projects.php','VOLUNTEER_PROJECT_SOURCE'],
  ['BACALHAU','https://www.bacalhau.org/','DISTRIBUTED_COMPUTE_SOURCE'],
];
for(const [provider,url,capability] of providerRoots){
  records.push({
    type:'service',value:'provider-root:'+provider,evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',
    computeHint:true,serviceHint:true,source:'OFFICIAL_PROVIDER_SOURCE_ROOT',sourceEvidenceRef:url,
    observedAt:new Date().toISOString(),freshnessState:'SOURCE_MAPPED',
    metadata:{provider,url,capability,offerState:'AUTH_OR_CONTRACT_REQUIRED_UNLESS_SEPARATELY_CONNECTED'},
  });
}

const batch=registerParticipationBatch(records);
const registrations=batch.registrations;
const bySource={};
const byClass={};
for(const r of registrations){
  bySource[r.source]=(bySource[r.source]??0)+1;
  byClass[r.participationClass]=(byClass[r.participationClass]??0)+1;
}
const akash=registrations.filter(x=>x.source==='AKASH_PUBLIC_PROVIDER_API');
const horde=registrations.filter(x=>x.source==='AI_HORDE_PUBLIC_STATUS_API');
const roots=registrations.filter(x=>x.source==='OFFICIAL_PROVIDER_SOURCE_ROOT');
const manifest={
  schema:'deus-provider-participation-backfill/1',
  generatedAt:new Date().toISOString(),
  counts:batch.counts,
  bySource,byClass,
  akash:{registered:akash.length,offerEligible:akash.filter(x=>x.offerEligible).length,online:akash.filter(x=>x.metadata?.isOnline===true).length},
  aiHorde:{registered:horde.length,offerEligible:horde.filter(x=>x.offerEligible).length},
  providerRoots:{registered:roots.length,indexOnly:roots.filter(x=>!x.offerEligible).length},
  sourceReceipts:receipts,
  batchDigest:batch.batchDigest,
  truthBoundary:'REGISTRY_BACKFILL_NE_ACTIVE_CAPACITY__OFFER_ELIGIBLE_NE_LEASE__PROVIDER_ROOT_NE_CONNECTED_ACCOUNT__EXECUTION_REQUIRES_CURRENT_ACCORD_LEASE',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/registrations.jsonl',registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
if(!(akash.length>1000)) throw new Error('Akash provider backfill unexpectedly small: '+akash.length);
if(!(horde.length>0)) throw new Error('AI Horde model/service backfill empty');
if(batch.counts.executionAdmitted!==0) throw new Error('Backfill must not mint execution admission');
console.log(JSON.stringify({verdict:'PASS',counts:batch.counts,akash:manifest.akash,aiHorde:manifest.aiHorde,providerRoots:manifest.providerRoots,digest:manifest.digest}));
