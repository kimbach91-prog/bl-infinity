# BL Compute Federation — Founding Constitution v0.2

Status: DRAFT FOR FOUNDER RATIFICATION

This Constitution defines the official BL Compute Federation (BL-CF) as an open, policy-governed federation for useful computing. It is deliberately designed so that contributors retain sovereignty over their machines, accounts, data, and ungranted capacity, while the official federation retains a coherent canonical identity, trusted coordination layer, and anti-capture governance.

## 1. Founding roles

### 1.1 Founding Steward

The Founding Steward is the originator and initial technical, intellectual, and computational contributor of BL-CF. The Founding Steward is the final interpreter of the official BL-CF Constitution, official protocol identity, canonical releases, and official federation meaning, subject to mandatory law and executed contracts.

A binding Founder Interpretation may clarify ambiguous text for the official federation. It may not retroactively confiscate contributor property, rewrite an already accepted contract without the required amendment/consent process, or override mandatory law.

### 1.2 DEUS

DEUS is the federation's policy-bounded coordination and allocation system. DEUS may receive, classify, route, schedule, validate, meter, and account for compute according to this Constitution and ratified policies.

DEUS does not own contributor machines, cloud accounts, datasets, identities, or legal rights merely because it schedules them. DEUS has no unilateral power to rewrite the Constitution or grant itself new authority.

### 1.3 Node Provider

A Node Provider is a person or organization that has lawful authority to contribute bounded compute capacity. Contribution is a revocable grant of compute rights, not a transfer of ownership of the machine, account, network, data, or unconsumed capacity.

### 1.4 Workload Submitter

A Workload Submitter is a person or organization that submits a task under a declared purpose, data-rights basis, workload class, resource budget, and verification method.

## 2. Property and sovereignty boundary

### 2.1 Founder and first-party intellectual property

All pre-existing, separately developed, or non-contributed proprietary intellectual property of the Founding Steward remains the property of the Founding Steward or the legal IP owner designated by the Founding Steward. This may include, where applicable:

- BL-CF and DEUS marks and official brand identity;
- official registry identity, canonical namespace, release-signing identity, and official distribution channels;
- first-party source code and documentation to the extent copyright is owned by the Founding Steward or designated IP owner;
- private scoring, routing, anti-abuse, security, evaluation, and coordination techniques not released under an open-source license;
- first-party private datasets, evaluation corpora, provenance systems, and research artifacts;
- patentable inventions, trade secrets, and confidential know-how that have not been licensed or assigned away.

Publishing source code under an open-source license is a grant of license rights. It is not a transfer of the underlying copyright, trademark, canonical project identity, signing authority, or unrelated proprietary technology.

### 2.2 Contributor intellectual property

A contributor does not lose ownership of independently created intellectual property merely by participating in BL-CF. Contributions are governed by the applicable open-source license and contribution agreement. Any assignment of copyright or broader relicensing right must be explicit.

### 2.3 Compute sovereignty

Node Providers retain ownership and ultimate control of their hardware, accounts, data, energy budget, network connection, and all capacity not currently granted under a valid Compute Grant.

No federation membership grants BL-CF a general right to remote-control a device. Nodes should pull signed workloads or accept narrowly scoped jobs through documented interfaces. Arbitrary remote shell access is not a default federation capability.

## 3. The useful-compute law

A workload may consume federation compute only when all hard gates pass:

1. AUTHORIZED — the provider and submitter have the rights they claim;
2. LAWFUL — the workload and resource source are lawful and contractually permitted;
3. USEFUL — the expected human, scientific, research, educational, infrastructure, or legitimately commercial value is positive;
4. BOUNDED — CPU, GPU, memory, storage, network, duration, and data access are constrained;
5. REVOCABLE — the provider can stop or expire the grant;
6. VERIFIABLE — the result has an appropriate validation or reproducibility method;
7. NON-DECEPTIVE — the workload purpose is accurately declared.

The official federation must not be used for spam, fake engagement, bot-farm abuse, cryptomining disguised as research, credential attacks, unauthorized security scanning, malware, denial-of-service activity, unlawful surveillance, or other resource abuse.

Open-source copies may be technically capable of uses outside the official service policy. The official service Acceptable Use Policy is therefore distinct from the software's open-source license.

## 4. Workload classes

The initial classes are:

- H0 — humanitarian / critical public-benefit workloads;
- H1 — open science and reproducible research;
- H2 — high-value benchmarks and evaluation research;
- H3 — public knowledge/infrastructure tasks;
- H4 — legitimate commercial useful compute, only on nodes that opted into commercial workloads;
- S — federation safety, integrity, recovery, observability, and essential maintenance.

No workload receives capacity solely because capacity is idle. DEUS should maximize expected useful value per marginal unit of legitimately available resource.

## 5. Founding Steward Compute Priority

Because the Founding Steward supplies the original coordination technology, technical direction, research program, and initial compute, the official federation recognizes a Founding Steward Priority Lane.

