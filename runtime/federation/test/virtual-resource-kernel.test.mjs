import test from 'node:test';
import assert from 'node:assert/strict';
import {
  aggregateVirtualResourceVector,
  buildVirtualCpuFabric,
  DeusVirtualResourceKernel,
  dominantResourceShare,
  planUnifiedResourcePlacement,
} from '../lib/virtual-resource-kernel.mjs';

function currentReceiptBoundFixture() {
  return [
    {
      id: 'GHA_STRESS8',
      platform: 'GitHub Actions',
      resourceClass: 'CPU',
      vcpuEquivalent: 28,
      hostRamGiB: 112,
      simultaneousGroup: 'GHA_STRESS8_EXACT_RUN',
      exactReceipt: 'RCP-20260920-PUBLIC-GITHUB-ACTIONS-STRESS8-EXEC-018',
      dataClassMax: 'BL-S0',
    },
    {
      id: 'HIGGSFIELD_CPU8',
      platform: 'Higgsfield',
      resourceClass: 'CPU',
      vcpuEquivalent: 8,
      hostRamGiB: null,
      dataClassMax: 'BL-S0',
    },
    { id: 'RAILWAY_CONTROLLER', platform: 'Railway', resourceClass: 'CPU', vcpuEquivalent: 2, hostRamGiB: 1, dataClassMax: 'BL-S1' },
    { id: 'RAILWAY_NATIVE', platform: 'Railway', resourceClass: 'CPU', vcpuEquivalent: 2, hostRamGiB: 1, dataClassMax: 'BL-S1' },
    { id: 'RAILWAY_A2', platform: 'Railway', resourceClass: 'CPU', vcpuEquivalent: 2, hostRamGiB: 1, dataClassMax: 'BL-S1' },
    { id: 'RAILWAY_B2', platform: 'Railway', resourceClass: 'CPU', vcpuEquivalent: 4, hostRamGiB: 2, dataClassMax: 'BL-S1' },
    { id: 'VERCEL_PROFILE', platform: 'Vercel', resourceClass: 'CPU', vcpuEquivalent: 2, hostRamGiB: 8, dataClassMax: 'BL-S0' },
    { id: 'AIHORDE', platform: 'AI Horde', resourceClass: 'LLM', opaqueInference: true, dataClassMax: 'BL-S0' },
    { id: 'BLOCKRUN', platform: 'BlockRun', resourceClass: 'LLM', opaqueInference: true, dataClassMax: 'BL-S0' },
  ];
}

test('current receipt-bound virtual CPU/RAM snapshot stays a vector, not fake GPU equivalence', () => {
  const vector = aggregateVirtualResourceVector(currentReceiptBoundFixture());
  assert.equal(vector.vcpuEquivalent, 48);
  assert.equal(vector.provenSimultaneousVcpuLowerBound, 28);
  assert.equal(vector.hostRamGiBPortfolio, 125);
  assert.equal(vector.verifiedGpuCount, 0);
  assert.equal(vector.verifiedVramGiB, 0);
  assert.equal(vector.opaqueInferenceSlots, 2);
});

test('virtual CPU fabric separates addressable portfolio from proven simultaneous lower bound', () => {
  const cpu = buildVirtualCpuFabric(currentReceiptBoundFixture());
  assert.equal(cpu.addressableVcpuEquivalent, 48);
  assert.equal(cpu.provenSimultaneousVcpuLowerBound, 28);
});

test('duplicate aliases of one physical GPU root are deduplicated for GPU/VRAM credit', () => {
  const vector = aggregateVirtualResourceVector([
    {
      id: 'gpu-lane-a',
      hardwareRootId: 'gpu-root-1',
      resourceClass: 'GPU',
      gpuVerified: true,
      gpuCount: 1,
      physicalVramGiB: 24,
    },
    {
      id: 'gpu-lane-b',
      hardwareRootId: 'gpu-root-1',
      resourceClass: 'GPU',
      gpuVerified: true,
      gpuCount: 1,
      physicalVramGiB: 24,
    },
  ]);
  assert.equal(vector.verifiedGpuCount, 1);
  assert.equal(vector.verifiedVramGiB, 24);
});

test('opaque inference never creates physical GPU or VRAM credit', () => {
  const vector = aggregateVirtualResourceVector([
    { id: 'opaque-1', resourceClass: 'LLM', opaqueInference: true },
  ]);
  assert.equal(vector.verifiedGpuCount, 0);
  assert.equal(vector.verifiedVramGiB, 0);
  assert.equal(vector.opaqueInferenceSlots, 1);
});

test('GPU-required job fails closed until a verified GPU root exists', () => {
  const plan = planUnifiedResourcePlacement(
    { gpuCount: 1, vramGiB: 8, dataClass: 'BL-S0' },
    currentReceiptBoundFixture(),
  );
  assert.equal(plan.state, 'HOLD_REAL_GPU_REQUIRED');
});

test('single-node CPU/RAM job selects an admitted node that fits', () => {
  const kernel = new DeusVirtualResourceKernel(currentReceiptBoundFixture());
  const plan = kernel.plan({ vcpuEquivalent: 2, hostRamGiB: 1, dataClass: 'BL-S0' });
  assert.equal(plan.state, 'PLACED_SINGLE_NODE');
});

test('dominant-resource share remains multidimensional', () => {
  const dominant = dominantResourceShare(
    { vcpuEquivalent: 4, hostRamGiB: 8, gpuCount: 0, vramGiB: 0 },
    { vcpuEquivalent: 8, hostRamGiB: 10, gpuCount: 0, vramGiB: 0 },
  );
  assert.equal(dominant.resource, 'hostRamGiB');
  assert.equal(dominant.share, 0.8);
});
