function nonNegative(value, name, { allowUnknown = false } = {}) {
  if (value === null || value === undefined || value === '' || value === 'UNKNOWN') {
    if (allowUnknown) return null;
    return 0;
  }
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${name} must be a non-negative number`);
  return number;
}

function asBoolean(value) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') return value.toLowerCase() === 'true';
  return Boolean(value);
}

function normalizeDataClass(value = 'BL-S0') {
  const normalized = String(value || 'BL-S0').trim().toUpperCase();
  const rank = new Map([
    ['BL-S0', 0],
    ['BL-S1', 1],
    ['BL-S1_CONTROL', 1],
    ['BL-S2', 2],
    ['BL-S2_REF_ONLY', 2],
    ['BL-S3', 3],
    ['BL-S3_REF_ONLY', 3],
    ['BL-S4', 4],
    ['BL-S4_REF_ONLY', 4],
  ]);
  return { value: normalized, rank: rank.get(normalized) ?? 0 };
}

function dataClassAdmits(nodeMax, requested) {
  return normalizeDataClass(nodeMax).rank >= normalizeDataClass(requested).rank;
}

export function normalizeVirtualResourceNode(node = {}) {
  const id = String(node.id ?? node.nodeId ?? '').trim();
  if (!id) throw new Error('node.id is required');

  const resourceClass = String(node.resourceClass ?? 'CPU').trim().toUpperCase();
  const hardwareRootId = String(node.hardwareRootId ?? id).trim();
  const runtimeRootId = String(node.runtimeRootId ?? id).trim();

  return Object.freeze({
    id,
    platform: String(node.platform ?? 'UNKNOWN'),
    resourceClass,
    hardwareRootId,
    runtimeRootId,
    state: String(node.state ?? 'UNKNOWN'),
    dataClassMax: String(node.dataClassMax ?? 'BL-S0'),

    vcpuEquivalent: nonNegative(node.vcpuEquivalent, 'vcpuEquivalent'),
    hostRamGiB: nonNegative(node.hostRamGiB, 'hostRamGiB', { allowUnknown: true }),

    gpuVerified: asBoolean(node.gpuVerified),
    gpuCount: nonNegative(node.gpuCount, 'gpuCount'),
    physicalVramGiB: nonNegative(node.physicalVramGiB, 'physicalVramGiB'),

    opaqueInference: asBoolean(node.opaqueInference),
    functionalRoot: asBoolean(node.functionalRoot),

    addressableNow: node.addressableNow === undefined ? true : asBoolean(node.addressableNow),
    simultaneousGroup: node.simultaneousGroup ? String(node.simultaneousGroup) : null,
    exactReceipt: node.exactReceipt ? String(node.exactReceipt) : null,
  });
}

export function buildVirtualCpuFabric(nodes = []) {
  const normalized = nodes.map(normalizeVirtualResourceNode);
  const cpuNodes = normalized.filter((node) => node.vcpuEquivalent > 0);

  const addressableVcpuEquivalent = cpuNodes
    .filter((node) => node.addressableNow)
    .reduce((sum, node) => sum + node.vcpuEquivalent, 0);

  const bySimultaneousGroup = new Map();
  for (const node of cpuNodes) {
    if (!node.simultaneousGroup) continue;
    const current = bySimultaneousGroup.get(node.simultaneousGroup) ?? 0;
    bySimultaneousGroup.set(node.simultaneousGroup, current + node.vcpuEquivalent);
  }

  const provenSimultaneousVcpuLowerBound = bySimultaneousGroup.size
    ? Math.max(...bySimultaneousGroup.values())
    : 0;

  return {
    schema: 'deus-virtual-cpu-fabric/1',
    nodeCount: cpuNodes.length,
    addressableVcpuEquivalent,
    provenSimultaneousVcpuLowerBound,
    note: 'Addressable vCPU-equivalent is a routing portfolio, not a claim of one SMP machine or permanent simultaneous allocation.',
  };
}

export function aggregateVirtualResourceVector(nodes = []) {
  const normalized = nodes.map(normalizeVirtualResourceNode);

  const cpu = buildVirtualCpuFabric(normalized);

  const addressableHostRamGiB = normalized
    .filter((node) => node.addressableNow && node.hostRamGiB !== null)
    .reduce((sum, node) => sum + node.hostRamGiB, 0);

  const strictGpuRoots = new Map();
  for (const node of normalized) {
    if (!node.gpuVerified || node.gpuCount <= 0 || node.physicalVramGiB <= 0) continue;
    const existing = strictGpuRoots.get(node.hardwareRootId);
    if (!existing) {
      strictGpuRoots.set(node.hardwareRootId, node);
      continue;
    }
    // Keep the strongest observed envelope for the same hardware root; never sum aliases/lanes.
    const currentScore = existing.gpuCount + existing.physicalVramGiB;
    const nextScore = node.gpuCount + node.physicalVramGiB;
    if (nextScore > currentScore) strictGpuRoots.set(node.hardwareRootId, node);
  }

  const verifiedGpuCount = [...strictGpuRoots.values()].reduce((sum, node) => sum + node.gpuCount, 0);
  const verifiedVramGiB = [...strictGpuRoots.values()].reduce((sum, node) => sum + node.physicalVramGiB, 0);

  const opaqueInferenceSlots = normalized.filter((node) => node.opaqueInference && node.addressableNow).length;
  const functionalRoots = normalized.filter((node) => node.functionalRoot && node.addressableNow).length;

  return {
    schema: 'deus-virtual-resource-vector/1',
    vcpuEquivalent: cpu.addressableVcpuEquivalent,
    provenSimultaneousVcpuLowerBound: cpu.provenSimultaneousVcpuLowerBound,
    hostRamGiBPortfolio: addressableHostRamGiB,
    verifiedGpuCount,
    verifiedVramGiB,
    opaqueInferenceSlots,
    functionalRoots,
    truthBoundary: 'CPU/RAM portfolio, GPU/VRAM hardware, and opaque functional compute remain separate dimensions. No scalar FLOPS equivalence is implied.',
  };
}

export function dominantResourceShare(request = {}, capacity = {}) {
  const dimensions = [
    ['vcpuEquivalent', request.vcpuEquivalent, capacity.vcpuEquivalent],
    ['hostRamGiB', request.hostRamGiB, capacity.hostRamGiB],
    ['gpuCount', request.gpuCount, capacity.gpuCount],
    ['vramGiB', request.vramGiB, capacity.vramGiB],
  ];

  let dominant = { resource: null, share: 0 };
  for (const [resource, requested, available] of dimensions) {
    const req = nonNegative(requested, `request.${resource}`);
    const cap = nonNegative(available, `capacity.${resource}`);
    if (req === 0) continue;
    if (cap <= 0) return { resource, share: Infinity };
    const share = req / cap;
    if (share > dominant.share) dominant = { resource, share };
  }
  return dominant;
}

export function planUnifiedResourcePlacement(job = {}, nodes = []) {
  const normalized = nodes.map(normalizeVirtualResourceNode);
  const requested = {
    vcpuEquivalent: nonNegative(job.vcpuEquivalent, 'job.vcpuEquivalent'),
    hostRamGiB: nonNegative(job.hostRamGiB, 'job.hostRamGiB'),
    gpuCount: nonNegative(job.gpuCount, 'job.gpuCount'),
    vramGiB: nonNegative(job.vramGiB, 'job.vramGiB'),
    dataClass: String(job.dataClass ?? 'BL-S0'),
  };

  const requiresGpu = requested.gpuCount > 0 || requested.vramGiB > 0;

  const candidates = normalized.filter((node) => {
    if (!node.addressableNow) return false;
    if (!dataClassAdmits(node.dataClassMax, requested.dataClass)) return false;
    if (requiresGpu && !node.gpuVerified) return false;
    if (requiresGpu && node.gpuCount < requested.gpuCount) return false;
    if (requiresGpu && node.physicalVramGiB < requested.vramGiB) return false;
    if (requested.vcpuEquivalent > 0 && node.vcpuEquivalent < requested.vcpuEquivalent) return false;
    if (requested.hostRamGiB > 0 && (node.hostRamGiB === null || node.hostRamGiB < requested.hostRamGiB)) return false;
    return true;
  });

  if (candidates.length > 0) {
    candidates.sort((a, b) => {
      const aWaste = (a.vcpuEquivalent - requested.vcpuEquivalent)
        + ((a.hostRamGiB ?? 0) - requested.hostRamGiB)
        + (a.gpuCount - requested.gpuCount)
        + (a.physicalVramGiB - requested.vramGiB);
      const bWaste = (b.vcpuEquivalent - requested.vcpuEquivalent)
        + ((b.hostRamGiB ?? 0) - requested.hostRamGiB)
        + (b.gpuCount - requested.gpuCount)
        + (b.physicalVramGiB - requested.vramGiB);
      return aWaste - bWaste;
    });

    return {
      state: 'PLACED_SINGLE_NODE',
      nodeId: candidates[0].id,
      hardwareRootId: candidates[0].hardwareRootId,
      requested,
    };
  }

  const vector = aggregateVirtualResourceVector(normalized);
  if (requiresGpu && vector.verifiedGpuCount === 0) {
    return {
      state: 'HOLD_REAL_GPU_REQUIRED',
      requested,
      vector,
      reason: 'No verified GPU/VRAM root is currently admitted.',
    };
  }

  return {
    state: 'NEEDS_MULTI_NODE_PLAN_OR_OFFLOAD',
    requested,
    vector,
    reason: 'No single admitted node satisfies the full resource envelope. Tensor/pipeline/offload planning must remain separately gated by network and framework evidence.',
  };
}

export class DeusVirtualResourceKernel {
  constructor(nodes = []) {
    this.nodes = new Map();
    for (const node of nodes) this.upsertNode(node);
  }

  upsertNode(node) {
    const normalized = normalizeVirtualResourceNode(node);
    this.nodes.set(normalized.id, normalized);
    return normalized;
  }

  removeNode(nodeId) {
    return this.nodes.delete(String(nodeId));
  }

  snapshot() {
    const nodes = [...this.nodes.values()];
    return {
      schema: 'deus-virtual-resource-kernel/1',
      vector: aggregateVirtualResourceVector(nodes),
      cpuFabric: buildVirtualCpuFabric(nodes),
      nodeCount: nodes.length,
      nodes,
    };
  }

  plan(job = {}) {
    return planUnifiedResourcePlacement(job, [...this.nodes.values()]);
  }
}
