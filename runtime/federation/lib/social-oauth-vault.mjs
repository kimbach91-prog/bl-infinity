import crypto from 'node:crypto';
import {
  SocialControlError,
  normalizeSocialProvider,
  applySocialRuntimeCredentials,
  clearSocialRuntimeCredentials,
} from './social-control.mjs';

const META_VERSION = process.env.META_API_VERSION || 'v26.0';
const FACEBOOK_BASE = `https://graph.facebook.com/${META_VERSION}`;
const INSTAGRAM_BASE = `https://graph.instagram.com/${META_VERSION}`;
const THREADS_BASE = 'https://graph.threads.net/v1.0';
const TIKTOK_TOKEN_URL = 'https://open.tiktokapis.com/v2/oauth/token/';
const PROVIDERS = Object.freeze(['facebook','instagram','threads','tiktok']);

function env(name, fallback='') { return String(process.env[name] || fallback || '').trim(); }
function form(values={}) {
  const out=new URLSearchParams();
  for (const [k,v] of Object.entries(values)) if (v!==undefined && v!==null && v!=='') out.set(k,String(v));
  return out;
}
function publicBase() {
  const explicit=env('DEUS_SOCIAL_PUBLIC_BASE').replace(/\/$/,'');
  if (explicit) return explicit;
  const railway=env('RAILWAY_PUBLIC_DOMAIN');
  return railway ? `https://${railway}` : '';
}
function providerApp(providerInput) {
  const provider=normalizeSocialProvider(providerInput);
  const metaId=env('META_APP_ID') || env('FB_APP_ID');
  const metaSecret=env('META_APP_SECRET') || env('FB_APP_SECRET');
  if (provider==='facebook') return {
    provider, clientId:metaId, clientSecret:metaSecret,
    authorize:`https://www.facebook.com/${META_VERSION}/dialog/oauth`,
    token:`${FACEBOOK_BASE}/oauth/access_token`,
    scopes:['pages_show_list','pages_read_engagement','pages_manage_posts','read_insights'],
  };
  if (provider==='instagram') return {
    provider, clientId:env('INSTAGRAM_APP_ID') || metaId, clientSecret:env('INSTAGRAM_APP_SECRET') || metaSecret,
    authorize:'https://www.instagram.com/oauth/authorize',
    token:'https://api.instagram.com/oauth/access_token',
    scopes:['instagram_business_basic','instagram_business_content_publish','instagram_business_manage_insights','instagram_business_manage_comments'],
  };
  if (provider==='threads') return {
    provider, clientId:env('THREADS_APP_ID') || metaId, clientSecret:env('THREADS_APP_SECRET') || metaSecret,
    authorize:'https://threads.net/oauth/authorize',
    token:'https://graph.threads.net/oauth/access_token',
    scopes:['threads_basic','threads_content_publish','threads_manage_insights','threads_read_replies','threads_manage_replies'],
  };
  return {
    provider, clientId:env('TIKTOK_CLIENT_KEY'), clientSecret:env('TIKTOK_CLIENT_SECRET'),
    authorize:'https://www.tiktok.com/v2/auth/authorize/',
    token:TIKTOK_TOKEN_URL,
    scopes:['user.info.basic','video.list','video.publish'],
  };
}
function safeAppStatus() {
  return Object.fromEntries(PROVIDERS.map((provider)=>{
    const cfg=providerApp(provider);
    return [provider,{
      appConfigured:Boolean(cfg.clientId && cfg.clientSecret),
      scopes:cfg.scopes,
      callbackUrl:publicBase() ? `${publicBase()}/v1/social/oauth/${provider}/callback` : null,
    }];
  }));
}
function kekMaterial() {
  return env('DEUS_SOCIAL_VAULT_KEK') || env('DEUS_WORKSTATION_001_TOKEN');
}
function kekKey() {
  const material=kekMaterial();
  if (material.length<24) throw new SocialControlError('social',503,'VAULT_KEK_NOT_CONFIGURED');
  return crypto.createHash('sha256').update('DEUS_SOCIAL_VAULT_KEK_V1\0').update(material).digest();
}
function sealWithKey(value,key) {
  if (value===null || value===undefined || value==='') return null;
  const iv=crypto.randomBytes(12);
  const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);
  const body=Buffer.from(String(value),'utf8');
  const ciphertext=Buffer.concat([cipher.update(body),cipher.final()]);
  const tag=cipher.getAuthTag();
  return [iv.toString('base64url'),ciphertext.toString('base64url'),tag.toString('base64url')].join('.');
}
function openWithKey(token,key) {
  if (!token) return '';
  try {
    const [iv64,ct64,tag64]=String(token).split('.');
    if (!iv64 || !ct64 || !tag64) throw new Error('parts');
    const decipher=crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(iv64,'base64url'));
    decipher.setAuthTag(Buffer.from(tag64,'base64url'));
    return Buffer.concat([decipher.update(Buffer.from(ct64,'base64url')),decipher.final()]).toString('utf8');
  } catch {
    throw new SocialControlError('social',500,'VAULT_DECRYPT_FAILED');
  }
}
async function getOrCreateDek(pool) {
  const row=await pool.query("SELECT sealed_value FROM deus_social_vault_meta WHERE key_name='social-dek-v1'");
  if (row.rowCount) return Buffer.from(openWithKey(row.rows[0].sealed_value,kekKey()),'base64url');
  const dek=crypto.randomBytes(32);
  const wrapped=sealWithKey(dek.toString('base64url'),kekKey());
  await pool.query("INSERT INTO deus_social_vault_meta(key_name,sealed_value) VALUES('social-dek-v1',$1) ON CONFLICT (key_name) DO NOTHING",[wrapped]);
  const reread=await pool.query("SELECT sealed_value FROM deus_social_vault_meta WHERE key_name='social-dek-v1'");
  return Buffer.from(openWithKey(reread.rows[0].sealed_value,kekKey()),'base64url');
}
function safeAccount(row) {
  return {
    provider:row.provider,
    account_id:row.account_id,
    display_name:row.display_name || null,
    account_type:row.account_type || null,
    scopes:Array.isArray(row.scopes)?row.scopes:[],
    token_expiry:row.token_expires_at || null,
    connection_state:'CONNECTED_STORED',
    active:Boolean(row.is_active),
    metadata:row.metadata || {},
    last_verified_at:row.last_verified_at || null,
    updated_at:row.updated_at || null,
  };
}
async function jsonResponse(provider,response) {
  const text=await response.text();
  let data={};
  try { data=text?JSON.parse(text):{}; } catch { data={raw:text.slice(0,500)}; }
  const failed=!response.ok || (provider==='tiktok' && data?.error?.code && data.error.code!=='ok');
  if (failed) {
    const detail=data?.error && typeof data.error==='object'
      ? {code:data.error.code||null,message:data.error.message||null,type:data.error.type||null,subcode:data.error.error_subcode||null,trace_id:data.error.fbtrace_id||data.error.log_id||null}
      : {code:data?.code||data?.error||null,message:data?.message||null};
    throw new SocialControlError(provider,response.status||502,String(detail.code||`HTTP_${response.status||502}`),detail);
  }
  return data;
}
async function fetchJson(provider,url,options={}) {
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),30_000);
  try {
    return await jsonResponse(provider,await fetch(url,{...options,signal:controller.signal}));
  } catch (error) {
    if (error instanceof SocialControlError) throw error;
    if (error?.name==='AbortError') throw new SocialControlError(provider,504,'UPSTREAM_TIMEOUT');
    throw new SocialControlError(provider,502,'UPSTREAM_NETWORK_ERROR');
  } finally { clearTimeout(timeout); }
}
function stateSeal(payload,dek) {
  return sealWithKey(JSON.stringify(payload),crypto.createHash('sha256').update('DEUS_SOCIAL_OAUTH_STATE_V1\0').update(dek).digest());
}
function stateOpen(token,dek,now=Date.now()) {
  try {
    const raw=openWithKey(token,crypto.createHash('sha256').update('DEUS_SOCIAL_OAUTH_STATE_V1\0').update(dek).digest());
    const value=JSON.parse(raw);
    if (!value.exp || Number(value.exp)<now) throw new Error('expired');
    return value;
  } catch {
    throw new SocialControlError('social',400,'OAUTH_STATE_INVALID');
  }
}

