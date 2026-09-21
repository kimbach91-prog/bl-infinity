import { sha256Json } from './canonical.mjs';

export const LOGICAL_RESOURCE_COMPILER_VERSION='deus-logical-resource-compiler/1.0';
export const ONE_T_LOGICAL_NAMESPACE='1000000000000';

function nn(value,name,allowNull=false){
  if((value===null||value===undefined||value==='UNKNOWN')&&allowNull) return null;
  const n=Number(value??0);
  if(!Number.isFinite(n)||n<0) throw new Error(`${name} must be a non-negative number`);
  return n;
}
function bool(v){return v===true||String(v).toLowerCase()==='true';}
function uniq(xs){return [...new Set(xs)];}
function clone(v){return v===undefined?undefined:structuredClone(v);}

export function normalizeResourceVector(vector={}){
  return Object.freeze({
    vcpuEquivalent:nn(vector.vcpuEquivalent,'vcpuEquivalent'),
    provenSimultaneousVcpuLowerBound:nn(vector.provenSimultaneousVcpuLowerBound,'provenSimultaneousVcpuLowerBound'),
    hostRamGiBPortfolio:nn(vector.hostRamGiBPortfolio,'hostRamGiBPortfolio'),
    verifiedGpuCount:nn(vector.verifiedGpuCount,'verifiedGpuCount'),
    verifiedVramGiB:nn(vector.verifiedVramGiB,'verifiedVramGiB'),
    opaqueInferenceSlots:nn(vector.opaqueInferenceSlots,'opaqueInferenceSlots'),
    functionalRoots:nn(vector.functionalRoots,'functionalRoots'),
  });
}

function normalizeStage(stage,index){
  const id=String(stage?.id??`stage-${index+1}`).trim();
  if(!id) throw new Error('stage.id required');
  const cpu=String(stage.cpu??'OPTIONAL').toUpperCase();
  const gpu=String(stage.gpu??'NONE').toUpperCase();
  if(!['NONE','OPTIONAL','PREFERRED','REQUIRED'].includes(cpu)) throw new Error(`invalid cpu mode for ${id}`);
  if(!['NONE','OPTIONAL','PREFERRED','REQUIRED'].includes(gpu)) throw new Error(`invalid gpu mode for ${id}`);
  return Object.freeze({
    id,
    role:String(stage.role??'COMPUTE').toUpperCase(),
    deps:Object.freeze([...(stage.deps??[])].map(String)),
    cpu,
    gpu,
    cpuFallback:stage.cpuFallback!==false,
    vramRole:String(stage.vramRole??'NONE').toUpperCase(),
    ramRole:String(stage.ramRole??'NONE').toUpperCase(),
    storageRole:String(stage.storageRole??'NONE').toUpperCase(),
    cacheable:bool(stage.cacheable),
    reusableState:bool(stage.reusableState),
    logicalWorkUnits:stage.logicalWorkUnits==null?null:String(stage.logicalWorkUnits),
    capability:String(stage.capability??stage.role??'compute').trim(),
    metadata:clone(stage.metadata??{}),
  });
}

