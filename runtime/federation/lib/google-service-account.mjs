import { createSign } from 'node:crypto';

const DEFAULT_SCOPE='https://www.googleapis.com/auth/spreadsheets';

function base64url(value){
  const input=Buffer.isBuffer(value)?value:Buffer.from(typeof value==='string'?value:JSON.stringify(value));
  return input.toString('base64url');
}

export function loadGoogleServiceAccount(env=process.env){
  if(env.DEUS_GOOGLE_SERVICE_ACCOUNT_JSON){
    const parsed=JSON.parse(env.DEUS_GOOGLE_SERVICE_ACCOUNT_JSON);
    if(!parsed.client_email||!parsed.private_key) throw new Error('DEUS_GOOGLE_SERVICE_ACCOUNT_JSON requires client_email and private_key');
    return Object.freeze({
      clientEmail:String(parsed.client_email),
      privateKey:String(parsed.private_key).replace(/\\n/g,'\n'),
      tokenUri:String(parsed.token_uri||'https://oauth2.googleapis.com/token'),
    });
  }
  const clientEmail=String(env.DEUS_GOOGLE_SERVICE_ACCOUNT_EMAIL||'').trim();
  const privateKey=String(env.DEUS_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY||'').replace(/\\n/g,'\n').trim();
  if(!clientEmail&&!privateKey) return null;
  if(!clientEmail||!privateKey) throw new Error('Both DEUS_GOOGLE_SERVICE_ACCOUNT_EMAIL and DEUS_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY are required');
  return Object.freeze({clientEmail,privateKey,tokenUri:'https://oauth2.googleapis.com/token'});
}

export function createServiceAccountTokenSource({
  credentials,
  fetchImpl=fetch,
  scope=DEFAULT_SCOPE,
  clock=()=>Date.now(),
}={}){
  if(!credentials?.clientEmail||!credentials?.privateKey) throw new Error('service account credentials required');
  let cached=null;
  return async function token(){
    const nowMs=clock();
    if(cached && cached.expiresAtMs-nowMs>60_000) return cached.accessToken;

    const iat=Math.floor(nowMs/1000);
    const header=base64url({alg:'RS256',typ:'JWT'});
    const payload=base64url({
      iss:credentials.clientEmail,
      scope,
      aud:credentials.tokenUri||'https://oauth2.googleapis.com/token',
      iat,
      exp:iat+3600,
    });
    const signingInput=`${header}.${payload}`;
    const signer=createSign('RSA-SHA256');
    signer.update(signingInput);
    signer.end();
    const signature=signer.sign(credentials.privateKey).toString('base64url');
    const assertion=`${signingInput}.${signature}`;

    const response=await fetchImpl(credentials.tokenUri||'https://oauth2.googleapis.com/token',{
      method:'POST',
      headers:{'content-type':'application/x-www-form-urlencoded'},
      body:new URLSearchParams({
        grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',
        assertion,
      }),
      signal:AbortSignal.timeout(15_000),
    });
    const text=await response.text();
    let body={};
    try{body=text?JSON.parse(text):{};}catch{body={raw:text};}
    if(!response.ok||!body.access_token) throw new Error(`google token exchange failed (${response.status})`);
    const expiresIn=Math.max(60,Number(body.expires_in||3600));
    cached={accessToken:String(body.access_token),expiresAtMs:nowMs+expiresIn*1000};
    return cached.accessToken;
  };
}
