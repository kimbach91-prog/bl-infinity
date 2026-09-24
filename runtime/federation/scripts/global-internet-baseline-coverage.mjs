import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const OUT='.deus/global-internet-baseline/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Internet-Baseline/1.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

const SOURCES=[
  // Numbering / RIR delegated statistics.
  {id:'RIR_APNIC',class:'NUMBERING_RIR',url:'https://ftp.apnic.net/stats/apnic/delegated-apnic-latest',kind:'RIR_DELEGATED'},
  {id:'RIR_RIPE',class:'NUMBERING_RIR',url:'https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest',kind:'RIR_DELEGATED'},
  {id:'RIR_ARIN',class:'NUMBERING_RIR',url:'https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest',kind:'RIR_DELEGATED'},
  {id:'RIR_LACNIC',class:'NUMBERING_RIR',url:'https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest',kind:'RIR_DELEGATED'},
  {id:'RIR_AFRINIC',class:'NUMBERING_RIR',url:'https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest',kind:'RIR_DELEGATED'},

  // DNS / root system.
  {id:'DNS_ROOT_ZONE',class:'DNS_ROOT',url:'https://www.internic.net/domain/root.zone',kind:'ROOT_ZONE'},
  {id:'DNS_ROOT_HINTS',class:'DNS_ROOT',url:'https://www.internic.net/domain/named.root',kind:'ROOT_HINTS'},
  {id:'ROOT_SERVERS',class:'DNS_ROOT',url:'https://root-servers.org/',kind:'ROOT_SERVER_DIRECTORY'},

  // Routing / BGP / peering.
  {id:'RIPE_RIS_PEERS',class:'ROUTING_BGP',url:'https://stat.ripe.net/data/ris-peers/data.json',kind:'RIS_PUBLIC_API'},
  {id:'ROUTEVIEWS',class:'ROUTING_BGP',url:'https://www.routeviews.org/routeviews/',kind:'ROUTEVIEWS_DIRECTORY'},
  {id:'BGPSTREAM',class:'ROUTING_BGP',url:'https://bgpstream.caida.org/',kind:'BGPSTREAM_PUBLIC'},
  {id:'PEERINGDB_NET_SAMPLE',class:'IX_PEERING',url:'https://www.peeringdb.com/api/net?limit=1',kind:'PEERINGDB_API'},
  {id:'PEERINGDB_IX_SAMPLE',class:'IX_PEERING',url:'https://www.peeringdb.com/api/ix?limit=1',kind:'PEERINGDB_API'},

  // Web corpus / public graph.
  {id:'COMMONCRAWL_COLLECTIONS',class:'WEB_CORPUS',url:'https://index.commoncrawl.org/collinfo.json',kind:'COMMONCRAWL_INDEX'},
  {id:'COMMONCRAWL_HOME',class:'WEB_CORPUS',url:'https://commoncrawl.org/',kind:'COMMONCRAWL_ROOT'},

  // PKI / Certificate Transparency.
  {id:'CHROME_CT_LOG_LIST',class:'CT_PKI',url:'https://www.gstatic.com/ct/log_list/v3/log_list.json',kind:'CT_LOG_LIST'},
  {id:'CABFORUM',class:'CT_PKI',url:'https://cabforum.org/',kind:'PKI_GOVERNANCE_ROOT'},

  // Cloud/CDN/public infrastructure address catalogs.
  {id:'AWS_IP_RANGES',class:'CLOUD_RANGES',url:'https://ip-ranges.amazonaws.com/ip-ranges.json',kind:'IP_PREFIX_CATALOG'},
  {id:'GOOGLE_CLOUD_RANGES',class:'CLOUD_RANGES',url:'https://www.gstatic.com/ipranges/cloud.json',kind:'IP_PREFIX_CATALOG'},
  {id:'GOOGLE_GLOBAL_RANGES',class:'CLOUD_RANGES',url:'https://www.gstatic.com/ipranges/goog.json',kind:'IP_PREFIX_CATALOG'},
  {id:'CLOUDFLARE_IPS',class:'CLOUD_RANGES',url:'https://api.cloudflare.com/client/v4/ips',kind:'IP_PREFIX_CATALOG'},
  {id:'GITHUB_META',class:'CLOUD_RANGES',url:'https://api.github.com/meta',kind:'IP_PREFIX_CATALOG'},
  {id:'FASTLY_PUBLIC_IPS',class:'CLOUD_RANGES',url:'https://api.fastly.com/public-ip-list',kind:'IP_PREFIX_CATALOG'},

  // Measurement / observability.
  {id:'RIPE_ATLAS_PROBES_SAMPLE',class:'MEASUREMENT',url:'https://atlas.ripe.net/api/v2/probes/?page_size=1',kind:'RIPE_ATLAS_API'},
  {id:'RIPE_ATLAS_HOME',class:'MEASUREMENT',url:'https://atlas.ripe.net/',kind:'MEASUREMENT_ROOT'},
  {id:'CAIDA_DATASETS',class:'MEASUREMENT',url:'https://www.caida.org/catalog/datasets/',kind:'MEASUREMENT_CATALOG'},

  // Compute/provider layer already established.
  {id:'AKASH_PROVIDER_API',class:'COMPUTE_MARKET',url:'https://console-api.akash.network/v1/providers',kind:'COMPUTE_MARKET_API'},
  {id:'AIHORDE_PERFORMANCE',class:'COMPUTE_MARKET',url:'https://aihorde.net/api/v2/status/performance',kind:'PUBLIC_COMPUTE_API'},
  {id:'BOINC_PROJECTS',class:'COMPUTE_MARKET',url:'https://boinc.berkeley.edu/projects.php',kind:'VOLUNTEER_COMPUTE_DIRECTORY'},
];

