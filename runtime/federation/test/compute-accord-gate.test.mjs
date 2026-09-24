import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateComputeOffer, negotiateComputeAccord } from '../lib/compute-accord-gate.mjs';

test('declines mapped device without authority or opt-in',()=>{
  const d=evaluateComputeOffer({offerId:'x',authorityClass:'ADDRESS_ONLY',receiptPath:true,canaryPassed:true,currentLease:true,expectedUsefulValue:10});
  assert.equal(d.decision,'DECLINE');
  assert.equal(d.supercellAttachAllowed,false);
});

test('holds paid market offer without economic authority',()=>{
  const d=evaluateComputeOffer({
    offerId:'golem',authorityClass:'OPT_IN_MARKET',optIn:true,receiptPath:true,
    canaryPassed:true,currentLease:true,paymentRequired:true,economicAuthority:false,
    expectedUsefulValue:20,computeCost:2,
  });
  assert.equal(d.decision,'HOLD');
  assert.ok(d.reasons.includes('ECONOMIC_AUTHORITY_REQUIRED'));
});

test('admits fresh owner route with receipt and positive value',()=>{
  const d=evaluateComputeOffer({
    offerId:'gha',authorityClass:'OWNER_AUTHORIZED',ownerAuthorized:true,receiptPath:true,
    canaryPassed:true,currentLease:true,freshnessMs:1000,expectedUsefulValue:10,
  });
  assert.equal(d.decision,'ADMIT_CURRENT');
  assert.equal(d.supercellAttachAllowed,true);
});

test('never attaches installable mini-cell without explicit consent',()=>{
  const d=evaluateComputeOffer({
    offerId:'volunteer',authorityClass:'OPT_IN_VOLUNTEER',optIn:true,receiptPath:true,
    canaryPassed:true,currentLease:true,installMode:'MINI_DEUS',installConsent:false,expectedUsefulValue:10,
  });
  assert.equal(d.decision,'DECLINE');
});

test('negotiation partitions admitted/hold/decline truthfully',()=>{
  const n=negotiateComputeAccord([
    {offerId:'drive',authorityClass:'CONNECTED_ACCOUNT',receiptPath:true,canaryPassed:true,currentLease:true,expectedUsefulValue:3},
    {offerId:'hf',authorityClass:'CONNECTED_ACCOUNT',receiptPath:true,canaryPassed:false,currentLease:false,expectedUsefulValue:8},
    {offerId:'unknown',authorityClass:'ADDRESS_ONLY',receiptPath:false},
  ]);
  assert.equal(n.counts.total,3);
  assert.equal(n.counts.admitted,1);
  assert.equal(n.counts.candidate,1);
  assert.equal(n.counts.decline,1);
});
