import fs from 'node:fs';
import zlib from 'node:zlib';
import { createHash } from 'node:crypto';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/global-internet-bgp-rpki-join/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-BGP-RPKI-Join/1.0','accept':'application/json,text/plain,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');
const h=createHash('sha256');

async function fetchBuf(url,{timeout=120000,accept=null}={}){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:{...UA,...(accept?{accept}:{})},redirect:'follow',signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,body:b};
  }catch(e){return {ok:false,status:null,url,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};}
}
async function firstOk(sources){
  const attempts=[];
  for(const src of sources){
    const r=await fetchBuf(src.url,{timeout:src.timeout??120000,accept:src.accept??null});
    attempts.push({id:src.id,...r,body:undefined});
    if(r.ok) return {source:src,result:r,attempts};
  }
  return {source:null,result:null,attempts};
}
function json(b){try{return JSON.parse(b.toString('utf8'));}catch{return null;}}
function normalizeAsn(value){
  if(value==null)return null;
  const m=String(value).trim().toUpperCase().match(/^(?:AS)?(\d+)$/);
  return m?'AS'+BigInt(m[1]).toString():null;
}
function ipv4Big(ip){return ip.split('.').reduce((n,p)=>(n<<8n)|BigInt(Number(p)),0n);}
function ipv6Big(ip){
  const parts=String(ip).toLowerCase().split('::');
  if(parts.length>2) throw new Error('bad ipv6');
  const left=parts[0]?parts[0].split(':'):[];
  const right=parts.length===2&&parts[1]?parts[1].split(':'):[];
  const fill=8-left.length-right.length;
  if(fill<0) throw new Error('bad ipv6 width');
  const groups=[...left,...Array(fill).fill('0'),...right];
  let n=0n;
  for(const g of groups)n=(n<<16n)|BigInt('0x'+(g||'0'));
  return n;
}
function mask(base,bits,len){
  if(len===0)return 0n;
  const host=bits-len;
  return (base>>BigInt(host))<<BigInt(host);
}
function parseCidr(cidr){
  const [addr,ls]=String(cidr).trim().split('/');
  const len=Number(ls);
  if(!Number.isInteger(len)) throw new Error('bad prefix len');
  const family=addr.includes(':')?6:4,bits=family===6?128:32;
  if(len<0||len>bits)throw new Error('bad prefix len');
  const raw=family===6?ipv6Big(addr):ipv4Big(addr);
  return {family,bits,len,base:mask(raw,bits,len)};
}
function cidrKey(family,len,base){return family+'|'+len+'|'+base.toString(16);}
function sameAsKey(asn,family){return asn+'|'+family;}

const rpkiSources=[
  {id:'CLOUDFLARE_RPKI_JSON',url:'https://rpki.cloudflare.com/rpki.json',accept:'application/json'},
  {id:'RPKI_CLIENT_VRPS_JSON',url:'https://console.rpki-client.org/vrps.json',accept:'application/json'},
];
const rpki=await firstOk(rpkiSources);
if(!rpki.result?.body) throw new Error('no RPKI bulk source');
const obj=json(rpki.result.body);
function extractVrps(o){
  const arrs=[Array.isArray(o)?o:null,o?.roas,o?.vrps,o?.data,o?.validated_roas,o?.routes].filter(Array.isArray);
  const arr=arrs.sort((a,b)=>b.length-a.length)[0]??[];
  return arr.map(x=>{
    const prefix=String(x.prefix??x.route??x.cidr??'').trim();
    const asn=normalizeAsn(x.asn??x.origin??x.asID??x.as_id);
    const maxLength=Number(x.maxLength??x.max_length??x.maxlen??prefix.split('/')[1]);
    return {prefix,asn,maxLength,ta:x.ta??x.trustAnchor??x.trust_anchor??null};
  }).filter(x=>x.prefix.includes('/')&&x.asn&&Number.isFinite(x.maxLength));
}
let vrps=extractVrps(obj);
if(vrps.length<500000) throw new Error('RPKI source unexpectedly small '+vrps.length);

