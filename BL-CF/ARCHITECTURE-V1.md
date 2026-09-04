# BL-CF — End-to-End Federation Architecture v1

Status: IMPLEMENTATION BLUEPRINT

## 1. Architectural objective

BL-CF is not a central supercomputer and not a remote-control mesh. It is a federation of independently owned resources that expose bounded capabilities under revocable grants.

The design optimizes four things simultaneously:

1. useful human/research/economic value;
2. contributor sovereignty;
3. security and verifiability;
4. efficiency of genuinely idle or otherwise authorized compute.

## 2. Logical planes

### 2.1 Constitutional / Trust Plane

Public or independently verifiable:

- Constitution and policy versions;
- official protocol schemas;
- canonical release manifests;
- official registry roots;
- signed policy hashes;
- public audit/impact receipts.

Private where necessary:

- root recovery material;
- anti-abuse thresholds;
- proprietary routing/evaluation heuristics;
- private datasets and secrets.

Git is a publication plane, not the sole root of trust.

### 2.2 Identity & Contract Plane

Responsibilities:

- human/operator authentication;
- node/workload identity;
- Node Contribution Agreements;
- Workload Submitter Agreements;
- Shared-Benefit Contracts;
- commercial settlement consent;
- agreement hashes and revocation state.

### 2.3 Admission Plane

Every job passes:

`identity -> rights -> purpose -> data -> safety -> resource -> value -> verification -> settlement`

Reject before scheduling when any mandatory gate fails.

### 2.4 DEUS Intelligence / Allocation Plane

DEUS receives admissible jobs and produces a plan using:

- utility score;
- capability fit;
- trust/reputation;
- locality/data sovereignty;
- latency;
- cost;
- availability;
- energy/thermal signals where available;
- fairness debt;
- common-benefit budget state;
- provider-specific policy.

A recommendation is not authority by itself. The plan is constrained by signed grants and contracts.

### 2.5 Execution Plane

Pools:

- PUBLIC COMMONS — public/non-sensitive jobs on volunteer/commodity nodes;
- TRUSTED FEDERATION — authenticated commercial, lab, enterprise, BYOC and cloud nodes;
- SOVEREIGN / COMPUTE-TO-DATA — sensitive data stays at the data owner's node/region;
- FOUNDER FIRST-PARTY — resources directly owned/contracted by the Founding Steward; separate from common-benefit accounting.

### 2.6 Validation Plane

Validation methods depend on task type:

- deterministic: replicated result/quorum or cryptographic verification;
- stochastic: statistical validator and seeded reproducibility checks;
- AI benchmark: hidden test set, evaluator separation and anti-leak controls;
- simulation: independent sample/spot-check and artifact hashes;
- private shared-benefit: independent proof/attestation of the promised common return.

### 2.7 Metering & Settlement Plane

Produces append-only receipts for:

- resources granted;
- resources consumed;
- common-benefit accounting;
- validated result;
- provider credit/payment;
- Official Protocol Commercial Share;
- shared-benefit delivery.

## 3. Node model

The node agent should be intentionally narrow.

A node advertises a signed Capability Manifest:

- architecture/OS/runtime class;
- CPU/GPU/RAM/storage envelope;
- supported workload runtimes;
- max concurrency;
- commercial opt-in;
- common-benefit opt-in and cap;
- private/shared-benefit opt-in;
- network policy;
- data-locality policy;
- permitted hours/energy/thermal budget;
- grant expiry;
- identity and attestation references.

The node pulls work outbound. It does not expose a general shell.

## 4. Workload package

A job is never a naked command string.

Each job references an immutable workload artifact such as:

- OCI image digest; or
- WASM/WASI module digest; or
- another explicitly approved reproducible runtime artifact.

Job Manifest minimum fields:

- `jobId`, `tenantId`, `idempotencyKey`;
- `workloadClass`;
- `purposeCode` and human-readable purpose;
- `artifactDigest`;
- `dataClass` / locality;
- requested CPU/GPU/RAM/storage/network/time;
- egress allowlist;
- checkpoint/resume policy;
- result-validation policy;
- commercial settlement class;
- `commonBenefitRequested`;
- Shared-Benefit Contract reference where applicable;
- contract/policy hashes;
- expiry/deadline.

## 5. Scheduling state machine

Reference lifecycle:

`SUBMITTED -> ADMISSION_PENDING -> ADMITTED -> QUEUED -> OFFERED -> LEASED -> RUNNING -> CHECKPOINTED? -> RESULT_PENDING -> VALIDATING -> VERIFIED | FAILED | QUARANTINED | REVOKED`

Economic lifecycle is separate:

`UNMETERED -> METERED -> VALIDATED -> SETTLEMENT_PENDING -> SETTLED | DISPUTED`

Approval is not execution; execution is not verification; verification is not settlement.

## 6. Common-benefit controller

The controller measures actual eligible compute units over a rolling 30-day window by resource class rather than pretending one CPU-hour equals one GPU-hour.

Resource ledgers should maintain at least:

- CPU-seconds normalized by declared performance class;
- GPU-seconds by accelerator class;
- memory GiB-seconds;
- storage/network units when material;
- optional energy estimate.

Common-benefit consumption must be measured in the same resource class denominator from which it is allocated.

Default target = 5%, default ceiling = 10%, provider cap may be lower.

## 7. Multi-resource fairness

Avoid one scalar 'compute unit' for all scheduling decisions.

Use dominant-resource fairness or a similar multidimensional mechanism for scarce shared resources, then apply value priority and deadline constraints.

Example: a job using 70% of GPU but 2% CPU is GPU-dominant; another using 60% RAM but 5% GPU is memory-dominant. Fairness debt should follow the dominant scarce resource.

## 8. Data architecture

Data classes:

- PUBLIC;
- INTERNAL;
- PRIVATE;
- REGULATED;
- SEALED.

Default routing:

- PUBLIC may enter public/common nodes;
- INTERNAL only to trusted nodes with matching policy;
- PRIVATE to trusted/sovereign nodes;
- REGULATED to approved jurisdiction/compliance nodes only;
- SEALED does not leave the sovereign boundary; compute must go to data.

The router fails closed if a node cannot prove it satisfies the required data policy.

## 9. Failure and recovery

Every material job should declare:

- retry policy;
- idempotency semantics;
- checkpoint interval;
- maximum duplicated cost;
- alternate node strategy;
- validation quorum;
- rollback/cleanup behavior.

DEUS should prefer safe checkpoint preemption rather than maximizing utilization at the cost of corrupted work.

## 10. Federation growth model

New resources are acquired through explicit lawful grants:

- individual volunteer nodes;
- university/lab idle capacity;
- enterprise off-hours capacity;
- render farms and development workstations;
- BYOC/BYOGPU;
- cloud credits/grants;
- sponsor-funded capacity;
- regional partners;
- first-party owned infrastructure.

Every provider type uses the same core contract vocabulary but may have different technical adapters and settlement models.

## 11. Compatibility strategy

The public protocol should be implementable independently. Official participation requires conformance, signed policy acceptance, security minimums, and registry admission.

This preserves genuine openness while allowing the official federation to maintain a high-trust operational standard.

## 12. Evolution rule

Do not rebuild the federation around fashionable infrastructure. Keep stable abstractions:

`Identity -> Grant -> Capability -> Job -> Lease -> Result -> Validation -> Meter -> Settlement -> Audit`

Adapters may change from Cloud Run to another cloud, from containers to WASM, or from one queue/database to another without changing contributor sovereignty or constitutional semantics.
