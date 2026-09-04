# BL-SCA / BL-CF — Implementation Roadmap v0.4

Status: EXECUTION PLAN

This roadmap separates what is implemented as a reference/runtime invariant from what still requires durable infrastructure, real counterparties, security evidence, legal review or production deployment.

## Stage A — Canonical identity and economic baseline

Deliverables:

- BL Sovereign Compute Alliance (BL-SCA) public identity;
- BL Compute Federation (BL-CF) technical identity;
- DEUS Compute Treasury (DCT) model;
- DEUS Compute Credit (DCC) model;
- Founding Constitution v0.4;
- 10% Official Protocol Commercial Share;
- 5–10% Strategic Compute Reinvestment policy;
- lawful resource-acquisition doctrine;
- damage-grounded knowledge valuation;
- supercompounding-learning model;
- security/protocol/legal/communication docs.

Gate: public materials distinguish ownership, compute grants, protocol revenue, reinvestment capacity, DCC liabilities and projected knowledge value without ambiguity.

## Stage B — Runtime value and provider-policy enforcement

Implemented/reference targets in `runtime/federation`:

- value-policy hard gates;
- H4 commercial and PFR Federation Return classes;
- strategic-reinvestment target 5% / ceiling 10%;
- v0.3 common-benefit compatibility aliases;
- provider commercial/reinvestment/private-return opt-ins;
- provider-specific reinvestment cap;
- server-derived queue priority;
- 10% commercial settlement helper;
- deterministic unit tests.

Gate: tests prove a workload cannot use strategic-reinvestment capacity without provider permission and private/commercial reinvestment work requires a verifiable Federation Return where policy requires it.

## Stage C — DEUS Compute Treasury reference layer

Implemented/reference targets:

- cash backing;
- committed compute backing;
- reserved liabilities;
- DCC outstanding/liability;
- 1.20 minimum DCC backing-ratio policy;
- protocol revenue ledger categories;
- verified efficiency-profit category;
- verified knowledge-profit category;
- value-first quote helper;
- heterogeneous resource-value price vector.

Gate: unit tests reject DCC issuance that would breach backing and keep protocol, efficiency and knowledge revenue categories separate.

## Stage D — Durable treasury and DCC ledger

Implement production-grade persistent state for:

- backing assets by source, expiry and revocation state;
- DCC issuance/burn/redemption receipts;
- double-spend/replay protection;
- reserved liabilities;
- settlement holds/disputes;
- backing-ratio snapshots;
- reconciliation and accounting periods;
- emergency freeze;
- role/authority controls for M3 actions.

Gate: every DCC unit has a traceable issuance receipt and expired/revoked compute backing is removed before further issuance.

## Stage E — Durable resource-class accounting

Implement ledgers for:

- CPU core-seconds;
- normalized GPU-seconds plus accelerator identity/class;
- memory GiB-seconds;
- storage GiB-hours;
- egress/network units;
- request/transaction units where material;
- provider/resource-class strategic-reinvestment usage;
- rolling accounting windows;
- provider-specific lower caps.

Gate: control plane and node independently determine whether a proposed lease exceeds a provider's current grant or reinvestment cap.

## Stage F — Lawful resource-acquisition engine

Reference engine exists; production work must add:

- signed Resource Offer objects;
- source-use-class enforcement;
- ToS/contract entitlement metadata;
- value-first provider preview;
- bid/ask and unit-economics evaluation;
- explicit/pre-authorized enrollment state;
- compensation preference: cash/DCC/reciprocal/hybrid;
- offer expiry/revocation;
- provider renewal/retention signals;
- trusted marketplace/provider connectors.

Gate: `ci-only`, `interactive-admin-only`, `research-only` and other restricted entitlements cannot be promoted to `general-compute` by routing logic alone.

## Stage G — Founder first-party acquisition pilot

Use only a resource clearly controlled/authorized by the Founding Steward.

Prove:

1. capability/value profile;
2. offer object;
3. economic baseline/quote;
4. explicit grant;
5. provider registration;
6. one bounded workload;
7. result validation;
8. exact resource meter;
9. settlement receipt;
10. revoke test;
11. realized-margin report.

Gate: end-to-end lifecycle works without manual hidden state or ownership ambiguity.

## Stage H — Node agent hardening

Build/reference node client with:

- outbound-only enrollment/pull;
- signed node identity and short-lived credentials;
- local enforcement of provider limits;
- source-use-class enforcement;
- local reinvestment-cap accounting;
- immutable artifact digest verification;
- network default deny;
- sandbox adapters;
- local pause/revoke;
- human-readable current-job/settlement view;
- resource-meter/result receipts.

Gate: compromise of central scheduler cannot make an honest node exceed its signed grant.

## Stage I — Supply-chain and root-of-trust security

Add:

- signed build artifacts;
- SBOM;
- provenance attestations;
- dependency scanning;
- immutable images/WASM modules where appropriate;
- secure update metadata;
- release-key separation;
- offline/hardware-backed recovery keys;
- source mirror and independent archive;
- recovery/freeze drills.

Gate: production nodes accept only artifacts satisfying configured trust policy, and loss of one hosting account cannot redefine canonical BL-SCA/BL-CF.

## Stage J — Digital agreement service

Implement version/hash registry for:

