import fs from 'node:fs';
import { createHash, X509Certificate } from 'node:crypto';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';

const OUT='.deus/ct-cdxj-sparse/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-CT-CDXJ-Sparse/1.0','accept':'*/*'};
function sha256(x){return createHash('sha256').update(x).digest('hex');}
async function fetchBytes(url,{timeout=15000,accept='*/*'}={}){
  const started=Date.now();
  try{
    const r=await fetch(url,{headers:{...UA,accept},signal:AbortSignal.timeout(timeout)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const body=Buffer.from(await r.arrayBuffer());
    return {ok:true,url,status:r.status,bytes:body.length,sha256:sha256(body),ms:Date.now()-started,body};
  }catch(e){return {ok:false,url,error:String(e?.message||e),ms:Date.now()-started};}
}
function readU24(buf,o){return (buf[o]<<16)|(buf[o+1]<<8)|buf[o+2];}
function dnsNamesFromCert(certBytes){
  const cert=new X509Certificate(certBytes);
  const out=new Set();
  const san=String(cert.subjectAltName||'');
  for(const part of san.split(/,\s*/)){
    const m=part.match(/^DNS:(.+)$/i);
    if(m){
      const d=m[1].trim().replace(/^\*\./,'').toLowerCase().replace(/\.$/,'');
      if(d && !d.includes(' ') && d.includes('.')) out.add(d);
    }
  }
  return {fingerprint256:cert.fingerprint256.replace(/:/g,'').toLowerCase(),subject:cert.subject,issuer:cert.issuer,dns:[...out]};
}
function certFromEntry(entry){
  const leaf=Buffer.from(entry.leaf_input,'base64');
  if(leaf.length<15) throw new Error('short leaf_input');
  const entryType=leaf.readUInt16BE(10);
  if(entryType===0){
    const n=readU24(leaf,12);
    if(n<=0||15+n>leaf.length) throw new Error('bad x509 cert length');
    return {entryType:'x509_entry',cert:leaf.subarray(15,15+n)};
  }
  if(entryType===1){
    const extra=Buffer.from(entry.extra_data,'base64');
    if(extra.length<4) throw new Error('short precert extra_data');
    const n=readU24(extra,0);
    if(n<=0||3+n>extra.length) throw new Error('bad precert length');
    return {entryType:'precert_entry',cert:extra.subarray(3,3+n)};
  }
  throw new Error('unknown entry type '+entryType);
}
function stableDigest(rows,keys){
  return sha256(Buffer.from(rows.map(r=>keys.map(k=>String(r[k]??'')).join('|')).sort().join('\n')));
}

// ---- bounded Common Crawl CDXJ/API rows ----
const domains=['example.com','iana.org','commoncrawl.org','wikipedia.org','github.com','cloudflare.com','google.com','mozilla.org'];
const cdxRows=[], cdxReceipts=[];
for(const domain of domains){
  const u=new URL('https://index.commoncrawl.org/CC-MAIN-2026-39-index');
  u.searchParams.set('url',domain+'/*');
  u.searchParams.set('output','json');
  u.searchParams.set('filter','status:200');
  u.searchParams.set('filter','mime:text/html');
  u.searchParams.set('limit','5');
  const r=await fetchBytes(u.toString(),{accept:'application/json,text/plain,*/*'});
  cdxReceipts.push({domain,url:u.toString(),ok:r.ok,status:r.status??null,bytes:r.bytes??0,sha256:r.sha256??null,error:r.error??null});
  if(!r.ok) continue;
  for(const line of r.body.toString('utf8').split(/\r?\n/)){
    if(!line.trim()) continue;
    try{
      const x=JSON.parse(line);
      const p=projectInternetIdentityHierarchical({type:'url',value:x.url});
      cdxRows.push({
        schema:'deus-commoncrawl-cdxj-member/1',
        crawl:'CC-MAIN-2026-39',queryDomain:domain,
        url:x.url,timestamp:x.timestamp??null,digest:x.digest??null,
        status:x.status??null,mime:x.mime??null,filename:x.filename??null,
        offset:x.offset??null,length:x.length??null,
        resourceKey:p.resourceKey,supercellId:p.supercellId,microcellId:p.microcellId,
        class:'OBSERVED_WEB_ARCHIVE_MEMBER',
        truthBoundary:'CRAWL_MEMBER_NE_CURRENT_URL_LIVENESS_NE_SERVICE_NE_AUTHORITY',
      });
    }catch{}
  }
}
if(cdxRows.length===0) throw new Error('zero useful Common Crawl CDXJ rows');

// ---- bounded sparse CT certificate/domain relations ----
const list=await fetchBytes('https://www.gstatic.com/ct/log_list/v3/all_logs_list.json',{accept:'application/json'});
if(!list.ok) throw new Error('CT log list unavailable: '+list.error);
const lj=JSON.parse(list.body.toString('utf8'));
const logs=[];
for(const op of (lj.operators||[])) for(const log of (op.logs||[])){
  if(log.url&&log.log_id) logs.push({operator:op.name??null,...log});
}
const ctRelations=[], ctReceipts=[], certRecords=[];
let logsUsed=0;
for(const log of logs){
  if(logsUsed>=4 || ctRelations.length>=8) break;
  const base=String(log.url).replace(/\/+$/,'');
  const sth=await fetchBytes(base+'/ct/v1/get-sth',{accept:'application/json'});
  if(!sth.ok){ctReceipts.push({log:log.description,url:base,stage:'sth',ok:false,error:sth.error});continue;}
  let sj; try{sj=JSON.parse(sth.body.toString('utf8'));}catch{continue;}
  const tree=BigInt(sj.tree_size??0);
  if(tree<=0n) continue;
  const end=tree-1n, start=end>0n?end-1n:end;
  const entries=await fetchBytes(base+'/ct/v1/get-entries?start='+start+'&end='+end,{accept:'application/json'});
  ctReceipts.push({log:log.description,url:base,stage:'entries',ok:entries.ok,status:entries.status??null,treeSize:tree.toString(),start:start.toString(),end:end.toString(),bytes:entries.bytes??0,sha256:entries.sha256??null,error:entries.error??null});
  if(!entries.ok) continue;
  let ej; try{ej=JSON.parse(entries.body.toString('utf8'));}catch{continue;}
  const arr=ej.entries||[];
  let useful=false;
  for(let i=0;i<arr.length;i++){
    try{
      const parsed=certFromEntry(arr[i]);
      const info=dnsNamesFromCert(parsed.cert);
      const certId='sha256:'+info.fingerprint256;
      const cp=projectInternetIdentityHierarchical({type:'service',value:'certificate:'+certId});
      certRecords.push({logId:log.log_id,log:log.description,leafIndex:(start+BigInt(i)).toString(),entryType:parsed.entryType,certificateId:certId,subject:info.subject,issuer:info.issuer,resourceKey:cp.resourceKey,supercellId:cp.supercellId,microcellId:cp.microcellId,dnsCount:info.dns.length});
      for(const domain of info.dns.slice(0,20)){
        const dp=projectInternetIdentityHierarchical({type:'dns',value:domain});
        ctRelations.push({
          schema:'deus-ct-certificate-domain-relation/1',
          logId:log.log_id,log:log.description,operator:log.operator,
          leafIndex:(start+BigInt(i)).toString(),entryType:parsed.entryType,
          certificateId:certId,domain,
          certificateResourceKey:cp.resourceKey,domainResourceKey:dp.resourceKey,
          domainSupercellId:dp.supercellId,domainMicrocellId:dp.microcellId,
          class:'OBSERVED_CT_CERT_DOMAIN_RELATION',
          truthBoundary:'CT_CERT_DOMAIN_RELATION_NE_CURRENT_DNS_RESOLUTION_NE_LIVE_SERVICE_NE_AUTHORITY',
        });
      }
      if(info.dns.length) useful=true;
    }catch{}
  }
  if(useful) logsUsed++;
}
if(ctRelations.length===0) throw new Error('zero useful CT certificate/domain relations');

const out={
  schema:'deus-ct-cdxj-sparse-fabric/1',
  generatedAt:new Date().toISOString(),
  commonCrawl:{crawl:'CC-MAIN-2026-39',queries:domains.length,rows:cdxRows.length,digest:stableDigest(cdxRows,['queryDomain','url','timestamp','digest','resourceKey']),receipts:cdxReceipts},
  certificateTransparency:{logListVersion:lj.version??null,logsConsidered:logs.length,logsUsed,certificates:certRecords.length,relations:ctRelations.length,relationDigest:stableDigest(ctRelations,['logId','leafIndex','certificateId','domain','domainResourceKey']),receipts:ctReceipts},
  truthBoundary:'SPARSE_PUBLIC_OBSERVATION_ONLY__NO_HOST_SCAN__NO_ENDPOINT_CONTROL__NO_EXECUTION_AUTHORITY',
};
out.manifestDigest=sha256(Buffer.from(JSON.stringify(out)));
fs.writeFileSync(OUT+'/commoncrawl-cdxj.jsonl',cdxRows.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/ct-cert-domain-relations.jsonl',ctRelations.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/ct-certificates.jsonl',certRecords.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({verdict:'PASS',cdxRows:cdxRows.length,ctCertificates:certRecords.length,ctRelations:ctRelations.length,logsUsed,manifestDigest:out.manifestDigest}));
