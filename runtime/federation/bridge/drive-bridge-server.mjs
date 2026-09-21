import http from 'node:http';
import { hostname } from 'node:os';
import { loadGoogleServiceAccount, createServiceAccountTokenSource } from '../lib/google-service-account.mjs';
import { GoogleSheetsCanonicalBridge } from './drive-machine-bridge.mjs';

const PORT=Number(process.env.PORT||3000);
const spreadsheetId=process.env.DEUS_LIVEBUS_SPREADSHEET_ID||'1pVtDbKFGECbogSR0-nrVDEecF8xQNelCux6GFUEmVrQ';
const intervalMs=Math.max(60_000,Number(process.env.DEUS_DRIVE_BRIDGE_INTERVAL_MS||300_000));
const instanceId=process.env.DEUS_DRIVE_BRIDGE_INSTANCE_ID||process.env.RAILWAY_SERVICE_ID||hostname();

let state={
  process:'ALIVE',
  bridge:'CREDENTIAL_GATE',
  ready:false,
  lastAttemptAt:null,
  lastSuccessAt:null,
  lastError:null,
  receipt:null,
};

let bridge=null;
try{
  const credentials=loadGoogleServiceAccount();
  if(credentials){
    bridge=new GoogleSheetsCanonicalBridge({
      spreadsheetId,
      tokenSource:createServiceAccountTokenSource({credentials}),
      instanceId,
    });
    state.bridge='INITIALIZING';
  }
}catch(error){
  state.bridge='CREDENTIAL_INVALID';
  state.lastError=error.message;
}

async function reconcile(){
  state.lastAttemptAt=new Date().toISOString();
  if(!bridge){
    state.ready=false;
    return state;
  }
  try{
    const receipt=await bridge.verifyReadWrite({
      receiptRef:process.env.DEUS_DRIVE_BRIDGE_RECEIPT_REF||'',
    });
    state={
      ...state,
      bridge:'LIVE',
      ready:true,
      lastSuccessAt:new Date().toISOString(),
      lastError:null,
      receipt,
    };
  }catch(error){
    state={
      ...state,
      bridge:error.status===401||error.status===403?'AUTH_OR_SHARE_GATE':'IO_DEGRADED',
      ready:false,
      lastError:error.message,
    };
  }
  return state;
}

const server=http.createServer(async (req,res)=>{
  if(req.url==='/healthz'){
    res.writeHead(200,{'content-type':'application/json'});
    res.end(JSON.stringify(state));
    return;
  }
  if(req.url==='/readyz'){
    const code=state.ready?200:503;
    res.writeHead(code,{'content-type':'application/json'});
    res.end(JSON.stringify(state));
    return;
  }
  if(req.url==='/reconcile' && req.method==='POST'){
    await reconcile();
    res.writeHead(state.ready?200:503,{'content-type':'application/json'});
    res.end(JSON.stringify(state));
    return;
  }
  res.writeHead(404,{'content-type':'application/json'});
  res.end(JSON.stringify({error:'not found'}));
});

server.listen(PORT,'0.0.0.0',async ()=>{
  await reconcile();
  setInterval(()=>{void reconcile();},intervalMs).unref();
  console.log(JSON.stringify({service:'DEUS_DRIVE_MACHINE_BRIDGE_V1',port:PORT,intervalMs,state:state.bridge}));
});
