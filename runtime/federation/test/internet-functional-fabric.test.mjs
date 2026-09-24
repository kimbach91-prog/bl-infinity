import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CAPABILITY_ABI_VERSION,
  compileCapabilityAtlas,
  compileGenerativeNamespace,
  selectTaskFitRoutes,
  evaluateTaskFitRoutes,
  resolveNamespaceCandidates,
  compileInternetFabricPlan,
  buildCrossCheckSet,
  internetNamespace,
  normalizeCapabilitySignature,
  SUPERCELL_PROFILE,
  INTERNET_ADDRESS_SLOT_DOMAIN,
  canonicalizeInternetIdentity,
  projectInternetIdentity,
  cidrCardinality,
  projectCidrAddress,
  classifyComputeRegistry,
  compileInternetObservatoryKernel,
} from '../lib/internet-functional-fabric.mjs';

const NOW=Date.parse('2026-09-23T16:40:00Z');
const resources=[
  {id:'google-dns-a',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public-a']),capabilities:['net.dns.resolve'],dedupGroup:'google-dns',independenceGroup:'google',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:20},state:'ACTIVE'},
  {id:'google-dns-b',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public-b']),capabilities:['net.dns.resolve'],dedupGroup:'google-dns',independenceGroup:'google',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.99,p95LatencyMs:18},state:'ACTIVE'},
  {id:'quad9-dns',family:'dns',provider:'Quad9',namespace:internetNamespace(['quad9','dns','public']),capabilities:['net.dns.resolve'],dedupGroup:'quad9',independenceGroup:'quad9',authorization:{allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.98,p95LatencyMs:25},state:'ACTIVE'},
  {id:'workspace',family:'workspace',provider:'Google',namespace:internetNamespace(['google','workspace']),capabilities:['state.store','doc.transform'],authorization:{mode:'OWNER_OAUTH',allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99,p95LatencyMs:120},state:'VERIFIED'},
  {id:'owner-gpu',family:'compute',provider:'Owner',namespace:internetNamespace(['owner','workstation','gpu0']),capabilities:['compute.cuda.fp32','compute.general'],authorization:{mode:'OWNER',allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:2,estimatedBandwidthMbps:10000},state:'VERIFIED'},
  {id:'expired',family:'compute',provider:'Old',namespace:internetNamespace(['old','worker']),capabilities:['compute.general'],authorization:{allowedDataClasses:['BL-S1'],expiresAt:'2020-01-01T00:00:00Z'},telemetry:{trust:1,availability:1},state:'ACTIVE'},
];

test('V1 string capabilities remain compatible and atlas is content-addressed',()=>{
  const atlas=compileCapabilityAtlas(resources);
  assert.equal(atlas.summary.resources,6);
  assert.equal(atlas.atlasDigest.length,64);
  assert.equal(atlas.resources[0].capabilityAbi[0].schema,CAPABILITY_ABI_VERSION);
  assert.equal(atlas.resources[0].capabilityAbi[0].inputType,'ANY');
  assert.throws(()=>compileCapabilityAtlas([...resources,resources[0]]),/duplicate resource id/);
});

test('typed capability ABI preserves IO, protocol, ceiling and receipt contract',()=>{
  const abi=normalizeCapabilitySignature({
    id:'net.dns.resolve',inputType:'dns.question',outputType:'dns.answer',protocols:['doh'],
    sideEffect:'READ_ONLY',dataCeiling:'PUBLIC',receiptSchema:'dns-receipt/1',verifier:'dns-answer-check/1',
  });
  assert.equal(abi.uri,'cap://net.dns.resolve/dns.question->dns.answer');
  assert.deepEqual(abi.protocols,['DOH']);
  assert.equal(abi.dataCeiling,'PUBLIC');
  assert.equal(abi.receiptSchema,'dns-receipt/1');
});

test('route selection deduplicates lanes and respects authority expiry',()=>{
  const atlas=compileCapabilityAtlas(resources);
  const dns=selectTaskFitRoutes(atlas,{capability:'net.dns.resolve',dataClass:'BL-S0',maxRoutes:8,now:NOW});
  assert.equal(dns.length,2);
  assert.equal(new Set(dns.map(x=>x.dedupGroup)).size,2);
  const compute=selectTaskFitRoutes(atlas,{capability:'compute.general',dataClass:'BL-S1',maxRoutes:8,now:NOW});
  assert.deepEqual(compute.map(x=>x.id),['owner-gpu']);
});

test('freshness, quota, cost, trust and receipt requirements fail closed when requested',()=>{
  const atlas=compileCapabilityAtlas([
    {id:'fresh',namespace:internetNamespace(['compute','fresh']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result',receiptSchema:'exec/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99,p95LatencyMs:10,costPerUnitUsd:.001},freshness:{observedAt:'2026-09-23T16:39:30Z',ttlMs:120000},quota:{remaining:2},receipt:{capable:true,schema:'exec/1'},state:'VERIFIED'},
    {id:'stale',namespace:internetNamespace(['compute','stale']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result',receiptSchema:'exec/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:1},freshness:{observedAt:'2026-09-23T15:00:00Z',ttlMs:1000},quota:{remaining:3},receipt:{capable:true,schema:'exec/1'},state:'VERIFIED'},
    {id:'no-receipt',namespace:internetNamespace(['compute','no-receipt']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:1},freshness:{observedAt:'2026-09-23T16:39:50Z',ttlMs:120000},quota:{remaining:3},state:'VERIFIED'},
    {id:'zero-quota',namespace:internetNamespace(['compute','zero']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result',receiptSchema:'exec/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:1},freshness:{observedAt:'2026-09-23T16:39:50Z'},quota:{remaining:0},receipt:{capable:true,schema:'exec/1'},state:'VERIFIED'},
  ]);
  const evaluated=evaluateTaskFitRoutes(atlas,{
    operatorAbi:{id:'compute.general',inputType:'job',outputType:'result'},dataClass:'BL-S1',now:NOW,
    requireReceipt:true,maxEvidenceAgeMs:120000,requireKnownQuota:true,maxCostPerUnitUsd:.01,minTrust:.9,
  });
  assert.deepEqual(evaluated.routes.map(x=>x.id),['fresh']);
  assert.equal(evaluated.rejectionCounts.FRESHNESS,1);
  assert.equal(evaluated.rejectionCounts.RECEIPT_PATH,1);
  assert.equal(evaluated.rejectionCounts.QUOTA,1);
});

test('data ceiling, side-effect and receipt-schema contracts reject incompatible routes',()=>{
  const atlas=compileCapabilityAtlas([
    {id:'public-read',namespace:internetNamespace(['service','public-read']),capabilityAbi:[{id:'object.store',inputType:'object',outputType:'revision',sideEffect:'READ_ONLY',dataCeiling:'PUBLIC',receiptSchema:'read/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1},receipt:{capable:true,schema:'read/1'},state:'VERIFIED'},
    {id:'public-write',namespace:internetNamespace(['service','public-write']),capabilityAbi:[{id:'object.store',inputType:'object',outputType:'revision',sideEffect:'WRITE',dataCeiling:'PUBLIC',receiptSchema:'write/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1},receipt:{capable:true,schema:'write/1'},state:'VERIFIED'},
    {id:'private-write-wrong-receipt',namespace:internetNamespace(['service','private-write-wrong']),capabilityAbi:[{id:'object.store',inputType:'object',outputType:'revision',sideEffect:'WRITE',dataCeiling:'BL-S1',receiptSchema:'write/0'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1},receipt:{capable:true,schema:'write/0'},state:'VERIFIED'},
    {id:'private-write',namespace:internetNamespace(['service','private-write']),capabilityAbi:[{id:'object.store',inputType:'object',outputType:'revision',sideEffect:'WRITE',dataCeiling:'BL-S1',receiptSchema:'write/1'}],authorization:{allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99},receipt:{capable:true,schema:'write/1'},state:'VERIFIED'},
  ]);
  const evaluated=evaluateTaskFitRoutes(atlas,{
    operatorAbi:{id:'object.store',inputType:'object',outputType:'revision',sideEffect:'WRITE',receiptSchema:'write/1'},
    dataClass:'BL-S1',requireReceipt:true,now:NOW,
  });
  assert.deepEqual(evaluated.routes.map(x=>x.id),['private-write']);
  assert.equal(evaluated.rejectionCounts.CAPABILITY_ABI,1);
  assert.equal(evaluated.rejectionCounts.DATA_CEILING,1);
  assert.equal(evaluated.rejectionCounts.RECEIPT_PATH,1);
});

test('independent cross-check set uses distinct failure groups',()=>{
  const atlas=compileCapabilityAtlas(resources);
  const set=buildCrossCheckSet(atlas,{capability:'net.dns.resolve',width:3,now:NOW});
  assert.equal(set.length,2);
  assert.equal(new Set(set.map(x=>x.independenceGroup)).size,2);
});

test('generative namespace keeps logical cardinality cold and resolves bounded atlas routes',()=>{
  const atlas=compileCapabilityAtlas(resources);
  const namespaceIndex=compileGenerativeNamespace([{
    id:'public-dns',template:'deus://internet/{provider}/dns/{lane}',
    capabilities:['net.dns.resolve'],estimatedCardinality:'1000000000000',maxMaterialized:2,
  }]);
  assert.equal(namespaceIndex.families.length,1);
  assert.equal(namespaceIndex.summary.declaredCardinality,'1000000000000');
  assert.equal(namespaceIndex.summary.materialized,0);
  const resolved=resolveNamespaceCandidates(namespaceIndex,atlas,{
    namespace:'deus://internet/',capability:'net.dns.resolve',maxResults:2,now:NOW,
  });
  assert.equal(resolved.materialized,2);
  assert.equal(resolved.logicalCardinality,'1000000000000');
  assert.equal(new Set(resolved.resourceIds).size,2);
});

test('1T logical plan materializes bounded physical shards and globally bounded hot routes',()=>{
  const plan=compileInternetFabricPlan({
    taskId:'internet-fabric-canary',logicalUnits:'1000000000000',
    resourceVector:{vcpuEquivalent:48,provenSimultaneousVcpuLowerBound:28,hostRamGiBPortfolio:125,verifiedGpuCount:1,verifiedVramGiB:6,opaqueInferenceSlots:0,functionalRoots:8},
    resources,
    namespaceFamilies:[
      {id:'net',template:'deus://internet/{provider}/{service}/{lane}',capabilities:['net.dns.resolve','compute.general','state.store'],estimatedCardinality:'1000000000000'},
    ],
    operators:[
      {id:'resolve',operatorAbi:{id:'net.dns.resolve',inputType:'ANY',outputType:'ANY'},logicalWorkUnits:'100000000000'},
      {id:'compute',capability:'compute.general',deps:['resolve'],dataClass:'BL-S1',logicalWorkUnits:'1000000'},
      {id:'commit',capability:'state.store',deps:['compute'],dataClass:'BL-S1',logicalWorkUnits:'1'},
    ],
    maxHotRoutes:4,maxPhysicalShards:64,now:NOW,
    metadata:{purpose:'bounded 1T Internet-fabric compile canary'},
  });
  assert.equal(plan.profile,SUPERCELL_PROFILE);
  assert.equal(plan.logicalNamespace,'1000000000000');
  assert.equal(plan.summary.addressableLogicalUnits,'1000000000000');
  assert.ok(plan.summary.physicalShards<=64);
  assert.ok(plan.summary.physicalShards>=1);
  assert.equal(plan.summary.heldOperators,0);
  assert.ok(plan.summary.hotRoutes<=4);
  assert.equal(plan.namespaceSummary.declaredCardinality,'1000000000000');
  assert.equal(plan.namespaceSummary.materialized,plan.summary.hotRoutes);
  assert.match(plan.truthBoundary,/ONE_T_IS_LOGICAL_ADDRESS_SPACE/);
});


test('per-address projection is deterministic across IPv4 and IPv6 CIDRs',()=>{
  assert.equal(INTERNET_ADDRESS_SLOT_DOMAIN,1000000000000n);
  assert.deepEqual(canonicalizeInternetIdentity({type:'ipv4',value:'173.245.48.1'}),{type:'ipv4',value:'173.245.48.1'});
  assert.deepEqual(canonicalizeInternetIdentity({type:'ipv6',value:'2400:cb00:0:0:0:0:0:1'}),{type:'ipv6',value:'2400:cb00::1'});
  assert.equal(cidrCardinality('173.245.48.0/20').addressCount,'4096');
  assert.equal(cidrCardinality('2400:cb00::/32').addressCount,(1n<<96n).toString());
  const first=projectCidrAddress('173.245.48.0/20',0n);
  const last=projectCidrAddress('173.245.48.0/20',4095n);
  assert.equal(first.value,'173.245.48.0');
  assert.equal(last.value,'173.245.63.255');
  assert.equal(first.slotDomain,'1000000000000');
  assert.equal(projectInternetIdentity({type:'ipv4',value:first.value}).resourceKey,first.resourceKey);
  const v6last=projectCidrAddress('2400:cb00::/32',(1n<<96n)-1n);
  assert.equal(v6last.value,'2400:cb00:ffff:ffff:ffff:ffff:ffff:ffff');
  assert.match(first.truthBoundary,/VIRTUAL_PER_ADDRESS_MAPPING/);
});

test('compute registry keeps historical positive routes out until fresh attributable execution receipt exists',()=>{
  const now=Date.parse('2026-09-24T04:55:00Z');
  const classified=classifyComputeRegistry([
    {MAP_ID:'old',ROUTE_ROOT:'old-cpu',PLATFORM:'Old',RESOURCE_CLASS:'REMOTE_CPU_SERVICE',EXECUTABLE_STATE:'EXECUTED_VERIFIED',EFFECTIVE_CREDIT:'POSITIVE',LAST_VERIFIED_UTC:'2026-09-20T00:00:00Z'},
    {MAP_ID:'fresh-control-only',ROUTE_ROOT:'railway-a',PLATFORM:'Railway',RESOURCE_CLASS:'REMOTE_CPU_SERVICE',EXECUTABLE_STATE:'EXECUTED_VERIFIED',EFFECTIVE_CREDIT:'POSITIVE',LAST_VERIFIED_UTC:'2026-09-24T04:54:30Z'},
    {MAP_ID:'fresh-executed',ROUTE_ROOT:'gha',PLATFORM:'GitHub Actions',RESOURCE_CLASS:'HOSTED_CPU_CI',EXECUTABLE_STATE:'EXECUTED_VERIFIED',EFFECTIVE_CREDIT:'POSITIVE',LAST_VERIFIED_UTC:'2026-09-24T04:54:30Z',currentExecutionReceipt:'gha-run-123'},
  ],{now,maxFreshAgeMs:60000});
  assert.equal(classified.total,3);
  assert.equal(classified.historicalPositive,3);
  assert.equal(classified.currentAdmitted,1);
  assert.equal(classified.freshnessRequired,2);
  assert.equal(classified.routes.find(x=>x.id==='fresh-control-only').admission,'FRESHNESS_CANARY_REQUIRED');
  assert.equal(classified.routes.find(x=>x.id==='fresh-executed').admission,'CURRENT_ADMITTED');
});

test('Internet Observatory kernel compiles virtual member coverage and current compute admission without enumerating address space',()=>{
  const now=Date.parse('2026-09-24T04:55:00Z');
  const kernel=compileInternetObservatoryKernel({
    identities:[
      {type:'dns',value:'EXAMPLE.COM.'},
      {type:'asn',value:'AS13335'},
      {type:'url',value:'HTTPS://EXAMPLE.COM/a'},
    ],
    cidrs:['173.245.48.0/20','2400:cb00::/32'],
    computeRoutes:[
      {id:'gha',routeRoot:'gha',platform:'GitHub Actions',resourceClass:'HOSTED_CPU_CI',executableState:'EXECUTED_VERIFIED',effectiveCredit:'POSITIVE',lastVerifiedUtc:'2026-09-24T04:54:30Z',currentExecutionReceipt:'gha-run-123'},
      {id:'stale',routeRoot:'stale',platform:'Old',resourceClass:'REMOTE_CPU_SERVICE',executableState:'EXECUTED_VERIFIED',effectiveCredit:'POSITIVE',lastVerifiedUtc:'2026-09-20T04:00:00Z'},
    ],
    now,maxFreshAgeMs:60000,
  });
  assert.equal(kernel.materializedIdentityCount,3);
  assert.equal(kernel.virtualCidrFamilies,2);
  assert.equal(kernel.virtualAddressCount,(4096n+(1n<<96n)).toString());
  assert.equal(kernel.compute.currentAdmitted,1);
  assert.equal(kernel.compute.freshnessRequired,1);
  assert.equal(kernel.cidrCoverage[0].first.value,'173.245.48.0');
  assert.equal(kernel.cidrCoverage[0].last.value,'173.245.63.255');
  assert.equal(kernel.kernelDigest.length,64);
  assert.match(kernel.truthBoundary,/FULL_VIRTUAL_ADDRESSABILITY_NE_FULL_OBSERVATION/);
});
