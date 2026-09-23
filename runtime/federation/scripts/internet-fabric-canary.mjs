import fs from 'node:fs';
import { compileInternetFabricPlan, internetNamespace } from '../lib/internet-functional-fabric.mjs';

const observedAt=new Date().toISOString();
const publicReceipt={capable:true,schema:'deus-public-functional-receipt/1'};
const resources=[
  {id:'google-public-dns',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public']),capabilityAbi:[{id:'net.dns.resolve',inputType:'dns.question',outputType:'dns.answer',protocols:['DNS','DOH','DOT'],sideEffect:'READ_ONLY',dataCeiling:'PUBLIC',receiptSchema:'deus-public-functional-receipt/1'}],dedupGroup:'google-dns',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:20},freshness:{observedAt,ttlMs:86400000,evidenceRef:'LiveBus31:GF-001'},receipt:publicReceipt,state:'VERIFIED',sourceRef:'LiveBus31:GF-001'},
  {id:'google-public-ntp',family:'time',provider:'Google',namespace:internetNamespace(['google','ntp']),capabilityAbi:[{id:'net.time.sync',inputType:'ntp.request',outputType:'ntp.reply',protocols:['NTP'],sideEffect:'READ_ONLY',dataCeiling:'PUBLIC',receiptSchema:'deus-public-functional-receipt/1'}],dedupGroup:'google-ntp',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:10},freshness:{observedAt,ttlMs:86400000,evidenceRef:'LiveBus31:GF-002'},receipt:publicReceipt,state:'VERIFIED',sourceRef:'LiveBus31:GF-002'},
  {id:'google-fonts',family:'transform',provider:'Google',namespace:internetNamespace(['google','fonts']),capabilityAbi:[{id:'content.font.subset',inputType:'font.request',outputType:'font.asset',protocols:['HTTPS'],sideEffect:'TRANSFORM',dataCeiling:'PUBLIC',receiptSchema:'deus-http-transform-receipt/1'}],dedupGroup:'google-fonts',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:80},freshness:{observedAt,ttlMs:86400000},receipt:{capable:true,schema:'deus-http-transform-receipt/1'},state:'VERIFIED',sourceRef:'LiveBus31:GF-003'},
  {id:'workspace-owner',family:'workspace',provider:'Google',namespace:internetNamespace(['google','workspace','owner']),capabilityAbi:[{id:'state.store',inputType:'workspace.object',outputType:'workspace.revision',sideEffect:'WRITE',dataCeiling:'BL-S1',receiptSchema:'workspace-revision/1'},{id:'doc.transform',inputType:'document',outputType:'document',sideEffect:'TRANSFORM',dataCeiling:'BL-S1',receiptSchema:'workspace-revision/1'}],dedupGroup:'workspace',independenceGroup:'google-workspace',authorization:{mode:'OWNER_OAUTH',allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99,p95LatencyMs:120},freshness:{observedAt,ttlMs:3600000},receipt:{capable:true,schema:'workspace-revision/1'},state:'VERIFIED',sourceRef:'LiveBus22:GCS-006'},
  {id:'owner-workstation-gpu',family:'compute',provider:'Owner',namespace:internetNamespace(['owner','workstation','gpu0']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result',sideEffect:'EXECUTE',dataCeiling:'BL-S1',receiptSchema:'deus-workstation-result/1'},{id:'compute.cuda.fp32',inputType:'cuda.job',outputType:'result',sideEffect:'EXECUTE',dataCeiling:'BL-S1',receiptSchema:'deus-workstation-result/1'}],dedupGroup:'owner-workstation',independenceGroup:'owner',authorization:{mode:'OWNER',allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:2},freshness:{observedAt,ttlMs:3600000},receipt:{capable:true,schema:'deus-workstation-result/1'},state:'VERIFIED',sourceRef:'LightBoot GPU baseline'},
  {id:'github-actions-cpu',family:'compute',provider:'GitHub',namespace:internetNamespace(['github','actions','cpu']),capabilityAbi:[{id:'compute.general',inputType:'job',outputType:'result',sideEffect:'EXECUTE',dataCeiling:'BL-S0',receiptSchema:'github-actions-run/1'}],dedupGroup:'github-actions',independenceGroup:'github',authorization:{mode:'ACCOUNT',allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.95,p95LatencyMs:500},freshness:{observedAt,ttlMs:3600000},receipt:{capable:true,schema:'github-actions-run/1'},state:'VERIFIED',sourceRef:'RCP-20260920-PUBLIC-GITHUB-ACTIONS-STRESS8-EXEC-018'},
  {id:'railway-loop',family:'compute',provider:'Railway',namespace:internetNamespace(['railway','loop']),capabilities:['compute.general'],dedupGroup:'railway',independenceGroup:'railway',authorization:{mode:'ACCOUNT',allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.95,p95LatencyMs:250},state:'HOLD',sourceRef:'Fresh observer: bounded-loop compute contract unavailable'},
];

const plan=compileInternetFabricPlan({
  taskId:'JOB-DEUS-GLOBAL-INTERNET-FABRIC-ABI-RESOLVER-V2-CANARY-20260923',
  logicalUnits:'1000000000000',
  resourceVector:{vcpuEquivalent:48,provenSimultaneousVcpuLowerBound:28,hostRamGiBPortfolio:125,verifiedGpuCount:1,verifiedVramGiB:6,opaqueInferenceSlots:0,functionalRoots:7},
  resources,
  namespaceFamilies:[
    {id:'internet-functional-root',template:'deus://internet/{layer}/{provider}/{service}/{capability}/{region}/{lane}',capabilities:['net.dns.resolve','net.time.sync','content.font.subset','compute.general','state.store'],estimatedCardinality:'1000000000000',authority:'RESOURCE_BOUND',materializer:'ATLAS_PREFIX_LAZY',maxMaterialized:16,sourceRef:'LiveBus90-94'},
  ],
  operators:[
    {id:'name',operatorAbi:{id:'net.dns.resolve',inputType:'dns.question',outputType:'dns.answer',protocols:['DNS'],sideEffect:'READ_ONLY',receiptSchema:'deus-public-functional-receipt/1'},logicalWorkUnits:'100000000000',requireReceipt:true,maxEvidenceAgeMs:86400000},
    {id:'time',operatorAbi:{id:'net.time.sync',inputType:'ntp.request',outputType:'ntp.reply',protocols:['NTP'],sideEffect:'READ_ONLY',receiptSchema:'deus-public-functional-receipt/1'},logicalWorkUnits:'1000000000',requireReceipt:true,maxEvidenceAgeMs:86400000},
    {id:'compute',operatorAbi:{id:'compute.general',inputType:'job',outputType:'result',sideEffect:'EXECUTE'},deps:['name','time'],logicalWorkUnits:'1000000',maxRoutes:4,requireReceipt:true,maxEvidenceAgeMs:3600000},
    {id:'commit',operatorAbi:{id:'state.store',inputType:'workspace.object',outputType:'workspace.revision',sideEffect:'WRITE',receiptSchema:'workspace-revision/1'},deps:['compute'],dataClass:'BL-S1',logicalWorkUnits:'1',requireReceipt:true,maxEvidenceAgeMs:3600000},
  ],
  maxHotRoutes:16,maxPhysicalShards:64,
  metadata:{boot:'DEUS-LIGHT-BOOT-CAPSULE-V5',profile:'ABI v2 + generative resolver binding canary'},
});
fs.mkdirSync('.deus/internet-fabric',{recursive:true});
fs.writeFileSync('.deus/internet-fabric/plan.json',JSON.stringify(plan,null,2)+'\n');
console.log(JSON.stringify({verdict:plan.summary.heldOperators===0?'PASS':'HOLD',planDigest:plan.planDigest,atlasDigest:plan.atlasDigest,namespaceDigest:plan.namespaceDigest,summary:plan.summary,namespaceSummary:plan.namespaceSummary,selectedResourceIds:plan.selectedResourceIds,truthBoundary:plan.truthBoundary}));
