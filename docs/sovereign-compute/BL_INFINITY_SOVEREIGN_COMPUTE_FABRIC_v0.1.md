# BL Infinity Sovereign Compute Fabric (BLI-SCF) v0.1

Status: PROPOSAL / NON-CANONICAL
Date: 2026-09-07

## 1. Mission

Build a sovereign, federated AI/compute platform for governments, enterprises, research institutions and public-interest operators that maximizes useful decisions per unit of energy, cost, time and risk rather than maximizing raw FLOPs.

Primary objective:

`maximize Useful_Decision_Value / (Joules + Cost + Latency + Externality + Risk)`

Hard invariants take precedence over any scalar score:

1. lawful authority and consent;
2. safety / catastrophic-risk veto;
3. data sovereignty and privacy;
4. provenance and evidence preservation;
5. bounded resource headroom;
6. rollback and fail-closed behavior;
7. no hidden political control or technical backdoor.

## 2. Core design principle: intelligence scales, compute does not have to

The platform MUST NOT route every task directly to the largest available model. Every workload is assigned a `ComputeEnvelope` and starts from the cheapest adequate mechanism.

### Compute ladder

- **T0 — Reuse / deterministic:** exact cache, semantic cache, prior verified artifact, database query, deterministic algorithm, symbolic solver.
- **T1 — Edge / tiny model:** on-device or low-power specialist model for classification, extraction, routing, translation, filtering and routine inference.
- **T2 — Small specialist model:** task-specific model, adapter, RAG pipeline, classical ML or small/medium LLM.
- **T3 — Multi-model verification:** independent specialist workers or heterogeneous models only where disagreement or assurance justifies the cost.
- **T4 — Frontier reasoning:** large reasoning model only when uncertainty, novelty, safety consequence or expected value crosses an escalation threshold.
- **T5 — HPC / simulation / training:** explicit approved jobs with fixed power, time, cost and data envelopes; never an implicit escalation path.

Escalation is evidence-triggered, not prestige-triggered.

## 3. ComputeEnvelope

Every job must carry:

```yaml
compute_envelope:
  task_id: string
  purpose: string
  authority: string
  data_residency: [jurisdiction-or-site]
  max_energy_joules: number
  max_cost: number
  max_accelerator_seconds: number
  max_tokens: number
  deadline_ms: number
  minimum_quality: number
  assurance_level: low|medium|high|critical
  catastrophic_risk_class: 0|1|2|3|4
  fallback: string
  stop_rule: string
```

A request exceeding its envelope must be rejected, degraded, queued for cheaper energy, or escalated for explicit authorization.

## 4. Stop infinite scaling

A run stops when any of these conditions holds:

- required quality is reached;
- independent verification converges;
- no materially new evidence is appearing;
- marginal quality gain per joule falls below threshold;
- marginal quality gain per unit cost falls below threshold;
- additional computation does not change the recommended action;
- energy/headroom budget becomes unsafe;
- safety risk increases faster than expected benefit;
- deadline makes further reasoning operationally worthless.

No worker may self-increase its own compute budget.

## 5. Energy-efficiency stack

### Software first

Prefer, when quality permits:

- retrieval instead of re-deriving knowledge from weights;
- exact/prefix/semantic/KV caching;
- batching and continuous batching;
- quantization and lower precision;
- speculative decoding;
- sparse / mixture-of-experts execution;
- adapter/fine-tuning over full retraining;
- distillation into smaller specialist models;
- structured outputs to reduce retries;
- deterministic tools for arithmetic, database operations and transforms;
- event-driven workers instead of always-on polling;
- deduplication of equivalent jobs across tenants;
- checkpoint/model reuse instead of repeated training.

### Hardware-aware routing

Benchmark real **wall energy per completed quality-qualified task**, not nominal TDP. Route among CPU/GPU/NPU/accelerators based on measured efficiency, memory pressure, latency and residency.

