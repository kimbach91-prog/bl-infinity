# Sovereign Compute Pilot Dossier Template v0.1

Status: PROPOSAL / NON-CANONICAL
Date: 2026-09-07

## Purpose

Reusable due-diligence and pilot package for a government, public institution, enterprise, university or infrastructure operator evaluating BL Infinity Sovereign Compute Fabric (BLI-SCF).

The pilot is designed so the recipient can remain operationally autonomous. It must not depend on undisclosed vendor credentials, hidden control channels or political conditions.

## 1. Counterparty profile

- Legal entity:
- Jurisdiction:
- Contracting authority:
- Beneficial owner / controlling public body:
- Procurement route:
- Data controller(s):
- Critical-infrastructure status:
- Export-control / sanctions screening required: YES/NO
- Primary technical owner:
- Security owner:
- Legal/privacy owner:
- Independent reviewer:

## 2. Problem definition

Document one narrow, measurable pilot problem before discussing hardware scale.

Examples:

- reduce energy used per document-intelligence task;
- improve grid dispatch or load forecasting;
- reduce logistics waste;
- improve disaster-response allocation;
- accelerate research retrieval and verification;
- reduce inference cost while meeting a fixed quality floor.

Required fields:

- baseline workflow;
- baseline quality metric;
- baseline wall energy / cost / latency;
- minimum acceptable quality;
- data classification;
- residency constraints;
- maximum allowed externality/risk;
- decision owner.

## 3. Pilot success metric

Primary metric:

`Verified Useful Decision Value / (Joules + Cost + Latency + Risk)`

Operational metrics:

- joules per quality-qualified task;
- cost per quality-qualified task;
- p50/p95/p99 latency;
- percentage served by T0/T1/T2 vs T4/T5;
- cache/reuse hit rate;
- accelerator-seconds per task;
- model/provider escalation rate and reason;
- provenance completeness;
- rollback success;
- data-residency violations (target zero);
- safety-gate violations (target zero).

No pilot is declared successful using token throughput, GPU utilization or FLOPs alone.

## 4. Sovereignty architecture

Recipient-controlled components:

- identity and access management;
- cryptographic keys;
- production credentials;
- data stores;
- audit retention;
- model/provider allowlist;
- compute budget policy;
- safety policy and local legal constraints;
- deployment approval.

Vendor/operator may provide:

- reproducible deployment artifacts;
- orchestration software;
- model adapters;
- optimization rules;
- benchmark harness;
- training and support;
- optional managed operations under explicit contract.

Prohibited architecture:

- undisclosed remote-admin account;
- hidden political kill switch;
- mandatory export of private reasoning/user data;
- vendor-only root keys;
- forced dependence on one external model provider.

## 5. Compute-envelope policy

Every high-cost job should declare a bounded envelope:

```yaml
computeEnvelope:
  purpose: <declared-purpose>
  authority: <legal-or-contractual-authority>
  dataResidency: [<allowed-sites-or-jurisdictions>]
  limits:
    energyJoules: <finite-budget-where-metered>
    costUsd: <finite-budget>
    acceleratorSeconds: <finite-budget>
    tokens: <finite-budget>
    wallTimeMs: <finite-budget>
  tierCeiling: T0|T1|T2|T3|T4
  assuranceLevel: low|medium|high|critical
  catastrophicRiskClass: 0|1|2|3|4
```

T5 HPC/training is a separate explicit authorization, not a hidden escalation path.

## 6. Measurement plan

Before optimizing, establish a repeatable task set and measurement protocol.

Required:

- representative input set;
- quality rubric and independent verifier where material;
- wall-energy measurement method;
- meter ownership and calibration/provenance;
- cost source;
- latency source;
- software/model versions;
- hardware identity;
- run count / variance reporting;
- failure and retry accounting.

Unknown energy is represented as UNKNOWN, never zero.

## 7. Data and security plan

- data inventory;
- data-class mapping;
- residency map;
- encryption at rest/in transit;
- key custody;
- retention/deletion rules;
- incident response;
- privileged-access review;
- supply-chain/SBOM controls;
- model and dependency provenance;
- backup and restore drill;
- offline/disconnected operating requirement if applicable.

## 8. Safety and end-use classification

Classify use under the Safe Technology Transfer & Resource Partnership Gate.

- Class A: preferred low-risk;
- Class B: controlled/regulated;
- Class C: high-risk dual use;
- Class D: prohibited.

A failed catastrophic-risk or sovereignty gate cannot be offset by economic benefit.

## 9. Commercial / resource consideration

Permissible consideration may include normal payment or lawful, independently valued resources such as:

- electricity / contracted generation capacity;
- renewable generation or storage;
- data-centre facilities/land under lawful contract;
- fibre/connectivity;
- compute capacity;
- hardware;
- research facilities;
- talent/training commitments;
- lawful mineral/material supply subject to environmental, labour and anti-corruption review.

For any resource component record:

- independent market valuation;
- quantity/quality measurement;
- delivery schedule;
- beneficial ownership;
- environmental/community impact;
- local benefit;
- audit rights;
- dispute resolution;
- force majeure;
- termination and revaluation mechanism.

Technology must never be exchanged for secret political concessions, territorial authority, election influence, unlawful surveillance access or military alignment.

## 10. Technology-transfer package

Select explicitly:

- binary/runtime license;
- source-code access;
- reproducible build package;
- source escrow;
- model weights where lawful/licensed;
- deployment automation;
- training/certification;
- local operator handbook;
- security hardening guide;
- incident-response handbook;
- migration/export path;
- end-of-contract continuity plan.

The recipient must know which components remain third-party dependencies.

## 11. Pilot stages

### Stage 0 — Baseline

Measure current quality, energy, cost and latency without BLI-SCF.

### Stage 1 — T0/T1/T2 optimization

Deploy reuse, deterministic tools, retrieval, edge/small specialists, batching, quantization and other low-cost mechanisms where quality permits.

### Stage 2 — Controlled escalation

Enable T3 verification and T4 frontier reasoning only on evidence-triggered cases.

### Stage 3 — Sovereign operations

Recipient operators perform restore, provider replacement, key rotation, budget-policy change and offline/degraded-mode drills.

### Stage 4 — Independent evaluation

Independent reviewer repeats the benchmark and checks sovereignty/safety controls.

### Stage 5 — Scale decision

Scale only if verified improvement survives realistic load and the marginal benefit of additional hardware remains positive.

## 12. Go / no-go gate

Proceed to production only if all are true:

- measurable useful-value improvement;
- energy/cost claims independently reproducible;
- no unresolved critical security finding;
- no unresolved catastrophic-use finding;
- recipient controls production credentials and keys;
- rollback/restore proven;
- legal/data-residency requirements met;
- commercial/resource exchange independently auditable;
- exit/migration path demonstrated.

Otherwise remain pilot-only or stop.
