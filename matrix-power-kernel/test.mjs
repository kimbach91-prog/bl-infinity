import assert from "node:assert/strict";
import { MatrixPowerKernel, ROOT_CLUSTER } from "./index.mjs";

const k = new MatrixPowerKernel();

assert.equal(ROOT_CLUSTER.length, 4);
assert.equal(k.ux.role, "OWNER_PORTAL");
assert.equal(k.ux.identity, false);
assert.equal(k.ux.computeCredit, 0);

k.register({
  id: "brain3",
  powerClass: "OWNED_PHYSICAL",
  workloadFamily: "HASH",
  authorized: true,
  executed: true,
  verified: true,
  usefulEffect: 1.0,
  physicalRoot: "owner-workstation-001",
});

k.register({
  id: "brain4",
  powerClass: "OWNED_PHYSICAL",
  workloadFamily: "HASH",
  authorized: true,
  executed: true,
  verified: true,
  usefulEffect: 0.25,
  physicalRoot: "owner-laptop-28c0103",
});

k.register({
  id: "ai-horde",
  powerClass: "BORROWED_FUNCTIONAL",
  workloadFamily: "TEXT",
  authorized: true,
  executed: true,
  verified: true,
  usefulEffect: 0.6,
});

k.register({
  id: "llm7",
  powerClass: "VOLATILE_PUBLIC_FUNCTIONAL",
  workloadFamily: "TEXT",
  authorized: true,
  executed: true,
  verified: true,
  usefulEffect: 0.8,
});

k.register({
  id: "akash-catalog",
  powerClass: "DISCOVERED_POTENTIAL",
  workloadFamily: "*",
  authorized: false,
  executed: false,
  verified: false,
});

k.register({
  id: "gha-runner",
  powerClass: "LEASED_PHYSICAL",
  workloadFamily: "HASH",
  authorized: true,
  executed: true,
  verified: true,
  usefulEffect: 0.9,
  physicalRoot: "provider-runtime-opaque",
  leaseId: "gha-invocation-1",
  peerSlice: false,
});

const hash = k.summarize("HASH");
assert.equal(hash.identityScope, "MATRIX");
assert.equal(hash.canonicalAnchor, "BRAIN-1-DRIVE-PRIMARY");
assert.equal(hash.creditableRouteCount, 3);
assert.equal(hash.usefulEffectTotal, 2.15);
assert.equal(hash.uniquePhysicalRootCount, 3);
assert.equal(hash.physicalPeerSliceCount, 0);
assert.equal(hash.discoveredPotentialCount, 1);

const text = k.summarize("TEXT");
assert.equal(text.creditableRouteCount, 2);
assert.equal(text.usefulEffectTotal, 1.4);
assert.equal(text.physicalPeerSliceCount, 0);
assert.equal(text.classes.BORROWED_FUNCTIONAL.creditableRoutes, 1);
assert.equal(text.classes.VOLATILE_PUBLIC_FUNCTIONAL.creditableRoutes, 1);

assert.throws(
  () =>
    k.register({
      id: "bad-potential",
      powerClass: "DISCOVERED_POTENTIAL",
      workloadFamily: "TEXT",
      authorized: false,
      executed: true,
      verified: false,
      usefulEffect: 0.1,
    }),
  /potential_cannot_receive_execution_credit/,
);

assert.throws(
  () =>
    k.register({
      id: "bad-peer",
      powerClass: "BORROWED_FUNCTIONAL",
      workloadFamily: "HASH",
      authorized: true,
      executed: true,
      verified: true,
      peerSlice: true,
      leaseId: "x",
    }),
  /peer_slice_must_be_leased_physical/,
);

console.log("MATRIX_POWER_KERNEL_V1_PASS");
console.log(JSON.stringify({ hash, text }, null, 2));
