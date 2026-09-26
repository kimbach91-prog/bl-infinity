import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const PROTECTED = new Set([
  'ROOT_CREDENTIAL',
  'ACCOUNT_RECOVERY',
  'PAYOUT_DESTINATION',
  'MATERIAL_SPEND',
  'LEGAL_AGREEMENT',
  'KYC',
  'IRREVERSIBLE_DELETE',
  'NEW_PRIVILEGE'
]);

const ROUTINE = new Set([
  'READ',
  'PUBLISH',
  'UPDATE_CONTENT',
  'SCHEDULE',
  'COMMENT_REPLY',
  'MESSAGE_REPLY',
  'INSIGHTS_READ',
  'API_CALL',
  'CONFIG_UPDATE',
  'RESOURCE_START',
  'RESOURCE_STOP',
  'DEPLOY_REVERSIBLE'
]);

function str(v,n){if(typeof v!=='string'||!v.trim())throw new Error('INVALID_'+n);return v.trim();}
function arr(v){return [...new Set((Array.isArray(v)?v:[]).map(x=>str(x,'ACTION_CLASS')))];}
function isoOrNull(v){if(v==null||v==='')return null;const t=Date.parse(v);if(!Number.isFinite(t))throw new Error('INVALID_EXPIRY');return new Date(t).toISOString();}
function safeId(v){return str(v,'ACCOUNT_ID').replace(/[^a-zA-Z0-9._:@/-]/g,'_').slice(0,180);}
function atomicPath(root){return path.join(root||path.resolve('data'),'owner-authority','accounts.json');}

export class OwnerAccountAuthorityRegistry{
  constructor({root=process.env.DEUS_STATE_ROOT,now=()=>Date.now()}={}){
    this.file=atomicPath(root);this.now=now;this.cache=null;
  }
  async load(){
    if(this.cache)return this.cache;
    try{
      const raw=JSON.parse(await fs.readFile(this.file,'utf8'));
      if(raw?.schema!=='deus.owner-account-authority/1'||!Array.isArray(raw.accounts))throw new Error('AUTHORITY_REGISTRY_INVALID');
      this.cache=raw;return raw;
    }catch(e){
      if(e.code!=='ENOENT')throw e;
      this.cache={schema:'deus.owner-account-authority/1',accounts:[],updatedAt:null};return this.cache;
    }
  }
  async persist(doc){
    await fs.mkdir(path.dirname(this.file),{recursive:true,mode:0o700});
    const temp=this.file+'.'+crypto.randomUUID()+'.tmp';
    const body=JSON.stringify(doc,null,2);
    try{await fs.writeFile(temp,body,{mode:0o600,flag:'wx'});await fs.rename(temp,this.file);}
    finally{await fs.rm(temp,{force:true}).catch(()=>{});}
    this.cache=doc;
  }
  normalize(input){
    const accountId=safeId(input?.accountId),provider=str(input?.provider,'PROVIDER').toLowerCase();
    if(input?.ownerDelegated!==true)throw new Error('OWNER_DELEGATION_REQUIRED');
    const routineActions=arr(input?.routineActions);
    if(routineActions.some(x=>PROTECTED.has(x)))throw new Error('PROTECTED_ACTION_CANNOT_BE_ROUTINE');
    for(const a of routineActions)if(!ROUTINE.has(a))throw new Error('ROUTINE_ACTION_NOT_ALLOWLISTED');
    return Object.freeze({
      accountId,provider,ownerDelegated:true,
      providerAccountRef:input?.providerAccountRef?str(input.providerAccountRef,'PROVIDER_ACCOUNT_REF'):null,
      routineActions,
      protectedActions:arr(input?.protectedActions).filter(x=>PROTECTED.has(x)),
      vaultRef:input?.vaultRef?str(input.vaultRef,'VAULT_REF'):null,
      authorityRef:input?.authorityRef?str(input.authorityRef,'AUTHORITY_REF'):null,
      expiresAt:isoOrNull(input?.expiresAt),
      status:input?.status==='REVOKED'?'REVOKED':'ACTIVE',
      updatedAt:new Date(this.now()).toISOString()
    });
  }
  async upsert(input){
    const item=this.normalize(input),doc=await this.load();
    const accounts=doc.accounts.filter(x=>x.accountId!==item.accountId);
    accounts.push(item);accounts.sort((a,b)=>a.accountId.localeCompare(b.accountId));
    await this.persist({...doc,accounts,updatedAt:item.updatedAt});return item;
  }
  async revoke(accountId){
    const id=safeId(accountId),doc=await this.load(),now=new Date(this.now()).toISOString();
    const found=doc.accounts.find(x=>x.accountId===id);if(!found)throw new Error('ACCOUNT_NOT_FOUND');
    const accounts=doc.accounts.map(x=>x.accountId===id?{...x,status:'REVOKED',updatedAt:now}:x);
    await this.persist({...doc,accounts,updatedAt:now});return {accountId:id,status:'REVOKED'};
  }
  async list(){return (await this.load()).accounts.map(x=>({...x}));}
  async get(accountId){const id=safeId(accountId);return (await this.load()).accounts.find(x=>x.accountId===id)||null;}
}

