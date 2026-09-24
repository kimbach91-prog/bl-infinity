import fs from 'node:fs';
import { createHash } from 'node:crypto';

const OUT='.deus/global-internet-semantic-reducer/v1';
fs.mkdirSync(OUT,{recursive:true});
const sha=x=>createHash('sha256').update(x).digest('hex');
const UA={'user-agent':'DEUS-Internet-Semantic-Reducer/1.0','accept':'application/json,text/plain,text/html,*/*'};
const generatedAt=new Date().toISOString();

const TARGETS=[
  {id:'ROOT_SERVERS',class:'DNS_ROOT',url:'https://root-servers.org/',kind:'root_html'},
  {id:'RIPE_RIS_PEERS',class:'ROUTING_BGP',url:'https://stat.ripe.net/data/ris-peers/data.json',kind:'ris_json'},
  {id:'RIPE_ATLAS_PROBES_SAMPLE',class:'MEASUREMENT',url:'https://atlas.ripe.net/api/v2/probes/?page_size=25',kind:'atlas_probes'},
  {id:'RIPE_ATLAS_HOME',class:'MEASUREMENT',url:'https://atlas.ripe.net/',kind:'atlas_home'},
  {id:'AKASH_PROVIDER_API',class:'COMPUTE_MARKET',url:'https://console-api.akash.network/v1/providers',kind:'akash'},
  {id:'AIHORDE_PERFORMANCE',class:'COMPUTE_MARKET',url:'https://aihorde.net/api/v2/status/performance',kind:'aihorde'},
  {id:'RIR_AFRINIC',class:'NUMBERING_RIR',url:'https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest',kind:'afrinic'},
];

function stable(v){
  if(Array.isArray(v)) return v.map(stable);
  if(v && typeof v==='object') return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));
  return v;
}
function scalarSnapshot(o,limit=64){
  if(!o || typeof o!=='object') return {};
  return Object.fromEntries(Object.entries(o).filter(([,v])=>['string','number','boolean'].includes(typeof v)||v===null).slice(0,limit));
}
function parseRoot(text){
  const instances=[...text.matchAll(/Instances:\s*(\d+)/gi)].map(m=>Number(m[1]));
  const statuses=[...text.matchAll(/Status:\s*(operational|suspended|decommissioned)/gi)].map(m=>m[1].toLowerCase());
  const siteSummaries=[...text.matchAll(/Sites:\s*(\d+),\s*Operational:\s*(\d+),\s*Suspended:\s*(\d+),\s*Decommissioned:\s*(\d+)/gi)]
    .map(m=>({sites:+m[1],operational:+m[2],suspended:+m[3],decommissioned:+m[4]}));
  return {
    kind:'DNS_ROOT_PUBLIC_SITE_SEMANTICS',
    siteSummaryCount:siteSummaries.length,
    summedListedSites:siteSummaries.reduce((n,x)=>n+x.sites,0),
    summedOperationalSites:siteSummaries.reduce((n,x)=>n+x.operational,0),
    statusLineCounts:Object.fromEntries(['operational','suspended','decommissioned'].map(s=>[s,statuses.filter(x=>x===s).length])),
    instanceLineCount:instances.length,
    summedInstancesFromVisibleLocationEntries:instances.reduce((a,b)=>a+b,0),
    note:'Presentation-derived current public site/location semantics only; does not create execution authority.'
  };
}
function parseRis(obj){
  const data=obj?.data??obj;
  const peers=data?.peers;
  let collectors=0,peerRecords=0,uniqueAsns=new Set(),uniqueIps=new Set();
  if(Array.isArray(peers)){
    peerRecords=peers.length;
    for(const p of peers){ if(p?.asn!=null) uniqueAsns.add(String(p.asn)); if(p?.ip) uniqueIps.add(String(p.ip)); }
  } else if(peers && typeof peers==='object'){
    collectors=Object.keys(peers).length;
    for(const val of Object.values(peers)){
      const arr=Array.isArray(val)?val:(val&&typeof val==='object'?Object.values(val):[]);
      for(const p of arr){
        peerRecords++;
        if(p&&typeof p==='object'){ if(p.asn!=null) uniqueAsns.add(String(p.asn)); if(p.ip) uniqueIps.add(String(p.ip)); }
      }
    }
  }
  return {kind:'RIPE_RIS_PEER_DIRECTORY',collectors,peerRecords,uniquePeerAsns:uniqueAsns.size,uniquePeerIps:uniqueIps.size,topLevelKeys:Object.keys(data||{}).sort(),note:'Peer-directory observation metadata; not route liveness or compute authority.'};
}
function parseAtlasProbes(obj){
  const results=Array.isArray(obj?.results)?obj.results:[];
  const statuses={}; const countries=new Set(); const asns4=new Set(); const asns6=new Set();
  for(const p of results){
    const s=String(p?.status?.name??p?.status?.id??'UNKNOWN'); statuses[s]=(statuses[s]||0)+1;
    if(p?.country_code) countries.add(p.country_code);
    if(p?.asn_v4!=null) asns4.add(String(p.asn_v4));
    if(p?.asn_v6!=null) asns6.add(String(p.asn_v6));
  }
  return {kind:'RIPE_ATLAS_PUBLIC_PROBE_PAGE',reportedCount:Number(obj?.count??0),sampleSize:results.length,statusCounts:statuses,sampleCountries:countries.size,sampleAsnV4:asns4.size,sampleAsnV6:asns6.size,hasNext:Boolean(obj?.next),note:'Bounded public API page; total count is source-reported. No control of probes is inferred.'};
}
function parseAtlasHome(text){
  return {kind:'RIPE_ATLAS_PRESENTATION_SURFACE',titleMatch:/RIPE Atlas/i.test(text),bytes:Buffer.byteLength(text),note:'Presentation surface only; authoritative member semantics come from the public API.'};
}
function parseAkash(obj){
  const arr=Array.isArray(obj)?obj:(Array.isArray(obj?.providers)?obj.providers:(Array.isArray(obj?.data)?obj.data:[]));
  let online=0,gpuTagged=0; const owners=new Set();
  for(const p of arr){
    if(p?.owner) owners.add(String(p.owner));
    if(p?.isOnline===true || p?.online===true || p?.status==='online') online++;
    const gm=p?.gpuModels??p?.gpu_models??p?.attributes?.gpuModels;
    if(Array.isArray(gm)&&gm.length) gpuTagged++;
  }
  return {kind:'AKASH_PUBLIC_PROVIDER_CATALOG',providerRecords:arr.length,uniqueOwners:owners.size,onlineFlagged:online,gpuModelTagged:gpuTagged,topLevelKeys:Object.keys(obj||{}).sort().slice(0,64),note:'Public catalog/offer metadata only; no lease, execution or current compute admission inferred.'};
}
function parseAiHorde(obj){
  return {kind:'AIHORDE_PUBLIC_PERFORMANCE_SNAPSHOT',scalars:scalarSnapshot(obj),topLevelKeys:Object.keys(obj||{}).sort(),note:'Dynamic public performance snapshot only; no worker control or guaranteed capacity inferred.'};
}
function parseAfrinic(text){
  const lines=text.split(/\r?\n/).filter(Boolean);
  const records={ipv4:0,ipv6:0,asn:0}; const statuses={}; let dataRows=0;
  for(const line of lines){
    if(line.startsWith('#')) continue;
    const p=line.split('|');
    if(p.length<7 || p[0].toLowerCase()!=='afrinic' || p[1]==='*') continue;
    const type=(p[2]||'').toLowerCase();
    if(type in records){records[type]++; dataRows++;}
    const st=(p[6]||'').toLowerCase(); if(st) statuses[st]=(statuses[st]||0)+1;
  }
  return {kind:'AFRINIC_DELEGATED_STATS_CORPUS',lineCount:lines.length,dataRows,recordTypeCounts:records,statusCounts:statuses,note:'Registry allocation/delegation records; no address probing, liveness or authority beyond published registry semantics.'};
}

