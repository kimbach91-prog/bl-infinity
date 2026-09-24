import fs from 'node:fs';
import { createHash, X509Certificate } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/global-internet-real-member-expansion/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Internet-Real-Member-Expansion/1.0','accept':'application/json,text/plain,text/html,application/octet-stream,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');
const generatedAt=new Date().toISOString();

function stable(v){
  if(Array.isArray(v)) return v.map(stable);
  if(v&&typeof v==='object') return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));
  return v;
}
function writeJsonl(name,rows){
  fs.writeFileSync(OUT+'/'+name,rows.map(x=>JSON.stringify(x)).join('\n')+(rows.length?'\n':''));
}
async function fetchBuf(url,{timeout=30000,accept=null}={}){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:{...UA,...(accept?{accept}: {})},redirect:'follow',signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,finalUrl:r.url,bytes:b.length,sha256:sha(b),etag:r.headers.get('etag'),lastModified:r.headers.get('last-modified'),contentType:r.headers.get('content-type'),ms:Date.now()-t,body:b};
  }catch(e){
    return {ok:false,status:null,url,finalUrl:null,bytes:0,sha256:null,etag:null,lastModified:null,contentType:null,ms:Date.now()-t,error:String(e?.message||e),body:null};
  }
}
async function firstOk(sources){
  const attempts=[];
  for(const src of sources){
    const r=await fetchBuf(src.url,{timeout:src.timeout??45000,accept:src.accept??null});
    attempts.push({...r,body:undefined,id:src.id});
    if(r.ok) return {source:src,result:r,attempts};
  }
  return {source:null,result:null,attempts};
}
function json(buf){ try{return JSON.parse(buf.toString('utf8'));}catch{return null;} }
function mapIdentity(type,value,metadata={}){
  try{
    const p=projectInternetIdentityHierarchical({type,value});
    return {...p,metadata};
  }catch{return null;}
}
function normalizePrefix(value){
  const s=String(value??'').trim();
  return s.includes('/')?s:null;
}
function normalizeAsn(value){
  if(value==null) return null;
  const m=String(value).trim().toUpperCase().match(/^(?:AS)?(\d+)$/);
  return m?'AS'+BigInt(m[1]).toString():null;
}