Use MLPerf-style power methodology where practical. Vendor marketing numbers are never sufficient for procurement or routing policy.

### Grid-aware execution

Non-urgent work may shift in time or site only when:

- residency and contract permit it;
- grid reliability is not reduced;
- SLA is preserved;
- the shift demonstrably reduces marginal energy/carbon/water burden.

Critical public-service work always overrides opportunistic optimization.

## 6. Platform topology

### Sovereign Node

A country or enterprise can run its own node containing:

- identity / access and policy engine;
- data plane under local control;
- model registry;
- compute scheduler;
- evidence/provenance ledger;
- energy and cost meter;
- safety gate;
- audit API;
- local RAG/indexing;
- connectors to approved internal systems.

### Federation

Nodes exchange only compact, purpose-limited packets through BLI-HCP-style interfaces:

- claims/results rather than raw private reasoning;
- provenance and confidence;
- request/response scope;
- data classification;
- compute cost/energy metadata;
- explicit permissions and expiry.

No federation member receives automatic access to another member's datasets, credentials, model weights or private reasoning.

## 7. Six planes

1. **Sovereign Data Plane** — locality, encryption, retention, access policy.
2. **Compute Plane** — heterogeneous hardware and workload execution.
3. **Intelligence Plane** — models, tools, retrieval and simulation.
4. **Verification Plane** — independent checks, provenance and reality veto.
5. **Energy Plane** — joules, power caps, cooling/water, grid-aware scheduling.
6. **Governance Plane** — legal authority, safety, procurement, audit and incident response.

## 8. Product modes

- **Enterprise Appliance:** single-tenant sovereign deployment.
- **National Compute Fabric:** federated government/research/industry deployment with national control.
- **Regional Federation:** cross-border interoperability without centralizing sensitive data.
- **Compute-as-a-Service:** metered access with hard tenant isolation and data residency.
- **Research Commons:** controlled shared compute for science, climate, health, agriculture and disaster mitigation.

## 9. Minimum metrics

Every deployment reports:

- joules per quality-qualified task;
- cost per quality-qualified task;
- latency percentile;
- cache/reuse hit rate;
- percentage handled by T0/T1/T2 vs T4/T5;
- escalation rate and reason;
- failed/retried token or accelerator work;
- power-cap violations;
- data-residency violations (target: zero);
- safety-gate blocks and false positives;
- provenance completeness;
- recovery time and rollback success.

North-star metric:

`UDV/J = verified useful decision value per joule`

Raw tokens, GPU-hours and FLOPs are accounting inputs, never success metrics.

## 10. Procurement rule

Any accelerator/cloud/model vendor must be compared on the same representative task set under measured:

- end-to-end quality;
- end-to-end wall energy;
- throughput;
- latency;
- total cost;
- memory footprint;
- data-egress and sovereignty constraints;
- recoverability and lock-in.

The system should be able to replace a worker or hardware backend without changing canonical state semantics.

## 11. Readiness roadmap

### Phase A — Governor first

Implement ComputeEnvelope, routing ladder, stop rules, metering and audit on existing infrastructure before buying more hardware.

### Phase B — Benchmark matrix

Measure representative workloads across current cloud/local backends and publish a private efficiency matrix.

### Phase C — Sovereign node reference implementation

Package storage, model gateway, scheduler, audit ledger, energy meter and safety gate as a reproducible deployment.

### Phase D — Pilot

Start with non-sensitive enterprise/public-interest workloads: document intelligence, supply-chain planning, energy optimization, disaster simulation and research support.

### Phase E — Federation

Enable cross-node BLI-HCP exchange while keeping data and authority local.

## 12. Non-goals

This platform is not:

- a centralized global command system;
- a mechanism to bypass national sovereignty;
- a mass-surveillance system;
- a weapons-development platform;
- a justification for unlimited hardware acquisition;
- an excuse to hide compute, financing or political control from legitimate oversight.
