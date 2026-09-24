import fs from 'node:fs';
import { createHash, X509Certificate } from 'node:crypto';
import { projectInternetIdentityHierarchical } from '../lib/internet-functional-fabric.mjs';
import { registerParticipationBatch } from '../lib/universal-participation-registry.mjs';

const OUT='.deus/global-ct-stratified-member/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-CT-Stratified-Member/1.0','accept':'application/json,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');
const day=new Date().toISOString().slice(0,10);

async function fetchBuf(url,{timeout=15000}={}){
  const t=Date.now();
  try{
    const r=await fetch(url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,body:b};
  }catch(e){return {ok:false,status:null,url,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),body:null};}
}
function json(b){try{return JSON.parse(b.toString('utf8'));}catch{return null;}}
async function mapLimit(items,limit,fn){
  const out=new Array(items.length); let next=0;
  async function worker(){
    while(true){
      const i=next++; if(i>=items.length)return;
      try{out[i]=await fn(items[i],i);}catch(e){out[i]={ok:false,error:String(e?.message||e)};}
    }
  }
  await Promise.all(Array.from({length:Math.min(limit,items.length)},worker));
  return out;
}
function u24(b,o){return b.readUIntBE(o,3);}
function parseLeafCertificate(entry){
  const leaf=Buffer.from(entry.leaf_input,'base64');
  if(leaf.length<12) throw new Error('leaf_input too short');
  const version=leaf[0], leafType=leaf[1];
  if(version!==0||leafType!==0) throw new Error('unsupported leaf');
  const entryType=leaf.readUInt16BE(10);
  if(entryType===0){
    if(leaf.length<15) throw new Error('x509 leaf short');
    const len=u24(leaf,12); if(len<=0||15+len>leaf.length) throw new Error('bad x509 leaf length');
    return {der:leaf.subarray(15,15+len),entryType:'x509_entry'};
  }
  if(entryType===1){
    const extra=Buffer.from(entry.extra_data,'base64');
    if(extra.length<3) throw new Error('precert extra short');
    const len=u24(extra,0); if(len<=0||3+len>extra.length) throw new Error('bad precert length');
    return {der:extra.subarray(3,3+len),entryType:'precert_entry'};
  }
  throw new Error('unknown entry type '+entryType);
}
function namesFromCert(cert){
  const out=[];
  const san=String(cert.subjectAltName??'');
  const re=/DNS:([^,]+)/g; let m;
  while((m=re.exec(san))){
    let n=m[1].trim().replace(/^"|"$/g,'').toLowerCase().replace(/\.+$/,'');
    if(n.startsWith('*.'))n=n.slice(2);
    if(/^[a-z0-9_.-]+\.[a-z0-9_.-]+$/.test(n))out.push(n);
  }
  const subj=String(cert.subject??'');
  for(const line of subj.split(/\n|,/)){
    const mm=line.trim().match(/^CN\s*=\s*(.+)$/i);
    if(mm){
      let n=mm[1].trim().toLowerCase().replace(/^"|"$/g,'').replace(/\.+$/,'');
      if(n.startsWith('*.'))n=n.slice(2);
      if(/^[a-z0-9_.-]+\.[a-z0-9_.-]+$/.test(n))out.push(n);
    }
  }
  return [...new Set(out)].slice(0,128);
}
function id(type,value,meta={}){
  const x=projectInternetIdentityHierarchical({type,value});
  return {...x,meta};
}
function dailyIndex(logId,size){
  const h=createHash('sha256').update(day+'|'+logId).digest();
  let n=0n; for(let i=0;i<8;i++)n=(n<<8n)|BigInt(h[i]);
  return Number(n%BigInt(size));
}

