import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/global-market-telemetry/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Market-Telemetry/1.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function get(url,{timeout=20000}={}){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-started,contentType:r.headers.get('content-type'),body:b};
  }catch(e){
    return {ok:false,url,error:String(e?.message||e),ms:Date.now()-started};
  }
}
function j(r){try{return JSON.parse(r.body.toString('utf8'));}catch{return null;}}
function bi(v){try{return BigInt(v??0);}catch{return 0n;}}
function sum(arr,fn){let x=0n;for(const v of arr)x+=bi(fn(v));return x;}
function reg(type,value,meta={}){
  const p=projectInternetIdentityHierarchical({type,value});
  return {resourceKey:p.resourceKey,supercellId:p.supercellId,microcellId:p.microcellId,value:p.value,...meta};
}

const receipts=[];
const markets=[];

// Akash public, no-auth provider telemetry.
const ak=await get('https://console-api.akash.network/v1/providers');
receipts.push({...ak,body:undefined,source:'AKASH_PROVIDERS'});
{
  const data=ak.ok?j(ak):null;
  const providers=Array.isArray(data)?data:(Array.isArray(data?.providers)?data.providers:(Array.isArray(data?.data)?data.data:[]));
  const online=providers.filter(x=>x?.isOnline===true);
  const gpuAvailable=sum(online,x=>x?.stats?.gpu?.available);
  const gpuTotal=sum(online,x=>x?.stats?.gpu?.total);
  const cpuAvailable=sum(online,x=>x?.stats?.cpu?.available);
  const cpuTotal=sum(online,x=>x?.stats?.cpu?.total);
  const memAvailable=sum(online,x=>x?.stats?.memory?.available);
  const memTotal=sum(online,x=>x?.stats?.memory?.total);
  if(providers.length){
    const providerRecords=providers.map(x=>reg('service','akash:'+String(x.owner||x.hostUri||x.name||'unknown'),{
      provider:'AKASH',name:x.name??null,owner:x.owner??null,hostUri:x.hostUri??null,isOnline:x.isOnline===true,
      lastCheckDate:x.lastCheckDate??null,gpuModels:x.gpuModels??[],stats:x.stats??null,
      authorityClass:'OPT_IN_MARKET',offerEligible:true,executionAdmitted:false,
      truthBoundary:'PUBLIC_PROVIDER_TELEMETRY_NE_LEASE_NE_EXECUTION_AUTHORITY'
    }));
    fs.writeFileSync(OUT+'/akash-providers.jsonl',providerRecords.map(x=>JSON.stringify(x)).join('\n')+'\n');
  }
  markets.push({
    market:'AKASH',class:'PUBLIC_NOAUTH_MARKET_TELEMETRY',sourceOk:ak.ok,sourceStatus:ak.ok?'LIVE_TELEMETRY':'HOLD_SOURCE_UNREACHABLE',
    providers:providers.length,onlineProviders:online.length,
    cpuAvailable:cpuAvailable.toString(),cpuTotal:cpuTotal.toString(),gpuAvailable:gpuAvailable.toString(),gpuTotal:gpuTotal.toString(),
    memoryAvailableBytes:memAvailable.toString(),memoryTotalBytes:memTotal.toString(),
    source:'https://console-api.akash.network/v1/providers',
    offerState:ak.ok?'OFFER_ELIGIBLE_MARKET':'HOLD_SOURCE_UNREACHABLE',spendState:'NO_SPEND',
    sourceError:ak.ok?null:ak.error??('HTTP '+String(ak.status??'unknown')),
  });
}