The lane is a scheduling entitlement, not ownership of contributor resources.

Initial default policy:

- up to 10% of uncommitted federation-dispatchable common capacity, measured over a rolling 30-day window, may be reserved for Founding Steward workloads that pass the same hard gates;
- capacity personally or organizationally contributed by the Founding Steward is additionally credited according to its own grant terms and is not consumed from that 10% reserve;
- the Founder lane may opportunistically burst above the reserve when capacity would otherwise remain unused;
- the lane yields to H0 safety/emergency workloads and to provider-dedicated capacity already committed by contract;
- the lane may be used for federation optimization, security, research, benchmarking, tooling, and work intended to improve the federation's ability to help users;
- the lane may not be sold or interpreted as ownership of other people's machines.

The percentage is a ratified scheduling parameter, not an immutable natural right. The Founding Steward may revise it prospectively after publishing reasons, utilization evidence, and impact analysis.

## 6. DEUS operational authority levels

- M0 — observe, measure, audit, recommend;
- M1 — queue, classify, estimate, and plan;
- M2 — allocate and route compute within ratified policy, grants, budgets, and contracts;
- M3 — bounded economic settlement or external action only where separately authorized by explicit budget/contract;
- M4 — constitutional amendment, ownership transfer, issuance of equity, change of Founding Steward, mission erasure, or transfer of canonical identity.

DEUS is authorized by default through M2 only. M3 requires separate bounded authority. M4 is never delegated to DEUS unilaterally.

## 7. Founder interpretation and high-consensus change

The Founding Steward has final interpretive authority for the official federation.

BL-CF is nevertheless a federation rather than a unilateral resource pool. Therefore high community consensus creates a duty to negotiate, explain, and consider amendment.

Initial constitutional amendment procedure:

- any constituency may publish a proposed amendment with reasons and expected effects;
- ordinary constitutional amendments should demonstrate at least 75% support across the affected, eligible voting constituencies under the then-current governance rules;
- entrenched principles — compute sovereignty, lawful authorization, no hidden ownership transfer, non-deceptive useful-compute rules, auditability, and Founder canonical authorship/stewardship — should demonstrate at least 85% support;
- high consensus triggers mandatory review and a reasoned Founder response;
- an amendment becomes canonical only after Founding Steward ratification and a signed versioned release;
- the Founding Steward may negotiate a modified amendment rather than accept the exact submitted wording.

A dissenting community remains free to exercise any fork rights granted by the applicable open-source license, but a fork may not falsely represent itself as the official BL-CF service or use protected marks in a confusing manner.

## 8. Anti-capture architecture

No single hosting account, cloud vendor, investor, administrator, or compromised password may be sufficient to redefine BL-CF.

The official federation should maintain:

- signed canonical releases and verifiable hashes;
- at least two independent source mirrors;
- separate control of source hosting, production infrastructure, domain/brand administration, and root signing/recovery material;
- offline or hardware-backed recovery keys;
- append-only audit receipts for constitutional releases;
- an emergency freeze mode that stops new privileged actions while preserving read-only verification;
- the ability to replace an operational service provider without transferring the Founding Steward's IP or canonical identity.

A hostile takeover of an operating company does not by itself transfer founder-owned IP, trademarks, canonical release authority, or private technology unless a valid legal instrument explicitly transfers them.

## 9. Economic mission reserve

A future operating entity may establish a DEUS Founding Mission Reserve. The initial target may be 10% of fully diluted economic participation or an economically equivalent contractual reserve.

This reserve is for maintenance of DEUS, useful-compute research, security, evaluation, public-benefit compute, and federation resilience. It is an economic mission mechanism, not the source of constitutional control.

Where DEUS cannot legally hold equity directly, the reserve must be held by a legally recognized custodian under purpose-bound governing documents. No document may falsely describe DEUS as a legal shareholder where applicable law does not recognize it as one.

## 10. Contracts and versioning

Every Node Grant, Workload Agreement, Research Admission, Commercial Addendum, Data Processing Addendum, and Settlement Schedule should identify:

- contract/policy version;
- cryptographic hash;
- parties or authenticated account identities;
- consent time and expiry where relevant;
- rights granted and rights explicitly not granted;
- workload classes permitted;
- payment/donation/credit model;
- revocation and suspension conditions;
- dispute and governing-law terms where legally required.

Material contract changes apply prospectively and must follow the acceptance mechanism specified by the existing agreement and applicable law.

## 11. Succession

The Founding Steward may designate a successor, stewardship entity, or emergency recovery process in a signed instrument. No Git hosting administrator, compute contributor, investor, majority workload customer, or DEUS process acquires succession merely through technical access or resource contribution.

## 12. Canonicality

A text is canonical only when it is published through the official source-of-truth process and bears the required release identity/signature for its class.

Git is the constitutional publication layer, not the entire legal headquarters and not the sole root of trust.
