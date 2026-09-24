import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const SOURCES=[["IANA_IPV6_SPACE_XML","NUMBERING_RIR","https://www.iana.org/assignments/ipv6-address-space/ipv6-address-space.xml","IANA_XML"],["IANA_IPV4_SPECIAL","NUMBERING_RIR","https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.csv","IANA_CSV"],["IANA_IPV6_SPECIAL","NUMBERING_RIR","https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.csv","IANA_CSV"],["IANA_RDAP_DNS","RDAP_BOOTSTRAP","https://data.iana.org/rdap/dns.json","RDAP_JSON"],["IANA_RDAP_IPV4","RDAP_BOOTSTRAP","https://data.iana.org/rdap/ipv4.json","RDAP_JSON"],["IANA_RDAP_IPV6","RDAP_BOOTSTRAP","https://data.iana.org/rdap/ipv6.json","RDAP_JSON"],["IANA_RDAP_ASN","RDAP_BOOTSTRAP","https://data.iana.org/rdap/asn.json","RDAP_JSON"],["IANA_PROTOCOL_NUMBERS","PROTOCOL_REGISTRY","https://www.iana.org/assignments/protocol-numbers/protocol-numbers-1.csv","IANA_CSV"],["IANA_SERVICE_PORTS","PROTOCOL_REGISTRY","https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv","IANA_CSV"],["CAIDA_AS_RELATIONSHIPS","ROUTING_DATASET","https://publicdata.caida.org/datasets/as-relationships/serial-2/","PUBLIC_DIRECTORY"],["CAIDA_PREFIX2AS","ROUTING_DATASET","https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/","PUBLIC_DIRECTORY"],["RIPE_RIS_ARCHIVE_ROOT","ROUTING_DATASET","https://data.ris.ripe.net/","PUBLIC_DIRECTORY"],["ROUTEVIEWS_ARCHIVE_ROOT","ROUTING_DATASET","https://archive.routeviews.org/","PUBLIC_DIRECTORY"],["RIPE_RPKI_ROOT","RPKI","https://rpki.ripe.net/","RPKI_ROOT"],["APNIC_RPKI_ROOT","RPKI","https://rpki-repository.apnic.net/","RPKI_ROOT"],["ARIN_RPKI_TA","RPKI","https://rpki.arin.net/repository/arin-rpki-ta.cer","RPKI_BINARY"],["LACNIC_RPKI_ROOT","RPKI","https://rpki.lacnic.net/rpki/","RPKI_ROOT"],["AFRINIC_RPKI_ROOT","RPKI","https://rpki.afrinic.net/repository/","RPKI_ROOT"],["APPLE_PRIVATE_RELAY_RANGES","CLOUD_ENDPOINTS","https://mask-api.icloud.com/egress-ip-ranges.csv","IP_CSV"],["MICROSOFT365_ENDPOINTS","CLOUD_ENDPOINTS","https://endpoints.office.com/endpoints/worldwide?clientrequestid=6f7f9e8a-7dd4-4c6d-8a0a-202609240001","ENDPOINT_JSON"],["OONI_MEASUREMENTS","MEASUREMENT","https://api.ooni.io/api/v1/measurements?limit=1","MEASUREMENT_API"],["RIPESTAT_AS_OVERVIEW","MEASUREMENT","https://stat.ripe.net/data/as-overview/data.json?resource=AS3333","MEASUREMENT_API"],["ICANN_TLD_ROOT_DB","DNS_ROOT","https://www.iana.org/domains/root/db","ROOT_DB"],["ICANN_RZMS","DNS_ROOT","https://rzm.iana.org/","ROOT_ZONE_MANAGEMENT"]];
const OUT='.deus/global-internet-deepening/v2';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Internet-Deepening/2.0','accept':'application/json,text/plain,text/html,application/xml,application/octet-stream,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function get([id,cls,url,kind]){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(30000)});
    const b=Buffer.from(await r.arrayBuffer());
    return {id,class:cls,url,kind,ok:r.ok,status:r.status,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,contentType:r.headers.get('content-type'),body:b};
  }catch(e){
    return {id,class:cls,url,kind,ok:false,status:null,finalUrl:null,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};
  }
}
function json(b){try{return JSON.parse(b.toString('utf8'))}catch{return null}}
function countCsv(txt){return Math.max(0,txt.split(/\r?\n/).filter(Boolean).length-1)}
function extractLinks(txt){return [...txt.matchAll(/href=["']([^"'#]+)["']/gi)].map(m=>m[1]).filter(Boolean)}

