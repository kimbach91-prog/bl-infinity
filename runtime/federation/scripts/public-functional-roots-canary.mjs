import fs from 'node:fs';
import { compileCapabilityAtlas, compileInternetFabricPlan } from '../lib/internet-functional-fabric.mjs';

const catalog=JSON.parse(fs.readFileSync(new URL('../config/internet-capability-catalog.v2.json',import.meta.url),'utf8'));
const atlas=compileCapabilityAtlas(catalog.resources);

async function getJson(id,url,headers={}){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:{accept:'application/json',...headers},signal:AbortSignal.timeout(12000),redirect:'error'});
    const text=await r.text();
    let body=null; try{body=text?JSON.parse(text):null;}catch{body={raw:text.slice(0,160)}}
    return {id,ok:r.ok,status:r.status,elapsedMs:Date.now()-started,body};
  }catch(error){return {id,ok:false,error:String(error?.message??error),elapsedMs:Date.now()-started};}
}

const probes=[];
probes.push(await getJson('google-dns','https://dns.google/resolve?name=example.com&type=A'));
probes.push(await getJson('cloudflare-doh','https://cloudflare-dns.com/dns-query?name=example.com&type=A',{'accept':'application/dns-json'}));
probes.push(await getJson('commoncrawl-collinfo','https://index.commoncrawl.org/collinfo.json'));
probes.push(await getJson('routeviews-collectors','https://api.routeviews.org/meta/collectors'));

const plan=compileInternetFabricPlan({
  taskId:'JOB-DEUS-INTERNET-CAPABILITY-ATLAS-V2-CANARY-20260923',
  logicalUnits:'1000000000000',
  resourceVector:{vcpuEquivalent:48,provenSimultaneousVcpuLowerBound:28,hostRamGiBPortfolio:125,verifiedGpuCount:1,verifiedVramGiB:6,opaqueInferenceSlots:0,functionalRoots:14},
  resources:catalog.resources,
  operators:[
    {id:'resolve',capability:'net.dns.resolve',logicalWorkUnits:'100000000000',requireIndependent:true,maxRoutes:3},
    {id:'routing',capability:'net.bgp.observe',logicalWorkUnits:'1000000',maxRoutes:3},
    {id:'corpus',capability:'web.corpus.index.lookup',logicalWorkUnits:'1000000',maxRoutes:2},
    {id:'model-catalog',capability:'ai.model.catalog',logicalWorkUnits:'10000',maxRoutes:2}
  ],
  maxHotRoutes:16,
  maxPhysicalShards:64,
  metadata:{catalogSchema:catalog.schema,activationPolicy:catalog.activationPolicy}
});
const receipt={
  schema:'deus-internet-capability-atlas-v2-canary/1',
  observedAt:new Date().toISOString(),
  atlasDigest:atlas.atlasDigest,
  atlasSummary:atlas.summary,
  probes,
  probePass:probes.filter(x=>x.ok).length,
  probeTotal:probes.length,
  planDigest:plan.planDigest,
  planSummary:plan.summary,
  selectedResourceIds:plan.selectedResourceIds,
  heldAuthResources:catalog.resources.filter(x=>x.state==='HOLD').map(x=>x.id),
  verdict:probes.filter(x=>x.ok).length>=3 && plan.summary.heldOperators===0?'PASS':'HOLD',
  truthBoundary:'BOUNDED_DOCUMENTED_PUBLIC_ENDPOINT_CANARY__NO_BULK_SCRAPE__NO_OPEN_RESOLVER_HARVEST__NO_AUTH_OR_RATE_LIMIT_BYPASS__AI_APIS_WITHOUT_BOUND_AUTH_STAY_HOLD'
};
fs.mkdirSync('.deus/internet-fabric',{recursive:true});
fs.writeFileSync('.deus/internet-fabric/capability-atlas-v2-receipt.json',JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt,null,2));
