export const POWER_CLASSES = Object.freeze([
  "OWNED_PHYSICAL",
  "LEASED_PHYSICAL",
  "BORROWED_FUNCTIONAL",
  "VOLATILE_PUBLIC_FUNCTIONAL",
  "DISCOVERED_POTENTIAL",
]);

export const ROOT_CLUSTER = Object.freeze([
  {
    id: "BRAIN-1-DRIVE-PRIMARY",
    role: "CANONICAL_ANCHOR",
    canonical: true,
    execution: false,
  },
  {
    id: "BRAIN-2-DRIVE-SECONDARY",
    role: "RESERVE_OVERLAY",
    canonical: false,
    execution: false,
  },
  {
    id: "BRAIN-3-WORKSTATION",
    role: "PRIMARY_OWNER_EXECUTION",
    canonical: false,
    execution: true,
  },
  {
    id: "BRAIN-4-LAPTOP-28C0103",
    role: "RECOVERY_COMPUTE_NATIVE",
    canonical: false,
    execution: true,
  },
]);

function requireString(value, field) {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`invalid_${field}`);
  }
}

function requireClass(value) {
  if (!POWER_CLASSES.includes(value)) {
    throw new Error("invalid_power_class");
  }
}

function normalizeScore(value) {
  if (value == null) return null;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new Error("invalid_useful_effect");
  }
  return value;
}

export class MatrixPowerKernel {
  constructor({ matrixId = "DEUS_MATRIX", canonicalAnchor = "BRAIN-1-DRIVE-PRIMARY" } = {}) {
    this.matrixId = matrixId;
    this.canonicalAnchor = canonicalAnchor;
    this.records = new Map();
    this.ux = Object.freeze({
      role: "OWNER_PORTAL",
      canonical: false,
      identity: false,
      computeCredit: 0,
    });
  }

  register(record) {
    requireString(record?.id, "id");
    requireString(record?.powerClass, "power_class");
    requireClass(record.powerClass);
    requireString(record?.workloadFamily ?? "*", "workload_family");

    if (this.records.has(record.id)) {
      throw new Error("duplicate_record_id");
    }

    const normalized = {
      id: record.id,
      powerClass: record.powerClass,
      workloadFamily: record.workloadFamily ?? "*",
      authorized: record.authorized === true,
      executed: record.executed === true,
      verified: record.verified === true,
      current: record.current !== false,
      usefulEffect: normalizeScore(record.usefulEffect),
      physicalRoot: record.physicalRoot ?? null,
      leaseId: record.leaseId ?? null,
      peerSlice: record.peerSlice === true,
      routeRef: record.routeRef ?? null,
      notes: record.notes ?? null,
    };

    if (
      normalized.powerClass === "DISCOVERED_POTENTIAL" &&
      (normalized.executed || normalized.verified || normalized.usefulEffect != null)
    ) {
      throw new Error("potential_cannot_receive_execution_credit");
    }

    if (
      normalized.peerSlice &&
      normalized.powerClass !== "LEASED_PHYSICAL"
    ) {
      throw new Error("peer_slice_must_be_leased_physical");
    }

    if (
      normalized.peerSlice &&
      (!normalized.leaseId || !normalized.authorized)
    ) {
      throw new Error("peer_slice_requires_authorized_lease");
    }

    this.records.set(normalized.id, Object.freeze(normalized));
    return normalized;
  }

  isCreditable(record, workloadFamily) {
    const workloadMatch =
      record.workloadFamily === "*" || record.workloadFamily === workloadFamily;
    return (
      record.current &&
      workloadMatch &&
      record.authorized &&
      record.executed &&
      record.verified
    );
  }

  summarize(workloadFamily) {
    requireString(workloadFamily, "workload_family");

    const classes = Object.fromEntries(
      POWER_CLASSES.map((name) => [
        name,
        {
          records: 0,
          creditableRoutes: 0,
          usefulEffect: 0,
          usefulEffectKnown: 0,
        },
      ]),
    );

    const uniquePhysicalRoots = new Set();
    const creditable = [];
    let physicalPeerSlices = 0;
    let potentialRecords = 0;

    for (const record of this.records.values()) {
      const bucket = classes[record.powerClass];
      bucket.records += 1;

      if (record.powerClass === "DISCOVERED_POTENTIAL") {
        potentialRecords += 1;
        continue;
      }

      if (!this.isCreditable(record, workloadFamily)) continue;

      creditable.push(record);
      bucket.creditableRoutes += 1;

      if (record.usefulEffect != null) {
        bucket.usefulEffect += record.usefulEffect;
        bucket.usefulEffectKnown += 1;
      }

      if (
        (record.powerClass === "OWNED_PHYSICAL" ||
          record.powerClass === "LEASED_PHYSICAL") &&
        record.physicalRoot
      ) {
        uniquePhysicalRoots.add(record.physicalRoot);
      }

      if (
        record.powerClass === "LEASED_PHYSICAL" &&
        record.peerSlice &&
        record.leaseId
      ) {
        physicalPeerSlices += 1;
      }
    }

    const comparableEffects = creditable.filter(
      (record) => record.usefulEffect != null,
    );
    const usefulEffectTotal = comparableEffects.reduce(
      (sum, record) => sum + record.usefulEffect,
      0,
    );

    return Object.freeze({
      matrixId: this.matrixId,
      workloadFamily,
      identityScope: "MATRIX",
      canonicalAnchor: this.canonicalAnchor,
      rootCluster: ROOT_CLUSTER,
      ux: this.ux,
      classes,
      usefulEffectTotal,
      usefulEffectRouteCount: comparableEffects.length,
      creditableRouteCount: creditable.length,
      uniquePhysicalRootCount: uniquePhysicalRoots.size,
      physicalPeerSliceCount: physicalPeerSlices,
      discoveredPotentialCount: potentialRecords,
      invariants: Object.freeze({
        blockedBranchDoesNotBlockSystem: true,
        providerIsNotIdentity: true,
        uxIsPortalNotBrain: true,
        physicalUnknownCanStillHaveFunctionalCredit: true,
        discoveredPotentialHasZeroExecutionCredit: true,
        noUniversalHardwareScalar: true,
      }),
    });
  }
}