async function fetchSource(s){
  const t=Date.now();
  try{
    const r=await fetch(s.url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(25000)});
    const b=Buffer.from(await r.arrayBuffer());
    return {...s,ok:r.ok,status:r.status,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,contentType:r.headers.get('content-type'),body:b};
  }catch(e){
    return {...s,ok:false,status:null,finalUrl:null,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};
  }
}
const bi=x=>{try{return BigInt(x)}catch{return 0n}};
function ipv4Cardinality(cidr){
  const p=Number(String(cidr).split('/')[1]);
  return Number.isFinite(p)&&p>=0&&p<=32 ? 2n**BigInt(32-p) : 0n;
}
function ipv6Cardinality(cidr){
  const p=Number(String(cidr).split('/')[1]);
  return Number.isFinite(p)&&p>=0&&p<=128 ? 2n**BigInt(128-p) : 0n;
}
function safeJson(b){try{return JSON.parse(b.toString('utf8'))}catch{return null}}

const results=[];
const descriptors=[];
for(const s of SOURCES){
  const r=await fetchSource(s);
  results.push({...r,body:undefined});
  const d={
    id:s.id,class:s.class,kind:s.kind,url:s.url,ok:r.ok,status:r.status,bytes:r.bytes,sha256:r.sha256,ms:r.ms,
    descriptor:{},truthBoundary:'SOURCE_READ_NE_COMPLETE_WORLD_STATE__DESCRIPTOR_NE_EXECUTION_AUTHORITY'
  };
  if(r.ok&&r.body){
    const txt=r.body.toString('utf8');
    if(s.kind==='RIR_DELEGATED'){
      let ipv4=0n,ipv6=0n,asn=0n,records=0;
      for(const line of txt.split(/\r?\n/)){
        if(!line||line.startsWith('#')) continue;
        const p=line.split('|');
        if(p.length<7) continue;
        const type=p[2],value=p[4],count=p[5],status=p[6];
        if(status==='summary') continue;
        records++;
        if(type==='ipv4') ipv4+=bi(count);
        else if(type==='ipv6'){
          const prefix=Number(count);
          if(Number.isFinite(prefix)&&prefix>=0&&prefix<=128) ipv6+=2n**BigInt(128-prefix);
        } else if(type==='asn') asn+=bi(count);
      }
      d.descriptor={records,ipv4Addresses:ipv4.toString(),ipv6Addresses:ipv6.toString(),asnCount:asn.toString()};
    } else if(s.id==='DNS_ROOT_ZONE'){
      const rr=txt.split(/\r?\n/).filter(x=>x&&!x.startsWith(';'));
      d.descriptor={resourceRecords:rr.length,tlds:[...new Set(rr.map(x=>x.trim().split(/\s+/)[0]).filter(x=>x.endsWith('.')).map(x=>x.slice(0,-1)).filter(x=>!x.includes('.')))].length};
    } else if(s.id==='DNS_ROOT_HINTS'){
      d.descriptor={lines:txt.split(/\r?\n/).filter(Boolean).length,rootServerLabels:[...new Set((txt.match(/[A-M]\.ROOT-SERVERS\.NET\./gi)||[]).map(x=>x.toUpperCase()))].length};
    } else if(s.id==='COMMONCRAWL_COLLECTIONS'){
      const j=safeJson(r.body); d.descriptor={collections:Array.isArray(j)?j.length:0,latest:Array.isArray(j)&&j[0]?j[0].id??null:null};
    } else if(s.id==='CHROME_CT_LOG_LIST'){
      const j=safeJson(r.body); const ops=j?.operators||[]; const logs=ops.flatMap(x=>x.logs||[]);
      d.descriptor={operators:ops.length,logs:logs.length};
    } else if(s.id==='AWS_IP_RANGES'){
      const j=safeJson(r.body); const v4=j?.prefixes||[],v6=j?.ipv6_prefixes||[];
      d.descriptor={ipv4Prefixes:v4.length,ipv6Prefixes:v6.length,ipv4Addresses:v4.reduce((a,x)=>a+ipv4Cardinality(x.ip_prefix),0n).toString(),ipv6Addresses:v6.reduce((a,x)=>a+ipv6Cardinality(x.ipv6_prefix),0n).toString()};
    } else if(s.id==='GOOGLE_CLOUD_RANGES'||s.id==='GOOGLE_GLOBAL_RANGES'){
      const j=safeJson(r.body); const arr=j?.prefixes||[]; let v4=0,v6=0,a4=0n,a6=0n;
      for(const x of arr){if(x.ipv4Prefix){v4++;a4+=ipv4Cardinality(x.ipv4Prefix)} if(x.ipv6Prefix){v6++;a6+=ipv6Cardinality(x.ipv6Prefix)}}
      d.descriptor={ipv4Prefixes:v4,ipv6Prefixes:v6,ipv4Addresses:a4.toString(),ipv6Addresses:a6.toString()};
    } else if(s.id==='CLOUDFLARE_IPS'){
      const j=safeJson(r.body); const v4=j?.result?.ipv4_cidrs||[],v6=j?.result?.ipv6_cidrs||[];
      d.descriptor={ipv4Prefixes:v4.length,ipv6Prefixes:v6.length,ipv4Addresses:v4.reduce((a,x)=>a+ipv4Cardinality(x),0n).toString(),ipv6Addresses:v6.reduce((a,x)=>a+ipv6Cardinality(x),0n).toString()};
    } else if(s.id==='GITHUB_META'){
      const j=safeJson(r.body)||{}; const keys=['hooks','web','api','git','packages','pages','actions','actions_macos'];
      d.descriptor={categories:keys.filter(k=>Array.isArray(j[k])).length,prefixEntries:keys.reduce((n,k)=>n+(Array.isArray(j[k])?j[k].length:0),0)};
    } else if(s.id==='FASTLY_PUBLIC_IPS'){
      const j=safeJson(r.body)||{}; d.descriptor={ipv4Prefixes:(j.addresses||[]).length,ipv6Prefixes:(j.ipv6_addresses||[]).length};
    } else if(s.id==='RIPE_ATLAS_PROBES_SAMPLE'){
      const j=safeJson(r.body)||{}; d.descriptor={count:j.count??null,next:Boolean(j.next),sampleResults:Array.isArray(j.results)?j.results.length:0};
    } else if(s.id==='RIPE_RIS_PEERS'){
      const j=safeJson(r.body)||{}; const peers=j?.data?.peers||j?.data?.peer_count??null; d.descriptor={peerDataType:Array.isArray(peers)?'array':typeof peers,peerCount:Array.isArray(peers)?peers.length:(typeof peers==='number'?peers:null)};
    } else if(s.id==='PEERINGDB_NET_SAMPLE'||s.id==='PEERINGDB_IX_SAMPLE'){
      const j=safeJson(r.body)||{}; d.descriptor={sampleRecords:Array.isArray(j.data)?j.data.length:0,meta:j.meta??null};
    } else if(s.id==='AKASH_PROVIDER_API'){
      const j=safeJson(r.body); const p=Array.isArray(j)?j:(j?.providers||j?.data||[]); d.descriptor={providers:Array.isArray(p)?p.length:0,online:Array.isArray(p)?p.filter(x=>x?.isOnline===true).length:0};
    } else if(s.id==='AIHORDE_PERFORMANCE'){
      const j=safeJson(r.body)||{}; d.descriptor={workerCount:j.worker_count??null,textWorkerCount:j.text_worker_count??null,queuedRequests:j.queued_requests??null,textThreads:j.text_threads??null,imageThreads:j.image_threads??null};
    } else {
      d.descriptor={contentType:r.contentType??null,bytes:r.bytes};
    }
  }
  descriptors.push(d);
}

