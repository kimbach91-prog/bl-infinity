import { createHash } from 'node:crypto';
import fs from 'node:fs';

const OUT='.deus/web-trust-partition/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Web-Trust-Partition-Fabric/1.0','accept':'*/*'};

function sha256(value){return createHash('sha256').update(value).digest('hex');}
function xmlText(x){return String(x).replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'");}
function xmlTags(xml,tag){
  const re=new RegExp('<'+tag+'>([\\s\\S]*?)<\\/'+tag+'>','g');
  return [...xml.matchAll(re)].map(m=>xmlText(m[1]));
}
function stableDigest(rows,keys){
  const lines=rows.map(r=>keys.map(k=>String(r[k]??'')).join('|')).sort();
  return sha256(Buffer.from(lines.join('\n')));
}
async function fetchBytes(url,{timeout=30000,accept='*/*'}={}){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:{...UA,accept},signal:AbortSignal.timeout(timeout)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:true,url,status:r.status,bytes:b.length,sha256:sha256(b),ms:Date.now()-started,body:b,contentType:r.headers.get('content-type')};
  }catch(e){
    return {ok:false,url,error:String(e?.message||e),ms:Date.now()-started};
  }
}
function resource(type,value){
  const canonical=String(type).toLowerCase()+'|'+String(value).trim().toLowerCase();
  const resourceKey=sha256(Buffer.from(canonical));
  const keyInt=BigInt('0x'+resourceKey);
  const supercell=(keyInt%1000000000000n).toString();
  const microcell=((keyInt/1000000000000n)%(1n<<64n)).toString();
  return {resourceKey,supercellId:supercell,microcellId:microcell};
}
function stateOf(log){
  const state=log?.state&&typeof log.state==='object'?Object.keys(log.state)[0]:null;
  return state||'unknown';
}
async function mapLimit(items,limit,fn){
  const out=new Array(items.length);
  let next=0;
  async function worker(){
    while(true){
      const i=next++;
      if(i>=items.length) return;
      try{out[i]=await fn(items[i],i);}catch(e){out[i]={error:String(e?.message||e)};}
    }
  }
  await Promise.all(Array.from({length:Math.min(limit,items.length||1)},worker));
  return out;
}

// -------- Common Crawl partition fabric --------
const col=await fetchBytes('https://index.commoncrawl.org/collinfo.json',{accept:'application/json'});
if(!col.ok) throw new Error('Common Crawl collinfo unavailable: '+col.error);
const collections=JSON.parse(col.body.toString('utf8'));
if(!Array.isArray(collections)||!collections.length) throw new Error('Common Crawl collections empty');
const latest=collections[0];
const crawlId=String(latest.id||'');
if(!/^CC-MAIN-\d{4}-\d{2}$/.test(crawlId)) throw new Error('unexpected latest crawl id '+crawlId);
const prefix='cc-index/table/cc-main/warc/crawl='+crawlId+'/subset=warc/';
let token=null;
let listPages=0;
const ccObjects=[];
const ccListReceipts=[];
do{
  const u=new URL('https://commoncrawl.s3.amazonaws.com/');
  u.searchParams.set('list-type','2');
  u.searchParams.set('prefix',prefix);
  u.searchParams.set('max-keys','1000');
  if(token)u.searchParams.set('continuation-token',token);
  const page=await fetchBytes(u.toString(),{accept:'application/xml,text/xml,*/*',timeout:60000});
  ccListReceipts.push({url:u.toString(),ok:page.ok,status:page.status??null,bytes:page.bytes??0,sha256:page.sha256??null,error:page.error??null});
  if(!page.ok) throw new Error('Common Crawl S3 list failed: '+page.error);
  const xml=page.body.toString('utf8');
  const blocks=[...xml.matchAll(/<Contents>([\s\S]*?)<\/Contents>/g)].map(m=>m[1]);
  for(const b of blocks){
    const key=xmlTags(b,'Key')[0]; if(!key)continue;
    const size=Number(xmlTags(b,'Size')[0]||0);
    const etag=(xmlTags(b,'ETag')[0]||'').replace(/^"|"$/g,'');
    const modified=xmlTags(b,'LastModified')[0]||null;
    const r=resource('commoncrawl_partition',key);
    ccObjects.push({
      schema:'deus-commoncrawl-partition/1',
      crawlId,subset:'warc',key,size,etag,lastModified:modified,
      ...r,
      accessUrl:'https://data.commoncrawl.org/'+key,
      materializedRows:0,
      state:'WARM_PARTITION_DESCRIPTOR',
      truthBoundary:'PARTITION_OBJECT_NE_URL_ROWS_MATERIALIZED__COMMONCRAWL_CAPTURE_NE_CURRENT_SITE_LIVENESS_NE_EXECUTION_AUTHORITY',
    });
  }
  const truncated=(xmlTags(xml,'IsTruncated')[0]||'false').toLowerCase()==='true';
  token=truncated?(xmlTags(xml,'NextContinuationToken')[0]||null):null;
  listPages++;
  if(listPages>100)throw new Error('Common Crawl listing pagination runaway');
}while(token);
if(ccObjects.length<1) throw new Error('Common Crawl partition listing empty');

