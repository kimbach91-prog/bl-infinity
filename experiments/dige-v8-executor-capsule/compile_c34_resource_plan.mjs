import fs from 'node:fs';
import path from 'node:path';
import { compileDigeC34Plan } from '../../runtime/federation/lib/logical-resource-compiler.mjs';

const num=(name,fallback)=>{
  const raw=process.env[name];
  const n=raw==null?fallback:Number(raw);
  if(!Number.isFinite(n)||n<0) throw new Error(`${name} invalid`);
  return n;
};

const vector={
  vcpuEquivalent:num('DEUS_VCPU_EQ',48),
  provenSimultaneousVcpuLowerBound:num('DEUS_SIMUL_VCPU_LB',28),
  hostRamGiBPortfolio:num('DEUS_HOST_RAM_GIB',125),
  verifiedGpuCount:num('DEUS_GPU_COUNT',0),
  verifiedVramGiB:num('DEUS_VRAM_GIB',0),
  opaqueInferenceSlots:num('DEUS_OPAQUE_INFERENCE_SLOTS',0),
  functionalRoots:num('DEUS_FUNCTIONAL_ROOTS',0),
};

const plan=compileDigeC34Plan(vector,{
  guideDistances:[0.014,0.021,0.028],
  denseSearchCount:7,
  samplesSearch:24,
  samplesFinal:384,
});
const searches=plan.stages.filter(x=>x.role==='SEARCH_RENDER');
const matrix=searches.map((s)=>({
  id:s.id.replace('candidate-','d'),
  guide_dist:s.metadata.guideDistM.toFixed(3),
  execution:s.placement.execution,
}));
const finalStage=plan.stages.find(x=>x.id==='final-render');
const runtimeDevice=finalStage.placement.execution==='GPU'?'GPU':'CPU';
const receipt={
  schema:'DIGE_C34_LOGICAL_RESOURCE_PLAN_RECEIPT_V1',
  generatedAt:new Date().toISOString(),
  resourceSnapshotSource:process.env.DEUS_RESOURCE_SNAPSHOT_SOURCE||'LiveBus:38_UNIFIED_RESOURCE_KERNEL@2026-09-21',
  plan,
  matrix,
  runtimeDevice,
  truthBoundary:'COMPILER_PLAN_DRIVES_THIS_WORKFLOW__RESOURCE_SNAPSHOT_IS_SCOPED__CPU_FALLBACK_NE_GPU_EXECUTION'
};
const out=process.env.DIGE_RESOURCE_PLAN_OUT||'runtime/DIGE_C34_RESOURCE_PLAN.json';
fs.mkdirSync(path.dirname(out),{recursive:true});
fs.writeFileSync(out,JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
if(process.env.GITHUB_OUTPUT){
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`matrix=${JSON.stringify(matrix)}\n`);
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`runtime_device=${runtimeDevice}\n`);
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`plan_digest=${plan.planDigest}\n`);
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`avoided_candidates=${plan.optimization?.avoidedCandidates??0}\n`);
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`avoided_fraction=${plan.optimization?.avoidedFraction??0}\n`);
}
