import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {OwnerAccountAuthorityRegistry,AdaptiveTrustKernel,ADAPTIVE_TRUST_INVARIANTS} from './adaptive-trust.mjs';
import {createOwnerVault} from './owner-vault.mjs';
import {sealRecoveryEnvelope,openRecoveryEnvelope} from './recovery-envelope.mjs';

async function tmp(){return fs.mkdtemp(path.join(os.tmpdir(),'deus-owner-security-'));}

test('standing delegated routine action does not reprompt',async()=>{
  const root=await tmp(),registry=new OwnerAccountAuthorityRegistry({root});
  await registry.upsert({accountId:'x:owner',provider:'x',ownerDelegated:true,routineActions:['PUBLISH','API_CALL'],vaultRef:'vault://x/owner'});
  const k=new AdaptiveTrustKernel({registry});
  assert.deepEqual(await k.decide({accountId:'x:owner',actionClass:'PUBLISH',authenticatedOwnerSession:true,providerAllows:true}),{decision:'ALLOW',reason:'OWNER_STANDING_DELEGATION',receiptRequired:true});
});

test('provider-required user presence remains a step-up',async()=>{
  const root=await tmp(),registry=new OwnerAccountAuthorityRegistry({root});
  await registry.upsert({accountId:'g:owner',provider:'google',ownerDelegated:true,routineActions:['API_CALL']});
  const k=new AdaptiveTrustKernel({registry});
  const d=await k.decide({accountId:'g:owner',actionClass:'API_CALL',authenticatedOwnerSession:true,providerAllows:true,providerRequiresUserPresence:true});
  assert.equal(d.decision,'STEP_UP');assert.equal(d.gate,'PROVIDER_USER_PRESENCE');assert.equal(d.autoResume,true);
});

test('protected action is step-up unless precise standing mandate exists',async()=>{
  const root=await tmp(),registry=new OwnerAccountAuthorityRegistry({root});
  await registry.upsert({accountId:'cloud:owner',provider:'cloud',ownerDelegated:true,routineActions:['CONFIG_UPDATE'],protectedActions:['NEW_PRIVILEGE']});
  const k=new AdaptiveTrustKernel({registry});
  assert.equal((await k.decide({accountId:'cloud:owner',actionClass:'NEW_PRIVILEGE',authenticatedOwnerSession:true,providerAllows:true})).decision,'STEP_UP');
  assert.equal((await k.decide({accountId:'cloud:owner',actionClass:'NEW_PRIVILEGE',authenticatedOwnerSession:true,providerAllows:true,standingMandate:true})).decision,'ALLOW');
});

test('voice or message without authenticated owner session cannot act as root authority',async()=>{
  const root=await tmp(),registry=new OwnerAccountAuthorityRegistry({root});
  await registry.upsert({accountId:'meta:owner',provider:'meta',ownerDelegated:true,routineActions:['PUBLISH']});
  const k=new AdaptiveTrustKernel({registry});
  const d=await k.decide({accountId:'meta:owner',actionClass:'PUBLISH',authenticatedOwnerSession:false,providerAllows:true});
  assert.equal(d.decision,'STEP_UP');assert.equal(d.gate,'OWNER_SESSION');
  assert.equal(ADAPTIVE_TRUST_INVARIANTS.voiceAloneIsNotRootIdentity,true);
});

test('owner vault has no plaintext fallback and stores only protected bytes',async()=>{
  const root=await tmp();
  const protect=async x=>Buffer.from('ENC:'+x,'utf8').toString('base64');
  const unprotect=async x=>{const s=Buffer.from(x,'base64').toString('utf8');if(!s.startsWith('ENC:'))throw new Error('bad');return s.slice(4)};
  const vault=createOwnerVault({root,protect,unprotect});
  const secret={accessToken:'TOP-SECRET-123',refreshToken:'REFRESH-456'};
  const meta=await vault.set('provider/account',secret),artifact=await vault.encryptedArtifact('provider/account');
  assert.equal(artifact.plaintextIncluded,false);
  assert.equal(artifact.ciphertext.includes('TOP-SECRET-123'),false);
  assert.deepEqual(await vault.get('provider/account'),secret);
  assert.equal((await vault.status()).plaintextFallback,false);
  assert.ok(meta.ciphertextBytes>0);
});

test('multi-brain recovery envelope decrypts only for intended recipient keys',()=>{
  const a=crypto.generateKeyPairSync('rsa',{modulusLength:2048}),b=crypto.generateKeyPairSync('rsa',{modulusLength:2048}),wrong=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
  const pub=k=>k.publicKey.export({type:'spki',format:'pem'}),priv=k=>k.privateKey.export({type:'pkcs8',format:'pem'});
  const secret='ciphertext-backup-fixture';
  const env=sealRecoveryEnvelope({plaintext:secret,recipients:[{id:'brain3',publicKeyPem:pub(a)},{id:'brain4',publicKeyPem:pub(b)}]});
  assert.equal(JSON.stringify(env).includes(secret),false);
  assert.equal(openRecoveryEnvelope({envelope:env,recipientId:'brain3',privateKeyPem:priv(a)}),secret);
  assert.equal(openRecoveryEnvelope({envelope:env,recipientId:'brain4',privateKeyPem:priv(b)}),secret);
  assert.throws(()=>openRecoveryEnvelope({envelope:env,recipientId:'brain3',privateKeyPem:priv(wrong)}));
});