const liveClasses=[...new Set(descriptors.filter(x=>x.ok).map(x=>x.class))];
const allClasses=[...new Set(SOURCES.map(x=>x.class))];
const registry=registerParticipationBatch(descriptors.map(d=>({
  type:'service',value:'internet-baseline:'+d.id,evidenceClass:d.ok?'DATA_ONLY':'UNKNOWN',authorityClass:'UNKNOWN',
  serviceHint:true,computeHint:d.class==='COMPUTE_MARKET',
  source:'GLOBAL_INTERNET_BASELINE_V1',sourceEvidenceRef:d.url,observedAt:new Date().toISOString(),
  freshnessState:d.ok?'FRESH_SOURCE':'SOURCE_HOLD',
  metadata:{class:d.class,kind:d.kind,ok:d.ok,status:d.status,descriptor:d.descriptor},
})));

const manifest={
  schema:'deus-global-internet-baseline-coverage/1',
  generatedAt:new Date().toISOString(),
  sources:SOURCES.length,
  liveSources:descriptors.filter(x=>x.ok).length,
  heldSources:descriptors.filter(x=>!x.ok).length,
  classes:allClasses,
  liveClasses,
  classCoverage:{covered:liveClasses.length,total:allClasses.length},
  registry:registry.counts,
  batchDigest:registry.batchDigest,
  descriptors,
  truthBoundary:'BASELINE_COVERAGE_NE_OMNISCIENCE__PUBLIC_DATASET_NE_HOST_CONTROL__ADDRESS_SPACE_NE_OBSERVED_DEVICE__REGISTRATION_NE_EXECUTION_AUTHORITY',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/descriptors.jsonl',descriptors.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(liveClasses.length<7) throw new Error('Need at least 7 baseline classes live, got '+liveClasses.length);
if(descriptors.filter(x=>x.ok).length<20) throw new Error('Need at least 20 public source roots live');
if(registry.counts.executionAdmitted!==0) throw new Error('Baseline mapping must not admit execution');

console.log(JSON.stringify({verdict:'PASS',sources:manifest.sources,liveSources:manifest.liveSources,heldSources:manifest.heldSources,classCoverage:manifest.classCoverage,classes:manifest.liveClasses,registry:manifest.registry,digest:manifest.digest}));
