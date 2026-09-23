import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compileCapabilityAtlas,
  selectTaskFitRoutes,
  compileInternetFabricPlan,
  buildCrossCheckSet,
  internetNamespace,
  SUPERCELL_PROFILE,
} from '../lib/internet-functional-fabric.mjs';

const resources=[
  {id:'google-dns-a',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public-a']),capabilities:['net.dns.resolve'],dedupGroup:'google-dns',independenceGroup:'google',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:20},state:'ACTIVE'},
  {id:'google-dns-b',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public-b']),capabilities:['net.dns.resolve'],dedupGroup:'google-dns',independenceGroup:'google',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.99,p95LatencyMs:18},state:'ACTIVE'},
  {id:'quad9-dns',family:'dns',provider:'Quad9',namespace:internetNamespace(['quad9','dns','public']),capabilities:['net.dns.resolve'],dedupGroup:'quad9',independenceGroup:'quad9',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.98,p95LatencyMs:25},state:'ACTIVE'},
  {id:'workspace',family:'workspace',provider:'Google',namespace:internetNamespace(['google','workspace']),capabilities:['state.store','doc.transform'],authorization:{mode:'OWNER_OAUTH',allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99,p95LatencyMs:120},state:'VERIFIED'},
  {id:'owner-gpu',family:'compute',provider:'Owner',namespace:internetNamespace(['owner','workstation','gpu0']),capabilities:['compute.cuda.fp32','compute.general'],authorization:{mode:'OWNER',allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:2,estimatedBandwidthMbps:10000},state:'VERIFIED'},
  {id:'expired',family:'compute',provider:'Old',namespace:internetNamespace(['old','worker']),capabilities:['compute.general'],authorization:{allowedDataClasses:['BL-S1'],expiresAt:'2020-01-01T00:00:00Z'},telemetry:{trust:1,availability:1},state:'ACTIVE'},
];

test('capability atlas is content-addressed and namespace-unique',()=>{
  const atlas=compileCapabilityAtlas(resources);
  assert.equal(atlas.summary.resources,6);
  assert.equal(atlas.atlasDigest.length,64);
  assert.throws(()=>compileCapabilityAtlas([...resources,resources[0]]),/duplicate resource id/);
});

test('route selection deduplicates lanes and respects authority expiry',()=>{
  const atlas=compileCapabilityAtlas(resources);
  const dns=selectTaskFitRoutes(atlas,{capability:'net.dns.resolve',dataClass:'BL-S0',maxRoutes:8,now:Date.parse('2026-09-23T16:40:00Z')});
  assert.equal(dns.length,2);
  assert.equal(new Set(dns.map(x=>x.dedupGroup)).size,2);
  const compute=selectTaskFitRoutes(atlas,{capability:'compute.general',dataClass:'BL-S1',maxRoutes:8,now:Date.parse('2026-09-23T16:40:00Z')});
  assert.deepEqual(compute.map(x=>x.id),['owner-gpu']);
});

test('independent cross-check set uses distinct failure groups',()=>{
  const atlas=compileCapabilityAtlas(resources);
  const set=buildCrossCheckSet(atlas,{capability:'net.dns.resolve',width:3});
  assert.equal(set.length,2);
  assert.equal(new Set(set.map(x=>x.independenceGroup)).size,2);
});

test('1T logical plan materializes bounded physical shards and hot routes',()=>{
  const plan=compileInternetFabricPlan({
    taskId:'internet-fabric-canary',
    logicalUnits:'1000000000000',
    resourceVector:{vcpuEquivalent:48,provenSimultaneousVcpuLowerBound:28,hostRamGiBPortfolio:125,verifiedGpuCount:1,verifiedVramGiB:6,opaqueInferenceSlots:0,functionalRoots:8},
    resources,
    operators:[
      {id:'resolve',capability:'net.dns.resolve',logicalWorkUnits:'100000000000'},
      {id:'compute',capability:'compute.general',deps:['resolve'],dataClass:'BL-S1',logicalWorkUnits:'1000000'},
      {id:'commit',capability:'state.store',deps:['compute'],dataClass:'BL-S1',logicalWorkUnits:'1'},
    ],
    maxHotRoutes:8,
    maxPhysicalShards:64,
    metadata:{purpose:'bounded 1T Internet-fabric compile canary'},
  });
  assert.equal(plan.profile,SUPERCELL_PROFILE);
  assert.equal(plan.logicalNamespace,'1000000000000');
  assert.equal(plan.summary.addressableLogicalUnits,'1000000000000');
  assert.ok(plan.summary.physicalShards<=64);
  assert.ok(plan.summary.physicalShards>=1);
  assert.equal(plan.summary.heldOperators,0);
  assert.ok(plan.summary.hotRoutes<10);
  assert.match(plan.truthBoundary,/ONE_T_IS_LOGICAL_ADDRESS_SPACE/);
});