/* ---------------- RPKI BULK / MEMBER RELATIONS ---------------- */
const rpkiSources=[
  {id:'CLOUDFLARE_RPKI_JSON',url:'https://rpki.cloudflare.com/rpki.json',accept:'application/json'},
  {id:'RPKI_CLIENT_VRPS_JSON',url:'https://console.rpki-client.org/vrps.json',accept:'application/json'},
  {id:'RPKI_CLIENT_VRPS_CSV',url:'https://console.rpki-client.org/vrps.csv',accept:'text/csv,text/plain'},
];
const rpkiFetch=await firstOk(rpkiSources);
function extractVrpsFromJson(obj){
  const candidates=[
    Array.isArray(obj)?obj:null,
    obj?.roas,obj?.vrps,obj?.data,obj?.validated_roas,obj?.routes
  ].filter(Array.isArray);
  const arr=candidates.sort((a,b)=>b.length-a.length)[0]??[];
  return arr.map(x=>({
    prefix:normalizePrefix(x.prefix??x.route??x.cidr),
    asn:normalizeAsn(x.asn??x.origin??x.asID??x.as_id),
    maxLength:Number(x.maxLength??x.max_length??x.maxlen??String(x.prefix??'').split('/')[1]??NaN),
    ta:x.ta??x.trustAnchor??x.trust_anchor??x.source??null,
  })).filter(x=>x.prefix&&x.asn);
}
function extractVrpsFromCsv(text){
  const lines=text.split(/\r?\n/).filter(Boolean);
  if(!lines.length) return [];
  const head=lines[0].split(',').map(x=>x.replace(/^"|"$/g,'').trim().toLowerCase());
  const idx=(...names)=>names.map(n=>head.indexOf(n)).find(i=>i>=0)??-1;
  const ip=idx('prefix','route','cidr'), ia=idx('asn','origin','as'), im=idx('maxlength','max_length','maxlen'), it=idx('ta','trustanchor','trust_anchor');
  if(ip<0||ia<0) return [];
  return lines.slice(1).map(line=>{
    const f=line.match(/(?:^|,)(?:"([^"]*)"|([^,]*))/g)?.map(s=>s.replace(/^,/,'').replace(/^"|"$/g,''))??line.split(',');
    const prefix=normalizePrefix(f[ip]), asn=normalizeAsn(f[ia]);
    const maxLength=im>=0?Number(f[im]):Number(String(prefix??'').split('/')[1]);
    return {prefix,asn,maxLength,ta:it>=0?f[it]:null};
  }).filter(x=>x.prefix&&x.asn);
}
let vrps=[];
if(rpkiFetch.result?.body){
  const obj=json(rpkiFetch.result.body);
  vrps=obj?extractVrpsFromJson(obj):extractVrpsFromCsv(rpkiFetch.result.body.toString('utf8'));
}
const vrpDedup=new Map();
for(const v of vrps){
  const key=v.prefix+'|'+v.asn+'|'+String(v.maxLength);
  if(!vrpDedup.has(key)) vrpDedup.set(key,v);
}
vrps=[...vrpDedup.values()];
const RPKI_SAMPLE_MAX=256;
const step=Math.max(1,Math.floor(vrps.length/RPKI_SAMPLE_MAX));
const rpkiSampleRaw=[];
for(let i=0;i<vrps.length&&rpkiSampleRaw.length<RPKI_SAMPLE_MAX;i+=step) rpkiSampleRaw.push(vrps[i]);
const rpkiMembers=[];
const rpkiRelations=[];
for(const [i,v] of rpkiSampleRaw.entries()){
  const prefix=mapIdentity('cidr',v.prefix,{source:'RPKI_VRP',sampleIndex:i,maxLength:v.maxLength,ta:v.ta});
  const asn=mapIdentity('asn',v.asn,{source:'RPKI_VRP',sampleIndex:i});
  if(!prefix||!asn) continue;
  rpkiMembers.push({kind:'RPKI_PREFIX',...prefix},{kind:'RPKI_ASN',...asn});
  rpkiRelations.push({
    schema:'deus-internet-public-relation/1',
    relation:'RPKI_VRP_AUTHORIZES_ORIGIN',
    fromResourceKey:prefix.resourceKey,toResourceKey:asn.resourceKey,
    prefix:v.prefix,asn:v.asn,maxLength:v.maxLength,ta:v.ta,
    sourceRef:rpkiFetch.source?.url??null,
    truthBoundary:'VRP_VALIDATION_RELATION_NE_BGP_ANNOUNCEMENT_NE_REACHABILITY_NE_EXECUTION_AUTHORITY'
  });
}
const rpkiManifest={
  source:rpkiFetch.source?.id??null,sourceUrl:rpkiFetch.source?.url??null,
  sourceStatus:rpkiFetch.result?.status??null,sourceBytes:rpkiFetch.result?.bytes??0,sourceSha256:rpkiFetch.result?.sha256??null,
  attempts:rpkiFetch.attempts,totalVrps:vrps.length,sampledVrps:rpkiRelations.length,
  uniqueSampleResourceKeys:new Set(rpkiMembers.map(x=>x.resourceKey)).size,
  truthBoundary:'MACHINE_READABLE_RPKI_VRPS_NE_ROUTING_LIVENESS_NE_HOST_CONTROL_NE_COMPUTE_AUTHORITY'
};

