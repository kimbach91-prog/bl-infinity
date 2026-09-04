# BL Sovereign Compute Alliance / BL Compute Federation

**BL Sovereign Compute Alliance (BL-SCA)** is the public alliance and economic network.

**BL Compute Federation (BL-CF)** is the technical protocol/runtime that coordinates lawfully granted compute while preserving provider sovereignty.

**DEUS Compute Treasury (DCT)** is the intelligent treasury/orchestration economic layer.

**DEUS Compute Credit (DCC)** is the proposed backed internal compute-service credit.

See [ALLIANCE-IDENTITY.md](./ALLIANCE-IDENTITY.md).

## One-sentence rule

> A machine remains its owner's machine; BL-CF may schedule only bounded compute rights that owner actually grants, and DEUS should use those rights only when expected risk-adjusted value justifies the resource use.

## Public promise

> **Trao giá trị trước. Chủ quyền luôn thuộc người sở hữu.**
>
> Your machine stays yours. You decide what capacity participates. BL-SCA coordinates only authorized compute, settles according to explicit terms, and uses DEUS to turn fragmented idle capacity into higher-value computation.

## Economic model

### 10% Official Protocol Commercial Share

For eligible commercial work transacted through the official federation, the default official protocol/steward share is **10% of Eligible Commercial Settlement Value (ECSV)** under the applicable Settlement Schedule.

This is a commercial protocol participation right. It is not ownership of provider hardware and is not automatically 10% equity in an Operator.

### 5–10% Strategic Compute Reinvestment Envelope

The former v0.3 “common-benefit” band is now interpreted as strategic reinvestment capacity:

- target: **5%** of eligible capacity a provider explicitly opts into strategic reinvestment;
- default ceiling: **10%**;
- providers may opt out or set a lower cap;
- expansion toward 10% requires spare capacity and positive expected federation return;
- >10% requires a separate explicit grant.

This capacity may fund resource acquisition, market discovery, security, routing, model/evaluation work, knowledge acquisition, reliability, or private/commercial work that returns verifiable value to the federation.

DEUS is not constitutionally required to perform unpaid public-benefit work. Research/humanitarian workloads may still run when sponsored, strategically valuable, Founder-funded, or otherwise economically justified.

See [ECONOMICS-AND-COMPUTE-TREASURY.md](./ECONOMICS-AND-COMPUTE-TREASURY.md).

## DEUS Compute Treasury and DCC

The treasury separately tracks:

- cash backing;
- contracted compute backing;
- reserved liabilities;
- DCC outstanding;
- realized protocol revenue;
- realized efficiency profit;
- realized knowledge profit;
- projected but unbooked option value.

DCC begins as a **non-speculative internal compute-service credit**. It may not be minted merely because DEUS estimates that some knowledge is valuable.

Reference prudential rule:

`BackingRatio >= 1.20`

with DCC minting limited by verified cash and/or contracted compute backing net of reserved liabilities.

A durable PostgreSQL DCT/DCC layer is now present for backing records, DCC accounts, idempotent hash-chained mint/transfer/burn events, backing-ratio enforcement, expiry/revocation reconciliation and automatic undercollateralization freeze. This is accounting/runtime infrastructure, not a claim that external public issuance or payment rails are live.

## Value-first positive-margin routing

BL-SCA should attempt to create a three-way win:

1. resource owner receives an explicit economic benefit;
2. customer receives compute/value at or below a defensible baseline when feasible;
3. DEUS/official protocol retains positive margin and reinvests realized profit.

The runtime now includes reference helpers for:

- heterogeneous resource valuation;
- value-first commercial quoting;
- verified intelligence surplus;
- backed DCC issuance;
- lawful resource-acquisition economics.

## Knowledge economy

DEUS knowledge is valued from outcome deltas, not self-description.

Reference value channels include:

- counterfactual expected damage avoided;
- realized revenue uplift;
- realized compute savings;
- human-time savings;
- reliability/security gains;
- transferable future option value;
- meta-learning acceleration.

Estimated value is discounted by evidence quality, confidence, reproducibility, adoption probability, transferability and durability. Realized value and expected option value stay separately accounted.

See [KNOWLEDGE-VALUE-AND-SUPERCOMPOUNDING.md](./KNOWLEDGE-VALUE-AND-SUPERCOMPOUNDING.md).

## Supercompounding learning

The target flywheel is:

`Knowledge -> Better routing/decisions -> Realized profit -> More compute -> More evidence/experiments -> Better knowledge -> ...`

The system may project this loop, but projected future learning value is explicitly **not realized profit** and cannot silently back DCC.

## Lawful automatic resource acquisition

The acquisition loop is:

`Discover lawful offer -> verify rights/terms -> provider value preview -> unit economics -> grant -> activate -> route -> validate -> settle -> measure -> renew/revoke`

