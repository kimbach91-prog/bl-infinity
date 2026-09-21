import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import { loadGoogleServiceAccount, createServiceAccountTokenSource } from '../lib/google-service-account.mjs';

test('service account env is fail-closed and supports split variables',()=>{
  assert.equal(loadGoogleServiceAccount({}),null);
  assert.throws(()=>loadGoogleServiceAccount({DEUS_GOOGLE_SERVICE_ACCOUNT_EMAIL:'x@y'}),/Both/);
  const {privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});
  const pem=privateKey.export({type:'pkcs8',format:'pem'}).toString();
  const c=loadGoogleServiceAccount({
    DEUS_GOOGLE_SERVICE_ACCOUNT_EMAIL:'svc@example.iam.gserviceaccount.com',
    DEUS_GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY:pem,
  });
  assert.equal(c.clientEmail,'svc@example.iam.gserviceaccount.com');
});

test('token source signs JWT and caches token',async()=>{
  const {privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});
  const pem=privateKey.export({type:'pkcs8',format:'pem'}).toString();
  let calls=0;
  const fetchImpl=async (_url,init)=>{
    calls++;
    assert.equal(init.method,'POST');
    assert.match(String(init.body),/grant_type=/);
    return {ok:true,status:200,text:async()=>JSON.stringify({access_token:'tok',expires_in:3600})};
  };
  const source=createServiceAccountTokenSource({
    credentials:{clientEmail:'svc@example.iam.gserviceaccount.com',privateKey:pem,tokenUri:'https://oauth2.googleapis.com/token'},
    fetchImpl,
    clock:()=>1_000_000,
  });
  assert.equal(await source(),'tok');
  assert.equal(await source(),'tok');
  assert.equal(calls,1);
});
