import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes} from 'node:crypto';
import {CapabilityFabric} from './capability-fabric.mjs';
import {OwnerAccountAuthorityRegistry,AdaptiveTrustKernel,ADAPTIVE_TRUST_INVARIANTS} from './adaptive-trust.mjs';
import {createOwnerVault} from './owner-vault.mjs';
import {sealRecoveryEnvelope} from './recovery-envelope.mjs';

const D=path.dirname(fileURLToPath(import.meta.url)),PUB=path.join(D,'public'),HOST='127.0.0.1',PORT=Number(process.env.DEUS_OWNER_HQ_PORT||4320),cookie='deus_owner_hq',session=randomBytes(24).toString('hex'),fabric=new CapabilityFabric();
const registry=new OwnerAccountAuthorityRegistry(),trust=new AdaptiveTrustKernel({registry}),vault=createOwnerVault();
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
const auth=req=>String(req.headers.cookie||'').split(';').map(x=>x.trim()).includes(cookie+'='+session);
const json=(res,n,x)=>{res.writeHead(n,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(x))};
async function body(req){let a=[],n=0;for await(const c of req){n+=c.length;if(n>2*1024*1024)throw Error('BODY_TOO_LARGE');a.push(c)}return a.length?JSON.parse(Buffer.concat(a).toString('utf8')):{}}
async function proxy(req,res,ep){const b=['POST','PATCH','PUT'].includes(req.method)?await body(req):null;try{const d=await fabric.request(ep,{method:req.method,body:b,timeoutMs:60000});json(res,200,d)}catch(e){json(res,502,{error:'CORE_PROXY_FAILED',message:String(e.message||e)})}}
function ownerSecurityOrigin(req){
  const origin=String(req.headers.origin||'');
  if(!origin)return true;
  try{const u=new URL(origin);return ['127.0.0.1','localhost'].includes(u.hostname)&&Number(u.port||80)===PORT;}catch{return false}
}
async function securityStatus(){
  const accounts=await registry.list(),vaultStatus=await vault.status();
  return {
    schema:'deus.owner-security-status/1',
    authorityAccounts:accounts,
    vault:vaultStatus,
    adaptiveTrust:ADAPTIVE_TRUST_INVARIANTS,
    secretValuesRendered:false,
    executionCredit:false,
    truthBoundary:'DELEGATED != PROVIDER_ACCEPTED; VAULTED != EXECUTED; POLICY_ALLOW != VERIFIED_DONE'
  };
}
const server=http.createServer(async(req,res)=>{
 res.setHeader('X-Frame-Options','DENY');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');
 try{
   const u=new URL(req.url,'http://127.0.0.1');
   if(u.pathname==='/api/health')return json(res,200,{ok:true,version:'4.2.x-v6-adaptive-security-candidate',adaptiveTrust:true,ownerVault:true});
   if(u.pathname.startsWith('/api/')){
     if(!auth(req))return json(res,401,{error:'OWNER_SESSION_REQUIRED'});
     if(['POST','PUT','PATCH','DELETE'].includes(req.method)&&!ownerSecurityOrigin(req))return json(res,403,{error:'OWNER_ORIGIN_REQUIRED'});
     if(u.pathname==='/api/bootstrap'){
       const f=await fabric.refresh();let threads={threads:[]};try{threads=await fabric.request('/api/threads')}catch{}
       return json(res,200,{version:'4.2.x-v6-adaptive-security-candidate',fabric:f,system:f.workstation,threads:threads.threads||[],security:await securityStatus(),modes:['chat','work','build'],truthBoundary:f.truthBoundary})
     }
     if(u.pathname==='/api/security/status'&&req.method==='GET')return json(res,200,await securityStatus());
     if(u.pathname==='/api/security/authority'&&req.method==='POST'){
       const b=await body(req),item=await registry.upsert(b);
       return json(res,200,{schema:'deus.owner-authority-write/1',account:item,secretValuesRendered:false,receiptRequiredForProviderActions:true});
     }
     if(u.pathname==='/api/security/authority/revoke'&&req.method==='POST'){
       const b=await body(req);return json(res,200,{schema:'deus.owner-authority-revoke/1',...(await registry.revoke(String(b.accountId||'')))});
     }
     if(u.pathname==='/api/security/plan'&&req.method==='POST'){
       const b=await body(req),decision=await trust.decide({...b,authenticatedOwnerSession:true});
       return json(res,200,{schema:'deus.adaptive-trust-plan/1',...decision,policyOnly:true,executionAuthorized:false});
     }
     if(u.pathname==='/api/security/vault/store'&&req.method==='POST'){
       const b=await body(req);
       if(!b.ref||!Object.hasOwn(b,'value'))return json(res,400,{error:'VAULT_REF_AND_VALUE_REQUIRED'});
       const stored=await vault.set(String(b.ref),b.value);
       return json(res,200,{schema:'deus.owner-vault-store/1',...stored,secretValueRendered:false});
     }
     if(u.pathname==='/api/security/vault/delete'&&req.method==='POST'){
       const b=await body(req);return json(res,200,{schema:'deus.owner-vault-delete/1',...(await vault.delete(String(b.ref||'')))});
     }
     if(u.pathname==='/api/security/recovery/seal'&&req.method==='POST'){
       const b=await body(req);
       if(!b.vaultRef||!Array.isArray(b.recipients))return json(res,400,{error:'VAULT_REF_AND_RECIPIENTS_REQUIRED'});
       const value=await vault.get(String(b.vaultRef));if(value==null)return json(res,404,{error:'VAULT_ENTRY_NOT_FOUND'});
       const envelope=sealRecoveryEnvelope({plaintext:JSON.stringify({schema:'deus.owner-vault-recovery-payload/1',vaultRef:String(b.vaultRef),value}),recipients:b.recipients});
       return json(res,200,{schema:'deus.owner-vault-recovery-export/1',envelope,plaintextRendered:false});
     }
     if(u.pathname==='/api/deus/status'&&req.method==='GET')return json(res,200,await fabric.workstation.snapshot({force:true}));
     if(u.pathname==='/api/deus/action'&&req.method==='POST'){const b=await body(req);try{return json(res,200,await fabric.workstation.action(String(b.action||''),b.payload||{}))}catch(e){return json(res,502,{error:'DEUS_ACTION_HELD',message:String(e.message||e)})}}
     if(u.pathname==='/api/chat/stream'&&req.method==='POST'){
       const b=await body(req);const r=await fetch(fabric.coreUrl+'/api/chat/stream',{method:'POST',headers:{Authorization:'Bearer '+fabric.token,'Content-Type':'application/json'},body:JSON.stringify(b)});
       res.writeHead(r.status,{'Content-Type':r.headers.get('content-type')||'text/event-stream','Cache-Control':'no-cache','X-Accel-Buffering':'no'});
       for await(const c of r.body)res.write(c);return res.end()
     }
     return proxy(req,res,u.pathname)
   }
   let rel=u.pathname==='/'?'index.html':u.pathname.slice(1);if(rel.includes('..'))return json(res,400,{error:'BAD_PATH'});
   if(rel==='index.html')res.setHeader('Set-Cookie',cookie+'='+session+'; HttpOnly; SameSite=Strict; Path=/');
   const p=path.join(PUB,rel);try{const d=await fs.readFile(p);res.writeHead(200,{'Content-Type':mime[path.extname(p)]||'application/octet-stream'});res.end(d)}catch{json(res,404,{error:'NOT_FOUND'})}
 }catch(e){json(res,500,{error:'OWNER_HQ_ERROR',message:String(e.message||e).replace(/[^A-Z0-9_ .:/-]/gi,'_').slice(0,240)})}
});
server.listen(PORT,HOST);