// Golem public stats.
const golemEndpoints={
  online:'https://api.stats.golem.network/v1/network/online',
  stats:'https://api.stats.golem.network/v1/network/online/stats',
  median:'https://api.stats.golem.network/v1/network/pricing/median',
  average:'https://api.stats.golem.network/v1/network/pricing/average',
  computing:'https://api.stats.golem.network/v1/network/computing'
};
const gr={}, golemSourceState={};
for(const [k,u] of Object.entries(golemEndpoints)){
  const r=await get(u); receipts.push({...r,body:undefined,source:'GOLEM_'+k.toUpperCase()}); gr[k]=r.ok?j(r):null; golemSourceState[k]={ok:r.ok,status:r.status??null,error:r.error??null};
}
{
  const providers=Array.isArray(gr.online)?gr.online:(Array.isArray(gr.online?.data)?gr.online.data:[]);
  if(providers.length){
    const providerRecords=providers.map(x=>reg('service','golem:'+String(x.node_id||x?.data?.id||'unknown'),{
      provider:'GOLEM',nodeId:x.node_id??x?.data?.id??null,online:x.online===true,updatedAt:x.updated_at??null,
      cpuCores:x?.data?.['golem.inf.cpu.cores']??null,cpuThreads:x?.data?.['golem.inf.cpu.threads']??null,
      memoryGiB:x?.data?.['golem.inf.mem.gib']??null,storageGiB:x?.data?.['golem.inf.storage.gib']??null,
      pricingCoeffs:x?.data?.['golem.com.pricing.model.linear.coeffs']??null,
      authorityClass:'OPT_IN_MARKET',offerEligible:true,executionAdmitted:false,
      truthBoundary:'PUBLIC_PROVIDER_STATS_NE_MARKET_AGREEMENT_NE_EXECUTION_AUTHORITY'
    }));
    fs.writeFileSync(OUT+'/golem-providers.jsonl',providerRecords.map(x=>JSON.stringify(x)).join('\n')+'\n');
  }
  const live=Object.values(golemSourceState).some(x=>x.ok);
  markets.push({
    market:'GOLEM',class:'PUBLIC_NOAUTH_MARKET_TELEMETRY',sourceOk:live,sourceStatus:live?'LIVE_TELEMETRY':'HOLD_SOURCE_UNREACHABLE',
    onlineProviders:providers.length,networkStats:gr.stats,pricingMedian:gr.median,pricingAverage:gr.average,providersComputing:gr.computing,
    source:golemEndpoints.online,sourceState:golemSourceState,
    offerState:live?'OFFER_ELIGIBLE_MARKET':'HOLD_SOURCE_UNREACHABLE',spendState:'NO_SPEND'
  });
}

// AI Horde public performance/model telemetry.
const hPerf=await get('https://aihorde.net/api/v2/status/performance');
const hModels=await get('https://aihorde.net/api/v2/status/models');
receipts.push({...hPerf,body:undefined,source:'AIHORDE_PERFORMANCE'},{...hModels,body:undefined,source:'AIHORDE_MODELS'});
const perf=hPerf.ok?j(hPerf):null, models=hModels.ok?j(hModels):null;
{
  const modelList=Array.isArray(models)?models:[];
  if(modelList.length){
    fs.writeFileSync(OUT+'/aihorde-models.jsonl',modelList.map(x=>JSON.stringify(reg('service','aihorde:model:'+String(x.name||x.model||'unknown'),{
      provider:'AI_HORDE',model:x.name??x.model??null,performance:x.performance??null,queued:x.queued??null,jobs:x.jobs??null,
      authorityClass:'PUBLIC_SERVICE_INTENDED',offerEligible:true,executionAdmitted:false,
      truthBoundary:'PUBLIC_MODEL_AVAILABILITY_NE_EXECUTION_RECEIPT'
    }))).join('\n')+'\n');
  }
  const live=hPerf.ok||hModels.ok;
  markets.push({
    market:'AI_HORDE',class:'PUBLIC_INTENDED_SERVICE_TELEMETRY',sourceOk:live,sourceStatus:live?'LIVE_TELEMETRY':'HOLD_SOURCE_UNREACHABLE',
    performance:perf,models:modelList.length,
    source:'https://aihorde.net/api/v2/status/performance',
    offerState:live?'OFFER_ELIGIBLE_PUBLIC_SERVICE':'HOLD_SOURCE_UNREACHABLE',spendState:'NO_SPEND',
    sourceState:{performance:{ok:hPerf.ok,status:hPerf.status??null,error:hPerf.error??null},models:{ok:hModels.ok,status:hModels.status??null,error:hModels.error??null}}
  });
}