const globalCover=new Map(); // family|len -> Set(base)
const sameAs=new Map(); // asn|family -> Map(len -> Map(base,maxLength))
let indexed=0,parseFailures=0;
for(const v of vrps){
  try{
    const p=parseCidr(v.prefix);
    const base=mask(p.base,p.bits,p.len);
    const gk=p.family+'|'+p.len;
    let set=globalCover.get(gk); if(!set){set=new Set();globalCover.set(gk,set);} set.add(base);
    const ak=sameAsKey(v.asn,p.family);
    let byLen=sameAs.get(ak); if(!byLen){byLen=new Map();sameAs.set(ak,byLen);}
    let net=byLen.get(p.len); if(!net){net=new Map();byLen.set(p.len,net);}
    const prev=net.get(base);
    if(prev==null||v.maxLength>prev) net.set(base,v.maxLength);
    indexed++;
  }catch{parseFailures++;}
}
const globalLengths={4:[],6:[]};
for(const k of globalCover.keys()){
  const [fam,len]=k.split('|').map(Number);
  globalLengths[fam].push(len);
}
globalLengths[4]=[...new Set(globalLengths[4])].sort((a,b)=>b-a);
globalLengths[6]=[...new Set(globalLengths[6])].sort((a,b)=>b-a);

function classify(prefix,origin){
  const p=parseCidr(prefix);
  const byLen=sameAs.get(sameAsKey(origin,p.family));
  let sameCover=false;
  if(byLen){
    const lens=[...byLen.keys()].filter(x=>x<=p.len).sort((a,b)=>b-a);
    for(const len of lens){
      const base=mask(p.base,p.bits,len);
      const maxLen=byLen.get(len).get(base);
      if(maxLen!=null){
        sameCover=true;
        if(p.len<=maxLen) return {status:'VALID_AUTHORIZED',family:p.family,prefixLen:p.len,matchedVrpLen:len,maxLength:maxLen};
      }
    }
  }
  if(sameCover) return {status:'INVALID_LENGTH',family:p.family,prefixLen:p.len};
  for(const len of globalLengths[p.family]){
    if(len>p.len) continue;
    const base=mask(p.base,p.bits,len);
    if(globalCover.get(p.family+'|'+len)?.has(base)) return {status:'INVALID_ORIGIN',family:p.family,prefixLen:p.len,coveringVrpLen:len};
  }
  return {status:'NOT_FOUND',family:p.family,prefixLen:p.len};
}

