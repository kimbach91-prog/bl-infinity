import { sha256Json } from './canonical.mjs';

export const LOGICAL_RESOURCE_COMPILER_VERSION='deus-logical-resource-compiler/1.1';
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


function normalizeSolvedStageEvidence(value, stageId){
  if(!value || typeof value!=='object' || Array.isArray(value)) throw new Error(`solvedStages.${stageId} must be an object`);
  if(value.fingerprintMatched!==true) throw new Error(`solvedStages.${stageId} requires fingerprintMatched=true`);
  const evidenceRef=String(value.evidenceRef??'').trim();
  if(!evidenceRef) throw new Error(`solvedStages.${stageId}.evidenceRef required`);
  const reuseKind=String(value.reuseKind??'RESULT').toUpperCase();
  if(!['RESULT','ARTIFACT','METRIC','RECEIPT'].includes(reuseKind)) throw new Error(`invalid reuseKind for ${stageId}`);
  return Object.freeze({
    fingerprintMatched:true,
    evidenceRef,
    resultDigest:value.resultDigest==null?null:String(value.resultDigest),
    artifactDigest:value.artifactDigest==null?null:String(value.artifactDigest),
    reuseKind,
    note:value.note==null?null:String(value.note),
  });
}

export function recompileWithSolvedStageReuse(plan,{
  solvedStages={},
  reuseScope='EXACT_PLAN_INPUT_ENVIRONMENT_RESULT_CONTRACT',
  metadata={},
}={}){
  if(!plan || typeof plan!=='object' || !Array.isArray(plan.stages) || !plan.planDigest) throw new Error('compiled plan with planDigest required');
  if(!solvedStages || typeof solvedStages!=='object' || Array.isArray(solvedStages)) throw new Error('solvedStages must be an object map');

  const stageIds=new Set(plan.stages.map(s=>s.id));
  for(const id of Object.keys(solvedStages)) if(!stageIds.has(id)) throw new Error(`unknown solved stage ${id}`);

  const normalizedEvidence=new Map(
    Object.entries(solvedStages).map(([id,value])=>[id,normalizeSolvedStageEvidence(value,id)])
  );

  const stages=plan.stages.map(stage=>{
    const evidence=normalizedEvidence.get(stage.id);
    if(!evidence) return clone(stage);
    if(stage.cacheable!==true && stage.reusableState!==true) {
      throw new Error(`stage ${stage.id} is not declared reusable/cacheable`);
    }
    const execution=evidence.reuseKind==='ARTIFACT'?'REUSE_VERIFIED_ARTIFACT':'REUSE_VERIFIED_RESULT';
    return {
      ...clone(stage),
      placement:{
        ...clone(stage.placement),
        state:'REUSED',
        execution,
        memoryMaterialization:'REUSED_VERIFIED_STATE',
        gpuPromotionGate:null,
      },
      reuse:{
        ...evidence,
        reuseScope:String(reuseScope),
        originalPlanDigest:plan.planDigest,
      },
    };
  });

  const summary={
    stages:stages.length,
    reused:stages.filter(x=>x.placement.state==='REUSED').length,
    ready:stages.filter(x=>x.placement.state==='READY').length,
    hold:stages.filter(x=>x.placement.state==='HOLD').length,
    cpu:stages.filter(x=>x.placement.execution==='CPU').length,
    cpuFallback:stages.filter(x=>x.placement.execution==='CPU_FALLBACK').length,
    gpu:stages.filter(x=>x.placement.execution==='GPU').length,
    logicalOnly:stages.filter(x=>x.placement.execution==='LOGICAL_ONLY').length,
    physicalStagesRemaining:stages.filter(x=>!String(x.placement.execution).startsWith('REUSE_') && x.placement.state!=='HOLD' && x.placement.execution!=='LOGICAL_ONLY').length,
  };

  const payload={
    schema:'deus-logical-resource-recompile/1.0',
    compilerVersion:LOGICAL_RESOURCE_COMPILER_VERSION,
    originalPlanDigest:plan.planDigest,
    taskId:plan.taskId,
    dataClass:plan.dataClass,
    logicalNamespace:plan.logicalNamespace,
    taskLogicalUnits:plan.taskLogicalUnits,
    resourceVector:clone(plan.resourceVector),
    stages,
    optimization:clone(plan.optimization),
    summary,
    reuseScope:String(reuseScope),
    metadata:{...clone(plan.metadata??{}),...clone(metadata??{})},
    truthBoundary:'REUSE_REQUIRES_EXACT_FINGERPRINT_MATCH_AND_EVIDENCE_REF__REUSED_LOGICAL_STAGE_NE_NEW_PHYSICAL_EXECUTION__PHYSICAL_CREDIT_REMAINS_RECEIPT_GATED',
  };
  return Object.freeze({...payload,planDigest:sha256Json(payload)});
}

export function compileDigeC34RecoveryPlan(resourceVector,{
  originalPlan=null,
  selectedCandidateId='candidate-02',
  selectionEvidenceRef,
  prepArtifactRef,
  candidateEvidenceRefs={},
  visualGateEvidenceRef,
}={}){
  const base=originalPlan??compileDigeC34Plan(resourceVector);
  const candidateIds=['candidate-01','candidate-02','candidate-03'];
  const solved={
    'prep-runtime':{
      fingerprintMatched:true,
      evidenceRef:String(prepArtifactRef||''),
      reuseKind:'ARTIFACT',
      note:'Reuse verified shared runtime instead of rebuilding immutable assets/geometry.'
    },
    ...Object.fromEntries(candidateIds.map(id=>[id,{
      fingerprintMatched:true,
      evidenceRef:String(candidateEvidenceRefs[id]||''),
      reuseKind:'METRIC',
      note:'Reuse executed low-sample render/evaluator result; candidate image is not required by final render.'
    }])),
    'visual-gate':{
      fingerprintMatched:true,
      evidenceRef:String(visualGateEvidenceRef||selectionEvidenceRef||''),
      reuseKind:'RESULT',
      note:`Reuse visual selection ${selectedCandidateId}; no coarse rerender.`
    },
  };
  for(const [id,e] of Object.entries(solved)) if(!e.evidenceRef) throw new Error(`recovery evidence missing for ${id}`);
  return recompileWithSolvedStageReuse(base,{
    solvedStages:solved,
    metadata:{
      recoveryMode:'FINAL_ONLY_AFTER_VERIFIED_COARSE_REUSE',
      selectedCandidateId,
      selectionEvidenceRef:String(selectionEvidenceRef||''),
    },
  });
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