/* ---------------- CERTIFICATE TRANSPARENCY SPARSE MEMBERS ---------------- */
const ctListFetch=await fetchBuf('https://www.gstatic.com/ct/log_list/v3/all_logs_list.json',{accept:'application/json'});
const ctList=json(ctListFetch.body??Buffer.alloc(0))??{};
const ctLogs=(ctList.operators??[]).flatMap(op=>(op.logs??[]).map(l=>({operator:op.name??null,...l})));
function decodeTlsCert(extraDataB64){
  const b=Buffer.from(extraDataB64,'base64');
  if(b.length<3) throw new Error('extra_data too short');
  const len=b.readUIntBE(0,3);
  if(len<=0||3+len>b.length) throw new Error('invalid tls cert length');
  return b.subarray(3,3+len);
}
function dnsNames(cert){
  const san=cert.subjectAltName??'';
  const names=[];
  const re=/DNS:([^,]+)/g; let m;
  while((m=re.exec(san))){
    let n=m[1].trim().replace(/^"|"$/g,'').toLowerCase().replace(/\.+$/,'');
    if(n.startsWith('*.')) n=n.slice(2);
    if(n&&/^[a-z0-9_.-]+$/.test(n)&&n.includes('.')) names.push(n);
  }
  return [...new Set(names)].slice(0,64);
}
const ctSourceAttempts=[];
const ctCerts=[];
const ctRelations=[];
for(const log of ctLogs){
  if(ctCerts.length>=12 || ctSourceAttempts.length>=28) break;
  const base=String(log.url??'').replace(/\/+$/,'');
  if(!base.startsWith('https://')) continue;
  const sth=await fetchBuf(base+'/ct/v1/get-sth',{timeout:12000,accept:'application/json'});
  ctSourceAttempts.push({operator:log.operator,description:log.description??null,url:base,sth:{...sth,body:undefined}});
  if(!sth.ok||!sth.body) continue;
  const sj=json(sth.body); const size=Number(sj?.tree_size??0);
  if(!Number.isFinite(size)||size<1) continue;
  const idx=size-1;
  const ent=await fetchBuf(base+`/ct/v1/get-entries?start=${idx}&end=${idx}`,{timeout:12000,accept:'application/json'});
  ctSourceAttempts[ctSourceAttempts.length-1].entry={...ent,body:undefined,index:idx};
  if(!ent.ok||!ent.body) continue;
  const ej=json(ent.body); const e=Array.isArray(ej?.entries)?ej.entries[0]:null;
  if(!e?.extra_data) continue;
  try{
    const der=decodeTlsCert(e.extra_data);
    const cert=new X509Certificate(der);
    const names=dnsNames(cert);
    if(!names.length) continue;
    const certHash=sha(der);
    const certId=mapIdentity('generic','x509-sha256:'+certHash,{source:'CERTIFICATE_TRANSPARENCY',logUrl:base,entryIndex:idx,subject:cert.subject,issuer:cert.issuer,validFrom:cert.validFrom,validTo:cert.validTo});
    if(!certId) continue;
    const domains=[];
    for(const n of names){
      const d=mapIdentity('dns',n,{source:'CERTIFICATE_TRANSPARENCY',logUrl:base,entryIndex:idx});
      if(!d) continue;
      domains.push(d);
      ctRelations.push({
        schema:'deus-internet-public-relation/1',relation:'CT_CERTIFICATE_NAMES_DOMAIN',
        fromResourceKey:certId.resourceKey,toResourceKey:d.resourceKey,
        certSha256:certHash,domain:n,logUrl:base,operator:log.operator,entryIndex:idx,
        truthBoundary:'CERTIFICATE_LOGGED_NAME_NE_CURRENT_DOMAIN_OWNERSHIP_NE_DNS_RESOLUTION_NE_LIVE_HOST_NE_EXECUTION_AUTHORITY'
      });
    }
    if(domains.length) ctCerts.push({cert:certId,domains,logUrl:base,operator:log.operator,entryIndex:idx});
  }catch(e){
    ctSourceAttempts[ctSourceAttempts.length-1].parseError=String(e?.message||e);
  }
}
const ctManifest={
  logListStatus:ctListFetch.status,logListSha256:ctListFetch.sha256,listedLogs:ctLogs.length,
  attemptedLogs:ctSourceAttempts.length,certificates:ctCerts.length,domainRelations:ctRelations.length,
  uniqueDomains:new Set(ctRelations.map(x=>x.domain)).size,
  truthBoundary:'SPARSE_CT_MEMBERSHIP_NE_WEB_CRAWL_NE_HOST_PROBE_NE_LIVENESS_NE_AUTHORITY'
};

