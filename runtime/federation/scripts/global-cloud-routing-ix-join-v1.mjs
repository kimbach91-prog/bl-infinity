import fs from 'node:fs';
import zlib from 'node:zlib';
import { createHash } from 'node:crypto';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const OUT='.deus/global-cloud-routing-ix-join/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Cloud-Routing-IX-Join/1.0','accept':'application/json,text/plain,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function fetchBuf(url,{timeout=120000}={}){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,body:b};
  }catch(e){return {ok:false,status:null,url,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};}
}
function json(b){try{return JSON.parse(b.toString('utf8'));}catch{return null;}}
function ipv4Big(ip){return ip.split('.').reduce((n,p)=>(n<<8n)|BigInt(Number(p)),0n);}
function ipv6Big(ip){
  const parts=String(ip).toLowerCase().split('::');
  if(parts.length>2) throw new Error('bad ipv6');
  const l=parts[0]?parts[0].split(':'):[];
  const r=parts.length===2&&parts[1]?parts[1].split(':'):[];
  const fill=8-l.length-r.length; if(fill<0) throw new Error('bad ipv6');
  const gs=[...l,...Array(fill).fill('0'),...r];
  let n=0n; for(const g of gs)n=(n<<16n)|BigInt('0x'+(g||'0')); return n;
}
function mask(base,bits,len){return len===0?0n:(base>>BigInt(bits-len))<<BigInt(bits-len);}
function parseCidr(cidr){
  const [addr,ls]=String(cidr).trim().split('/');
  const len=Number(ls), family=addr.includes(':')?6:4, bits=family===6?128:32;
  if(!Number.isInteger(len)||len<0||len>bits)throw new Error('bad prefix '+cidr);
  const raw=family===6?ipv6Big(addr):ipv4Big(addr);
  return {family,bits,len,base:mask(raw,bits,len),cidr:String(cidr).trim()};
}
function normalizeAsn(x){
  const m=String(x??'').trim().toUpperCase().match(/^(?:AS)?(\d+)$/);
  return m?'AS'+BigInt(m[1]).toString():null;
}
function identity(type,value,meta={}){
  const p=projectInternetIdentityHierarchical({type,value});
  return {...p,meta};
}
function addCloud(rows,provider,prefix,meta={}){
  if(!String(prefix??'').includes('/'))return;
  try{const p=parseCidr(prefix);rows.push({provider,prefix:p.cidr,family:p.family,prefixLen:p.len,...meta});}catch{}
}
const sourceDefs=[
 ['AWS','https://ip-ranges.amazonaws.com/ip-ranges.json'],
 ['GCP','https://www.gstatic.com/ipranges/cloud.json'],
 ['GOOGLE','https://www.gstatic.com/ipranges/goog.json'],
 ['GITHUB','https://api.github.com/meta'],
 ['FASTLY','https://api.fastly.com/public-ip-list'],
 ['CLOUDFLARE_V4','https://www.cloudflare.com/ips-v4'],
 ['CLOUDFLARE_V6','https://www.cloudflare.com/ips-v6'],
 ['OCI','https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json'],
];
const cloud=[],sourceReceipts=[];
for(const [id,url] of sourceDefs){
  const r=await fetchBuf(url,{timeout:30000}); sourceReceipts.push({id,...r,body:undefined});
  if(!r.ok||!r.body)continue;
  const j=json(r.body), txt=r.body.toString('utf8');
  if(id==='AWS'){
    for(const x of (j?.prefixes??[]))addCloud(cloud,'AWS',x.ip_prefix,{service:x.service,region:x.region});
    for(const x of (j?.ipv6_prefixes??[]))addCloud(cloud,'AWS',x.ipv6_prefix,{service:x.service,region:x.region});
  }else if(id==='GCP'||id==='GOOGLE'){
    for(const x of (j?.prefixes??[]))addCloud(cloud,id,x.ipv4Prefix??x.ipv6Prefix,{service:x.service??null,scope:x.scope??null});
  }else if(id==='GITHUB'){
    for(const [k,v] of Object.entries(j??{}))if(Array.isArray(v))for(const p of v)if(typeof p==='string'&&p.includes('/'))addCloud(cloud,'GITHUB',p,{service:k});
  }else if(id==='FASTLY'){
    for(const p of (j?.addresses??[]))addCloud(cloud,'FASTLY',p);
    for(const p of (j?.ipv6_addresses??[]))addCloud(cloud,'FASTLY',p);
  }else if(id.startsWith('CLOUDFLARE_')){
    for(const line of txt.split(/\r?\n/))if(line.trim())addCloud(cloud,'CLOUDFLARE',line.trim());
  }else if(id==='OCI'){
    for(const reg of (j?.regions??[]))for(const x of (reg.cidrs??[]))addCloud(cloud,'OCI',x.cidr,{region:reg.region??null,tags:x.tags??[]});
  }
}
const cloudDedup=[...new Map(cloud.map(x=>[x.provider+'|'+x.prefix,x])).values()];
if(cloudDedup.length<1000)throw new Error('cloud prefix gate '+cloudDedup.length);

