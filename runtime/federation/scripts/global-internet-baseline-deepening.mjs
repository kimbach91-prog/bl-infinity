import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const SOURCES=[["IANA_TLD_LIST","DNS_ROOT","https://data.iana.org/TLD/tlds-alpha-by-domain.txt","TLD_LIST"],["IANA_ROOT_ANCHORS","DNS_ROOT","https://data.iana.org/root-anchors/root-anchors.xml","ROOT_ANCHORS"],["IANA_IPV4_SPACE","NUMBERING_RIR","https://www.iana.org/assignments/ipv4-address-space/ipv4-address-space.csv","IANA_CSV"],["IANA_IPV6_SPACE","NUMBERING_RIR","https://www.iana.org/assignments/ipv6-address-space/ipv6-address-space.csv","IANA_CSV"],["IANA_ASN_LOW","NUMBERING_RIR","https://www.iana.org/assignments/as-numbers/as-numbers-1.csv","IANA_CSV"],["IANA_ASN_HIGH","NUMBERING_RIR","https://www.iana.org/assignments/as-numbers/as-numbers-2.csv","IANA_CSV"],["PEERINGDB_FAC_SAMPLE","IX_PEERING","https://www.peeringdb.com/api/fac?limit=1","PEERINGDB_API"],["PEERINGDB_NETIXLAN_SAMPLE","IX_PEERING","https://www.peeringdb.com/api/netixlan?limit=1","PEERINGDB_API"],["PUBLIC_SUFFIX_LIST","WEB_CORPUS","https://publicsuffix.org/list/public_suffix_list.dat","PSL"],["TRANCO_ROOT","WEB_CORPUS","https://tranco-list.eu/","TOP_SITES_SOURCE"],["CHROME_CT_ALL_LOGS","CT_PKI","https://www.gstatic.com/ct/log_list/v3/all_logs_list.json","CT_ALL_LOGS"],["OCI_PUBLIC_IP_RANGES","CLOUD_RANGES","https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json","IP_PREFIX_CATALOG"],["AZURE_SERVICE_TAGS","CLOUD_RANGES","https://www.microsoft.com/en-us/download/details.aspx?id=56519","SERVICE_TAG_SOURCE"],["VERCEL_DOCS","CLOUD_RANGES","https://vercel.com/docs","CLOUD_SOURCE_ROOT"],["RIPE_ATLAS_ANCHORS","MEASUREMENT","https://atlas.ripe.net/api/v2/anchors/?page_size=1","RIPE_ATLAS_API"],["RIPE_ATLAS_MEASUREMENTS","MEASUREMENT","https://atlas.ripe.net/api/v2/measurements/?page_size=1","RIPE_ATLAS_API"],["MLAB_DATA","MEASUREMENT","https://www.measurementlab.net/data/","MEASUREMENT_CATALOG"],["APNIC_LABS_STATS","MEASUREMENT","https://stats.labs.apnic.net/","MEASUREMENT_ROOT"],["CAIDA_SCAMPER","MEASUREMENT","https://www.caida.org/catalog/software/scamper/","MEASUREMENT_SOFTWARE"],["CLOUDFLARE_RADAR","ROUTING_BGP","https://radar.cloudflare.com/","ROUTING_OBSERVABILITY_ROOT"]];
const OUT='.deus/global-internet-deepening/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Internet-Deepening/1.0','accept':'application/json,text/plain,text/html,application/xml,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function get([id,cls,url,kind]){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(25000)});
    const b=Buffer.from(await r.arrayBuffer());
    return {id,class:cls,url,kind,ok:r.ok,status:r.status,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,contentType:r.headers.get('content-type'),body:b};
  }catch(e){return {id,class:cls,url,kind,ok:false,status:null,finalUrl:null,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};}
}
const json=b=>{try{return JSON.parse(b.toString('utf8'))}catch{return null}};
const results=[],descriptors=[];
for(const src of SOURCES){
  const r=await get(src); results.push({...r,body:undefined});
  const d={id:r.id,class:r.class,kind:r.kind,url:r.url,ok:r.ok,status:r.status,bytes:r.bytes,sha256:r.sha256,descriptor:{},truthBoundary:'SOURCE_READ_NE_WORLD_COMPLETENESS__REGISTRATION_NE_EXECUTION_AUTHORITY'};
  if(r.ok&&r.body){
    const txt=r.body.toString('utf8');
    if(r.kind==='TLD_LIST') d.descriptor={tlds:txt.split(/\r?\n/).filter(x=>x&&!x.startsWith('#')).length};
    else if(r.kind==='ROOT_ANCHORS') d.descriptor={keyDigests:(txt.match(/<KeyDigest\b/g)||[]).length};
    else if(r.kind==='IANA_CSV') d.descriptor={rows:Math.max(0,txt.split(/\r?\n/).filter(Boolean).length-1)};
    else if(r.kind==='PEERINGDB_API'){const j=json(r.body)||{};d.descriptor={sampleRecords:Array.isArray(j.data)?j.data.length:0,meta:j.meta??null};}
    else if(r.kind==='PSL') d.descriptor={rules:txt.split(/\r?\n/).map(x=>x.trim()).filter(x=>x&&!x.startsWith('//')).length};
    else if(r.kind==='CT_ALL_LOGS'){const j=json(r.body)||{};const ops=j.operators||[];d.descriptor={operators:ops.length,logs:ops.flatMap(x=>x.logs||[]).length};}
    else if(r.id==='OCI_PUBLIC_IP_RANGES'){const j=json(r.body)||{};const regions=j.regions||[];d.descriptor={regions:regions.length,prefixes:regions.reduce((n,x)=>n+(x.cidrs||[]).length,0)};}
    else if(r.kind==='RIPE_ATLAS_API'){const j=json(r.body)||{};d.descriptor={count:j.count??null,sampleResults:Array.isArray(j.results)?j.results.length:0};}
    else d.descriptor={contentType:r.contentType??null,bytes:r.bytes};
  }
  descriptors.push(d);
}
const registry=registerParticipationBatch(descriptors.map(d=>({
  type:'service',value:'internet-deepening:'+d.id,evidenceClass:d.ok?'DATA_ONLY':'UNKNOWN',authorityClass:'UNKNOWN',
  serviceHint:true,source:'GLOBAL_INTERNET_DEEPENING_V1',sourceEvidenceRef:d.url,observedAt:new Date().toISOString(),
  freshnessState:d.ok?'FRESH_SOURCE':'SOURCE_HOLD',metadata:{class:d.class,kind:d.kind,status:d.status,descriptor:d.descriptor}
})));
const live=descriptors.filter(x=>x.ok),held=descriptors.filter(x=>!x.ok);
const liveClasses=[...new Set(live.map(x=>x.class))];
const manifest={
  schema:'deus-global-internet-baseline-deepening/1',generatedAt:new Date().toISOString(),
  sources:descriptors.length,live:live.length,held:held.length,classes:[...new Set(descriptors.map(x=>x.class))],liveClasses,
  registry:registry.counts,batchDigest:registry.batchDigest,descriptors,
  truthBoundary:'DEEPENING_SOURCE_COVERAGE_NE_HOST_CONTROL__PUBLIC_CATALOG_NE_ACTIVE_CAPACITY__NO_BLIND_SCAN'
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/descriptors.jsonl',descriptors.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
if(live.length<14) throw new Error('deepening live-source gate failed: '+live.length);
if(liveClasses.length<6) throw new Error('deepening class gate failed: '+liveClasses.length);
if(registry.counts.executionAdmitted!==0) throw new Error('deepening must not admit execution');
console.log(JSON.stringify({verdict:'PASS',sources:manifest.sources,live:manifest.live,held:manifest.held,classes:manifest.liveClasses,registry:manifest.registry,digest:manifest.digest}));