export async function createSocialOAuthVault(pool) {
  if (!pool) return {ready:false,pool:null,dek:null,reason:'POSTGRES_REQUIRED'};
  await pool.query(`
    CREATE TABLE IF NOT EXISTS deus_social_vault_meta (
      key_name TEXT PRIMARY KEY,
      sealed_value TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS deus_social_accounts (
      provider TEXT NOT NULL,
      account_id TEXT NOT NULL,
      display_name TEXT,
      account_type TEXT,
      access_token_sealed TEXT NOT NULL,
      refresh_token_sealed TEXT,
      scopes TEXT[] NOT NULL DEFAULT '{}',
      token_expires_at TIMESTAMPTZ,
      metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      is_active BOOLEAN NOT NULL DEFAULT FALSE,
      last_verified_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY(provider,account_id)
    );
    CREATE INDEX IF NOT EXISTS deus_social_accounts_provider_active_idx
      ON deus_social_accounts(provider,is_active);
    CREATE TABLE IF NOT EXISTS deus_social_receipts (
      receipt_id TEXT PRIMARY KEY,
      provider TEXT NOT NULL,
      account_id TEXT,
      action TEXT NOT NULL,
      idempotency_key TEXT,
      request_digest TEXT NOT NULL,
      state TEXT NOT NULL,
      provider_object_id TEXT,
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS deus_social_receipts_idempotency_idx
      ON deus_social_receipts(provider,COALESCE(account_id,''),action,idempotency_key)
      WHERE idempotency_key IS NOT NULL;
  `);
  const dek=await getOrCreateDek(pool);
  return {ready:true,pool,dek,reason:null};
}
export function socialOAuthStatus(vault) {
  return {
    schema:'deus-social-oauth-vault/1',
    vaultReady:Boolean(vault?.ready),
    publicBaseConfigured:Boolean(publicBase()),
    providers:safeAppStatus(),
    truthBoundary:'APP_CONFIGURED != OAUTH_CONNECTED != SCOPE_APPROVED != WRITE_VERIFIED',
  };
}
async function storeAccount(vault,record,{active=true}={}) {
  if (!vault?.ready) throw new SocialControlError('social',503,'VAULT_NOT_READY');
  const provider=normalizeSocialProvider(record.provider);
  if (active) await vault.pool.query('UPDATE deus_social_accounts SET is_active=FALSE,updated_at=NOW() WHERE provider=$1',[provider]);
  await vault.pool.query(`
    INSERT INTO deus_social_accounts(
      provider,account_id,display_name,account_type,access_token_sealed,refresh_token_sealed,
      scopes,token_expires_at,metadata,is_active,last_verified_at,updated_at
    ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,NOW(),NOW())
    ON CONFLICT(provider,account_id) DO UPDATE SET
      display_name=EXCLUDED.display_name,
      account_type=EXCLUDED.account_type,
      access_token_sealed=EXCLUDED.access_token_sealed,
      refresh_token_sealed=COALESCE(EXCLUDED.refresh_token_sealed,deus_social_accounts.refresh_token_sealed),
      scopes=EXCLUDED.scopes,
      token_expires_at=EXCLUDED.token_expires_at,
      metadata=EXCLUDED.metadata,
      is_active=EXCLUDED.is_active,
      last_verified_at=NOW(),
      updated_at=NOW()
  `,[
    provider,String(record.accountId),record.displayName||null,record.accountType||null,
    sealWithKey(record.accessToken,vault.dek),
    record.refreshToken?sealWithKey(record.refreshToken,vault.dek):null,
    record.scopes||[],record.expiresAt||null,JSON.stringify(record.metadata||{}),Boolean(active),
  ]);
  return getAccount(vault,provider,record.accountId);
}
async function getAccount(vault,providerInput,accountId) {
  const provider=normalizeSocialProvider(providerInput);
  const result=await vault.pool.query('SELECT * FROM deus_social_accounts WHERE provider=$1 AND account_id=$2',[provider,String(accountId)]);
  if (!result.rowCount) throw new SocialControlError(provider,404,'ACCOUNT_NOT_FOUND');
  return result.rows[0];
}
async function credentialAccount(vault,providerInput,accountId) {
  const row=await getAccount(vault,providerInput,accountId);
  return {
    row,
    accessToken:openWithKey(row.access_token_sealed,vault.dek),
    refreshToken:row.refresh_token_sealed?openWithKey(row.refresh_token_sealed,vault.dek):'',
  };
}
export async function listSocialAccounts(vault) {
  if (!vault?.ready) return [];
  const result=await vault.pool.query(`
    SELECT provider,account_id,display_name,account_type,scopes,token_expires_at,metadata,is_active,last_verified_at,updated_at
    FROM deus_social_accounts ORDER BY provider,is_active DESC,display_name NULLS LAST,account_id
  `);
  return result.rows.map(safeAccount);
}
export async function hydrateActiveSocialAccounts(vault) {
  if (!vault?.ready) return [];
  const rows=await vault.pool.query('SELECT provider,account_id FROM deus_social_accounts WHERE is_active=TRUE ORDER BY provider,updated_at DESC');
  const hydrated=[];
  for (const row of rows.rows) {
    const cred=await credentialAccount(vault,row.provider,row.account_id);
    applySocialRuntimeCredentials(row.provider,{accessToken:cred.accessToken,accountId:row.account_id});
    hydrated.push(safeAccount(cred.row));
  }
  return hydrated;
}
export async function activateSocialAccount(vault,providerInput,accountId) {
  const provider=normalizeSocialProvider(providerInput);
  await vault.pool.query('BEGIN');
  try {
    await vault.pool.query('UPDATE deus_social_accounts SET is_active=FALSE,updated_at=NOW() WHERE provider=$1',[provider]);
    const changed=await vault.pool.query('UPDATE deus_social_accounts SET is_active=TRUE,updated_at=NOW() WHERE provider=$1 AND account_id=$2 RETURNING *',[provider,String(accountId)]);
    if (!changed.rowCount) throw new SocialControlError(provider,404,'ACCOUNT_NOT_FOUND');
    await vault.pool.query('COMMIT');
    const cred=await credentialAccount(vault,provider,accountId);
    applySocialRuntimeCredentials(provider,{accessToken:cred.accessToken,accountId});
    return safeAccount(cred.row);
  } catch(error) {
    await vault.pool.query('ROLLBACK');
    throw error;
  }
}
export async function disconnectSocialAccount(vault,providerInput,accountId) {
  const provider=normalizeSocialProvider(providerInput);
  const row=await getAccount(vault,provider,accountId);
  await vault.pool.query('DELETE FROM deus_social_accounts WHERE provider=$1 AND account_id=$2',[provider,String(accountId)]);
  if (row.is_active) clearSocialRuntimeCredentials(provider);
  return {disconnected:true,provider,account_id:String(accountId),remote_revoke_state:'LOCAL_REVOKE_ONLY'};
}

