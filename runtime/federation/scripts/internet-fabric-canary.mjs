import fs from 'node:fs';
import {
  compileInternetFabricPlan,
  internetNamespace,
} from '../lib/internet-functional-fabric.mjs';

const resources=[
  {id:'google-public-dns',family:'dns',provider:'Google',namespace:internetNamespace(['google','dns','public']),capabilities:['net.dns.resolve'],dedupGroup:'google-dns',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:20},state:'VERIFIED',sourceRef:'LiveBus31:GF-001'},
  {id:'google-public-ntp',family:'time',provider:'Google',namespace:internetNamespace(['google','ntp']),capabilities:['net.time.sync'],dedupGroup:'google-ntp',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:10},state:'VERIFIED',sourceRef:'LiveBus31:GF-002'},
  {id:'google-fonts',family:'transform',provider:'Google',namespace:internetNamespace(['google','fonts']),capabilities:['content.font.subset'],dedupGroup:'google-fonts',independenceGroup:'google',authorization:{mode:'PUBLIC',allowedDataClasses:['BL-S0']},telemetry:{trust:.95,availability:.99,p95LatencyMs:80},state:'VERIFIED',sourceRef:'LiveBus31:GF-003'},
  {id:'workspace-owner',family:'workspace',provider:'Google',namespace:internetNamespace(['google','workspace','owner']),capabilities:['state.store','doc.transform'],dedupGroup:'workspace',independenceGroup:'google-workspace',authorization:{mode:'OWNER_OAUTH',allowedDataClasses:['BL-S1']},telemetry:{trust:.99,availability:.99,p95LatencyMs:120},state:'VERIFIED',sourceRef:'LiveBus22:GCS-006'},
  {id:'owner-workstation-gpu',family:'compute',provider:'Owner',namespace:internetNamespace(['owner','workstation','gpu0']),capabilities:['compute.general','compute.cuda.fp32'],dedupGroup:'owner-workstation',independenceGroup:'owner',authorization:{mode:'OWNER',allowedDataClasses:['BL-S1']},telemetry:{trust:1,availability:1,p95LatencyMs:2},state:'VERIFIED',sourceRef:'LightBoot GPU baseline'},
  {id:'github-actions-cpu',family:'compute',provider:'GitHub',namespace:internetNamespace(['github','actions','cpu']),capabilities:['compute.general'],dedupGroup:'github-actions',independenceGroup:'github',authorization:{mode:'ACCOUNT',allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.95,p95LatencyMs:500},state:'VERIFIED',sourceRef:'RCP-20260920-PUBLIC-GITHUB-ACTIONS-STRESS8-EXEC-018'},
  {id:'railway-loop',family:'compute',provider:'Railway',namespace:internetNamespace(['railway','loop']),capabilities:['compute.general'],dedupGroup:'railway',independenceGroup:'railway',authorization:{mode:'ACCOUNT',allowedDataClasses:['BL-S0']},telemetry:{trust:.9,availability:.95,p95LatencyMs:250},state:'ACTIVE',sourceRef:'LiveBus46/48'},
];

const plan=compileInternetFabricPlan({
  taskId:'JOB-DEUS-GLOBAL-INTERNET-FABRIC-CANARY-20260923',
  logicalUnits:'1000000000000',
  resourceVector:{vcpuEquivalent:48,provenSimultaneousVcpuLowerBound:28,hostRamGiBPortfolio:125,verifiedGpuCount:1,verifiedVramGiB:6,opaqueInferenceSlots:0,functionalRoots:7},
  resources,
  operators:[
    {id:'name',capability:'net.dns.resolve',logicalWorkUnits:'100000000000'},
    {id:'time',capability:'net.time.sync',logicalWorkUnits:'1000000000'},
    {id:'compute',capability:'compute.general',deps:['name','time'],logicalWorkUnits:'1000000',maxRoutes:4},
    {id:'commit',capability:'state.store',deps:['compute'],dataClass:'BL-S1',logicalWorkUnits:'1'},
  ],
  maxHotRoutes:16,
  maxPhysicalShards:64,
  metadata:{boot:'DEUS-LIGHT-BOOT-CAPSULE-V5',profile:'full-spectrum post-lightboot'},
});
fs.mkdirSync('.deus/internet-fabric',{recursive:true});
fs.writeFileSync('.deus/internet-fabric/plan.json',JSON.stringify(plan,null,2)+'\n');
console.log(JSON.stringify({verdict:plan.summary.heldOperators===0?'PASS':'HOLD',planDigest:plan.planDigest,summary:plan.summary,selectedResourceIds:plan.selectedResourceIds,truthBoundary:plan.truthBoundary}));