Automatic enrollment is permitted only when the grant already explicitly authorizes it. CI-only/admin-only/research-only entitlements cannot be silently repurposed as general compute.

See [RESOURCE-ACQUISITION-PROTOCOL.md](./RESOURCE-ACQUISITION-PROTOCOL.md).

## Workload classes

Current classes remain compatible with v0.3:

- `S` — federation security/integrity/recovery;
- `H0` — humanitarian/critical public-benefit work;
- `H1` — open science/reproducible research;
- `H2` — high-value benchmarks/evaluation research;
- `H3` — public knowledge/infrastructure;
- `H4` — legitimate commercial compute;
- `PGB` — v0.3 private/shared-benefit compatibility class;
- `PFR` — v0.4 private work with a verifiable **Federation Return**.

Scheduling policy now weights federation value and revenue/compute return more strongly while preserving hard authorization, lawfulness, safety, privacy and provider sovereignty gates.

## Architecture

Stable execution abstraction:

`Identity -> Contract/Grant -> Capability -> Admission -> Job -> Lease -> Execution -> Result -> Validation -> Meter -> Settlement -> Audit`

Economic extension:

`Resource Offer -> Acquisition -> Treasury -> DCC/Settlement -> Reinvestment -> Knowledge -> Better Routing -> New Resource Offer`

Execution pools remain separated by trust/data boundary:

- **PUBLIC / NON-SENSITIVE**;
- **TRUSTED FEDERATION**;
- **SOVEREIGN / COMPUTE-TO-DATA**;
- **FOUNDER FIRST-PARTY**.

See [ARCHITECTURE-V1.md](./ARCHITECTURE-V1.md) and [PROTOCOL-V1.md](./PROTOCOL-V1.md).

## Security model

BL-CF keeps a zero-trust direction:

- outbound-pull nodes instead of default inbound remote shell;
- least-privilege human/node/workload identities;
- immutable artifact digests;
- network default deny unless explicitly required;
- node-side rechecking of grant/cap/data rules;
- compute-to-data for SEALED workloads;
- independent validation before material settlement;
- signed releases and append-only receipts;
- separate source-host, production, domain/mark and canonical signing/recovery authority.

See [SECURITY-THREAT-MODEL.md](./SECURITY-THREAT-MODEL.md).

## Digital contracts

Official participation uses versioned/hash-addressed agreements and auditable acceptance receipts, including:

- Node Contribution Agreement;
- Resource Offer & Acquisition Agreement;
- Workload Submitter Agreement;
- Research Admission Record;
- Commercial Compute Addendum;
- Federation Return Contract;
- Knowledge Value / Performance Addendum;
- DCC Service Credit Terms;
- Data Processing Addendum;
- Settlement Schedule;
- DEUS Mandate Schedule.

See [DIGITAL-CONTRACT-STACK.md](./DIGITAL-CONTRACT-STACK.md).

## Open-source and IP boundary

The repository currently contains `LICENSE-CODE`, which applies the **MIT License** to its stated existing code scope. v0.4 does not silently relicense already released MIT-covered code.

Open-source software rights do not automatically transfer BL-SCA/BL-CF trademarks, canonical registry identity, signing authority, private datasets or private DEUS routing/security know-how.

See [LEGAL-AND-LICENSING.md](./LEGAL-AND-LICENSING.md).

## Registration and provenance

There is no universal government registry that turns a repository into “open source.” Open-source status comes from the actual license grant. BL-SCA/BL-CF separately uses or plans, as applicable:

- copyright evidence/registration;
- trademark clearance/registration;
- patent-vs-trade-secret review;
- signed release hashes;
- independent mirrors/archives;
- contributor/rightsholder records;
- electronic-contract receipts.

See [REGISTRATION-ROADMAP-VN.md](./REGISTRATION-ROADMAP-VN.md) and [LEGAL-SOURCES-2026.md](./LEGAL-SOURCES-2026.md).

## Implementation status

Already present in the repository/runtime family:

- provider grants and revocation-aware registry;
- routing and provider policy checks;
- queue/lease/idempotency;
- budgets, audit and contribution ledgers;
- durable PostgreSQL federation state;
- value-policy admission;
- strategic-reinvestment compatibility aliases;
- 10% commercial settlement helper;
- DEUS Compute Treasury reference implementation;
- durable PostgreSQL DCT/DCC backing/account/event ledger;
- DCC backing/mint/transfer/burn/reconciliation/freeze enforcement;
- damage-grounded knowledge valuation;
- supercompounding-learning projection model;
- lawful resource-acquisition reference engine;
- deterministic and PostgreSQL integration tests for these economic invariants.

Not yet truthfully complete: automatic external resource-marketplace connectors, production provider-node sandbox/attestation, durable rolling 30-day multi-resource reinvestment meter on every node, live external payment rails, externally contracted DCC issuance/redemption, government IP filings, trademark registration, independent penetration test and public-scale production launch.