export function buildSocialConnect(providerInput,{returnTo='/v1/social/accounts'}={}) {
  const provider=normalizeSocialProvider(providerInput);
  const cfg=providerApp(provider);
  if (!cfg.clientId || !cfg.clientSecret) throw new SocialControlError(provider,503,'OAUTH_APP_NOT_CONFIGURED');
  const base=publicBase();
  if (!base) throw new SocialControlError(provider,503,'PUBLIC_BASE_NOT_CONFIGURED');
  const redirectUri=`${base}/v1/social/oauth/${provider}/callback`;
  return {provider,cfg,redirectUri,returnTo};
}
export function socialAuthorizationUrl(vault,providerInput,{returnTo='/v1/social/accounts'}={}) {
  if (!vault?.ready) throw new SocialControlError('social',503,'VAULT_NOT_READY');
  const {provider,cfg,redirectUri}=buildSocialConnect(providerInput,{returnTo});
  const state=stateSeal({provider,exp:Date.now()+10*60_000,nonce:crypto.randomUUID(),return_to:returnTo},vault.dek);
  const url=new URL(cfg.authorize);
  if (provider==='tiktok') url.search=form({client_key:cfg.clientId,redirect_uri:redirectUri,scope:cfg.scopes.join(','),response_type:'code',state});
  else if (provider==='instagram') url.search=form({client_id:cfg.clientId,redirect_uri:redirectUri,scope:cfg.scopes.join(','),response_type:'code',state,enable_fb_login:'0',force_authentication:'1'});
  else url.search=form({client_id:cfg.clientId,redirect_uri:redirectUri,scope:cfg.scopes.join(','),response_type:'code',state});
  return {provider,authorization_url:url.toString(),redirect_uri:redirectUri,expires_in_seconds:600};
}

