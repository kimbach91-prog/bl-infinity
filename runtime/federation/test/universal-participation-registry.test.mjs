import test from 'node:test';
import assert from 'node:assert/strict';
import {
  registerParticipationIdentity,registerParticipationBatch,promoteRegistrationWithAccord,
  buildParticipationLease,leaseHealth,
} from '../lib/universal-participation-registry.mjs';

test('address-only identity is registered and logically addressable but not executable',()=>{
  const r=registerParticipationIdentity({type:'ipv4',value:'203.0.113.7',evidenceClass:'ADDRESS_ONLY',source:'TEST'});
  assert.equal(r.kernelIndexed,true);
  assert.equal(r.logicalActivationAllowed,true);
  assert.equal(r.offerEligible,false);
  assert.equal(r.executionAdmitted,false);
  assert.equal(r.participationClass,'INDEX_ONLY');
});

test('opt-in compute becomes offer eligible but not execution admitted before Accord Gate',()=>{
  const r=registerParticipationIdentity({
    type:'service',value:'golem:provider:test',evidenceClass:'PUBLIC_SERVICE',
    authorityClass:'OPT_IN_MARKET',optIn:true,computeHint:true,source:'TEST',
  });
  assert.equal(r.offerEligible,true);
  assert.equal(r.participationClass,'OFFER_ELIGIBLE_COMPUTE');
  assert.equal(r.executionAdmitted,false);
});

test('Accord admission promotes only eligible registration',()=>{
  const r=registerParticipationIdentity({
    type:'service',value:'owner:gha',evidenceClass:'PUBLIC_SERVICE',
    authorityClass:'OWNER_AUTHORIZED',ownerAuthorized:true,computeHint:true,source:'TEST',
  });
  const p=promoteRegistrationWithAccord(r,{decision:'ADMIT_CURRENT',supercellAttachAllowed:true,decisionDigest:'abc'});
  assert.equal(p.executionAdmitted,true);
  assert.equal(p.supercellComputeAttachAllowed,true);
  assert.equal(p.installAllowed,false);
});

test('install remains disabled without explicit install consent',()=>{
  const r=registerParticipationIdentity({
    type:'service',value:'optin:worker:1',evidenceClass:'PUBLIC_SERVICE',
    authorityClass:'OPT_IN_VOLUNTEER',optIn:true,computeHint:true,installConsent:false,source:'TEST',
  });
  const p=promoteRegistrationWithAccord(r,{decision:'ADMIT_CURRENT',supercellAttachAllowed:true});
  assert.equal(p.executionAdmitted,true);
  assert.equal(p.installAllowed,false);
});

test('batch registration deduplicates resource identities',()=>{
  const b=registerParticipationBatch([
    {type:'dns',value:'Example.COM',evidenceClass:'ADDRESS_ONLY'},
    {type:'dns',value:'example.com.',evidenceClass:'ADDRESS_ONLY'},
    {type:'service',value:'x',evidenceClass:'PUBLIC_SERVICE',authorityClass:'CONNECTED_ACCOUNT',computeHint:true},
  ]);
  assert.equal(b.counts.total,2);
  assert.equal(b.counts.offerEligible,1);
});

test('lease heartbeat gates stable dispatch',()=>{
  const r=registerParticipationIdentity({
    type:'service',value:'owner:runner',evidenceClass:'PUBLIC_SERVICE',
    authorityClass:'OWNER_AUTHORIZED',ownerAuthorized:true,computeHint:true,
  });
  const p=promoteRegistrationWithAccord(r,{decision:'ADMIT_CURRENT',supercellAttachAllowed:true});
  const lease=buildParticipationLease({
    registration:p,leaseId:'L1',issuedAt:'2026-09-24T07:00:00Z',expiresAt:'2026-09-24T08:00:00Z',heartbeatIntervalMs:10000,
  });
  assert.equal(leaseHealth(lease,{now:Date.parse('2026-09-24T07:00:15Z'),lastHeartbeatAt:'2026-09-24T07:00:10Z'}).dispatchAllowed,true);
  assert.equal(leaseHealth(lease,{now:Date.parse('2026-09-24T07:00:40Z'),lastHeartbeatAt:'2026-09-24T07:00:10Z'}).dispatchAllowed,false);
  assert.equal(leaseHealth(lease,{now:Date.parse('2026-09-24T08:00:00Z'),lastHeartbeatAt:'2026-09-24T07:59:59Z'}).state,'EXPIRED');
});
