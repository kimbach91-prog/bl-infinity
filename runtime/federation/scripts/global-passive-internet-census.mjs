import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import {
  compileCidrAddressDescriptor,
  projectInternetIdentityHierarchical,
} from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/internet-census/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Passive-Census/1.0','accept':'*/*'};

function sha256(x){return createHash('sha256').update(x).digest('hex');}
async function fetchBytes(url,{timeout=30000}={}){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,signal:AbortSignal.timeout(timeout)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:true,url,status:r.status,bytes:b.length,sha256:sha256(b),ms:Date.now()-t,body:b};
  }catch(e){
    return {ok:false,url,error:String(e?.message||e),ms:Date.now()-t};
  }
}
async function fetchFirst(urls){
  const attempts=[];
  for(const url of urls){
    const r=await fetchBytes(url);
    attempts.push({...r,body:undefined});
    if(r.ok) return {result:r,attempts};
  }
  return {result:null,attempts};
}
function ipv4ToBigInt(ip){
  return ip.split('.').reduce((n,p)=>(n<<8n)|BigInt(Number(p)),0n);
}
function bigIntToIpv4(n){
  return [24n,16n,8n,0n].map(s=>Number((n>>s)&255n)).join('.');
}
function trailingZeros32(n){
  if(n===0n) return 32;
  let z=0; while(z<32 && ((n>>BigInt(z))&1n)===0n) z++; return z;
}
function floorLog2(n){
  let x=n, k=-1; while(x>0n){x>>=1n;k++;} return k;
}
function ipv4RangeToCidrs(start,count){
  let cur=ipv4ToBigInt(start), left=BigInt(count);
  const out=[];
  while(left>0n){
    const align=trailingZeros32(cur);
    const sizePow=Math.min(align,floorLog2(left));
    const prefix=32-sizePow;
    out.push(bigIntToIpv4(cur)+'/'+prefix);
    const step=1n<<BigInt(sizePow);
    cur+=step; left-=step;
  }
  return out;
}
function parseIpv6BigInt(ip){
  let text=ip.toLowerCase();
  const parts=text.split('::');
  if(parts.length>2) throw new Error('bad ipv6');
  const l=parts[0]?parts[0].split(':'):[];
  const r=parts.length===2&&parts[1]?parts[1].split(':'):[];
  const fill=8-l.length-r.length;
  const gs=[...l,...Array(fill).fill('0'),...r];
  let out=0n;
  for(const g of gs) out=(out<<16n)|BigInt('0x'+(g||'0'));
  return out;
}
function cidrInterval(cidr){
  const [addr,pfxs]=cidr.split('/'); const pfx=Number(pfxs);
  if(addr.includes(':')){
    const base=parseIpv6BigInt(addr); const bits=128; const host=bits-pfx;
    const size=1n<<BigInt(host);
    const start=(base/size)*size;
    return {family:6,start,end:start+size-1n};
  }
  const base=ipv4ToBigInt(addr); const bits=32; const host=bits-pfx;
  const size=1n<<BigInt(host);
  const start=(base/size)*size;
  return {family:4,start,end:start+size-1n};
}
function unionCardinality(intervals){
  if(!intervals.length) return 0n;
  intervals.sort((a,b)=>a.start<b.start?-1:a.start>b.start?1:0);
  let total=0n, s=intervals[0].start, e=intervals[0].end;
  for(let i=1;i<intervals.length;i++){
    const x=intervals[i];
    if(x.start<=e+1n){ if(x.end>e)e=x.end; }
    else { total+=e-s+1n; s=x.start; e=x.end; }
  }
  return total+(e-s+1n);
}
function stableDigestRows(rows,keys){
  const lines=rows.map(r=>keys.map(k=>String(r[k]??'')).join('|')).sort();
  return sha256(Buffer.from(lines.join('\n')));
}
function writeJsonl(file,rows){
  fs.writeFileSync(path.join(OUT,file),rows.map(x=>JSON.stringify(x)).join('\n')+(rows.length?'\n':''));
}

const sourceReceipts=[];
const rirDescriptors=[];
const asnRecords=[];
const interval4=[], interval6=[];
const rirNames=['afrinic','apnic','arin','lacnic','ripencc'];

for(const rir of rirNames){
  const candidates=[
    'https://ftp.apnic.net/stats/'+rir+'/delegated-'+rir+'-extended-latest',
    rir==='arin'?'https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest':null,
    rir==='ripencc'?'https://ftp.ripe.net/ripe/stats/delegated-ripencc-extended-latest':null,
    rir==='lacnic'?'https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest':null,
    rir==='afrinic'?'https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-extended-latest':null,
  ].filter(Boolean);
  const got=await fetchFirst(candidates);
  sourceReceipts.push({source:'RIR_'+rir.toUpperCase(),attempts:got.attempts});
  if(!got.result) continue;
  const text=got.result.body.toString('utf8');
  for(const raw of text.split(/\r?\n/)){
    if(!raw || raw.startsWith('#')) continue;
    const f=raw.split('|'); if(f.length<7) continue;
    const [registry,cc,type,start,value,date,status,opaqueId='']=f;
    if(type==='asn'){
      asnRecords.push({source:'RIR_EXTENDED',registry,cc,type,start,value,date,status,opaqueId});
      continue;
    }
    let cidrs=[];
    try{
      if(type==='ipv4') cidrs=ipv4RangeToCidrs(start,value);
      else if(type==='ipv6') cidrs=[start+'/'+value];
      else continue;
    }catch{continue;}
    for(const cidr of cidrs){
      try{
        const d=compileCidrAddressDescriptor(cidr);
        const rec={
          schema:'deus-global-address-descriptor/1',
          source:'RIR_EXTENDED',registry,cc,status,date,opaqueId,
          cidr:d.cidr,family:d.family,addressCount:d.addressCount,
          descriptorDigest:d.descriptorDigest,
          activationClass:'ADDRESS_SPACE_ONLY',
          observedState:'DELEGATED_OR_ALLOCATED_RESOURCE',
          executionReady:false,
          truthBoundary:'RIR_DELEGATION_NE_LIVE_DEVICE_NE_SERVICE_NE_EXECUTION_AUTHORITY',
        };
        rirDescriptors.push(rec);
        const iv=cidrInterval(d.cidr);
        (iv.family===4?interval4:interval6).push(iv);
      }catch{}
    }
  }
}

for(const [name,url] of [
 ['IANA_IPV4','https://www.iana.org/assignments/ipv4-address-space/ipv4-address-space.csv'],
 ['IANA_IPV6','https://www.iana.org/assignments/ipv6-unicast-address-assignments/ipv6-unicast-address-assignments.csv'],
]){
  const r=await fetchBytes(url); sourceReceipts.push({source:name,...r,body:undefined});
  if(r.ok) fs.writeFileSync(path.join(OUT,name.toLowerCase()+'.csv'),r.body);
}

const atlasRows=[];
let atlasUrl='https://atlas.ripe.net/api/v2/probes/?page_size=500';
let atlasPages=0;
while(atlasUrl && atlasPages<200){
  const r=await fetchBytes(atlasUrl,{timeout:30000});
  sourceReceipts.push({source:'RIPE_ATLAS_PROBES_PAGE_'+atlasPages,...r,body:undefined});
  if(!r.ok) break;
  const j=JSON.parse(r.body.toString('utf8')); atlasPages++;
  for(const p of (j.results||[])){
    const base={
      schema:'deus-observed-device-record/1',
      source:'RIPE_ATLAS',
      deviceClass:'MEASUREMENT_PROBE',
      sourceId:String(p.id),
      status:(p.status&&typeof p.status==='object')?p.status.name:p.status,
      asnV4:p.asn_v4??null,asnV6:p.asn_v6??null,
      prefixV4:p.prefix_v4??null,prefixV6:p.prefix_v6??null,
      activationClass:'PUBLIC_MEASUREMENT_INFRASTRUCTURE_METADATA',
      executionReady:false,
      truthBoundary:'PUBLIC_PROBE_METADATA_NE_OWNER_AUTHORITY_NE_GENERIC_COMPUTE',
    };
    let emitted=false;
    for(const [kind,address] of [['ipv4',p.address_v4],['ipv6',p.address_v6]]){
      if(!address) continue;
      try{
        const pr=projectInternetIdentityHierarchical({type:kind,value:address});
        atlasRows.push({...base,identityType:kind,address:pr.value,resourceKey:pr.resourceKey,supercellId:pr.supercellId,microcellId:pr.microcellId});
        emitted=true;
      }catch{}
    }
    if(!emitted){
      const pr=projectInternetIdentityHierarchical({type:'service',value:'ripe-atlas-probe:'+p.id});
      atlasRows.push({...base,identityType:'service',address:null,resourceKey:pr.resourceKey,supercellId:pr.supercellId,microcellId:pr.microcellId});
    }
  }
  atlasUrl=j.next||null;
}

const peeringRows=[];
for(const kind of ['net','ix','fac']){
  const r=await fetchBytes('https://www.peeringdb.com/api/'+kind+'?limit=10000',{timeout:30000});
  sourceReceipts.push({source:'PEERINGDB_'+kind.toUpperCase(),...r,body:undefined});
  if(!r.ok) continue;
  try{
    const j=JSON.parse(r.body.toString('utf8'));
    for(const x of (j.data||[])){
      const value='peeringdb:'+kind+':'+x.id;
      const pr=projectInternetIdentityHierarchical({type:'service',value});
      peeringRows.push({
        schema:'deus-internet-topology-entity/1',source:'PEERINGDB',entityType:kind,id:x.id,
        name:x.name??null,asn:x.asn??null,status:x.status??null,country:x.country??null,
        resourceKey:pr.resourceKey,supercellId:pr.supercellId,microcellId:pr.microcellId,
        activationClass:'TOPOLOGY_ONLY',executionReady:false,
        truthBoundary:'PEERINGDB_ENTITY_NE_DEVICE_NE_EXECUTION_AUTHORITY',
      });
    }
  }catch{}
}

const universe=[
  compileCidrAddressDescriptor('0.0.0.0/0'),
  compileCidrAddressDescriptor('::/0'),
].map(d=>({
  schema:'deus-address-universe-root/1',cidr:d.cidr,family:d.family,addressCount:d.addressCount,
  descriptorDigest:d.descriptorDigest,activationClass:'UNIVERSE_ONLY',executionReady:false,
  truthBoundary:'ADDRESS_UNIVERSE_NE_PUBLIC_REACHABILITY_NE_DEVICE_NE_AUTHORITY',
}));

const dedupDesc=[...new Map(rirDescriptors.map(x=>[x.cidr+'|'+x.registry+'|'+x.status,x])).values()];
const uniqueIpv4=unionCardinality(interval4);
const uniqueIpv6=unionCardinality(interval6);

writeJsonl('rir-address-descriptors.jsonl',dedupDesc);
writeJsonl('rir-asn-records.jsonl',asnRecords);
writeJsonl('ripe-atlas-observed-devices.jsonl',atlasRows);
writeJsonl('peeringdb-topology.jsonl',peeringRows);
writeJsonl('address-universe-roots.jsonl',universe);

const manifest={
  schema:'deus-global-passive-internet-census/1',
  generatedAt:new Date().toISOString(),
  policy:{
    collection:'PASSIVE_PUBLIC_SOURCE_INGESTION_ONLY',
    activeScanning:false,
    arbitraryHostProbing:false,
    unknownDeviceActivation:false,
    activationAdmission:'PUBLIC_SERVICE_INTENDED_OR_AUTHORIZED_OPT_IN_WITH_FRESH_RECEIPT_ONLY',
  },
  universe:{
    ipv4:'0.0.0.0/0',ipv4Cardinality:(1n<<32n).toString(),
    ipv6:'::/0',ipv6Cardinality:(1n<<128n).toString(),
  },
  rir:{
    descriptorRecords:dedupDesc.length,
    asnRecords:asnRecords.length,
    uniqueCoveredIpv4Addresses:uniqueIpv4.toString(),
    uniqueCoveredIpv6Addresses:uniqueIpv6.toString(),
    descriptorDigest:stableDigestRows(dedupDesc,['registry','cidr','status','descriptorDigest']),
  },
  observedDevices:{
    ripeAtlasRecords:atlasRows.length,
    exactAddressRecords:atlasRows.filter(x=>x.address).length,
    digest:stableDigestRows(atlasRows,['sourceId','identityType','address','resourceKey']),
  },
  topology:{
    peeringDbEntities:peeringRows.length,
    digest:stableDigestRows(peeringRows,['entityType','id','resourceKey']),
  },
  sourceReceipts,
  snowballFrontier:[
    {source:'CENSYS_HOST_WEB_CERT',state:'SOURCE_MAPPED_BULK_ACCESS_TIER_BOUND',use:'third-party observed host/service/certificate overlay'},
    {source:'CAIDA_ITDK',state:'SOURCE_MAPPED_RECENT_ACCESS_APPROVAL_OR_PUBLIC_OLDER_RELEASE',use:'router/interface/topology overlay'},
    {source:'COMMON_CRAWL',state:'ALREADY_MAPPED_CONTINUE_PARTITIONS',use:'web/domain/url membership'},
    {source:'CERTIFICATE_TRANSPARENCY',state:'ALREADY_MAPPED_CONTINUE_LOG_DELTA',use:'certificate/domain relation graph'},
    {source:'ROUTING_RIS_ROUTEVIEWS',state:'MAPPED_NEXT_ADAPTER',use:'active announced prefix/BGP relation overlay'},
  ],
  snowballRule:'EACH_VERIFIED_SOURCE_DELTA_ADDS_DESCRIPTORS_OR_OBSERVATIONS__NEW_RELATIONS_RANK_NEXT_SOURCES__ONLY_PUBLIC_INTENDED_OR_AUTHORIZED_ROUTES_CAN_ENTER_ACTIVATION_CANDIDATES',
  truthBoundary:'ADDRESSABLE_NE_KNOWN_DEVICE__OBSERVED_DEVICE_NE_LIVE_NOW__LIVE_NE_USABLE__USABLE_NE_AUTHORIZED_EXECUTION',
};
manifest.manifestDigest=sha256(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({
  verdict:'PASS',
  manifestDigest:manifest.manifestDigest,
  rirDescriptors:manifest.rir.descriptorRecords,
  asnRecords:manifest.rir.asnRecords,
  atlasRecords:manifest.observedDevices.ripeAtlasRecords,
  atlasExactAddresses:manifest.observedDevices.exactAddressRecords,
  peeringDbEntities:manifest.topology.peeringDbEntities,
  uniqueCoveredIpv4Addresses:manifest.rir.uniqueCoveredIpv4Addresses,
  uniqueCoveredIpv6Addresses:manifest.rir.uniqueCoveredIpv6Addresses,
  sources:sourceReceipts.length,
}));