function decideMaterialization(stage,vector){
  const cpuAvailable=vector.vcpuEquivalent>0;
  const gpuAvailable=vector.verifiedGpuCount>0 && vector.verifiedVramGiB>0;
  let execution='LOGICAL_ONLY';
  let state='READY';

  if(stage.gpu==='REQUIRED'){
    if(gpuAvailable) execution='GPU';
    else {execution='HOLD_GPU_REQUIRED';state='HOLD';}
  } else if(stage.gpu==='PREFERRED'){
    if(gpuAvailable) execution='GPU';
    else if(stage.cpuFallback && cpuAvailable) execution='CPU_FALLBACK';
    else if(cpuAvailable && stage.cpu!=='NONE') execution='CPU';
    else {execution='HOLD_NO_EXECUTOR';state='HOLD';}
  } else if(stage.cpu==='REQUIRED'||stage.cpu==='PREFERRED'){
    if(cpuAvailable) execution='CPU';
    else {execution='HOLD_CPU_REQUIRED';state='HOLD';}
  } else if(stage.cpu==='OPTIONAL'&&cpuAvailable){
    execution='CPU';
  }

  const virtualRoles=[];
  if(stage.cpu!=='NONE') virtualRoles.push('vCPU');
  if(stage.ramRole!=='NONE') virtualRoles.push('vRAM');
  if(stage.gpu!=='NONE') virtualRoles.push('vGPU');
  if(stage.vramRole!=='NONE') virtualRoles.push('vVRAM');
  if(stage.storageRole!=='NONE') virtualRoles.push('vSTATE');

  let memoryMaterialization='NONE';
  if(stage.vramRole!=='NONE' && execution==='GPU') memoryMaterialization='PHYSICAL_VRAM';
  else if(stage.ramRole!=='NONE' && vector.hostRamGiBPortfolio>0) memoryMaterialization='HOST_RAM_WORKING_SET';
  else if(stage.vramRole!=='NONE'||stage.ramRole!=='NONE') memoryMaterialization='LOGICAL_STATE_CACHE_OR_RECOMPUTE';

  return {
    state,
    execution,
    virtualRoles:uniq(virtualRoles),
    memoryMaterialization,
    gpuPromotionGate:stage.gpu!=='NONE'&&!gpuAvailable?'FRESH_GPU_VRAM_RECEIPT_REQUIRED':null,
  };
}

export function compileLogicalResourcePlan({
  taskId,
  stages,
  resourceVector,
  logicalNamespace=ONE_T_LOGICAL_NAMESPACE,
  taskLogicalUnits=null,
  optimization=null,
  dataClass='BL-S0',
  metadata={},
}={}){
  const id=String(taskId??'').trim();
  if(!id) throw new Error('taskId required');
  if(!Array.isArray(stages)||stages.length===0) throw new Error('stages must be non-empty');
  const vector=normalizeResourceVector(resourceVector);
  const normalizedStages=stages.map(normalizeStage);
  const ids=new Set(normalizedStages.map(s=>s.id));
  if(ids.size!==normalizedStages.length) throw new Error('stage ids must be unique');
  for(const s of normalizedStages) for(const dep of s.deps) if(!ids.has(dep)) throw new Error(`unknown dependency ${dep}`);

  const compiled=normalizedStages.map(stage=>Object.freeze({
    ...stage,
    placement:decideMaterialization(stage,vector),
  }));

  const dense=optimization?.denseCandidateCount==null?null:nn(optimization.denseCandidateCount,'denseCandidateCount');
  const materialized=optimization?.materializedCandidateCount==null?null:nn(optimization.materializedCandidateCount,'materializedCandidateCount');
  if(dense!==null && materialized!==null && materialized>dense) throw new Error('materializedCandidateCount > denseCandidateCount');
  const workAvoidance=(dense!==null&&materialized!==null&&dense>0)?{
    scope:String(optimization.scope??'SEARCH_PLAN'),
    denseCandidateCount:dense,
    materializedCandidateCount:materialized,
    avoidedCandidates:dense-materialized,
    avoidedFraction:(dense-materialized)/dense,
    avoidedFactor:materialized>0?dense/materialized:Infinity,
    truthBoundary:'PLANNED_CANDIDATE_WORK_AVOIDANCE__NOT_JOULE_SAVINGS_OR_RUNTIME_SPEEDUP',
  }:null;

  const summary={
    stages:compiled.length,
    ready:compiled.filter(x=>x.placement.state==='READY').length,
    hold:compiled.filter(x=>x.placement.state==='HOLD').length,
    cpu:compiled.filter(x=>x.placement.execution==='CPU').length,
    cpuFallback:compiled.filter(x=>x.placement.execution==='CPU_FALLBACK').length,
    gpu:compiled.filter(x=>x.placement.execution==='GPU').length,
    logicalOnly:compiled.filter(x=>x.placement.execution==='LOGICAL_ONLY').length,
  };

  const payload={
    schema:LOGICAL_RESOURCE_COMPILER_VERSION,
    taskId:id,
    dataClass:String(dataClass),
    logicalNamespace:String(logicalNamespace),
    taskLogicalUnits:taskLogicalUnits==null?null:String(taskLogicalUnits),
    resourceVector:vector,
    stages:compiled,
    optimization:workAvoidance,
    summary,
    metadata:clone(metadata),
    truthBoundary:'LOGICAL_ROLES_ARE_COMPILATION_ABSTRACTIONS__PHYSICAL_CPU_GPU_RAM_VRAM_CREDIT_REQUIRES_RUNTIME_RECEIPTS__LOGICAL_NAMESPACE_NE_PHYSICAL_HARDWARE',
  };
  return Object.freeze({...payload,planDigest:sha256Json(payload)});
}