const risSources=[
  {id:'RIPE_RIS_IPV4',family:4,url:'https://www.ris.ripe.net/dumps/riswhoisdump.IPv4.gz'},
  {id:'RIPE_RIS_IPV6',family:6,url:'https://www.ris.ripe.net/dumps/riswhoisdump.IPv6.gz'},
];
const risReceipts=[];
const seen=new Set();
const counts={VALID_AUTHORIZED:0,INVALID_LENGTH:0,INVALID_ORIGIN:0,NOT_FOUND:0};
const familyCounts={4:{VALID_AUTHORIZED:0,INVALID_LENGTH:0,INVALID_ORIGIN:0,NOT_FOUND:0},6:{VALID_AUTHORIZED:0,INVALID_LENGTH:0,INVALID_ORIGIN:0,NOT_FOUND:0}};
const samples={VALID_AUTHORIZED:[],INVALID_LENGTH:[],INVALID_ORIGIN:[],NOT_FOUND:[]};
const originAgg=new Map();
let rawRows=0,routeParseFailures=0;
for(const src of risSources){
  const r=await fetchBuf(src.url,{timeout:180000});
  risReceipts.push({id:src.id,family:src.family,...r,body:undefined});
  if(!r.ok||!r.body) throw new Error('RIS source failed '+src.id);
  const raw=zlib.gunzipSync(r.body).toString('utf8');
  for(const line0 of raw.split(/\r?\n/)){
    const line=line0.trim();
    if(!line||line.startsWith('%')) continue;
    const f=line0.split('\t'); if(f.length<3) continue;
    const origin=normalizeAsn(f[0]); const prefix=String(f[1]??'').trim();
    if(!origin||!prefix.includes('/')) continue;
    rawRows++;
    const key=prefix+'|'+origin;
    if(seen.has(key)) continue;
    seen.add(key);
    let c;
    try{c=classify(prefix,origin);}catch{routeParseFailures++;continue;}
    counts[c.status]++; familyCounts[c.family][c.status]++;
    const oa=originAgg.get(origin)??{total:0,VALID_AUTHORIZED:0,INVALID_LENGTH:0,INVALID_ORIGIN:0,NOT_FOUND:0};
    oa.total++;oa[c.status]++;originAgg.set(origin,oa);
    h.update(prefix+'|'+origin+'|'+c.status+'|'+String(c.matchedVrpLen??'')+'|'+String(c.maxLength??'')+'\n');
    if(samples[c.status].length<512){
      const p=projectInternetIdentityHierarchical({type:'cidr',value:prefix});
      const a=projectInternetIdentityHierarchical({type:'asn',value:origin});
      samples[c.status].push({
        schema:'deus-bgp-rpki-relation-sample/1',prefix,origin,status:c.status,
        prefixResourceKey:p.resourceKey,prefixSlot:p.supercellId,prefixMicrocell:p.microcellId,
        asnResourceKey:a.resourceKey,asnSlot:a.supercellId,asnMicrocell:a.microcellId,
        matchedVrpLen:c.matchedVrpLen??null,maxLength:c.maxLength??null,coveringVrpLen:c.coveringVrpLen??null,
        source:'RIPE_RISWHOIS_DAILY_DUMP + PUBLIC_RPKI_BULK',
        truthBoundary:'RPKI_ORIGIN_VALIDATION_NE_ROUTE_REACHABILITY_NE_HOST_LIVENESS_NE_CONTROL_NE_EXECUTION_AUTHORITY'
      });
    }
  }
}
const classified=Object.values(counts).reduce((a,b)=>a+b,0);
const topOrigins=[...originAgg.entries()].map(([origin,x])=>({origin,...x,invalid:x.INVALID_LENGTH+x.INVALID_ORIGIN})).sort((a,b)=>b.invalid-a.invalid||b.total-a.total).slice(0,100);
const registry=registerParticipationBatch([
  {type:'service',value:'internet-routing-source:RIPE_RISWHOIS_DAILY',evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',serviceHint:true,source:'GLOBAL_BGP_RPKI_JOIN_V1',sourceEvidenceRef:'https://www.ris.ripe.net/dumps/',observedAt:new Date().toISOString(),freshnessState:'FRESH_SOURCE',metadata:{uniqueObservedRoutes:classified}},
  {type:'service',value:'internet-routing-source:'+rpki.source.id,evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',serviceHint:true,source:'GLOBAL_BGP_RPKI_JOIN_V1',sourceEvidenceRef:rpki.source.url,observedAt:new Date().toISOString(),freshnessState:'FRESH_SOURCE',metadata:{vrps:vrps.length,indexed}},
]);

const sampleRows=Object.values(samples).flat();
fs.writeFileSync(OUT+'/samples.jsonl',sampleRows.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/top-invalid-origins.json',JSON.stringify(topOrigins,null,2)+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');

const manifest={
  schema:'deus-global-bgp-rpki-relation-join/1',
  generatedAt:new Date().toISOString(),
  rpki:{source:rpki.source.id,url:rpki.source.url,status:rpki.result.status,bytes:rpki.result.bytes,sha256:rpki.result.sha256,totalVrps:vrps.length,indexed,parseFailures,attempts:rpki.attempts},
  ris:{receipts:risReceipts,rawRows,uniqueObservedRoutes:classified,routeParseFailures},
  validation:{counts,familyCounts,classifierDigest:h.digest('hex'),sampleRows:sampleRows.length,topInvalidOrigins:topOrigins.length},
  registry:registry.counts,
  semantics:{
    VALID_AUTHORIZED:'Observed route origin is authorized by at least one covering VRP and route prefix length is within maxLength.',
    INVALID_LENGTH:'A same-origin covering VRP exists but route prefix length exceeds all matching maxLength bounds.',
    INVALID_ORIGIN:'At least one covering VRP exists but none covers with the observed origin ASN.',
    NOT_FOUND:'No covering VRP was found in the selected public RPKI snapshot.'
  },
  truthBoundary:'RIPE_RIS_OBSERVED_ROUTE_NE_GLOBAL_GROUND_TRUTH__RPKI_VALIDATION_NE_ROUTE_REACHABILITY__RELATION_JOIN_NE_CONTROL_OR_COMPUTE_AUTHORITY'
};
manifest.manifestDigest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(classified<500000) throw new Error('observed-route coverage gate '+classified);
if(vrps.length<500000) throw new Error('RPKI gate '+vrps.length);
if(counts.VALID_AUTHORIZED<100000) throw new Error('valid classification unexpectedly small '+counts.VALID_AUTHORIZED);
if(registry.counts.executionAdmitted!==0) throw new Error('data-only join must not admit execution');

console.log(JSON.stringify({verdict:'PASS',vrps:vrps.length,observed:classified,counts,familyCounts,classifierDigest:manifest.validation.classifierDigest,manifestDigest:manifest.manifestDigest,registry:registry.counts}));