export async function handleSocialOAuthCallback(vault,providerInput,params={}) {
  const provider=normalizeSocialProvider(providerInput);
  if (!vault?.ready) throw new SocialControlError(provider,503,'VAULT_NOT_READY');
  if (params.error || params.error_description) throw new SocialControlError(provider,400,'OAUTH_DENIED');
  if (!params.code || !params.state) throw new SocialControlError(provider,400,'OAUTH_CODE_STATE_REQUIRED');
  const state=stateOpen(params.state,vault.dek);
  if (state.provider!==provider) throw new SocialControlError(provider,400,'OAUTH_STATE_PROVIDER_MISMATCH');
  const cfg=providerApp(provider);
  if (!cfg.clientId || !cfg.clientSecret) throw new SocialControlError(provider,503,'OAUTH_APP_NOT_CONFIGURED');
  const redirectUri=`${publicBase()}/v1/social/oauth/${provider}/callback`;

  if (provider==='facebook') {
    const tokenUrl=new URL(cfg.token);
    tokenUrl.search=form({client_id:cfg.clientId,client_secret:cfg.clientSecret,redirect_uri:redirectUri,code:params.code});
    const short=await fetchJson(provider,tokenUrl);
    let userToken=short.access_token;
    if (!userToken) throw new SocialControlError(provider,502,'ACCESS_TOKEN_MISSING');
    const longUrl=new URL(cfg.token);
    longUrl.search=form({grant_type:'fb_exchange_token',client_id:cfg.clientId,client_secret:cfg.clientSecret,fb_exchange_token:userToken});
    try {
      const long=await fetchJson(provider,longUrl);
      if (long.access_token) userToken=long.access_token;
    } catch {}
    const pagesUrl=new URL(`${FACEBOOK_BASE}/me/accounts`);
    pagesUrl.search=form({fields:'id,name,access_token,tasks',access_token:userToken,limit:100});
    const pages=await fetchJson(provider,pagesUrl);
    const desired=env('FB_PAGE_ID');
    const candidates=(pages?.data||[]).filter((p)=>p?.id && p?.access_token);
    if (!candidates.length) throw new SocialControlError(provider,403,'NO_PAGE_ACCESS');
    const activeId=(desired && candidates.some((p)=>String(p.id)===desired))?desired:String(candidates[0].id);
    const safe=[];
    for (const page of candidates) {
      const row=await storeAccount(vault,{
        provider,accountId:page.id,displayName:page.name||null,accountType:'PAGE',
        accessToken:page.access_token,scopes:cfg.scopes,metadata:{tasks:page.tasks||[]},
      },{active:String(page.id)===activeId});
      safe.push(safeAccount(row));
    }
    await activateSocialAccount(vault,provider,activeId);
    return {provider,connected:true,accounts:safe,active_account_id:activeId,return_to:state.return_to};
  }

  if (provider==='instagram') {
    const short=await fetchJson(provider,cfg.token,{
      method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},
      body:form({client_id:cfg.clientId,client_secret:cfg.clientSecret,grant_type:'authorization_code',redirect_uri:redirectUri,code:params.code}),
    });
    const exchange=new URL('https://graph.instagram.com/access_token');
    exchange.search=form({grant_type:'ig_exchange_token',client_secret:cfg.clientSecret,access_token:short.access_token});
    const long=await fetchJson(provider,exchange);
    const token=long.access_token||short.access_token;
    const me=new URL(`${INSTAGRAM_BASE}/me`);
    me.search=form({fields:'id,username,name,account_type',access_token:token});
    const identity=await fetchJson(provider,me);
    const id=identity.id||short.user_id;
    if (!id || !token) throw new SocialControlError(provider,502,'IDENTITY_OR_TOKEN_MISSING');
    const row=await storeAccount(vault,{
      provider,accountId:id,displayName:identity.username||identity.name||null,
      accountType:identity.account_type||'PROFESSIONAL',accessToken:token,scopes:cfg.scopes,
      expiresAt:long.expires_in?new Date(Date.now()+Number(long.expires_in)*1000):null,
      metadata:{username:identity.username||null,account_type:identity.account_type||null},
    });
    applySocialRuntimeCredentials(provider,{accessToken:token,accountId:id});
    return {provider,connected:true,accounts:[safeAccount(row)],active_account_id:String(id),return_to:state.return_to};
  }

  if (provider==='threads') {
    const short=await fetchJson(provider,cfg.token,{
      method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},
      body:form({client_id:cfg.clientId,client_secret:cfg.clientSecret,grant_type:'authorization_code',redirect_uri:redirectUri,code:params.code}),
    });
    const exchange=new URL('https://graph.threads.net/access_token');
    exchange.search=form({grant_type:'th_exchange_token',client_secret:cfg.clientSecret,access_token:short.access_token});
    const long=await fetchJson(provider,exchange);
    const token=long.access_token||short.access_token;
    const me=new URL(`${THREADS_BASE}/me`);
    me.search=form({fields:'id,username,name',access_token:token});
    const identity=await fetchJson(provider,me);
    const id=identity.id||short.user_id;
    if (!id || !token) throw new SocialControlError(provider,502,'IDENTITY_OR_TOKEN_MISSING');
    const row=await storeAccount(vault,{
      provider,accountId:id,displayName:identity.username||identity.name||null,
      accountType:'THREADS_PROFILE',accessToken:token,scopes:cfg.scopes,
      expiresAt:long.expires_in?new Date(Date.now()+Number(long.expires_in)*1000):null,
      metadata:{username:identity.username||null},
    });
    applySocialRuntimeCredentials(provider,{accessToken:token,accountId:id});
    return {provider,connected:true,accounts:[safeAccount(row)],active_account_id:String(id),return_to:state.return_to};
  }

  const tokenRaw=await fetchJson(provider,cfg.token,{
    method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},
    body:form({client_key:cfg.clientId,client_secret:cfg.clientSecret,code:params.code,grant_type:'authorization_code',redirect_uri:redirectUri}),
  });
  const token=tokenRaw?.data||tokenRaw;
  if (!token?.access_token || !token?.open_id) throw new SocialControlError(provider,502,'IDENTITY_OR_TOKEN_MISSING');
  const row=await storeAccount(vault,{
    provider,accountId:token.open_id,displayName:null,accountType:'TIKTOK_USER',
    accessToken:token.access_token,refreshToken:token.refresh_token||null,scopes:cfg.scopes,
    expiresAt:token.expires_in?new Date(Date.now()+Number(token.expires_in)*1000):null,metadata:{},
  });
  applySocialRuntimeCredentials(provider,{accessToken:token.access_token,accountId:token.open_id});
  return {provider,connected:true,accounts:[safeAccount(row)],active_account_id:String(token.open_id),return_to:state.return_to};
}

