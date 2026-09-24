import http from 'node:http';
import { timingSafeEqual, randomUUID } from 'node:crypto';
import { loadGoogleServiceAccount, createServiceAccountTokenSource } from './lib/google-service-account.mjs';
import { GoogleSheetsCanonicalBridge } from './bridge/drive-machine-bridge.mjs';

const port=Number(process.env.PORT||8080);
const host=process.env.HOST||'0.0.0.0';
const token=String(process.env.DEUS_BRAIN3_GATEWAY_TOKEN||'');
const spreadsheetId=String(process.env.DEUS_LIVEBUS_SPREADSHEET_ID||'1pVtDbKFGECbogSR0-nrVDEecF8xQNelCux6GFUEmVrQ');
const authorityRef=String(process.env.DEUS_BRAIN3_REMOTE_AUTHORITY_REF||'AUTH-GMAIL-REMOTE-EXEC-1a0ce128e8726a83');
const maxQueryChars=Math.max(32,Math.min(2048,Number(process.env.DEUS_BRAIN3_GATEWAY_MAX_QUERY_CHARS||256)));
const ttlSeconds=Math.max(60,Math.min(900,Number(process.env.DEUS_BRAIN3_GATEWAY_QUERY_TTL_SECONDS||180)));

if(!token) throw new Error('DEUS_BRAIN3_GATEWAY_TOKEN required');
const credentials=loadGoogleServiceAccount();
if(!credentials) throw new Error('DEUS_GOOGLE_SERVICE_ACCOUNT_JSON required');

const bridge=new GoogleSheetsCanonicalBridge({
  spreadsheetId,
  tokenSource:createServiceAccountTokenSource({credentials}),
  canonicalReadRange:'90_BRAIN3_PRIVILEGE_AUTHORITY_GATES!A1:R4',
  heartbeatRange:'54_MACHINE_BRIDGE_HEALTH!A:H',
  instanceId:process.env.RAILWAY_SERVICE_ID||'brain3-public-gateway',
});

