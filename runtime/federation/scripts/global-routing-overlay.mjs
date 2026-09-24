import fs from 'node:fs';
import zlib from 'node:zlib';
import { createHash } from 'node:crypto';
import { compileCidrAddressDescriptor, projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/internet-routing/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Routing-Overlay/1.0','accept':'*/*'};
const SOURCES=[
  ['v4','https://www.ris.ripe.net/dumps/riswhoisdump.IPv4.gz'],
  ['v6','https://www.ris.ripe.net/dumps/riswhoisdump.IPv6.gz'],
];
function sha256(x){return createHash('sha256').update(x).digest('hex');}
async function fetchBytes(url){
  const t=Date.now();
  const r=await fetch(url,{headers:UA,signal:AbortSignal.timeout(120000)});
  if(!r.ok) throw new Error(url+' HTTP '+r.status);
  const b=Buffer.from(await r.arrayBuffer());
  return {url,status:r.status,bytes:b.length,sha256:sha256(b),ms:Date.now()-t,body:b};
}
function parseOrigin(v){
  const m=String(v||'').trim().toUpperCase().match(/^AS(\d+)$/);
  return m?'AS'+BigInt(m[1]).toString():String(v||'').trim().toUpperCase();
}
function parseDump(text,family){
  const rows=[];
  let rec={};
  const flush=()=>{
    const prefix=rec.route6||rec.route;
    if(prefix&&rec.origin){
      try{
        const d=compileCidrAddressDescriptor(prefix);
        const origin=parseOrigin(rec.origin);
        const relation=projectInternetIdentityHierarchical({type:'service',value:'bgp:'+d.cidr+'|'+origin});
        rows.push({
          schema:'deus-bgp-prefix-origin-observation/1',
          source:'RIPE_RISWHOIS',
          family,
          prefix:d.cidr,
          descriptorDigest:d.descriptorDigest,
          addressCount:d.addressCount,
          origin,
          descr:rec.descr||null,
          seenAt:rec['seen-at']||null,
          numRisPeers:rec['num-rispeers']?Number(rec['num-rispeers']):null,
          lastUpdateFirst:rec['lastupd-frst']||null,
          lastUpdateLast:rec['lastupd-last']||null,
          relationKey:relation.resourceKey,
          supercellId:relation.supercellId,
          microcellId:relation.microcellId,
          activationClass:'ROUTING_OBSERVATION_ONLY',
          executionReady:false,
          truthBoundary:'RIS_BGP_OBSERVATION_NE_HOST_LIVENESS_NE_SERVICE_NE_EXECUTION_AUTHORITY',
        });
      }catch{}
    }
    rec={};
  };
  for(const line of text.split(/\r?\n/)){
    if(!line.trim()){flush();continue;}
    if(line.startsWith('%')) continue;
    const m=line.match(/^([a-zA-Z0-9-]+):\s*(.*)$/);
    if(m) rec[m[1].toLowerCase()]=m[2].trim();
  }
  flush();
  return rows;
}
function digestRows(rows){
  const h=createHash('sha256');
  for(const r of [...rows].sort((a,b)=>(a.prefix+'|'+a.origin).localeCompare(b.prefix+'|'+b.origin))){
    h.update(r.prefix+'|'+r.origin+'|'+String(r.numRisPeers??'')+'\n');
  }
  return h.digest('hex');
}
const all=[], receipts=[];
for(const [family,url] of SOURCES){
  const r=await fetchBytes(url);
  const raw=zlib.gunzipSync(r.body);
  receipts.push({family,url,status:r.status,gzipBytes:r.bytes,gzipSha256:r.sha256,rawBytes:raw.length,rawSha256:sha256(raw)});
  const rows=parseDump(raw.toString('utf8'),family);
  all.push(...rows);
  fs.writeFileSync(OUT+'/ris-'+family+'.jsonl',rows.map(x=>JSON.stringify(x)).join('\n')+'\n');
}
const dedup=[...new Map(all.map(x=>[x.prefix+'|'+x.origin,x])).values()];
const origins=new Set(dedup.map(x=>x.origin));
const prefixes=new Set(dedup.map(x=>x.prefix));
const v4=dedup.filter(x=>x.family==='v4');
const v6=dedup.filter(x=>x.family==='v6');
const manifest={
  schema:'deus-global-routing-overlay/1',
  generatedAt:new Date().toISOString(),
  source:'RIPE_RISWHOIS_DAILY_DUMPS',
  rows:dedup.length,
  uniquePrefixes:prefixes.size,
  uniqueOriginAsns:origins.size,
  ipv4Rows:v4.length,
  ipv6Rows:v6.length,
  digest:digestRows(dedup),
  receipts,
  integration:{
    parent:'DEUS_GLOBAL_PASSIVE_CENSUS_V1',
    joinKey:'PREFIX/CIDR + ORIGIN_ASN',
    use:'classify delegated address descriptors by observed BGP announcement and connect prefix-to-origin relations',
  },
  truthBoundary:'ROUTED_PREFIX_NE_LIVE_DEVICE__BGP_VISIBILITY_IS_RIS_COLLECTOR_SCOPED__ROUTING_OBSERVATION_NE_EXECUTION_AUTHORITY',
};
manifest.manifestDigest=sha256(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({verdict:'PASS',...manifest}));
