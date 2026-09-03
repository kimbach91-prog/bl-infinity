import test from "node:test";
import assert from "node:assert/strict";
import { ProviderRegistry, planRoute } from "../lib/fabric.mjs";

const base = {
  kind: "worker",
  status: "active",
  capabilities: ["embed"],
  regions: ["asia-southeast1"],
  dataLocations: ["shared"],
  dataPolicy: { privateDataAllowed: false },
  authorization: { mode: "contract", consentRef: "contract/test", expiresAt: null },
  limits: { maxConcurrency: 2, maxCostPerTaskUsd: 0.2 },
  telemetry: { inFlight: 0, trust: 0.9, availability: 0.99, p95LatencyMs: 50, costPerUnitUsd: 0.001 }
};

test("routes to best eligible authorized provider", () => {
  const r = new ProviderRegistry([
    { ...base, id: "fast", telemetry: { ...base.telemetry, p95LatencyMs: 20 } },
    { ...base, id: "slow", telemetry: { ...base.telemetry, p95LatencyMs: 900 } }
  ]);
  const out = planRoute(r, { id: "t1", capability: "embed", dataClass: "public", dataLocation: "shared" });
  assert.equal(out.selected[0].providerId, "fast");
  assert.equal(out.policy.noUnauthorizedCompute, true);
});

test("private task cannot leave a provider without private-data permission", () => {
  const r = new ProviderRegistry([{ ...base, id: "public-only" }]);
  const out = planRoute(r, { id: "t2", capability: "embed", dataClass: "private" });
  assert.equal(out.selected.length, 0);
});

test("provider at concurrency limit is rejected", () => {
  const r = new ProviderRegistry([{ ...base, id: "busy", telemetry: { ...base.telemetry, inFlight: 2 } }]);
  const out = planRoute(r, { id: "t3", capability: "embed", dataClass: "public" });
  assert.equal(out.selected.length, 0);
});