const results=[],descriptors=[];
for(const src of SOURCES){
  const r=await get(src); results.push({...r,body:undefined});
  const d={id:r.id,class:r.class,kind:r.kind,url:r.url,ok:r.ok,status:r.status,bytes:r.bytes,sha256:r.sha256,descriptor:{},truthBoundary:'PUBLIC_SOURCE_READ_NE_WORLD_COMPLETENESS__REGISTRATION_NE_EXECUTION_AUTHORITY'};
  if(r.ok&&r.body){
    const txt=r.body.toString('utf8');
    if(r.kind==='IANA_CSV'||r.kind==='IP_CSV') d.descriptor={rows:countCsv(txt)};
    else if(r.kind==='IANA_XML') d.descriptor={records:(txt.match(/<record>/g)||[]).length};
    else if(r.kind==='RDAP_JSON'){
      const j=json(r.body)||{}; d.descriptor={services:Array.isArray(j.services)?j.services.length:0,version:j.version??null,publication:j.publication??null};
    } else if(r.kind==='ENDPOINT_JSON'){
      const j=json(r.body); const arr=Array.isArray(j)?j:[]; let ips=0,urls=0;
      for(const x of arr){ips+=(x.ips||[]).length;urls+=(x.urls||[]).length}
      d.descriptor={records:arr.length,ipEntries:ips,urlEntries:urls};
    } else if(r.kind==='MEASUREMENT_API'){
      const j=json(r.body)||{}; d.descriptor={keys:Object.keys(j).slice(0,30),count:j.count??j?.metadata?.count??null};
    } else if(r.kind==='RPKI_BINARY'){
      d.descriptor={binaryBytes:r.bytes,sha256:r.sha256};
    } else if(r.kind==='PUBLIC_DIRECTORY'||r.kind==='RPKI_ROOT'||r.kind==='ROOT_DB'||r.kind==='ROOT_ZONE_MANAGEMENT'){
      const links=extractLinks(txt); d.descriptor={links:links.length,contentType:r.contentType??null};
    } else d.descriptor={contentType:r.contentType??null,bytes:r.bytes};
  }
  descriptors.push(d);
}

const registry=registerParticipationBatch(descriptors.map(d=>({
  type:'service',value:'internet-deepening-v2:'+d.id,
  evidenceClass:d.ok?'DATA_ONLY':'UNKNOWN',authorityClass:'UNKNOWN',
  serviceHint:true,source:'GLOBAL_INTERNET_DEEPENING_V2',
  sourceEvidenceRef:d.url,observedAt:new Date().toISOString(),
  freshnessState:d.ok?'FRESH_SOURCE':'SOURCE_HOLD',
  metadata:{class:d.class,kind:d.kind,status:d.status,descriptor:d.descriptor}
})));
const live=descriptors.filter(x=>x.ok),held=descriptors.filter(x=>!x.ok);
const liveClasses=[...new Set(live.map(x=>x.class))];
const allClasses=[...new Set(descriptors.map(x=>x.class))];
const manifest={
  schema:'deus-global-internet-baseline-deepening/2',
  generatedAt:new Date().toISOString(),
  sources:descriptors.length,live:live.length,held:held.length,
  classes:allClasses,liveClasses,registry:registry.counts,batchDigest:registry.batchDigest,
  descriptors,
  truthBoundary:'DEEPENING_SOURCE_COVERAGE_NE_OMNISCIENCE__PUBLIC_REGISTRY_NE_HOST_CONTROL__RPKI_RDAP_ROUTING_DATA_NE_EXECUTION_AUTHORITY'
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/descriptors.jsonl',descriptors.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(live.length<16) throw new Error('Deepening V2 live-source gate failed: '+live.length);
if(liveClasses.length<6) throw new Error('Deepening V2 class gate failed: '+liveClasses.length);
if(registry.counts.executionAdmitted!==0) throw new Error('Deepening V2 must not admit execution');
console.log(JSON.stringify({verdict:'PASS',sources:manifest.sources,live:manifest.live,held:manifest.held,liveClasses,registry:manifest.registry,digest:manifest.digest}));