export class AdaptiveTrustKernel{
  constructor({registry,now=()=>Date.now()}={}){if(!registry)throw new Error('REGISTRY_REQUIRED');this.registry=registry;this.now=now;}
  async decide({accountId,actionClass,authenticatedOwnerSession=false,providerAllows=true,providerRequiresUserPresence=false,riskSignals=[],standingMandate=false}={}){
    const item=await this.registry.get(accountId),action=str(actionClass,'ACTION_CLASS');
    if(!item||item.status!=='ACTIVE')return Object.freeze({decision:'DENY',reason:'ACCOUNT_NOT_ACTIVE'});
    if(item.expiresAt&&Date.parse(item.expiresAt)<=this.now())return Object.freeze({decision:'DENY',reason:'DELEGATION_EXPIRED'});
    if(!authenticatedOwnerSession)return Object.freeze({decision:'STEP_UP',reason:'OWNER_SESSION_REQUIRED',gate:'OWNER_SESSION'});
    if(!providerAllows)return Object.freeze({decision:'DENY',reason:'PROVIDER_AUTHORITY_ABSENT'});
    if(providerRequiresUserPresence)return Object.freeze({decision:'STEP_UP',reason:'PROVIDER_USER_PRESENCE_REQUIRED',gate:'PROVIDER_USER_PRESENCE',autoResume:true});
    if(PROTECTED.has(action)&&!standingMandate)return Object.freeze({decision:'STEP_UP',reason:'PROTECTED_ACTION_CLASS',gate:action,autoResume:true});
    const severe=(Array.isArray(riskSignals)?riskSignals:[]).some(x=>['AUTH_ANOMALY','DEVICE_INTEGRITY_FAIL','TOKEN_BINDING_MISMATCH','PROVIDER_RISK_ESCALATION'].includes(String(x)));
    if(severe)return Object.freeze({decision:'STEP_UP',reason:'RISK_ESCALATION',gate:'ADAPTIVE_RISK',autoResume:true});
    if(item.routineActions.includes(action)||standingMandate)return Object.freeze({decision:'ALLOW',reason:'OWNER_STANDING_DELEGATION',receiptRequired:true});
    return Object.freeze({decision:'STEP_UP',reason:'ACTION_OUTSIDE_ROUTINE_SCOPE',gate:'SCOPE_EXTENSION',autoResume:true});
  }
}

export const ADAPTIVE_TRUST_INVARIANTS=Object.freeze({
  routineNoReprompt:true,
  mandatoryProviderPresenceNotBypassed:true,
  capabilityScoped:true,
  riskAdaptiveStepUp:true,
  ownerFinalControl:true,
  voiceAloneIsNotRootIdentity:true
});