/* ---------------- CLOUD / CDN PUBLIC PREFIX MEMBERS ---------------- */
const cloudSources=[
  {id:'AWS_IP_RANGES',url:'https://ip-ranges.amazonaws.com/ip-ranges.json',kind:'AWS'},
  {id:'GCP_CLOUD_RANGES',url:'https://www.gstatic.com/ipranges/cloud.json',kind:'GOOGLE'},
  {id:'GOOGLE_GLOBAL_RANGES',url:'https://www.gstatic.com/ipranges/goog.json',kind:'GOOGLE'},
  {id:'CLOUDFLARE_IPV4',url:'https://www.cloudflare.com/ips-v4',kind:'LINES'},
  {id:'CLOUDFLARE_IPV6',url:'https://www.cloudflare.com/ips-v6',kind:'LINES'},
  {id:'GITHUB_META',url:'https://api.github.com/meta',kind:'GITHUB'},
  {id:'FASTLY_PUBLIC_IPS',url:'https://api.fastly.com/public-ip-list',kind:'FASTLY'},
  {id:'INTERNIC_ROOT_ZONE',url:'https://www.internic.net/domain/root.zone',kind:'ROOT_ZONE'},
];
const cloudSourceReceipts=[];
const prefixRows=[];
const namingRows=[];
function addPrefix(source,prefix,meta={}){
  const p=normalizePrefix(prefix); if(!p) return;
  const mapped=mapIdentity('cidr',p,{source,...meta}); if(!mapped) return;
  prefixRows.push({source,prefix:p,...mapped,meta});
}
for(const src of cloudSources){
  const r=await fetchBuf(src.url,{timeout:30000});
  cloudSourceReceipts.push({id:src.id,kind:src.kind,...r,body:undefined});
  if(!r.ok||!r.body) continue;
  const txt=r.body.toString('utf8'); const obj=json(r.body);
  if(src.kind==='AWS'){
    for(const x of (obj?.prefixes??[])) addPrefix(src.id,x.ip_prefix,{region:x.region,service:x.service,networkBorderGroup:x.network_border_group});
    for(const x of (obj?.ipv6_prefixes??[])) addPrefix(src.id,x.ipv6_prefix,{region:x.region,service:x.service,networkBorderGroup:x.network_border_group});
  }else if(src.kind==='GOOGLE'){
    for(const x of (obj?.prefixes??[])) addPrefix(src.id,x.ipv4Prefix??x.ipv6Prefix,{service:x.service,scope:x.scope});
  }else if(src.kind==='LINES'){
    for(const line of txt.split(/\r?\n/)) addPrefix(src.id,line.trim());
  }else if(src.kind==='GITHUB'){
    for(const [k,v] of Object.entries(obj??{})){
      if(Array.isArray(v)) for(const p of v) if(typeof p==='string'&&p.includes('/')) addPrefix(src.id,p,{category:k});
    }
  }else if(src.kind==='FASTLY'){
    for(const p of (obj?.addresses??[])) addPrefix(src.id,p,{family:'ipv4'});
    for(const p of (obj?.ipv6_addresses??[])) addPrefix(src.id,p,{family:'ipv6'});
  }else if(src.kind==='ROOT_ZONE'){
    for(const line of txt.split(/\r?\n/)){
      const m=line.match(/^([^;\s]+)\.\s+\d+\s+IN\s+NS\s+([^\s]+)\.?$/i);
      if(!m) continue;
      const zone=m[1].toLowerCase(), ns=m[2].toLowerCase().replace(/\.+$/,'');
      const z=mapIdentity('dns',zone,{source:src.id,recordType:'NS_OWNER'});
      const n=mapIdentity('dns',ns,{source:src.id,recordType:'NS_TARGET'});
      if(z&&n) namingRows.push({schema:'deus-internet-public-relation/1',relation:'DNS_ROOT_ZONE_NS',zone,ns,fromResourceKey:z.resourceKey,toResourceKey:n.resourceKey,truthBoundary:'ROOT_ZONE_DELEGATION_NE_NAMESERVER_REACHABILITY_NE_CONTROL'});
    }
  }
}
const prefixDedup=new Map();
for(const p of prefixRows) if(!prefixDedup.has(p.resourceKey)) prefixDedup.set(p.resourceKey,p);
const prefixes=[...prefixDedup.values()];
const cloudManifest={
  sources:cloudSourceReceipts.length,liveSources:cloudSourceReceipts.filter(x=>x.ok).length,
  prefixes:prefixes.length,uniquePrefixResourceKeys:prefixes.length,rootNsRelations:namingRows.length,
  truthBoundary:'PUBLISHED_PREFIX_OR_ROOTZONE_MEMBER_NE_CURRENT_SERVICE_LIVENESS_NE_PROVIDER_CONTROL_NE_EXECUTION_AUTHORITY'
};