const ccManifest={
  schema:'deus-commoncrawl-partition-fabric/1',
  generatedAt:new Date().toISOString(),
  crawlId,
  collectionName:latest.name??null,
  cdxApi:latest['cdx-api']??null,
  indexUrl:latest.index??null,
  partitionPrefix:prefix,
  partitionObjects:ccObjects.length,
  partitionBytes:ccObjects.reduce((n,x)=>n+BigInt(x.size||0),0n).toString(),
  objectDigest:stableDigest(ccObjects,['key','size','etag','resourceKey']),
  sourceReceipts:{
    collinfo:{url:col.url,status:col.status,bytes:col.bytes,sha256:col.sha256},
    s3List:ccListReceipts,
  },
  storageModel:'WARM_PARTITION_DESCRIPTORS__URL_ROWS_MATERIALIZE_ONLY_ON_QUERY_OR_PARTITION_READ',
  truthBoundary:'LATEST_CRAWL_PARTITIONS_MAPPED_NE_ALL_WEB_URLS_MATERIALIZED__ARCHIVED_PAGE_NE_LIVE_PAGE',
};
ccManifest.manifestDigest=sha256(Buffer.from(JSON.stringify(ccManifest)));
fs.writeFileSync(OUT+'/commoncrawl-partitions.jsonl',ccObjects.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/commoncrawl-manifest.json',JSON.stringify(ccManifest,null,2)+'\n');

// -------- Certificate Transparency generative log fabric --------
const ctList=await fetchBytes('https://www.gstatic.com/ct/log_list/v3/all_logs_list.json',{accept:'application/json'});
if(!ctList.ok) throw new Error('Chrome all_logs_list unavailable: '+ctList.error);
const ctJson=JSON.parse(ctList.body.toString('utf8'));
const ctLogs=[];
for(const op of (ctJson.operators||[])){
  for(const log of (op.logs||[])){
    const logId=String(log.log_id||'');
    const url=String(log.url||'');
    if(!logId||!url)continue;
    ctLogs.push({
      operator:op.name??null,
      description:log.description??null,
      logId,url,key:log.key??null,mmd:log.mmd??null,
      state:stateOf(log),
      stateDetail:log.state??null,
      temporalInterval:log.temporal_interval??null,
    });
  }
}
const sthResults=await mapLimit(ctLogs,8,async(log)=>{
  const url=log.url.replace(/\/+$/,'')+'/ct/v1/get-sth';
  const r=await fetchBytes(url,{accept:'application/json',timeout:10000});
  if(!r.ok)return {ok:false,url,error:r.error??('HTTP '+r.status),status:r.status??null};
  try{
    const j=JSON.parse(r.body.toString('utf8'));
    return {ok:true,url,status:r.status,bytes:r.bytes,sha256:r.sha256,treeSize:String(j.tree_size??''),timestamp:String(j.timestamp??''),sha256RootHash:j.sha256_root_hash??null,treeHeadSignature:j.tree_head_signature??null};
  }catch(e){return {ok:false,url,status:r.status,error:'JSON:'+e.message};}
});
const ctRecords=ctLogs.map((log,i)=>{
  const sth=sthResults[i]||{ok:false,error:'missing'};
  const r=resource('ct_log',log.logId);
  const treeSize=sth.ok&&/^\d+$/.test(sth.treeSize)?sth.treeSize:null;
  return {
    schema:'deus-ct-log-generative-descriptor/1',
    ...log,...r,
    sth,
    entryDomain:treeSize,
    memberGenerator:treeSize?'leaf_index=0..tree_size-1; identity=ct:'+log.logId+':<leaf_index>':null,
    materializedEntries:0,
    activationClass:'PUBLIC_TRUST_OBSERVATION_ONLY',
    executionReady:false,
    truthBoundary:'CT_LOG_ENTRY_ADDRESSABILITY_NE_CERTIFICATE_MATERIALIZATION_NE_ENDPOINT_CONTROL',
  };
});
const reachable=ctRecords.filter(x=>x.sth?.ok&&x.entryDomain);
const ctManifest={
  schema:'deus-certificate-transparency-partition-fabric/1',
  generatedAt:new Date().toISOString(),
  logListVersion:ctJson.version??null,
  logListTimestamp:ctJson.log_list_timestamp??null,
  operators:(ctJson.operators||[]).length,
  knownLogs:ctRecords.length,
  sthReachable:reachable.length,
  sthFailed:ctRecords.length-reachable.length,
  nonDedupTreeSizeSum:reachable.reduce((n,x)=>n+BigInt(x.entryDomain),0n).toString(),
  descriptorDigest:stableDigest(ctRecords,['operator','logId','url','state','entryDomain','resourceKey']),
  sourceReceipt:{url:ctList.url,status:ctList.status,bytes:ctList.bytes,sha256:ctList.sha256},
  storageModel:'LOG_DESCRIPTOR_PLUS_STH__CERTIFICATE_ENTRIES_GENERATIVE_BY_LEAF_INDEX__SPARSE_FETCH_ON_TASK',
  truthBoundary:'TREE_SIZE_SUM_IS_NONDEDUP_ACROSS_LOGS__CT_ENTRY_NE_CURRENT_DOMAIN_LIVENESS_NE_EXECUTION_AUTHORITY',
};
ctManifest.manifestDigest=sha256(Buffer.from(JSON.stringify(ctManifest)));
fs.writeFileSync(OUT+'/ct-logs.jsonl',ctRecords.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/ct-manifest.json',JSON.stringify(ctManifest,null,2)+'\n');

const manifest={
  schema:'deus-web-trust-partition-fabric/1',
  generatedAt:new Date().toISOString(),
  commoncrawl:ccManifest,
  certificateTransparency:ctManifest,
  snowballNext:[
    'Common Crawl webgraph host/domain partitions',
    'Common Crawl exact URL rows only on task/query demand',
    'CT sparse certificate/domain relation fetches only when task-relevant',
  ],
  truthBoundary:'PARTITION_MAPPED_NE_MEMBER_MATERIALIZED__ARCHIVED_OR_LOGGED_NE_LIVE_NOW__VISIBLE_NE_AUTHORIZED_CONTROL',
};
manifest.manifestDigest=sha256(Buffer.from(JSON.stringify({
  cc:ccManifest.manifestDigest,ct:ctManifest.manifestDigest,
})));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({
  verdict:'PASS',
  latestCrawl:crawlId,
  commonCrawlPartitions:ccObjects.length,
  commonCrawlPartitionBytes:ccManifest.partitionBytes,
  commonCrawlDigest:ccManifest.objectDigest,
  ctKnownLogs:ctRecords.length,
  ctSthReachable:reachable.length,
  ctSthFailed:ctManifest.sthFailed,
  ctNonDedupTreeSizeSum:ctManifest.nonDedupTreeSizeSum,
  ctDigest:ctManifest.descriptorDigest,
  manifestDigest:manifest.manifestDigest,
}));
