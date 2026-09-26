import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { fileURLToPath } from 'node:url';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';

const connectionString=process.env.BL_TEST_POSTGRES_URL||null;
const runtimeDir=fileURLToPath(new URL('..',import.meta.url));
const tenantToken='tenant-a-developer-api-token-0123456789abcdef';
const opsToken='ops-developer-api-token-0123456789abcdef';
const principalConfig=JSON.stringify([
  {id:'tenant-a-dev',tenantId:'tenant-a',tokenEnv:'TENANT_A_DEV_TOKEN',scopes:['task:submit']},
  {id:'ops-dev',tenantId:'*',tokenEnv:'OPS_DEV_TOKEN',scopes:['runtime:read']},
]);
let pool=null;

if(connectionString){
  before(async()=>{
    pool=new Pool({connectionString,max:8,application_name:'deus-dev-api-e2e'});
    const state=await openPostgresFederationState({pool,applySchema:true});
    await state.close();
  });
  beforeEach(async()=>{
    await pool.query(`
      TRUNCATE TABLE
        federation_provider_heartbeat_nonces,
        federation_jobs,
        federation_rate_limit_buckets,
        federation_budget_reservations,
        federation_contribution_ledger,
        federation_audit,
        federation_providers
      RESTART IDENTITY CASCADE
    `);
  });
  after(async()=>pool?.end());
}
const pgtest=(name,fn)=>test(name,{skip:connectionString?false:'BL_TEST_POSTGRES_URL not configured'},fn);

pgtest('versioned developer API enforces auth tenant binding and idempotency conflict',async(t)=>{
  const port=await freePort();
  const runtime=await startServer(port);
  t.after(()=>stop(runtime.child));

  const noVersion=await api(runtime.base,'POST','/v1/platform/jobs',tenantToken,{
    task:{id:'job-no-version',capability:'compute.echo',payload:{x:0},dataClass:'public'}
  },{'idempotency-key':'idem-no-version'});
  assert.equal(noVersion.status,400);
  assert.equal(noVersion.body.error.code,'API_VERSION_REQUIRED');

  const unauthorized=await api(runtime.base,'GET','/v1/platform/status',null,null,{'x-deus-api-version':'1.0.0'});
  assert.equal(unauthorized.status,401);
  assert.equal(unauthorized.body.error.code,'UNAUTHORIZED');

  const status=await api(runtime.base,'GET','/v1/platform/status',opsToken,null,{
    'x-deus-api-version':'1.2.0','x-request-id':'status-req','x-trace-id':'status-trace'
  });
  assert.equal(status.status,200);
  assert.equal(status.body.api_version,'1.0.0');
  assert.equal(status.body.request_id,'status-req');
  assert.equal(status.body.trace_id,'status-trace');
  assert.equal(status.body.data.state_backend,'postgres');
  assert.equal(status.headers.get('x-deus-api-version'),'1.0.0');

  const headers={
    'x-deus-api-version':'1.0.0',
    'x-request-id':'job-req-1',
    'x-trace-id':'job-trace-1',
    'idempotency-key':'idem-job-0001',
  };
  const task={id:'dev-job-1',capability:'compute.echo',payload:{x:1},dataClass:'public'};
  const first=await api(runtime.base,'POST','/v1/platform/jobs',tenantToken,{task},headers);
  assert.equal(first.status,202);
  assert.equal(first.body.data.job.task.tenantId,'tenant-a');
  assert.equal(first.body.meta.replay,false);

  const replay=await api(runtime.base,'POST','/v1/platform/jobs',tenantToken,{task},{...headers,'x-request-id':'job-req-2'});
  assert.equal(replay.status,200);
  assert.equal(replay.body.meta.replay,true);
  assert.equal(replay.body.data.job.id,'dev-job-1');

  const conflict=await api(runtime.base,'POST','/v1/platform/jobs',tenantToken,{
    task:{...task,payload:{x:2}}
  },{...headers,'x-request-id':'job-req-3'});
  assert.equal(conflict.status,409);
  assert.equal(conflict.body.error.code,'IDEMPOTENCY_CONFLICT');

  const cross=await api(runtime.base,'POST','/v1/platform/jobs',tenantToken,{
    task:{id:'dev-job-cross',tenantId:'tenant-b',capability:'compute.echo',payload:{x:3},dataClass:'public'}
  },{
    'x-deus-api-version':'1.0.0',
    'x-request-id':'cross-req',
    'x-trace-id':'cross-trace',
    'idempotency-key':'idem-cross-0001'
  });
  assert.equal(cross.status,403);
  assert.equal(cross.body.error.code,'TENANT_SCOPE_VIOLATION');

  const rows=await pool.query(
    "SELECT id,tenant_id,idempotency_key,task FROM federation_jobs ORDER BY id"
  );
  assert.equal(rows.rowCount,1);
  assert.equal(rows.rows[0].id,'dev-job-1');
  assert.equal(rows.rows[0].tenant_id,'tenant-a');
  assert.equal(rows.rows[0].idempotency_key,'idem-job-0001');
});