- NCA;
- Resource Offer & Acquisition Agreement;
- WSA;
- RAR;
- CCA;
- Federation Return Contract;
- Knowledge Value / Performance Addendum;
- DCC Service Credit Terms;
- DPA;
- Settlement Schedule;
- DEUS Mandate.

Also implement:

- affirmative acceptance/e-sign receipts;
- grant expiry/revocation;
- provider sovereignty API;
- treasury transparency API;
- stronger signature flow for material agreements.

Gate: every production lease and every DCC/settlement action resolves to active, retrievable agreement versions and authority.

## Stage K — Validation and anti-fraud

Implement:

- deterministic replicated quorum where appropriate;
- hidden/gold-test validation;
- stochastic validation interface;
- provider reputation with decay;
- resource attestation where economically justified;
- meter anomaly detection;
- Sybil/collusion controls;
- result replay/double-settlement prevention;
- payout/DCC holds for new providers;
- reference-price oracle hardening;
- Federation Return delivery verification.

Gate: neither provider self-report nor DEUS self-assessment alone can create rewarded value or DCC backing.

## Stage L — Commercial value-first pilot

Use one customer/workload with a defensible baseline.

Prove:

- same or better output/SLA than baseline;
- customer receives measurable value/savings;
- provider is settled correctly;
- BL-CF retains configured positive margin;
- 10% protocol share calculation reconciles;
- any intelligence/performance fee is based on non-overlapping verified surplus.

Gate: first commercial settlement reconciles exactly from signed validation/meter receipts.

## Stage M — DCC closed-loop pilot

Run DCC only as a restricted service credit among Founder/trusted counterparties.

Prove:

- verified backing deposit/compute commitment;
- mint under 1.20 minimum backing ratio;
- DCC transfer/award under contract;
- redemption for eligible compute;
- burn/reduction of liability;
- expiry/revocation of backing updates solvency;
- no public speculative trading.

Gate: full issuance-to-redemption reconciliation has zero unexplained liability gap.

## Stage N — Knowledge-value pilot

Pick one DEUS optimization/knowledge artifact with measurable economic effect.

Record:

- baseline and counterfactual;
- causal mechanism;
- realized value channels;
- expected option-value channels;
- overlap adjustment;
- implementation/verification/maintenance cost;
- evidence multiplier;
- realized net value;
- fee calculation where contracted;
- falsifier/limitations.

Gate: an independent reviewer can reproduce the economic calculation without accepting DEUS's own value claim on faith.

## Stage O — Supercompounding-learning experiment

Measure whether one learning delta improves future productive capacity.

Track at least:

- reuse count;
- cost/result before vs after;
- future failure-rate change;
- future learning/evaluation cost change;
- compute profit reinvested;
- extra experiments enabled by reinvestment;
- additional verified value generated.

Gate: projected compounding curves are compared against realized cohort outcomes. Forecast error is published internally and used to recalibrate the model.

## Stage P — Trusted multi-provider pilot

Add explicit third-party providers only after Stages G–K pass.

Requirements:

- verified owner/authority;
- source-use class;
- revocation;
- settlement preference;
- no sensitive data on unsuitable nodes;
- value-first preview;
- realized provider retention/renewal data.

Gate: no participant needs to trust an opaque background process to know what is being used and paid.

## Stage Q — IP/open-source formalization

Before broad commercialization/public-scale onboarding:

- contributor/rightsholder audit;
- preserve existing MIT obligations;
- define any future AGPL-covered scope explicitly if desired;
- SPDX/license metadata;
- copyright registration/deposit for selected Founder-owned snapshots;
- trademark clearance/filing for BL-SCA, BL-CF, DEUS/DCC marks as appropriate;
- patent-vs-trade-secret review before unnecessary disclosure;
- Founder-IP -> Operator licensing terms.

Gate: public claims exactly match actual ownership/registration/license evidence.

## Stage R — Multi-operator / multi-region federation

Add:

- operator identity;
- cross-operator trust/settlement;
- portable provider grants;
- sovereign compute-to-data nodes;
- multi-region treasury reconciliation;
- independent mirrors/disaster recovery;
- Operator replacement runbook.

Gate: failure/capture of one Operator or cloud account does not erase canonical identity, provider rights or DCC liability records.

## Stage S — Independent assurance

Before strong enterprise/financial/security claims:

- independent penetration test;
- contract/legal review;
- privacy/security impact assessment;
- supply-chain audit;
- treasury/DCC solvency review;
- economic/fraud/Sybil simulation;
- disaster-recovery exercise;
- remediation evidence.

## Metrics that matter

Track separately:

- verified compute acquired and sold by resource class;
- gross margin / contribution margin;
- provider acquisition cost and retention;
- customer savings/value delivered;
- Official Protocol Commercial Share;
- verified intelligence surplus;
- realized knowledge profit;
- projected knowledge option value (never mixed with realized profit);
- DCC outstanding/backing ratio/redemption rate;
- Strategic Compute Reinvestment actual vs provider caps;
- Federation Return delivery rate;
- cost per validated result;
- latency/deadline reliability;
- fraud/validation failure/dispute rates;
- security incidents and recovery time;
- compute added through lawful grants;
- forecast error of supercompounding-learning estimates.

Do not optimize raw node count, utilization, projected knowledge value or DCC issuance in isolation.
