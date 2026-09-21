import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compileLogicalResourcePlan,
  compileDigeC34Plan,
  ONE_T_LOGICAL_NAMESPACE,
} from '../lib/logical-resource-compiler.mjs';

const current={
  vcpuEquivalent:48,
  provenSimultaneousVcpuLowerBound:28,
  hostRamGiBPortfolio:125,
  verifiedGpuCount:0,
  verifiedVramGiB:0,
  opaqueInferenceSlots:2,
  functionalRoots:1,
};

test('DIGE C34 compiles logical roles into CPU fallback when GPU/VRAM are not admitted',()=>{
  const p=compileDigeC34Plan(current);
  assert.equal(p.logicalNamespace,ONE_T_LOGICAL_NAMESPACE);
  assert.equal(p.summary.stages,7);
  assert.equal(p.summary.gpu,0);
  assert.equal(p.summary.cpuFallback,4);
  assert.equal(p.summary.hold,0);
  assert.equal(p.stages.find(x=>x.id==='prep-runtime').placement.execution,'CPU');
  assert.equal(p.stages.find(x=>x.id==='final-render').placement.execution,'CPU_FALLBACK');
  assert.equal(p.stages.find(x=>x.id==='final-render').placement.gpuPromotionGate,'FRESH_GPU_VRAM_RECEIPT_REQUIRED');
  assert.ok(p.stages.find(x=>x.id==='final-render').placement.virtualRoles.includes('vGPU'));
  assert.ok(p.stages.find(x=>x.id==='final-render').placement.virtualRoles.includes('vVRAM'));
});

test('DIGE C34 planned search reduces seven-point brute force to coarse three-point bracket',()=>{
  const p=compileDigeC34Plan(current);
  assert.equal(p.optimization.denseCandidateCount,7);
  assert.equal(p.optimization.materializedCandidateCount,3);
  assert.equal(p.optimization.avoidedCandidates,4);
  assert.ok(Math.abs(p.optimization.avoidedFraction-(4/7))<1e-12);
  assert.ok(Math.abs(p.optimization.avoidedFactor-(7/3))<1e-12);
});

test('same logical DIGE plan promotes render stages to GPU only after verified GPU/VRAM exists',()=>{
  const p=compileDigeC34Plan({...current,verifiedGpuCount:1,verifiedVramGiB:24});
  assert.equal(p.summary.gpu,4);
  assert.equal(p.summary.cpuFallback,0);
  assert.equal(p.stages.find(x=>x.id==='final-render').placement.execution,'GPU');
  assert.equal(p.stages.find(x=>x.id==='final-render').placement.memoryMaterialization,'PHYSICAL_VRAM');
});

test('GPU-required logical role fails closed with current GPU0 state',()=>{
  const p=compileLogicalResourcePlan({
    taskId:'gpu-required',
    resourceVector:current,
    stages:[{id:'x',cpu:'NONE',gpu:'REQUIRED',vramRole:'MODEL'}],
  });
  assert.equal(p.summary.hold,1);
  assert.equal(p.stages[0].placement.execution,'HOLD_GPU_REQUIRED');
});

test('1T namespace is not multiplied into physical resource credit',()=>{
  const p=compileDigeC34Plan(current);
  assert.equal(p.resourceVector.vcpuEquivalent,48);
  assert.equal(p.resourceVector.hostRamGiBPortfolio,125);
  assert.equal(p.resourceVector.verifiedGpuCount,0);
  assert.equal(p.resourceVector.verifiedVramGiB,0);
  assert.equal(p.taskLogicalUnits,'3');
});
