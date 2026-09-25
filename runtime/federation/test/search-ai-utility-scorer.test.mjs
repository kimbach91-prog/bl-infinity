import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SEARCH_AI_UTILITY_SCORER_VERSION,
  normalizeSearchAiProfile,
  scoreSearchAiProfile,
  applySearchAiResultReceipt,
  selectSearchAiRoutes,
} from '../lib/search-ai-utility-scorer.mjs';

const google={
  rootId:'SAF-GOOGLE-SEARCH-ROOT',provider:'Google',surface:'Google Search / AI-assisted search',
  namespace:'deus://search-ai/google/search',taskFamily:'SEARCH_RESEARCH',
  routeState:'ADDRESSABLE / EXECUTION_SURFACE_SCOPED',authScope:'PUBLIC_OR_ACCOUNT_SESSION',
  executionAuthorized:false,receiptCount:0,successCount:0,failureScars:0,
};
const ms={
  rootId:'SAF-MS-BING-GROUNDING-ROOT',provider:'Microsoft',surface:'Grounding with Bing Search',
  namespace:'deus://search-ai/microsoft/foundry/bing-grounding',taskFamily:'SEARCH_RESEARCH',
  routeState:'HOLD_AUTH_COST_CANARY',authScope:'FOUNDRY_PROJECT_CONNECTION / BILLING_SCOPE_REQUIRED',
  executionAuthorized:false,receiptCount:0,successCount:0,failureScars:0,
};
const local={
  rootId:'SAF-DEUS-LOCAL-CACHE-ROOT',provider:'DEUS',surface:'Local semantic/address cache',
  namespace:'deus://search-ai/local/cache',taskFamily:'SEARCH_RESEARCH',
  routeState:'LOCAL_ROUTABLE_WHEN_SCOPE_ALLOWS',authScope:'INHERIT_SOURCE_DATA_CLASS',
  executionAuthorized:true,qualityMean:1,qualityCount:2,latencyMeanMs:4,latencyCount:2,
  costMeanUsd:0,costCount:2,freshnessFactor:1,reuseCount:8,receiptCount:2,successCount:2,
  failureScars:0,lastResultRef:'local-cache-receipt-2',
};

test('profile normalization is search-ai scoped and content-addressable inputs stay bounded',()=>{
  const p=normalizeSearchAiProfile(local);
  assert.equal(p.schema,SEARCH_AI_UTILITY_SCORER_VERSION);
  assert.equal(p.namespace,'deus://search-ai/local/cache');
  assert.throws(()=>normalizeSearchAiProfile({...local,namespace:'deus://internet/google/search'}),/search-ai/);
  assert.throws(()=>normalizeSearchAiProfile({...local,successCount:3,receiptCount:2}),/cannot exceed/);
});

test('discovery can rank official roots without promoting them to execution authority',()=>{
  const selected=selectSearchAiRoutes([google,ms,local],{mode:'DISCOVERY',maxRoutes:3});
  assert.equal(selected.routes.length,3);
  assert.ok(selected.routes.some(x=>x.rootId===google.rootId));
  assert.ok(selected.routes.some(x=>x.rootId===ms.rootId));
  assert.match(selected.truthBoundary,/ADDRESS_MEMORY_NE_AUTHORITY/);
});

test('execution fails closed for auth-unbound and unreceipted provider roots',()=>{
  const selected=selectSearchAiRoutes([google,ms,local],{mode:'EXECUTION',maxRoutes:3});
  assert.deepEqual(selected.routes.map(x=>x.rootId),[local.rootId]);
  assert.ok((selected.rejectionCounts.AUTHORITY??0)>=2);
});

test('a successful attributable receipt increases evidence and reusable utility',()=>{
  const before=normalizeSearchAiProfile({
    ...local,qualityMean:.8,qualityCount:1,reuseCount:0,receiptCount:1,successCount:1,
    latencyMeanMs:100,latencyCount:1,lastResultRef:'r1',
  });
  const beforeScore=scoreSearchAiProfile(before,{mode:'EXECUTION'}).utilityScore;
  const after=applySearchAiResultReceipt(before,{
    success:true,resultRef:'r2',qualityScore:1,latencyMs:80,costUsd:0,freshnessFactor:1,reuseHit:true,
  });
  const afterScore=scoreSearchAiProfile(after,{mode:'EXECUTION'}).utilityScore;
  assert.equal(after.receiptCount,2);
  assert.equal(after.successCount,2);
  assert.equal(after.reuseCount,1);
  assert.equal(after.failureScars,0);
  assert.ok(afterScore>beforeScore);
});

test('failure scars reduce route utility and can change selection order',()=>{
  const good=normalizeSearchAiProfile({
    ...local,rootId:'good',qualityMean:.8,qualityCount:3,receiptCount:3,successCount:3,
    failureScars:0,reuseCount:1,lastResultRef:'g3',
  });
  let scarred=normalizeSearchAiProfile({
    ...local,rootId:'scarred',qualityMean:.8,qualityCount:3,receiptCount:3,successCount:3,
    failureScars:0,reuseCount:1,lastResultRef:'s3',
  });
  scarred=applySearchAiResultReceipt(scarred,{
    success:false,resultRef:'s4-fail',latencyMs:200,costUsd:0,freshnessFactor:1,reuseHit:false,
  });
  const selected=selectSearchAiRoutes([scarred,good],{mode:'EXECUTION',maxRoutes:2});
  assert.equal(selected.routes[0].rootId,'good');
  assert.equal(scarred.failureScars,1);
  assert.ok(selected.routes[0].selectionScore>selected.routes[1].selectionScore);
});

test('cost ceiling rejects an otherwise authorized route',()=>{
  const paid=normalizeSearchAiProfile({
    ...local,rootId:'paid',provider:'ProviderX',costMeanUsd:.02,costCount:1,lastResultRef:'p1',
  });
  const selected=selectSearchAiRoutes([paid,local],{mode:'EXECUTION',maxCostUsd:.001,maxRoutes:2});
  assert.deepEqual(selected.routes.map(x=>x.rootId),[local.rootId]);
  assert.equal(selected.rejectionCounts.COST,1);
});

test('selection digest is deterministic and never claims physical backend capacity',()=>{
  const a=selectSearchAiRoutes([google,ms,local],{mode:'DISCOVERY',maxRoutes:3});
  const b=selectSearchAiRoutes([google,ms,local],{mode:'DISCOVERY',maxRoutes:3});
  assert.equal(a.selectionDigest,b.selectionDigest);
  assert.match(a.truthBoundary,/UTILITY_NE_BACKEND_CAPACITY/);
  assert.ok(!('physicalCapacity' in a));
});