export async function refreshSocialAccount(vault,providerInput,accountId) {
  const provider=normalizeSocialProvider(providerInput);
  const cfg=providerApp(provider);
  const cred=await credentialAccount(vault,provider,accountId);
  if (provider==='facebook') return {provider,account_id:String(accountId),refreshed:false,reauthorize_required:true};
  let data;
  if (provider==='instagram') {
    const url=new URL('https://graph.instagram.com/refresh_access_token');
    url.search=form({grant_type:'ig_refresh_token',access_token:cred.accessToken});
    data=await fetchJson(provider,url);
  } else if (provider==='threads') {
    const url=new URL('https://graph.threads.net/refresh_access_token');
    url.search=form({grant_type:'th_refresh_token',access_token:cred.accessToken});
    data=await fetchJson(provider,url);
  } else {
    if (!cred.refreshToken) throw new SocialControlError(provider,409,'REFRESH_TOKEN_NOT_AVAILABLE');
    data=await fetchJson(provider,TIKTOK_TOKEN_URL,{
      method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},
      body:form({client_key:cfg.clientId,client_secret:cfg.clientSecret,grant_type:'refresh_token',refresh_token:cred.refreshToken}),
    });
    data=data?.data||data;
  }
  const accessToken=data.access_token||cred.accessToken;
  const refreshToken=data.refresh_token||cred.refreshToken||null;
  const expiresAt=data.expires_in?new Date(Date.now()+Number(data.expires_in)*1000):cred.row.token_expires_at;
  const row=await storeAccount(vault,{
    provider,accountId:cred.row.account_id,displayName:cred.row.display_name,accountType:cred.row.account_type,
    accessToken,refreshToken,scopes:cred.row.scopes,expiresAt,metadata:cred.row.metadata,
  },{active:cred.row.is_active});
  if (row.is_active) applySocialRuntimeCredentials(provider,{accessToken,accountId:row.account_id});
  return {provider,account_id:row.account_id,refreshed:true,token_expiry:row.token_expires_at||null};
}