const list=await fetchBuf('https://www.gstatic.com/ct/log_list/v3/all_logs_list.json',{timeout:20000});
if(!list.ok||!list.body) throw new Error('CT log list unavailable');
const lj=json(list.body)||{};
const logs=(lj.operators||[]).flatMap(op=>(op.logs||[]).map(log=>({
  operator:op.name??null,description:log.description??null,logId:String(log.log_id??''),url:String(log.url??'').replace(/\/+$/,''),
  state:log.state??null,temporalInterval:log.temporal_interval??null
}))).filter(x=>x.logId&&x.url.startsWith('https://'));

const sth=await mapLimit(logs,10,async log=>{
  const r=await fetchBuf(log.url+'/ct/v1/get-sth',{timeout:12000});
  const j=r.ok&&r.body?json(r.body):null;
  return {...log,sth:{ok:Boolean(r.ok&&j&&Number(j.tree_size)>0),status:r.status,bytes:r.bytes,sha256:r.sha256,error:r.error??null,treeSize:Number(j?.tree_size??0),timestamp:j?.timestamp??null}};
});
const reachable=sth.filter(x=>x.sth.ok);
if(reachable.length<8) throw new Error('reachable CT logs too few '+reachable.length);

// Preserve operator diversity first; then fill by tree size.
const selected=[];
const ops=new Set();
for(const x of [...reachable].sort((a,b)=>b.sth.treeSize-a.sth.treeSize)){
  if(!ops.has(x.operator)){selected.push(x);ops.add(x.operator);}
  if(selected.length>=16)break;
}
for(const x of [...reachable].sort((a,b)=>b.sth.treeSize-a.sth.treeSize)){
  if(selected.includes(x))continue;
  selected.push(x); if(selected.length>=16)break;
}

const tasks=[];
for(const log of selected){
  const size=log.sth.treeSize;
  const idxs=[0,Math.floor((size-1)/3),Math.floor(2*(size-1)/3),size-1,dailyIndex(log.logId,size)];
  for(const index of [...new Set(idxs.filter(x=>x>=0&&x<size))]){
    tasks.push({log,index});
  }
}
const results=await mapLimit(tasks,8,async t=>{
  const r=await fetchBuf(t.log.url+`/ct/v1/get-entries?start=${t.index}&end=${t.index}`,{timeout:15000});
  if(!r.ok||!r.body)return {...t,ok:false,fetch:{...r,body:undefined}};
  const j=json(r.body); const entry=Array.isArray(j?.entries)?j.entries[0]:null;
  if(!entry)return {...t,ok:false,fetch:{...r,body:undefined},error:'no entry'};
  try{
    const parsed=parseLeafCertificate(entry);
    const cert=new X509Certificate(parsed.der);
    const certHash=sha(parsed.der);
    const names=namesFromCert(cert);
    return {...t,ok:true,fetch:{...r,body:undefined},entryType:parsed.entryType,certHash,names,
      cert:{subject:cert.subject,issuer:cert.issuer,validFrom:cert.validFrom,validTo:cert.validTo,serialNumber:cert.serialNumber,fingerprint256:cert.fingerprint256}};
  }catch(e){return {...t,ok:false,fetch:{...r,body:undefined},error:'parse:'+String(e?.message||e)};}
});