/* ---------------- PEERINGDB IX / NETIXLAN PUBLIC RELATIONS ---------------- */
async function peeringPaged(endpoint,maxPages=8){
  const all=[],receipts=[]; let skip=0;
  for(let page=0;page<maxPages;page++){
    const url=`https://www.peeringdb.com/api/${endpoint}?limit=1000&skip=${skip}`;
    const r=await fetchBuf(url,{timeout:30000,accept:'application/json'});
    receipts.push({page,url,...r,body:undefined});
    if(!r.ok||!r.body) break;
    const j=json(r.body); const data=Array.isArray(j?.data)?j.data:[];
    all.push(...data);
    if(data.length<1000) break;
    skip+=data.length;
  }
  return {data:all,receipts};
}
const [ixPage,netixPage]=await Promise.all([peeringPaged('ix',4),peeringPaged('netixlan',8)]);
const ixById=new Map(ixPage.data.map(x=>[String(x.id),x]));
const peeringRelations=[];
for(const x of netixPage.data){
  const asn=normalizeAsn(x.asn); if(!asn) continue;
  const ix=ixById.get(String(x.ix_id));
  const a=mapIdentity('asn',asn,{source:'PEERINGDB_NETIXLAN'});
  const i=mapIdentity('generic','peeringdb-ix:'+String(x.ix_id),{source:'PEERINGDB_IX',name:ix?.name??null,country:ix?.country??null,city:ix?.city??null});
  if(a&&i) peeringRelations.push({
    schema:'deus-internet-public-relation/1',relation:'PEERINGDB_ASN_PRESENT_AT_IXLAN',
    asn,ixId:x.ix_id,ixlanId:x.ixlan_id,ixName:ix?.name??null,
    fromResourceKey:a.resourceKey,toResourceKey:i.resourceKey,
    truthBoundary:'PUBLIC_PEERINGDB_MEMBERSHIP_NE_SESSION_LIVENESS_NE_TRAFFIC_NE_CONTROL'
  });
  for(const ip of [x.ipaddr4,x.ipaddr6].filter(Boolean)){
    const typ=String(ip).includes(':')?'ipv6':'ipv4';
    const p=mapIdentity(typ,ip,{source:'PEERINGDB_NETIXLAN',asn,ixId:x.ix_id});
    if(p&&a) peeringRelations.push({
      schema:'deus-internet-public-relation/1',relation:'PEERINGDB_IP_ASSIGNED_TO_ASN_AT_IXLAN',
      ip,asn,ixId:x.ix_id,ixlanId:x.ixlan_id,
      fromResourceKey:p.resourceKey,toResourceKey:a.resourceKey,
      truthBoundary:'PUBLIC_PEERING_ADDRESS_ASSIGNMENT_NE_HOST_PROBE_NE_CURRENT_BGP_SESSION_NE_EXECUTION_AUTHORITY'
    });
  }
}
const peeringManifest={
  ixRecords:ixPage.data.length,netixlanRecords:netixPage.data.length,relations:peeringRelations.length,
  ixReceipts:ixPage.receipts,netixlanReceipts:netixPage.receipts,
  truthBoundary:'PEERINGDB_PUBLIC_DIRECTORY_NE_COMPLETE_GLOBAL_PEERING_GRAPH_NE_CURRENT_SESSION_LIVENESS_NE_CONTROL'
};