export async function claimSocialReceipt(vault,{provider,accountId=null,action,idempotencyKey=null,requestDigest}) {
  const receiptId='RCP-SOCIAL-'+Date.now()+'-'+crypto.randomUUID().slice(0,8).toUpperCase();
  if (idempotencyKey) {
    const existing=await vault.pool.query(`
      SELECT * FROM deus_social_receipts
      WHERE provider=$1 AND COALESCE(account_id,'')=COALESCE($2,'') AND action=$3 AND idempotency_key=$4
      ORDER BY created_at DESC LIMIT 1
    `,[provider,accountId,action,idempotencyKey]);
    if (existing.rowCount) return {claimed:false,receipt:existing.rows[0]};
  }
  await vault.pool.query(`
    INSERT INTO deus_social_receipts(receipt_id,provider,account_id,action,idempotency_key,request_digest,state)
    VALUES($1,$2,$3,$4,$5,$6,'RESERVED')
  `,[receiptId,provider,accountId,action,idempotencyKey,requestDigest]);
  return {claimed:true,receipt:{receipt_id:receiptId,provider,account_id:accountId,action,idempotency_key:idempotencyKey,request_digest:requestDigest,state:'RESERVED'}};
}
export async function finalizeSocialReceipt(vault,receiptId,{state,providerObjectId=null,detail={}}) {
  const result=await vault.pool.query(`
    UPDATE deus_social_receipts
    SET state=$2,provider_object_id=$3,detail=$4::jsonb,updated_at=NOW()
    WHERE receipt_id=$1
    RETURNING *
  `,[receiptId,state,providerObjectId,JSON.stringify(detail||{})]);
  if (!result.rowCount) throw new SocialControlError('social',404,'RECEIPT_NOT_FOUND');
  return result.rows[0];
}
export async function getSocialReceipt(vault,receiptId) {
  const result=await vault.pool.query('SELECT * FROM deus_social_receipts WHERE receipt_id=$1',[String(receiptId)]);
  if (!result.rowCount) throw new SocialControlError('social',404,'RECEIPT_NOT_FOUND');
  return result.rows[0];
}