const routeMaps={4:new Map(),6:new Map()},routeLengths={4:new Set(),6:new Set()},risReceipts=[];
for(const [family,url] of [[4,'https://www.ris.ripe.net/dumps/riswhoisdump.IPv4.gz'],[6,'https://www.ris.ripe.net/dumps/riswhoisdump.IPv6.gz']]){
  const r=await fetchBuf(url,{timeout:180000}); risReceipts.push({family,...r,body:undefined});
  if(!r.ok||!r.body)throw new Error('RIS failed family '+family);
  const raw=zlib.gunzipSync(r.body).toString('utf8');
  for(const line0 of raw.split(/\r?\n/)){
    const line=line0.trim(); if(!line||line.startsWith('%'))continue;
    const f=line0.split('\t'); if(f.length<2)continue;
    const asn=normalizeAsn(f[0]),prefix=String(f[1]??'').trim();
    if(!asn||!prefix.includes('/'))continue;
    try{
      const p=parseCidr(prefix); if(p.family!==family)continue;
      routeLengths[family].add(p.len);
      let byLen=routeMaps[family].get(p.len); if(!byLen){byLen=new Map();routeMaps[family].set(p.len,byLen);}
      const key=p.base.toString(16); let set=byLen.get(key); if(!set){set=new Set();byLen.set(key,set);} set.add(asn);
    }catch{}
  }
}
const lens={4:[...routeLengths[4]].sort((a,b)=>b-a),6:[...routeLengths[6]].sort((a,b)=>b-a)};
function coveringOrigins(prefix){
  const p=parseCidr(prefix);
  for(const len of lens[p.family]){
    if(len>p.len)continue;
    const key=mask(p.base,p.bits,len).toString(16);
    const set=routeMaps[p.family].get(len)?.get(key);
    if(set?.size)return {routePrefixLen:len,origins:[...set].sort()};
  }
  return null;
}

async function paged(endpoint,maxPages){
  const data=[],receipts=[]; let skip=0;
  for(let page=0;page<maxPages;page++){
    const url=`https://www.peeringdb.com/api/${endpoint}?limit=1000&skip=${skip}`;
    const r=await fetchBuf(url,{timeout:30000}); receipts.push({page,...r,body:undefined});
    if(!r.ok||!r.body)break;
    const j=json(r.body);const a=Array.isArray(j?.data)?j.data:[];
    data.push(...a);if(a.length<1000)break;skip+=a.length;
  }
  return {data,receipts};
}
const [ixp,netix]=await Promise.all([paged('ix',4),paged('netixlan',10)]);
const ixById=new Map(ixp.data.map(x=>[String(x.id),x]));
const asnIx=new Map();
for(const x of netix.data){
  const asn=normalizeAsn(x.asn);if(!asn)continue;
  let s=asnIx.get(asn);if(!s){s=new Map();asnIx.set(asn,s);}
  const ix=ixById.get(String(x.ix_id));
  s.set(String(x.ix_id),{ixId:x.ix_id,ixlanId:x.ixlan_id,ixName:ix?.name??null,country:ix?.country??null,city:ix?.city??null});
}