async function readTarget(t){
  const started=Date.now();
  try{
    const r=await fetch(t.url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(30000)});
    const b=Buffer.from(await r.arrayBuffer());
    const text=b.toString('utf8');
    let projection;
    if(t.kind==='root_html') projection=parseRoot(text);
    else if(t.kind==='atlas_home') projection=parseAtlasHome(text);
    else if(t.kind==='afrinic') projection=parseAfrinic(text);
    else {
      const obj=JSON.parse(text);
      if(t.kind==='ris_json') projection=parseRis(obj);
      else if(t.kind==='atlas_probes') projection=parseAtlasProbes(obj);
      else if(t.kind==='akash') projection=parseAkash(obj);
      else if(t.kind==='aihorde') projection=parseAiHorde(obj);
      else projection={kind:'GENERIC_JSON',topLevelKeys:Object.keys(obj||{}).sort()};
    }
    const projectionStable=stable(projection);
    return {id:t.id,class:t.class,url:t.url,ok:r.ok,status:r.status,finalUrl:r.url,bytes:b.length,sha256:sha(b),etag:r.headers.get('etag'),lastModified:r.headers.get('last-modified'),ms:Date.now()-started,projection:projectionStable,projectionSha256:sha(Buffer.from(JSON.stringify(projectionStable)))};
  }catch(e){
    return {id:t.id,class:t.class,url:t.url,ok:false,status:null,finalUrl:null,bytes:0,sha256:null,ms:Date.now()-started,error:String(e?.message||e),projection:null,projectionSha256:null};
  }
}

const rows=[];
for(const t of TARGETS) rows.push(await readTarget(t));
const reachable=rows.filter(x=>x.ok).length;
const afrinic=rows.find(x=>x.id==='RIR_AFRINIC');
const semanticDigest=sha(Buffer.from(JSON.stringify(rows.map(x=>({id:x.id,projectionSha256:x.projectionSha256,status:x.status,ok:x.ok})))));
const manifest={
  schema:'deus-global-internet-semantic-reducer/1',generatedAt,sources:rows.length,reachable,
  afrinicRecovered:Boolean(afrinic?.ok),semanticDigest,rows,
  truthBoundary:'HASH_CHANGE_NE_SEMANTIC_CHANGE__PUBLIC_CATALOG_NE_EXECUTION_AUTHORITY__PROBE_DIRECTORY_NE_PROBE_CONTROL__REGISTRY_RECORD_NE_LIVE_HOST__SOURCE_RECOVERY_NE_PERSISTENT_AVAILABILITY'
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/semantic.jsonl',rows.map(r=>JSON.stringify(r)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(rows.length!==7) throw new Error('expected 7 semantic targets');
if(reachable<6) throw new Error('semantic coverage gate failed: '+reachable);
if(!afrinic?.ok) throw new Error('AFRINIC recovery not verified');
if(!rows.every(r=>!r.ok || Boolean(r.projectionSha256))) throw new Error('missing semantic projection digest');
console.log(JSON.stringify({verdict:'PASS',sources:rows.length,reachable,afrinicRecovered:manifest.afrinicRecovered,semanticDigest,digest:manifest.digest,summary:Object.fromEntries(rows.map(r=>[r.id,{ok:r.ok,status:r.status,projection:r.projection}]))}));
