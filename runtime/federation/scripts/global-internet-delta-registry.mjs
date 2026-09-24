import fs from 'node:fs';
import { createHash } from 'node:crypto';

const SEED=JSON.parse(fs.readFileSync('runtime/federation/config/global-internet-delta-seed-v1.json','utf8'));
const OUT='.deus/global-internet-delta/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Internet-Delta/1.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function fetchOne(source){
  const urls=[source.url,...(source.fallbacks||[])];
  const attempts=[];
  for(const url of urls){
    const started=Date.now();
    try{
      const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(30000)});
      const b=Buffer.from(await r.arrayBuffer());
      const a={url,ok:r.ok,status:r.status,bytes:b.length,sha256:sha(b),ms:Date.now()-started,error:null};
      attempts.push(a);
      if(r.ok) return {result:a,attempts};
    }catch(e){attempts.push({url,ok:false,status:null,bytes:0,sha256:null,ms:Date.now()-started,error:String(e?.message||e)});}
  }
  return {result:null,attempts};
}

const now=Date.now(), decisions=[], nextSources=[];
for(const source of SEED.sources){
  const ageMs=Math.max(0,now-Date.parse(source.lastVerifiedAt));
  const due=!source.ok || ageMs>=Number(source.ttlHours||24)*3600000;
  if(!due){
    decisions.push({id:source.id,class:source.class,state:'SKIP_FRESH_NOT_DUE',ageMs,ttlHours:source.ttlHours,priorSha256:source.sha256,bytesFetched:0});
    nextSources.push(source);
    continue;
  }
  const fetched=await fetchOne(source);
  if(!fetched.result){
    decisions.push({id:source.id,class:source.class,state:source.ok?'REFRESH_FAILED':'STILL_HELD',ageMs,ttlHours:source.ttlHours,attempts:fetched.attempts,bytesFetched:fetched.attempts.reduce((n,x)=>n+(x.bytes||0),0)});
    nextSources.push({...source,lastAttemptAt:new Date().toISOString(),lastAttempts:fetched.attempts});
    continue;
  }
  const x=fetched.result;
  const state=!source.ok?'RECOVERED_HELD':(x.sha256===source.sha256?'UNCHANGED_SHA':'CHANGED_SHA');
  decisions.push({id:source.id,class:source.class,state,ageMs,ttlHours:source.ttlHours,previousSha256:source.sha256,newSha256:x.sha256,previousBytes:source.bytes,newBytes:x.bytes,usedUrl:x.url,attempts:fetched.attempts,bytesFetched:x.bytes});
  nextSources.push({...source,url:x.url,ok:true,status:x.status,bytes:x.bytes,sha256:x.sha256,lastVerifiedAt:new Date().toISOString(),lastAttemptAt:new Date().toISOString(),lastAttempts:fetched.attempts});
}

const counts={};
for(const d of decisions) counts[d.state]=(counts[d.state]??0)+1;
const fetched=decisions.filter(x=>!x.state.startsWith('SKIP_'));
const bytesFetched=fetched.reduce((n,x)=>n+Number(x.bytesFetched||0),0);
const classes=[...new Set(SEED.sources.map(x=>x.class))];
const manifest={
  schema:'deus-global-internet-delta-registry/1',
  generatedAt:new Date().toISOString(),
  baselineDigest:SEED.baselineDigest,
  sources:SEED.sources.length,
  classes,
  counts,
  fetchedSources:fetched.length,
  skippedFresh:counts.SKIP_FRESH_NOT_DUE??0,
  bytesFetched,
  decisions,
  truthBoundary:'TTL_SKIP_MEANS_NOT_DUE_NE_PROVEN_UNCHANGED__UNCHANGED_REQUIRES_BODY_SHA_MATCH__HELD_RETRY_IS_SOURCE_SCOPED__DELTA_REGISTRY_NE_EXECUTION_AUTHORITY',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/decisions.jsonl',decisions.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/next-seed.json',JSON.stringify({...SEED,generatedAt:manifest.generatedAt,parentBaselineDigest:SEED.baselineDigest,deltaDigest:manifest.digest,sources:nextSources},null,2)+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(SEED.sources.length!==29) throw new Error('unexpected seed cardinality');
if((counts.SKIP_FRESH_NOT_DUE??0)===0) throw new Error('delta registry did not skip any fresh source');
if(decisions.some(x=>x.state==='CHANGED_SHA'&&x.newSha256===x.previousSha256)) throw new Error('invalid changed-state digest');

console.log(JSON.stringify({verdict:'PASS',sources:manifest.sources,classes:classes.length,counts,fetchedSources:manifest.fetchedSources,skippedFresh:manifest.skippedFresh,bytesFetched,digest:manifest.digest}));