const mappings=[],relations=[];
const originsSet=new Set(),resolvedProviders=new Set();
for(const c of cloudDedup){
  const cover=coveringOrigins(c.prefix);
  const pId=identity('cidr',c.prefix,{source:'PUBLIC_CLOUD_RANGE',provider:c.provider});
  if(!cover){mappings.push({...c,resolved:false,prefixResourceKey:pId.resourceKey});continue;}
  resolvedProviders.add(c.provider);
  const origins=cover.origins.slice(0,16);
  mappings.push({...c,resolved:true,routePrefixLen:cover.routePrefixLen,origins,prefixResourceKey:pId.resourceKey});
  for(const asn of origins){
    originsSet.add(asn);
    const aId=identity('asn',asn,{source:'RIPE_RIS_COVERING_ROUTE'});
    relations.push({schema:'deus-cloud-routing-relation/1',relation:'PUBLIC_RANGE_COVERED_BY_RIS_ORIGIN',
      provider:c.provider,prefix:c.prefix,routePrefixLen:cover.routePrefixLen,origin:asn,
      fromResourceKey:pId.resourceKey,toResourceKey:aId.resourceKey,
      truthBoundary:'PUBLISHED_RANGE_PLUS_COVERING_RIS_ROUTE_NE_SERVICE_LIVENESS_NE_PROVIDER_CONTROL_NE_EXHAUSTIVE_MORE_SPECIFICS'});
    const ixes=asnIx.get(asn);
    if(ixes)for(const ix of ixes.values()){
      const iId=identity('generic','peeringdb-ix:'+String(ix.ixId),{source:'PEERINGDB',...ix});
      relations.push({schema:'deus-cloud-routing-relation/1',relation:'OBSERVED_ORIGIN_ASN_PRESENT_AT_PUBLIC_IX',
        provider:c.provider,prefix:c.prefix,origin:asn,ixId:ix.ixId,ixName:ix.ixName,country:ix.country,city:ix.city,
        fromResourceKey:aId.resourceKey,toResourceKey:iId.resourceKey,
        truthBoundary:'PEERINGDB_MEMBERSHIP_NE_CURRENT_BGP_SESSION_NE_TRAFFIC_NE_PROVIDER_CONTROL'});
    }
  }
}
const relDedup=[...new Map(relations.map(x=>[x.relation+'|'+x.fromResourceKey+'|'+x.toResourceKey,x])).values()];
const resolved=mappings.filter(x=>x.resolved);
const ixRel=relDedup.filter(x=>x.relation==='OBSERVED_ORIGIN_ASN_PRESENT_AT_PUBLIC_IX').length;
const registry=registerParticipationBatch(sourceDefs.map(([id,url])=>({
  type:'service',value:'cloud-routing-source:'+id,evidenceClass:sourceReceipts.find(x=>x.id===id)?.ok?'DATA_ONLY':'UNKNOWN',
  authorityClass:'UNKNOWN',serviceHint:true,source:'GLOBAL_CLOUD_ROUTING_IX_JOIN_V1',sourceEvidenceRef:url,
  observedAt:new Date().toISOString(),freshnessState:sourceReceipts.find(x=>x.id===id)?.ok?'FRESH_SOURCE':'SOURCE_HOLD',metadata:{kind:'PUBLIC_PREFIX_SOURCE'}
})).concat([
 {type:'service',value:'cloud-routing-source:RIPE_RIS',evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',serviceHint:true,source:'GLOBAL_CLOUD_ROUTING_IX_JOIN_V1',sourceEvidenceRef:'https://www.ris.ripe.net/dumps/',observedAt:new Date().toISOString(),freshnessState:'FRESH_SOURCE',metadata:{kind:'PASSIVE_ROUTING'}},
 {type:'service',value:'cloud-routing-source:PEERINGDB',evidenceClass:netix.data.length?'DATA_ONLY':'UNKNOWN',authorityClass:'UNKNOWN',serviceHint:true,source:'GLOBAL_CLOUD_ROUTING_IX_JOIN_V1',sourceEvidenceRef:'https://www.peeringdb.com/api/',observedAt:new Date().toISOString(),freshnessState:netix.data.length?'FRESH_SOURCE':'SOURCE_HOLD',metadata:{kind:'PUBLIC_INTERCONNECTION'}}
]));
fs.writeFileSync(OUT+'/cloud-prefix-routing.jsonl',mappings.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/relations.jsonl',relDedup.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
const manifest={
 schema:'deus-global-cloud-routing-ix-join/1',generatedAt:new Date().toISOString(),
 cloud:{sources:sourceDefs.length,liveSources:sourceReceipts.filter(x=>x.ok).length,prefixes:cloudDedup.length,resolvedCoveringRoute:resolved.length,resolvedProviders:[...resolvedProviders].sort(),uniqueOrigins:originsSet.size},
 routing:{receipts:risReceipts,routePrefixLengthsV4:lens[4].length,routePrefixLengthsV6:lens[6].length},
 peering:{ixRecords:ixp.data.length,netixlanRecords:netix.data.length,originIxRelations:ixRel,receipts:{ix:ixp.receipts,netixlan:netix.receipts}},
 relations:{total:relDedup.length,routing:relDedup.length-ixRel,ix:ixRel},
 registry:registry.counts,sourceReceipts,
 truthBoundary:'PUBLIC_CLOUD_PREFIX_PLUS_PASSIVE_COVERING_ROUTE_PLUS_PUBLIC_IX_MEMBERSHIP_NE_SERVICE_LIVENESS__COVERING_ROUTE_JOIN_IS_NOT_EXHAUSTIVE_MORE_SPECIFIC_ROUTING__NO_CONTROL_OR_COMPUTE_AUTHORITY'
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
if(resolved.length<500)throw new Error('resolved cloud prefix gate '+resolved.length);
if(originsSet.size<5)throw new Error('origin diversity gate '+originsSet.size);
if(relDedup.length<500)throw new Error('relation gate '+relDedup.length);
if(registry.counts.executionAdmitted!==0)throw new Error('data-only cross-layer join must not admit execution');
console.log(JSON.stringify({verdict:'PASS',cloudPrefixes:cloudDedup.length,resolved:resolved.length,providers:manifest.cloud.resolvedProviders,uniqueOrigins:originsSet.size,ixRelations:ixRel,totalRelations:relDedup.length,registry:registry.counts,digest:manifest.digest}));
