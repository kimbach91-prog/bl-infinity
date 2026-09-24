import fs from 'node:fs';
import { createHash } from 'node:crypto';

const SEED_PATH='runtime/federation/data/global-internet-validator-seed-v1.json';
const OUT='.deus/global-internet-validator-delta/v2';
fs.mkdirSync(OUT,{recursive:true});
const seed=JSON.parse(fs.readFileSync(SEED_PATH,'utf8'));
const UA={'user-agent':'DEUS-Global-Internet-Validator-Delta/2.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function conditionalRead(s){
  const headers={...UA};
  const hasValidator=Boolean(s.etag||s.lastModified);
  if(s.etag) headers['if-none-match']=s.etag;
  if(s.lastModified) headers['if-modified-since']=s.lastModified;
  const started=Date.now();
  try{
    const r=await fetch(s.url,{headers,redirect:'follow',signal:AbortSignal.timeout(25000)});
    const currentEtag=r.headers.get('etag');
    const currentLastModified=r.headers.get('last-modified');
    const currentLength=r.headers.get('content-length');
    if(r.status===304){
      return {
        ...s,ok:true,status:304,finalUrl:r.url||s.url,hasValidator,usedConditional:true,
        bodyFetched:false,bodyBytesDownloaded:0,sha256:s.sha256,
        etag:currentEtag||s.etag||null,lastModified:currentLastModified||s.lastModified||null,
        contentLength:currentLength||null,ms:Date.now()-started,
        deltaState:'UNCHANGED_VALIDATOR',
        estimatedBodyBytesAvoided:Number(s.bytes||0),
      };
    }
    const b=Buffer.from(await r.arrayBuffer());
    const currentSha=sha(b);
    let deltaState;
    if(!r.ok) deltaState='REGRESSED_HTTP_'+String(r.status);
    else if(currentSha===s.sha256) deltaState='UNCHANGED_BODY_HASH';
    else deltaState='CONTENT_CHANGED';
    return {
      ...s,ok:r.ok,status:r.status,finalUrl:r.url,hasValidator,usedConditional:hasValidator,
      bodyFetched:true,bodyBytesDownloaded:b.length,sha256:currentSha,
      previousSha256:s.sha256,etag:currentEtag,lastModified:currentLastModified,
      contentLength:currentLength,ms:Date.now()-started,deltaState,
      estimatedBodyBytesAvoided:0,
    };
  }catch(e){
    return {
      ...s,ok:false,status:null,finalUrl:null,hasValidator,usedConditional:hasValidator,
      bodyFetched:false,bodyBytesDownloaded:0,sha256:null,previousSha256:s.sha256,
      etag:s.etag||null,lastModified:s.lastModified||null,contentLength:null,
      ms:Date.now()-started,error:String(e?.message||e),deltaState:'REGRESSED_UNREACHABLE',
      estimatedBodyBytesAvoided:0,
    };
  }
}

const rows=[];
for(const s of seed.sources) rows.push(await conditionalRead(s));

const counts={};
for(const r of rows) counts[r.deltaState]=(counts[r.deltaState]||0)+1;
const changed=rows.filter(r=>r.deltaState==='CONTENT_CHANGED'||r.deltaState.startsWith('REGRESSED_'));
const changedClasses=[...new Set(changed.map(r=>r.class))];
const conditionalEligible=rows.filter(r=>r.hasValidator).length;
const validator304=rows.filter(r=>r.deltaState==='UNCHANGED_VALIDATOR').length;
const bodyFetchCount=rows.filter(r=>r.bodyFetched).length;
const bodyBytesDownloaded=rows.reduce((n,r)=>n+Number(r.bodyBytesDownloaded||0),0);
const estimatedBodyBytesAvoided=rows.reduce((n,r)=>n+Number(r.estimatedBodyBytesAvoided||0),0);
const fallbackFullHash=rows.filter(r=>!r.hasValidator).length;
const reachable=rows.filter(r=>r.ok).length;

const nextSeed={
  schema:'deus-global-internet-validator-seed/2',
  generatedAt:new Date().toISOString(),
  parentSeedDigest:sha(Buffer.from(JSON.stringify(seed))),
  baselineDigest:seed.baselineDigest,
  sourceSnapshotDigest:seed.sourceSnapshotDigest,
  sources:rows.map(r=>({
    id:r.id,class:r.class,url:r.url,sha256:r.sha256||r.previousSha256||null,ok:r.ok,
    etag:r.etag||null,lastModified:r.lastModified||null,contentLength:r.contentLength||null,
    bytes:r.bodyFetched?Number(r.bodyBytesDownloaded||0):Number(r.bytes||0),
  })),
};
nextSeed.digest=sha(Buffer.from(JSON.stringify(nextSeed)));

const manifest={
  schema:'deus-global-internet-validator-delta/2',
  generatedAt:nextSeed.generatedAt,
  sources:rows.length,reachable,conditionalEligible,validator304,bodyFetchCount,
  fallbackFullHash,bodyBytesDownloaded,estimatedBodyBytesAvoided,
  stateCounts:counts,deltaCount:changed.length,changedClasses,changedSources:changed.map(r=>r.id),
  efficiency:{
    bodyFetchFraction:rows.length?bodyFetchCount/rows.length:1,
    conditional304Fraction:conditionalEligible?validator304/conditionalEligible:0,
    previousSnapshotBytes:seed.sources.reduce((n,s)=>n+Number(s.bytes||0),0),
  },
  nextSeedDigest:nextSeed.digest,
  rows,
  truthBoundary:'HTTP_304_PROVES_REPRESENTATION_NOT_MODIFIED_UNDER_SERVER_VALIDATOR__HASH_DELTA_NE_SEMANTIC_CHANGE__SOURCE_DELTA_NE_EXECUTION_AUTHORITY',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));

fs.writeFileSync(OUT+'/delta-v2.jsonl',rows.map(r=>JSON.stringify(r)).join('\n')+'\n');
fs.writeFileSync(OUT+'/validator-next.json',JSON.stringify(nextSeed,null,2)+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(rows.length!==29) throw new Error('expected 29 sources');
if(reachable<20) throw new Error('too few reachable sources');
if(conditionalEligible<15) throw new Error('validator coverage unexpectedly low: '+conditionalEligible);
if(bodyFetchCount>=29) throw new Error('validator-aware run avoided zero body fetches');
if(validator304<1) throw new Error('no 304 validator hit; optimization unproven');

console.log(JSON.stringify({
  verdict:'PASS',sources:rows.length,reachable,conditionalEligible,validator304,
  bodyFetchCount,fallbackFullHash,bodyBytesDownloaded,estimatedBodyBytesAvoided,
  stateCounts:counts,deltaCount:changed.length,changedClasses,digest:manifest.digest,
  nextSeedDigest:nextSeed.digest
}));
