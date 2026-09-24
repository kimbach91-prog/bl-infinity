import fs from 'node:fs';
import { createHash } from 'node:crypto';

const OUT='.deus/aihorde-public-canary/v1';
fs.mkdirSync(OUT,{recursive:true});
const API_KEY='0000000000';
const UA='DEUS-AIHorde-Canary/1.0';
const sha=x=>createHash('sha256').update(x).digest('hex');

async function req(url,{method='GET',body=null,timeout=120000,auth=true}={}){
  const started=Date.now();
  try{
    const headers={'user-agent':UA,'client-agent':'DEUS:public-canary:1.0','accept':'application/json'};
    if(auth) headers.authorization='Bearer '+API_KEY;
    if(body!=null) headers['content-type']='application/json';
    const r=await fetch(url,{method,headers,body:body==null?undefined:JSON.stringify(body),signal:AbortSignal.timeout(timeout)});
    const b=Buffer.from(await r.arrayBuffer());
    return {ok:r.ok,status:r.status,url:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-started,body:b,headers:{contentType:r.headers.get('content-type'),requestId:r.headers.get('x-request-id')}};
  }catch(e){return {ok:false,status:null,url,error:String(e?.message||e),bytes:0,ms:Date.now()-started};}
}
function j(r){try{return JSON.parse(r.body.toString('utf8'));}catch{return null;}}

const receipts=[];
const heartbeat=await req('https://aihorde.net/api/v2/status/heartbeat',{auth:false,timeout:15000});
receipts.push({...heartbeat,body:undefined,stage:'heartbeat'});
if(!heartbeat.ok) throw new Error('AI Horde heartbeat unavailable');

let models=await req('https://oai.aihorde.net/v1/models',{timeout:20000});
receipts.push({...models,body:undefined,stage:'oai_models'});
let modelIds=[];
if(models.ok){
  const mj=j(models);
  modelIds=(mj?.data||[]).map(x=>String(x.id||'')).filter(Boolean);
}
if(modelIds.length===0){
  const hm=await req('https://aihorde.net/api/v2/status/models',{auth:false,timeout:20000});
  receipts.push({...hm,body:undefined,stage:'horde_models_fallback'});
  const arr=j(hm);
  modelIds=(Array.isArray(arr)?arr:[]).map(x=>String(x.name||x.model||'')).filter(Boolean);
}
if(modelIds.length===0) throw new Error('No active text model candidate discovered');

let result=null,attempts=[];
for(const model of modelIds.slice(0,5)){
  const body={
    model,
    messages:[{role:'user',content:'Reply with exactly this token and nothing else: DEUS_CANARY_OK'}],
    max_tokens:12,
    temperature:0.01,
    stream:false,
  };
  const r=await req('https://oai.aihorde.net/v1/chat/completions',{method:'POST',body,timeout:120000});
  attempts.push({model,ok:r.ok,status:r.status,bytes:r.bytes,sha256:r.sha256,ms:r.ms,error:r.error??null});
  if(r.ok){
    const x=j(r);
    const content=x?.choices?.[0]?.message?.content ?? x?.choices?.[0]?.text ?? null;
    if(typeof content==='string'&&content.trim()){
      result={model,content:content.trim(),response:x,status:r.status,bytes:r.bytes,sha256:r.sha256,ms:r.ms};
      break;
    }
  }
}
if(!result) throw new Error('No useful AI Horde OpenAI-proxy completion from first five active models');

const perf=await req('https://aihorde.net/api/v2/status/performance',{auth:false,timeout:15000});
receipts.push({...perf,body:undefined,stage:'performance'});
const manifest={
  schema:'deus-public-service-execution-canary/1',
  generatedAt:new Date().toISOString(),
  provider:'AI_HORDE',
  authorityClass:'PUBLIC_SERVICE_INTENDED',
  api:'https://oai.aihorde.net/',
  anonymous:true,
  spendCurrency:false,
  requestScope:'ONE_MINIMAL_TEXT_COMPLETION',
  heartbeat:{ok:heartbeat.ok,status:heartbeat.status,sha256:heartbeat.sha256,ms:heartbeat.ms},
  modelCandidates:modelIds.length,
  attempts,
  selectedModel:result.model,
  resultText:result.content,
  resultSha256:sha(Buffer.from(result.content)),
  responseSha256:result.sha256,
  latencyMs:result.ms,
  performance:perf.ok?j(perf):null,
  decision:'EXECUTED_USEFUL_RESULT_CANDIDATE_FOR_INVOCATION_SCOPED_ADMISSION',
  leaseModel:'PUBLIC_SERVICE_HEARTBEAT_FRESHNESS_WINDOW_NOT_RESERVED_CAPACITY',
  truthBoundary:'ONE_PUBLIC_SERVICE_EXECUTION_NE_RESERVED_CAPACITY__ANONYMOUS_LOW_PRIORITY_NE_SLA__FRESH_HEARTBEAT_REQUIRED_PER_ADMISSION_WINDOW',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(OUT+'/result.txt',result.content+'\n');
if(!manifest.resultText) throw new Error('empty result');
console.log(JSON.stringify({verdict:'PASS',selectedModel:manifest.selectedModel,resultText:manifest.resultText,latencyMs:manifest.latencyMs,digest:manifest.digest}));