const certMap=new Map(), domainMap=new Map(), relations=[];
for(const r of results.filter(x=>x.ok)){
  const c=id('generic','x509-sha256:'+r.certHash,{source:'CERTIFICATE_TRANSPARENCY',operator:r.log.operator,logId:r.log.logId,logUrl:r.log.url,entryIndex:r.index,entryType:r.entryType,...r.cert});
  if(!certMap.has(c.resourceKey))certMap.set(c.resourceKey,{kind:'CT_CERTIFICATE',...c,certSha256:r.certHash});
  for(const name of r.names){
    const d=id('dns',name,{source:'CERTIFICATE_TRANSPARENCY',operator:r.log.operator,logId:r.log.logId,entryIndex:r.index});
    if(!domainMap.has(d.resourceKey))domainMap.set(d.resourceKey,{kind:'CT_DOMAIN_NAME',...d,domain:name});
    relations.push({
      schema:'deus-ct-certificate-domain-relation/2',relation:'CT_CERTIFICATE_NAMES_DOMAIN',
      certResourceKey:c.resourceKey,domainResourceKey:d.resourceKey,certSha256:r.certHash,domain:name,
      operator:r.log.operator,logId:r.log.logId,logUrl:r.log.url,entryIndex:r.index,entryType:r.entryType,
      observedAt:new Date().toISOString(),
      truthBoundary:'CT_LOGGED_CERTIFICATE_NAME_NE_CURRENT_DOMAIN_OWNERSHIP_NE_DNS_RESOLUTION_NE_HOST_LIVENESS_NE_CONTROL'
    });
  }
}
const relDedup=[...new Map(relations.map(x=>[x.certResourceKey+'|'+x.domainResourceKey,x])).values()];
const certs=[...certMap.values()],domains=[...domainMap.values()];
const registry=registerParticipationBatch(selected.map(log=>({
  type:'service',value:'ct-log:'+log.logId,evidenceClass:'DATA_ONLY',authorityClass:'UNKNOWN',serviceHint:true,
  source:'GLOBAL_CT_STRATIFIED_MEMBER_V1',sourceEvidenceRef:log.url,observedAt:new Date().toISOString(),freshnessState:'FRESH_SOURCE',
  metadata:{operator:log.operator,treeSize:log.sth.treeSize,sthTimestamp:log.sth.timestamp}
})));

fs.writeFileSync(OUT+'/certificates.jsonl',certs.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/domains.jsonl',domains.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/relations.jsonl',relDedup.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/sample-attempts.jsonl',results.map(x=>JSON.stringify({...x,log:{operator:x.log.operator,description:x.log.description,logId:x.log.logId,url:x.log.url,treeSize:x.log.sth.treeSize}})).join('\n')+'\n');
fs.writeFileSync(OUT+'/registrations.jsonl',registry.registrations.map(x=>JSON.stringify(x)).join('\n')+'\n');

const manifest={
  schema:'deus-global-ct-stratified-member/1',generatedAt:new Date().toISOString(),sampleDay:day,
  logList:{url:list.url,status:list.status,bytes:list.bytes,sha256:list.sha256,operators:(lj.operators||[]).length,knownLogs:logs.length,reachable:reachable.length},
  selection:{logs:selected.length,operators:new Set(selected.map(x=>x.operator)).size,tasks:tasks.length,success:results.filter(x=>x.ok).length,failed:results.filter(x=>!x.ok).length},
  members:{certificates:certs.length,domains:domains.length,relations:relDedup.length},
  registry:registry.counts,
  selectedLogs:selected.map(x=>({operator:x.operator,description:x.description,logId:x.logId,url:x.url,treeSize:x.sth.treeSize,sthTimestamp:x.sth.timestamp})),
  truthBoundary:'STRATIFIED_CT_MEMBER_SAMPLE_NE_FULL_CT_ENUMERATION__LOGGED_NAME_NE_CURRENT_DOMAIN_OWNERSHIP__CT_VISIBILITY_NE_SERVICE_LIVENESS_OR_CONTROL'
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(results.filter(x=>x.ok).length<20) throw new Error('CT entry success gate '+results.filter(x=>x.ok).length);
if(certs.length<20) throw new Error('CT certificate gate '+certs.length);
if(relDedup.length<20) throw new Error('CT relation gate '+relDedup.length);
if(registry.counts.executionAdmitted!==0) throw new Error('CT data-only registry must not admit execution');

console.log(JSON.stringify({verdict:'PASS',knownLogs:logs.length,reachable:reachable.length,selectedLogs:selected.length,operators:manifest.selection.operators,tasks:tasks.length,success:manifest.selection.success,certificates:certs.length,domains:domains.length,relations:relDedup.length,registry:registry.counts,digest:manifest.digest}));