export function compileDigeC34Plan(resourceVector,{
  guideDistances=[0.014,0.021,0.028],
  denseSearchCount=7,
  samplesSearch=24,
  samplesFinal=384,
}={}){
  const scatter=guideDistances.map((d,i)=>({
    id:`candidate-${String(i+1).padStart(2,'0')}`,
    role:'SEARCH_RENDER',
    deps:['prep-runtime'],
    cpu:'REQUIRED',
    gpu:'PREFERRED',
    cpuFallback:true,
    ramRole:'SCENE_WORKING_SET',
    vramRole:'RENDER_WORKING_SET',
    cacheable:true,
    capability:'dige.render.low_sample',
    metadata:{guideDistM:Number(d),samples:samplesSearch},
  }));
  return compileLogicalResourcePlan({
    taskId:'DIGE-C34-ADAPTIVE-RESOURCE-COMPILED-RENDER',
    resourceVector,
    logicalNamespace:ONE_T_LOGICAL_NAMESPACE,
    taskLogicalUnits:String(guideDistances.length),
    optimization:{
      denseCandidateCount:denseSearchCount,
      materializedCandidateCount:guideDistances.length,
      scope:'C33_7POINT_TO_C34_COARSE3',
    },
    stages:[
      {
        id:'prep-runtime',role:'PREP',cpu:'REQUIRED',gpu:'NONE',
        ramRole:'ASSET_GEOMETRY_CACHE',storageRole:'DURABLE_CACHE',cacheable:true,reusableState:true,
        capability:'dige.runtime.prepare'
      },
      ...scatter,
      {
        id:'visual-gate',role:'REDUCE',deps:scatter.map(x=>x.id),cpu:'REQUIRED',gpu:'NONE',
        ramRole:'IMAGE_METRICS',cacheable:true,capability:'dige.visual.evaluate'
      },
      {
        id:'final-render',role:'FINALIZE',deps:['visual-gate'],cpu:'REQUIRED',gpu:'PREFERRED',cpuFallback:true,
        ramRole:'SCENE_WORKING_SET',vramRole:'FINAL_RENDER_WORKING_SET',cacheable:false,
        capability:'dige.render.high_sample',metadata:{samples:samplesFinal}
      },
      {
        id:'canon-result',role:'CANON',deps:['final-render'],cpu:'OPTIONAL',gpu:'NONE',
        storageRole:'DRIVE_CANON',cacheable:true,reusableState:true,capability:'result.verify+canon'
      },
    ],
    metadata:{
      renderer:'Blender Cycles',
      searchMode:'COARSE3_THEN_REFINE_IF_REQUIRED',
      failureScar:'C33_EVALUATOR_DEP_MISSING_NUMPY; C33_TOPOLOGY_CENTRAL_ROOT_LEAK_ZERO',
      guideDistances,
    },
  });
}