/* ---------------- PARTICIPATION REGISTRY: DATA-ONLY SOURCES ---------------- */
const sourceDescriptors=[
  {id:'RPKI_BULK',class:'RPKI_MEMBER_GRAPH',ok:Boolean(rpkiFetch.result?.ok),ref:rpkiFetch.source?.url??null,count:vrps.length},
  {id:'CT_LOG_MEMBERS',class:'CT_PKI_MEMBER_GRAPH',ok:ctCerts.length>0,ref:'https://www.gstatic.com/ct/log_list/v3/all_logs_list.json',count:ctRelations.length},
  ...cloudSourceReceipts.map(x=>({id:x.id,class:'CLOUD_NAMING_MEMBER',ok:x.ok,ref:x.url,count:null})),
  {id:'PEERINGDB_IX',class:'IX_PEERING_MEMBER_GRAPH',ok:ixPage.data.length>0,ref:'https://www.peeringdb.com/api/ix',count:ixPage.data.length},
  {id:'PEERINGDB_NETIXLAN',class:'IX_PEERING_MEMBER_GRAPH',ok:netixPage.data.length>0,ref:'https://www.peeringdb.com/api/netixlan',count:netixPage.data.length},
];
const registry=registerParticipationBatch(sourceDescriptors.map(d=>({
  type:'service',value:'internet-real-member-source:'+d.id,
  evidenceClass:d.ok?'DATA_ONLY':'UNKNOWN',authorityClass:'UNKNOWN',serviceHint:true,
  source:'GLOBAL_INTERNET_REAL_MEMBER_EXPANSION_V1',sourceEvidenceRef:d.ref,
  observedAt:generatedAt,freshnessState:d.ok?'FRESH_SOURCE':'SOURCE_HOLD',
  metadata:{class:d.class,count:d.count}
})));

writeJsonl('rpki-members.jsonl',rpkiMembers);
writeJsonl('rpki-relations.jsonl',rpkiRelations);
writeJsonl('ct-relations.jsonl',ctRelations);
writeJsonl('cloud-prefixes.jsonl',prefixes);
writeJsonl('root-ns-relations.jsonl',namingRows);
writeJsonl('peering-relations.jsonl',peeringRelations);
writeJsonl('registrations.jsonl',registry.registrations);

const manifest={
  schema:'deus-global-internet-real-member-expansion/1',generatedAt,
  rpki:rpkiManifest,ct:ctManifest,cloud:cloudManifest,peering:peeringManifest,
  registry:registry.counts,
  relationCounts:{
    rpki:rpkiRelations.length,ct:ctRelations.length,rootNs:namingRows.length,peering:peeringRelations.length,
    total:rpkiRelations.length+ctRelations.length+namingRows.length+peeringRelations.length
  },
  sourceReceipts:{cloud:cloudSourceReceipts,ctAttempts:ctSourceAttempts},
  truthBoundary:'PUBLIC_MEMBER_GRAPH_NE_LIVE_INTERNET_COMPLETE__MAPPING_NE_CONTROL__CATALOG_NE_COMPUTE__NO_HOST_SCANNING'
};
manifest.digest=sha(Buffer.from(JSON.stringify(stable(manifest))));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(vrps.length<1000) throw new Error('RPKI bulk gate failed: '+vrps.length);
if(rpkiRelations.length<128) throw new Error('RPKI sampled relation gate failed: '+rpkiRelations.length);
if(ctRelations.length<1) throw new Error('CT sparse relation gate failed');
if(prefixes.length<100) throw new Error('cloud/CDN public prefix gate failed: '+prefixes.length);
if(registry.counts.executionAdmitted!==0) throw new Error('data-only member expansion must not admit execution');

console.log(JSON.stringify({
  verdict:'PASS',
  rpkiVrps:vrps.length,rpkiSampled:rpkiRelations.length,
  ctCertificates:ctCerts.length,ctDomainRelations:ctRelations.length,
  cloudPrefixes:prefixes.length,rootNsRelations:namingRows.length,
  peeringRelations:peeringRelations.length,
  registry:registry.counts,digest:manifest.digest
}));