// BOINC official project directory = volunteer compute participation frontier, not capacity.
const boinc=await get('https://boinc.berkeley.edu/projects.php');
receipts.push({...boinc,body:undefined,source:'BOINC_PROJECT_DIRECTORY'});
if(boinc.ok){
  const html=boinc.body.toString('utf8');
  const projectLinks=[...html.matchAll(/href="([^"]+)"[^>]*>([^<]+)<\/a>/gi)]
    .map(m=>({href:m[1],label:m[2].replace(/\s+/g,' ').trim()}))
    .filter(x=>x.label && !x.href.startsWith('#'));
  markets.push({
    market:'BOINC',class:'OPT_IN_VOLUNTEER_DIRECTORY',directoryReadable:true,linkCandidates:projectLinks.length,
    source:'https://boinc.berkeley.edu/projects.php',offerState:'OFFER_ELIGIBLE_VOLUNTEER_PROJECTS',spendState:'NO_SPEND',
    truthBoundary:'PROJECT_DIRECTORY_NE_AVAILABLE_VOLUNTEER_CAPACITY_NE_RIGHT_TO_SUBMIT_ARBITRARY_WORK'
  });
}

// Auth-required or account-scoped markets: mapped, not queried for paid capacity.
const authRequired=[
  {market:'RUNPOD',api:'https://api.runpod.io/graphql',auth:'BEARER_API_KEY'},
  {market:'VAST',api:'https://cloud.vast.ai/api/v1/bundles/',auth:'BEARER_API_KEY'},
  {market:'HF_JOBS',api:'https://huggingface.co/api/jobs',auth:'BEARER_TOKEN'},
  {market:'SALAD',api:'https://api.salad.com/',auth:'ACCOUNT_TOKEN'},
  {market:'IO_NET',api:'https://cloud.io.net/',auth:'ACCOUNT_OR_API_AUTH'},
];
for(const x of authRequired) markets.push({...x,class:'AUTH_REQUIRED_OFFER_SOURCE',offerState:'HOLD_AUTH_OR_SPEND',spendState:'NO_SPEND'});

const manifest={
  schema:'deus-global-market-telemetry/1',
  generatedAt:new Date().toISOString(),
  markets,
  sourceReceipts:receipts,
  summary:{
    markets:markets.length,
    publicNoAuth:markets.filter(x=>x.class==='PUBLIC_NOAUTH_MARKET_TELEMETRY'||x.class==='PUBLIC_INTENDED_SERVICE_TELEMETRY'||x.class==='OPT_IN_VOLUNTEER_DIRECTORY').length,
    authRequired:markets.filter(x=>x.class==='AUTH_REQUIRED_OFFER_SOURCE').length,
  },
  decision:'TELEMETRY_ONLY',
  next:'Feed offer-eligible public/opt-in provider identities into Participation Registry; create task-specific Accord offers only when cost/terms/authority are known.',
  truthBoundary:'PUBLIC_TELEMETRY_NE_RESERVED_CAPACITY__PROVIDER_LIST_NE_LEASE__PRICE_DATA_NE_PROFIT__AUTH_REQUIRED_MARKET_NE_PERMISSION_TO_SPEND',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/markets.jsonl',markets.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

const livePublic=markets.filter(x=>['AKASH','GOLEM','AI_HORDE'].includes(x.market)&&x.sourceOk===true);
if(livePublic.length===0){
  console.error(JSON.stringify({markets:markets.map(x=>({market:x.market,sourceOk:x.sourceOk,sourceStatus:x.sourceStatus,offerState:x.offerState})),receipts}));
  throw new Error('No live public telemetry market available');
}
console.log(JSON.stringify({verdict:'PASS',summary:manifest.summary,digest:manifest.digest,livePublic:livePublic.length,markets:markets.map(x=>({market:x.market,class:x.class,sourceOk:x.sourceOk??null,providers:x.providers??x.onlineProviders??null,models:x.models??null,offerState:x.offerState}))}));
