import { createHash } from 'node:crypto';
import fs from 'node:fs';

const OUT='.deus/internet-observatory/commoncrawl-url-sample/v1';
fs.mkdirSync(OUT,{recursive:true});
const SLOT_DOMAIN=1000000000000n;
const UA='DEUS-Internet-Observatory-CommonCrawl/1.0';
const sha256=(v)=>createHash('sha256').update(v).digest('hex');
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
function identity(type,value){
  const canonical=String(type).toLowerCase()+'|'+String(value).trim().toLowerCase();
  const resourceKey=sha256(Buffer.from(canonical));
  return {type,value:String(value),resourceKey,slotId:(BigInt('0x'+resourceKey)%SLOT_DOMAIN).toString()};
}
async function read(url,accept='application/json'){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:{'user-agent':UA,accept},signal:AbortSignal.timeout(20000)});
    const body=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,body,bytes:body.length,sha256:sha256(body),ms:Date.now()-started};
  }catch(e){return {ok:false,url,error:String(e?.message||e),ms:Date.now()-started};}
}
const col=await read('https://index.commoncrawl.org/collinfo.json');
if(!col.ok) throw new Error('collinfo unavailable '+(col.status||col.error));
const collections=JSON.parse(col.body.toString('utf8'));
const latest=collections?.[0];
if(!latest?.id || !latest?.['cdx-api']) throw new Error('latest index missing');
const targets=['https://example.com/','https://commoncrawl.org/','https://www.iana.org/domains/example'];
const records=[]; const scars=[];
for(const target of targets){
  let found=[];
  for(const candidate of [target,target.replace(/^https:/,'http:')]){
    const q=new URL(latest['cdx-api']);
    q.searchParams.set('url',candidate); q.searchParams.set('output','json'); q.searchParams.set('matchType','exact');
    const r=await read(q.href,'application/x-ndjson,application/json,text/plain');
    if(!r.ok){scars.push({target:candidate,status:r.status??null,error:r.error??('HTTP '+r.status)}); await sleep(1500); continue;}
    const lines=r.body.toString('utf8').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    for(const line of lines.slice(0,2)){
      try{found.push({row:JSON.parse(line),sourceUrl:q.href,responseSha256:r.sha256});}
      catch(e){scars.push({target:candidate,error:'JSON '+e.message});}
    }
    await sleep(1500);
    if(found.length) break;
  }
  for(const x of found.slice(0,2)){
    const u=new URL(x.row.url); const canonicalUrl=u.href; const host=u.hostname.toLowerCase();
    const urlIdentity=identity('url',canonicalUrl); const hostIdentity=identity('host',host);
    records.push({schema:'deus-commoncrawl-url-member/1',crawlId:latest.id,queryTarget:target,canonicalUrl,host,urlIdentity,hostIdentity,
      observation:{timestamp:x.row.timestamp??null,status:x.row.status??null,mime:x.row.mime??null,digest:x.row.digest??null,filename:x.row.filename??null,offset:x.row.offset??null,length:x.row.length??null},
      source:{cdx:x.sourceUrl,responseSha256:x.responseSha256},classification:'OBSERVED / DATA_ONLY',truthBoundary:'ARCHIVED_URL_MEMBER_NE_LIVE_URL_NE_CURRENT_CONTENT_NE_EXECUTION_AUTHORITY'});
  }
}
if(!records.length) throw new Error('no Common Crawl URL members returned');
const identities=records.flatMap(r=>[r.urlIdentity,r.hostIdentity]);
const uniqueKeys=new Map(identities.map(x=>[x.resourceKey,x]));
const slotMap=new Map();
for(const x of uniqueKeys.values()){if(!slotMap.has(x.slotId))slotMap.set(x.slotId,new Set());slotMap.get(x.slotId).add(x.resourceKey);}
let slotCollisions=0; for(const s of slotMap.values()) if(s.size>1) slotCollisions+=s.size-1;
const memberDigest=sha256(Buffer.from(records.map(r=>[r.crawlId,r.urlIdentity.resourceKey,r.hostIdentity.resourceKey,r.observation.timestamp??''].join('|')).sort().join('\n')));
const manifest={schema:'deus-commoncrawl-url-member-sample/1',generatedAt:new Date().toISOString(),crawlId:latest.id,cdxApi:latest['cdx-api'],targets:targets.length,urlRows:records.length,relations:records.length,identityRecords:identities.length,uniqueKeys:uniqueKeys.size,uniqueSlots:slotMap.size,slotCollisions,scars:scars.length,memberDigest,collinfoSha256:col.sha256,truthBoundary:'SOURCE_MEMBER_READ_NE_LIVE_NOW__NO_HOST_PROBING__OBSERVED_NE_USABLE_NE_AUTHORITY'};
manifest.manifestDigest=sha256(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/members.jsonl',records.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/scars.json',JSON.stringify(scars,null,2)+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({verdict:'PASS',...manifest}));