async function api(base,method,path,token,body,headers={}){
  const h={...headers};
  if(token) h.authorization=`Bearer ${token}`;
  if(body!=null) h['content-type']='application/json';
  const response=await fetch(base+path,{method,headers:h,body:body==null?undefined:JSON.stringify(body)});
  return {status:response.status,headers:response.headers,body:await response.json()};
}
async function startServer(port){
  const env={
    ...process.env,
    HOST:'127.0.0.1',
    PORT:String(port),
    BL_POSTGRES_URL:connectionString,
    BL_POSTGRES_AUTO_MIGRATE:'false',
    BL_POSTGRES_ALLOWED_DATA_CLASSES:'public',
    BL_PROVIDER_SYNC_MODE:'full',
    BL_RATE_LIMIT_MODE:'memory',
    BL_RATE_LIMIT_BURST:'100',
    BL_RATE_LIMIT_PER_SECOND:'100',
    BL_CONTROL_TOKEN:'',
    BL_CONTROL_PRINCIPALS_JSON:principalConfig,
    BL_PUBLIC_READ_SCOPES:'',
    TENANT_A_DEV_TOKEN:tenantToken,
    OPS_DEV_TOKEN:opsToken,
    DEUS_AUTONOMOUS_OBSERVER_ENABLED:'false',
  };
  const child=spawn(process.execPath,['dev-server.mjs'],{cwd:runtimeDir,env,stdio:['ignore','pipe','pipe']});
  const stderr=[];
  child.stderr.on('data',(c)=>stderr.push(c.toString()));
  await waitForLine(child,new RegExp(`listening on http://127\\.0\\.0\\.1:${port}`),15000,stderr);
  return {child,base:`http://127.0.0.1:${port}`};
}
function waitForLine(child,pattern,timeoutMs,stderr){
  return new Promise((resolve,reject)=>{
    let output='';
    const timer=setTimeout(()=>finish(new Error('startup timeout '+stderr.join(''))),timeoutMs);
    const onData=(c)=>{output+=c.toString(); if(pattern.test(output)) finish();};
    const onExit=(code)=>finish(new Error('server exited '+code+' '+stderr.join('')));
    function finish(error=null){clearTimeout(timer);child.stdout.off('data',onData);child.off('exit',onExit);error?reject(error):resolve();}
    child.stdout.on('data',onData);child.once('exit',onExit);
  });
}
function stop(child){if(child&&!child.killed)child.kill('SIGTERM');}
function freePort(){return new Promise((resolve,reject)=>{const s=net.createServer();s.unref();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const a=s.address();const p=typeof a==='object'&&a?a.port:null;s.close(()=>p?resolve(p):reject(new Error('no port')));});});}
