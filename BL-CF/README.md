# BL Compute Federation (BL-CF)

BL-CF is an open-protocol, policy-governed federation for useful computing. It coordinates lawfully contributed compute without claiming ownership of contributor hardware, accounts, data, energy, networks, or capacity that has not been explicitly granted.

## One-sentence rule

> A machine remains its owner's machine; BL-CF may schedule only the bounded compute rights that owner actually grants, and only for admitted work whose expected useful value justifies its cost and risk.

## Founding stewardship

The official BL-CF federation separates contributor sovereignty, open-source rights, commercial participation, and canonical project stewardship.

- The Founding Steward is the final interpreter of the official Constitution and canonical federation identity, subject to mandatory law and executed contracts.
- Contributors retain their hardware, accounts, data, ungranted capacity, and independently created IP unless an explicit agreement says otherwise.
- Official BL-CF marks, canonical namespace, release/signing identity, first-party IP, and private coordination/security technology remain with the Founding Steward or designated legal owner to the extent legally owned.
- DEUS defaults to M2: policy-bounded admission-aware allocation and routing. Scheduling does not transfer ownership.
- High community consensus creates a duty to review, explain, and negotiate; canonical constitutional change still requires a signed Founder ratification.

See [CONSTITUTION.md](./CONSTITUTION.md).

## Economics: two different percentages

### 10% Official Protocol Commercial Share

For eligible commercial work transacted through the official federation, the default official protocol/steward participation is **10% of Eligible Commercial Settlement Value (ECSV)** under the applicable Settlement Schedule.

This compensates the official protocol, intelligent coordination, security architecture, trust registry, validation/settlement framework, and continuing protocol development. It is **not** an ownership claim over provider hardware and is **not automatically 10% equity** in an Operator.

### 5–10% Common-Benefit Compute Envelope

This is a scheduling rule, not revenue and not property ownership.

- target: **5%** of eligible capacity that a provider explicitly opted into common-benefit scheduling, measured over a rolling 30-day accounting window;
- default ceiling: **10%**;
- providers may opt out or set a lower cap;
- 0–5% may be allocated automatically by DEUS M2 to admitted useful work;
- 5–10% requires spare capacity, qualified benefit backlog, no material service harm, and provider permission;
- above 10% requires a separate explicit emergency/mission grant.

Private work may qualify only through a **Verified Shared-Benefit Contract** that returns independently auditable common value. Paying the normal 10% protocol share alone does not make a private job common-benefit work.

See [ECONOMICS-AND-COMMON-BENEFIT.md](./ECONOMICS-AND-COMMON-BENEFIT.md).

## Useful workloads

Initial classes:

- `S` — federation security, integrity, recovery and essential maintenance;
- `H0` — humanitarian / critical public benefit;
- `H1` — open science and reproducible research;
- `H2` — high-value benchmarks and evaluation research;
- `H3` — public knowledge/infrastructure;
- `H4` — legitimate commercial compute on commercially opted-in nodes;
- `PGB` — private work with a Verified Shared-Benefit Contract.

The official federation rejects spam, fake engagement, hidden cryptomining, credential attacks, unauthorized scanning, malware, denial-of-service activity, unlawful surveillance, and other resource abuse.

## Architecture

Stable abstraction:

`Identity -> Contract/Grant -> Capability -> Admission -> Job -> Lease -> Execution -> Result -> Validation -> Meter -> Settlement -> Audit`

Execution pools:

- **PUBLIC COMMONS** for public/non-sensitive work;
- **TRUSTED FEDERATION** for authenticated enterprise/lab/BYOC/cloud workloads;
- **SOVEREIGN / COMPUTE-TO-DATA** for sensitive data that should remain at the data owner/required region;
- **FOUNDER FIRST-PARTY** for resources directly owned/contracted by the Founding Steward, accounted separately from common-benefit capacity.

See [ARCHITECTURE-V1.md](./ARCHITECTURE-V1.md) and [PROTOCOL-V1.md](./PROTOCOL-V1.md).

## Security model

BL-CF uses a zero-trust direction:

- outbound-pull nodes rather than a default inbound remote shell;
- least-privilege human/node/workload identities;
- immutable artifact digests;
- network default deny for workloads unless explicitly needed;
- provider-side rechecking of grants and caps;
- data classification and compute-to-data for SEALED workloads;
- independent validation before materially rewarded settlement;
- separation of source hosting, production infrastructure, domains/marks, and canonical signing/recovery authority;
- signed releases, mirrors, append-only receipts, and emergency freeze/recovery.

See [SECURITY-THREAT-MODEL.md](./SECURITY-THREAT-MODEL.md).

## Digital contracts

Official participation is designed around versioned, hash-addressed agreements and auditable acceptance receipts:

- Node Contribution Agreement;
- Workload Submitter Agreement;
- Research Admission Record;
- Commercial Compute Addendum;
- Verified Shared-Benefit Contract;
- Data Processing Addendum;
- Settlement Schedule;
- DEUS Mandate Schedule.

See [DIGITAL-CONTRACT-STACK.md](./DIGITAL-CONTRACT-STACK.md).

## Open-source and IP boundary

The repository currently contains `LICENSE-CODE`, which applies the **MIT License** to its stated existing code scope. BL-CF does not silently convert already released MIT-covered code to AGPL.

A future network-facing component may use AGPL-3.0-only if a rightsholder/contributor audit confirms BL-CF has the rights required for that clearly defined scope. Service Acceptable Use Policy remains separate from software-license permissions.

Open-source code rights do not automatically transfer trademarks, canonical registry identity, signing authority, private datasets, or private routing/security know-how.

See [LEGAL-AND-LICENSING.md](./LEGAL-AND-LICENSING.md).

## Registration and provenance

There is no universal government registry that turns a repository into 'open source'. Open-source status derives from the actual license grant. BL-CF separately plans/uses, as applicable:

- copyright evidence/registration for major first-party snapshots;
- trademark clearance/registration for official identity;
- patent-vs-trade-secret review before unnecessary disclosure;
- signed release hashes;
- independent source mirrors and long-term archives;
- contributor/rightsholder records;
- electronic-contract receipts.

See [REGISTRATION-ROADMAP-VN.md](./REGISTRATION-ROADMAP-VN.md) and [LEGAL-SOURCES-2026.md](./LEGAL-SOURCES-2026.md).

## Communication and adoption

Public promise:

> **Your machine stays yours. You grant only bounded compute you explicitly authorize. Useful work only. No hidden mining. No spam. No coin required. Commercial protocol share and common-benefit allocation are disclosed and auditable.**

See [COMMUNICATION-AND-ADOPTION.md](./COMMUNICATION-AND-ADOPTION.md).

## Implementation status

The repository already contains a functioning federation runtime with provider grants, routing, queue/leases, budgets, ledgers, durable-storage lanes and tests. The current implementation branch adds value-policy admission, provider commercial/common-benefit opt-ins, task schemas, server-derived queue priorities, the 10% commercial settlement helper, and the 5–10% common-benefit policy model.

**Not yet truthfully claimable as complete:** durable rolling-30-day multi-resource enforcement, production node sandbox/attestation, live payment market, government IP filings, trademark registration, external penetration test, and public volunteer production launch. These remain staged gates in [IMPLEMENTATION-ROADMAP-V1.md](./IMPLEMENTATION-ROADMAP-V1.md).