function send(res,status,body){
  res.statusCode=status;
  res.setHeader('content-type','application/json; charset=utf-8');
  res.setHeader('cache-control','no-store');
  res.setHeader('x-content-type-options','nosniff');
  res.end(JSON.stringify(body));
}
function pathname(raw){try{return new URL(raw||'/','http://localhost').pathname}catch{return raw||'/'}}
function bearer(req){
  const raw=String(req.headers.authorization||'');
  if(!raw.startsWith('Bearer ')) return false;
  const supplied=Buffer.from(raw.slice(7),'utf8');
  const expected=Buffer.from(token,'utf8');
  return supplied.length===expected.length && timingSafeEqual(supplied,expected);
}
async function jsonBody(req,max=8192){
  let size=0;const chunks=[];
  for await(const c of req){
    size+=c.length;
    if(size>max) throw new Error('body too large');
    chunks.push(c);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8')||'{}');
}
async function gateSnapshot(){
  const read=await bridge.readRange('90_BRAIN3_PRIVILEGE_AUTHORITY_GATES!A1:R4');
  const rows=read.values||[];
  return rows.slice(1,4).map(r=>({
    gateId:r?.[0]||null,state:r?.[1]||null,privilegeClass:r?.[3]||null,killSwitch:r?.[12]||null
  }));
}
async function enqueue(query){
  const jobId='JOB-BRAIN3-PUBLIC-QUERY-'+Date.now()+'-'+randomUUID().slice(0,8).toUpperCase();
  const created=new Date();const expires=new Date(created.getTime()+ttlSeconds*1000);
  const row=[
    jobId,'workstation-win-001','QUEUED',created.toISOString(),'',
    expires.toISOString(),authorityRef,
    'THIRDBRAIN_QUERY_SCOPED','SEARCH_V1',JSON.stringify([query]),
    'brain3-public-gateway','{}',30,65536,
    '','','','','','','','','','','','',0,
    'Authenticated dedicated Brain3 public gateway query.'
  ];
  const app=await bridge.appendRows({range:'84_WORKSTATION_REMOTE_JOBS!A:AB',rows:[row]});
  if(app.updatedRows!==1) throw new Error('enqueue did not append exactly one row');
  return {jobId,expiresAt:expires.toISOString()};
}
async function result(jobId){
  const read=await bridge.readRange('84_WORKSTATION_REMOTE_JOBS!A1:AB500');
  const rows=read.values||[];const headers=rows[0]||[];
  const row=rows.slice(1).find(r=>String(r?.[0]||'')===jobId);
  if(!row) return null;
  const rec={};headers.forEach((h,i)=>{rec[String(h)]=row[i]??''});
  return {
    jobId,state:rec.STATE||null,createdAt:rec.CREATED_AT_UTC||null,
    startedAt:rec.STARTED_AT_UTC||null,finishedAt:rec.FINISHED_AT_UTC||null,
    exitCode:rec.EXIT_CODE===''?null:Number(rec.EXIT_CODE),
    stdoutPreview:String(rec.STDOUT_PREVIEW||'').slice(0,32768),
    stderrPreview:String(rec.STDERR_PREVIEW||'').slice(0,8192),
    receiptId:rec.RECEIPT_ID||null,
  };
}

const server=http.createServer(async(req,res)=>{
  try{
    const path=pathname(req.url);
    if(req.method==='GET'&&path==='/health'){
      const gates=await gateSnapshot();
      return send(res,200,{ok:true,schema:'deus-brain3-public-gateway-health/1',drive:true,gates});
    }
    if(!bearer(req)) return send(res,401,{error:'authentication required'});
    if(req.method==='GET'&&path==='/brain3/gateway/status'){
      return send(res,200,{
        schema:'deus-brain3-public-gateway/1',ready:true,nodeId:'workstation-win-001',
        transport:'public-https-to-drive-queue-to-workstation-pull',
        rawWorkstationListener:false,gates:await gateSnapshot()
      });
    }
    if(req.method==='POST'&&path==='/brain3/gateway/query'){
      const body=await jsonBody(req);
      const query=String(body.query||'').trim();
      if(!query||query.length>maxQueryChars) return send(res,400,{error:'invalid query'});
      const enq=await enqueue(query);
      return send(res,202,{schema:'deus-brain3-public-gateway-job/1',accepted:true,state:'QUEUED',...enq});
    }
    if(req.method==='GET'&&path==='/brain3/gateway/result'){
      const u=new URL(req.url||'/','http://localhost');
      const jobId=String(u.searchParams.get('jobId')||'');
      if(!/^JOB-BRAIN3-PUBLIC-QUERY-[A-Za-z0-9_-]{8,128}$/.test(jobId)) return send(res,400,{error:'invalid jobId'});
      const r=await result(jobId);
      return r?send(res,200,{schema:'deus-brain3-public-gateway-result/1',...r}):send(res,404,{error:'job not found'});
    }
    return send(res,404,{error:'not found'});
  }catch(error){return send(res,500,{error:error.message})}
});

server.listen(port,host,async()=>{
  console.log(JSON.stringify({event:'DEUS_BRAIN3_PUBLIC_GATEWAY_LISTENING',port,host,serviceId:process.env.RAILWAY_SERVICE_ID||null}));
  const probe=await bridge.verifyReadWrite({receiptRef:'brain3-public-gateway-startup'}).catch(e=>({error:e.message}));
  if(probe?.error){
    console.error(JSON.stringify({event:'DEUS_BRAIN3_PUBLIC_GATEWAY_DRIVE_FAIL',error:probe.error}));
    process.exit(1);
  }
  console.log(JSON.stringify({event:'DEUS_BRAIN3_PUBLIC_GATEWAY_DRIVE_PASS',digest:probe.heartbeatDigest}));
});
