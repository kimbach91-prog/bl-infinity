import fs from 'node:fs';
import { createHash } from 'node:crypto';

const SOURCES=[];
const OUT='.deus/global-offer-discovery/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Offer-Discovery/1.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function probe(url){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(12000)});
    const b=Buffer.from(await r.arrayBuffer());
    return {
      url,ok:r.ok,status:r.status,finalUrl:r.url,contentType:r.headers.get('content-type'),
      bytes:b.length,sha256:sha(b),ms:Date.now()-t,
      class:r.ok?'OFFER_SOURCE_REACHABLE':'OFFER_SOURCE_HOLD',
      authority:'PUBLIC_SOURCE_ONLY',
      executionAdmitted:false,
      truthBoundary:'SOURCE_REACHABLE_NE_COMPUTE_OFFER_NE_LEASE_NE_EXECUTION_AUTHORITY',
    };
  }catch(e){
    return {url,ok:false,error:String(e?.message||e),ms:Date.now()-t,class:'OFFER_SOURCE_HOLD',authority:'PUBLIC_SOURCE_ONLY',executionAdmitted:false};
  }
}
const results=[];
for(const url of SOURCES) results.push(await probe(url));
const reachable=results.filter(x=>x.ok);
const manifest={
  schema:'deus-global-compute-offer-discovery/1',
  generatedAt:new Date().toISOString(),
  sourceCount:SOURCES.length,
  reachableCount:reachable.length,
  holdCount:results.length-reachable.length,
  results,
  decision:'DISCOVERY_ONLY',
  next:'Normalize provider-specific offer metadata where an intended public API exists; paid/authorized jobs remain separate.',
  truthBoundary:'DISCOVERED_SOURCE_NE_CURRENT_CAPACITY__NO_SPEND__NO_ARBITRARY_DEVICE_CONTACT__ADMISSION_REQUIRES_ACCORD_CANARY_LEASE_RECEIPT',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/sources.jsonl',results.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
if(SOURCES.length===0) throw new Error('No canonical offer sources available');
if(reachable.length===0) throw new Error('No canonical offer source reachable');
console.log(JSON.stringify({verdict:'PASS',sources:SOURCES.length,reachable:reachable.length,hold:results.length-reachable.length,digest:manifest.digest}));
