import fs from 'node:fs';
import { createHash } from 'node:crypto';

const OUT='.deus/aihorde-public-canary/v1';
fs.mkdirSync(OUT,{recursive:true});
const API_KEY='0000000000';
const UA='DEUS-AIHorde-Canary/1.0';
const sha=x=>createHash('sha256').update(x).digest('hex');

async function req(url,{method='GET',body=null,timeout=120000,auth=true,extraHeaders={}}={}){
  const started=Date.now();
  try{
    const headers={'user-agent':UA,'client-agent':'DEUS:public-canary:1.0','accept':'application/json',...extraHeaders};
    if(auth && !headers.apikey && !headers.authorization) headers.authorization='Bearer '+API_KEY;
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

const hm=await req('https://aihorde.net/api/v2/status/models',{auth:false,timeout:20000});
receipts.push({...hm,body:undefined,stage:'horde_models'});
if(!hm.ok) throw new Error('AI Horde model status unavailable');
const activeModels=j(hm);
const modelRows=(Array.isArray(activeModels)?activeModels:[])
  .filter(x=>String(x.name||x.model||'').trim())
  .map(x=>({
    name:String(x.name||x.model),
    workers:Number(x.count??x.workers??0),
    queued:Number(x.queued??0),
    performance:Number(x.performance??0),
    jobs:Number(x.jobs??0),
    eta:Number(x.eta??0),
  }))
  .sort((a,b)=>{
    if((b.workers>0)!==(a.workers>0)) return (b.workers>0)?1:-1;
    if(a.queued!==b.queued) return a.queued-b.queued;
    if(b.workers!==a.workers) return b.workers-a.workers;
    return b.performance-a.performance;
  });
if(modelRows.length===0) throw new Error('No active text model candidate discovered');

const attempts=[];
let result=null;
for(const candidate of modelRows.slice(0,8)){
  const submitBody={
    prompt:'Reply with exactly this token and nothing else: DEUS_CANARY_OK',
    trusted_workers:false,
    models:[candidate.name],
    dry_run:false,
    params:{n:1,max_context_length:256,max_length:12,temperature:0.01},
  };
  const submitted=await req('https://aihorde.net/api/v2/generate/text/async',{
    method:'POST',
    body:submitBody,
    timeout:20000,
    auth:false,
    extraHeaders:{apikey:API_KEY,'Client-Agent':UA},
  });
  const attempt={model:candidate.name,submitOk:submitted.ok,submitStatus:submitted.status,submitBytes:submitted.bytes,submitSha256:submitted.sha256,submitMs:submitted.ms,error:submitted.error??null};
  if(!submitted.ok){
    attempt.responsePreview=submitted.body?submitted.body.toString('utf8').slice(0,500):null;
    attempts.push(attempt);
    continue;
  }
  const sj=j(submitted);
  const id=sj?.id;
  attempt.requestId=id??null;
  if(!id){attempt.error='submit succeeded without request id';attempts.push(attempt);continue;}
  const pollStarted=Date.now();
  let status=null;
  while(Date.now()-pollStarted<90000){
    const st=await req('https://aihorde.net/api/v2/generate/text/status/'+encodeURIComponent(id),{auth:false,timeout:15000});
    if(st.ok){
      status=j(st);
      if(status?.done===true || status?.faulted===true) break;
    }else{
      attempt.pollError=st.error??('HTTP '+st.status);
    }
    await new Promise(r=>setTimeout(r,1000));
  }
  attempt.pollMs=Date.now()-pollStarted;
  attempt.done=status?.done===true;
  attempt.faulted=status?.faulted===true;
  attempt.queuePosition=status?.queue_position??null;
  attempt.waitTime=status?.wait_time??null;
  const generation=(status?.generations||[])[0];
  const text=typeof generation?.text==='string'?generation.text.trim():'';
  attempt.resultLength=text.length;
  attempts.push(attempt);
  if(text){
    result={
      model:candidate.name,
      content:text,
      requestId:id,
      generationId:generation?.id??null,
      workerId:generation?.worker_id??null,
      workerName:generation?.worker_name??null,
      seed:generation?.seed??null,
      status,
      latencyMs:Date.now()-pollStarted+submitted.ms,
    };
    break;
  }
}
if(!result) throw new Error('No useful direct AI Horde text generation from first eight current model candidates');

const perf=await req('https://aihorde.net/api/v2/status/performance',{auth:false,timeout:15000});
receipts.push({...perf,body:undefined,stage:'performance'});
const manifest={
  schema:'deus-public-service-execution-canary/1',
  generatedAt:new Date().toISOString(),
  provider:'AI_HORDE',
  authorityClass:'PUBLIC_SERVICE_INTENDED',
  api:'https://aihorde.net/api/v2/generate/text/async',
  anonymous:true,
  spendCurrency:false,
  requestScope:'ONE_MINIMAL_TEXT_COMPLETION',
  heartbeat:{ok:heartbeat.ok,status:heartbeat.status,sha256:heartbeat.sha256,ms:heartbeat.ms},
  modelCandidates:modelRows.length,
  modelSelection: modelRows.slice(0,8),
  attempts,
  selectedModel:result.model,
  requestId:result.requestId,
  generationId:result.generationId,
  workerId:result.workerId,
  workerName:result.workerName,
  resultText:result.content,
  resultSha256:sha(Buffer.from(result.content)),
  latencyMs:result.latencyMs,
  performance:perf.ok?j(perf):null,
  decision:'EXECUTED_USEFUL_RESULT_CANDIDATE_FOR_INVOCATION_SCOPED_ADMISSION',
  leaseModel:'PUBLIC_SERVICE_INVOCATION_SCOPED_FRESHNESS_WINDOW_NOT_RESERVED_CAPACITY',
  truthBoundary:'ONE_PUBLIC_SERVICE_EXECUTION_NE_RESERVED_CAPACITY__ANONYMOUS_LOW_PRIORITY_NE_SLA__FRESH_HEARTBEAT_REQUIRED_PER_ADMISSION_WINDOW',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(OUT+'/result.txt',result.content+'\n');
if(!manifest.resultText) throw new Error('empty result');
console.log(JSON.stringify({verdict:'PASS',selectedModel:manifest.selectedModel,resultText:manifest.resultText,latencyMs:manifest.latencyMs,digest:manifest.digest}));
