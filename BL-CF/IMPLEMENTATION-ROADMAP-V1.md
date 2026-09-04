# BL-CF — Implementation Roadmap v1

Status: EXECUTION PLAN

The roadmap deliberately separates what can be implemented immediately from what requires legal, security, infrastructure or external-partner evidence.

## Stage A — Constitutional and policy baseline

Deliverables:

- Founding Constitution v0.3;
- Economics/Common-Benefit policy;
- Security Threat Model;
- Federation Protocol v1;
- End-to-End Architecture;
- Digital Contract Stack;
- registration/IP roadmap;
- Communication/Adoption doctrine.

Gate: no percentage, ownership or workload-policy ambiguity remains in the public bootstrap docs.

## Stage B — Runtime value/admission enforcement

Implement in `runtime/federation`:

- task value-policy schema;
- common-benefit admission class;
- private/shared-benefit contract reference;
- provider common-benefit/commercial opt-ins;
- 5% target / 10% default ceiling policy object;
- 10% commercial settlement calculation helper;
- queue priority derived from admitted value policy;
- backward compatibility for existing legacy test tasks;
- unit tests.

Gate: deterministic tests prove commercial jobs cannot silently use common-benefit capacity and private jobs require a qualifying benefit contract.

## Stage C — Resource-class accounting

Implement durable ledgers for:

- CPU-seconds;
- GPU-seconds by accelerator class;
- memory GiB-seconds;
- material network/storage;
- common-benefit usage per provider/resource class;
- rolling 30-day target/ceiling;
- provider-specific lower caps.

Gate: control plane and node can independently determine whether a common-benefit lease would exceed allowed share.

## Stage D — Node agent hardening

Build/reference node client with:

- outbound-only enrollment/pull;
- signed identity and short-lived credential support;
- local enforcement of provider limits;
- immutable artifact digest verification;
- network default deny;
- sandbox adapters;
- local revoke/pause control;
- human-readable current-job view;
- metering/result receipts.

Gate: compromise of the central scheduler cannot make an honest node exceed its locally signed grant.

## Stage E — Supply-chain security

Add:

- signed build artifacts;
- SBOM;
- provenance attestations;
- dependency scanning;
- immutable image publishing;
- secure update/release metadata;
- release-key separation and offline recovery procedure.

Gate: production node accepts only artifacts meeting the configured trust policy.

## Stage F — Digital agreement service

Implement:

- versioned NCA, WSA, RAR, CCA, DPA, Shared-Benefit Contract, Settlement Schedule and DEUS Mandate registry;
- agreement hashes;
- affirmative acceptance receipts;
- revoke/expiry state;
- provider sovereignty API;
- appropriate stronger e-sign flow for material contracts.

Gate: every production lease can be traced to an active resource grant and workload agreement.

## Stage G — Validation and anti-fraud

Implement:

- replicated quorum for deterministic tasks;
- hidden/gold-test validator;
- stochastic validation interface;
- reputation with decay;
- result replay/double-settlement prevention;
- payout hold/canary limits for new providers;
- Shared-Benefit delivery verification.

Gate: rewarded compute is validated, not self-reported.

## Stage H — Founder/trusted pilot

Nodes:

- Founder local machines;
- explicit BYOC cloud resources;
- trusted partner test nodes.

Workloads:

- SHA/hash/deterministic tasks;
- useful benchmark slices;
- build/research workloads with public data.

Gate: demonstrate full Grant -> Job -> Lease -> Result -> Validate -> Meter -> Receipt -> Revoke lifecycle.

## Stage I — Public research pilot

Find one credible research/academic workload with clear methodology and expected value.

Publish:

- admission record;
- compute consumed;
- validation method;
- result/limitations;
- common-benefit accounting;
- impact report.

Gate: one externally understandable useful outcome, not a synthetic demo only.

## Stage J — IP/open-source formalization

Before broad public distribution:

- complete contributor/rightsholder audit;
- decide which currently MIT-covered code remains MIT;
- do not retroactively relicense third-party code without rights;
- define separate future AGPL-covered scope if desired;
- add SPDX/license metadata;
- copyright-deposit major Founder-owned software snapshot;
- trademark clearance/filing;
- patent-vs-trade-secret review before further disclosure.

Gate: public claims match actual legal status.

## Stage K — Commercial pilot

Use paid nodes/workloads with explicit opt-in.

Implement:

- ECSV settlement object;
- default 10% protocol share;
- provider payout calculation;
- invoice/tax integration appropriate to Operator jurisdiction;
- dispute/reconciliation flow;
- no common-benefit subsidy unless separately admitted.

Gate: first commercial settlement reconciles exactly from signed meter and validation receipts.

## Stage L — Public volunteer beta

Requirements:

- simple installer;
- clear limits/revocation;
- only public/non-sensitive workload classes by default;
- common-benefit default opt-in choice is explicit rather than hidden;
- no commercial work unless separately opted in;
- public impact dashboard;
- public SECURITY policy.

Gate: no contributor needs to trust a hidden background process to understand resource use.

## Stage M — Multi-operator federation

Add:

- regional operator identity;
- cross-operator trust and settlement;
- portable provider grants;
- compute-to-data sovereign nodes;
- independent mirror and disaster recovery;
- Operator replacement runbook.

Gate: loss of one Operator/cloud account does not erase canonical federation or contributor rights.

## Stage N — Independent assurance

Before strong security/enterprise claims:

- independent penetration test;
- contract/legal review;
- privacy/security impact review;
- supply-chain audit;
- disaster-recovery exercise;
- economic/fraud simulation;
- public post-test remediation summary.

## Metrics that matter

Track:

- verified useful compute / eligible compute;
- completion/validation success;
- cost per verified result;
- latency and deadline reliability;
- common-benefit share actual vs 5–10% policy;
- provider retention and revocation rate;
- commercial provider payout;
- protocol share and reinvestment;
- verified shared-benefit delivery rate;
- security incident and recovery metrics;
- research/public outcomes;
- amount of compute added through lawful grants.

Do not optimize node count, raw CPU-hours, or utilization in isolation.
