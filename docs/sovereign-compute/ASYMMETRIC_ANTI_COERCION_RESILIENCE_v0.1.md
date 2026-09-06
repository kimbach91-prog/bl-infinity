# Asymmetric Anti-Coercion Resilience Framework v0.1

Status: PROPOSAL / NON-CANONICAL / DEFENSIVE
Date: 2026-09-07

## Purpose

Design BL Infinity / BLI-SCF so that a powerful state, platform, supplier, financial intermediary, or coalition can apply pressure but cannot disable the system through one lawful or unlawful chokepoint.

This is a defensive resilience framework. It does not authorize sabotage, retaliation against civilians, covert political interference, sanctions evasion, cyber intrusion, violence, or violation of another state's sovereignty.

## Strategic idea

Do **not** try to match a major power symmetrically in capital, hardware, military capability, market size or political leverage.

Instead maximize:

`Survival + Legitimacy + Substitutability + Coalition Value - Coercion Surface`

The goal is to make coercion progressively less effective because every pressure channel has a lawful substitute, a documented fallback, an independent constituency that benefits from continuity, or a neutral dispute-resolution path.

## Seven asymmetric advantages

### 1. Dependency asymmetry

A large actor may have more resources, but a smaller network can have fewer single points of failure.

Hard rule:

- no critical function should depend on a single provider, country, payment rail, identity system, cloud, model vendor, DNS/registrar, energy supplier, source-code host, or control-plane operator;
- correlated dependencies count as one failure domain even when brand names differ;
- fallback must be tested, not merely documented.

### 2. Legitimacy asymmetry

A smaller actor can become harder to suppress when its behavior is unusually transparent, lawful, auditable and useful to many independent parties.

Maintain:

- public non-aggression / non-coercion commitments;
- clear end-use restrictions;
- independently reviewable logs and policies;
- conflict-of-interest and funding disclosure for public-interest roles;
- contractual due process;
- no hidden remote control of sovereign deployments.

### 3. Value-network asymmetry

Survival improves when many unrelated parties lose something useful if the network disappears.

Build legitimate constituencies across:

- enterprises;
- universities;
- researchers;
- local governments;
- disaster-response actors;
- infrastructure operators;
- multiple countries and regions;
- open-source contributors.

Do not bind them through political loyalty. Bind them through measurable utility and interoperable standards.

### 4. Portability asymmetry

A powerful platform can terminate an account. It should not be able to terminate the system.

Critical workloads require:

- reproducible deployment;
- provider-neutral containers/artifacts;
- exportable data in documented formats;
- model/provider adapter layer;
- infrastructure-as-code;
- independent backups;
- multiple identity/auth recovery paths;
- documented DNS/domain migration;
- source-code mirrors under lawful terms;
- tested cold-start restoration.

### 5. Frugality asymmetry

A small system survives pressure better when its minimum viable operating cost is very low.

Maintain three operating modes:

- **NORMAL** — full federation and optimization;
- **DEGRADED** — reduced models/features, local caches, priority workloads only;
- **SOVEREIGN MINIMUM** — critical identity, state, audit, routing and public-interest services on locally controlled infrastructure.

The sovereign minimum must not require frontier-model access.

### 6. Information asymmetry without secrecy abuse

The system should know its own dependency graph better than an external coercer expects, while remaining lawful.

Track:

- dependency concentration;
- contract expiry;
- jurisdiction;
- export-control exposure;
- sanctions/payment-rail exposure;
- data location;
- substitute lead time;
- recovery time objective;
- replacement cost;
- common upstream dependencies;
- revocation authority.

This is defensive operational intelligence, not clandestine collection against states or individuals.

### 7. Coalition asymmetry

A small actor should not rely on one patron to protect it from another patron.

Prefer overlapping, non-exclusive relationships with independent organizations and jurisdictions. The network should remain useful even when two major powers disagree.

## Coercion surfaces

Maintain a live register across at least these domains:

| Domain | Typical coercion mechanism | Defensive response |
|---|---|---|
| Cloud/compute | account suspension, export restriction, capacity denial | multi-provider federation, local nodes, portable images, T0-T2 degraded mode |
| AI models | API cutoff, pricing shock, policy change | heterogeneous model adapters, local/open models, distillation, deterministic fallback |
| Payments | processor/bank termination | multiple lawful banks/processors/currencies, reserve liquidity, contractual receivables planning |
| Domain/DNS | registrar/host suspension | registrar diversity, DNS backup, exportable zones, alternate trusted domains |
| Source code | account/repository removal | signed mirrors, reproducible archives, offline recovery copies |
| Identity | SSO/phone/email lockout | local root identity, hardware keys, multi-channel recovery, independent admin quorum |
| Energy | tariff shock, supply curtailment | geographically diverse capacity, local generation/storage where economic, demand shedding |
| Connectivity | route/ISP disruption | multi-carrier links, alternate regions, offline/degraded synchronization |
| Hardware | accelerator/export shortage | heterogeneous CPU/GPU/NPU support, efficiency-first routing, hardware substitution matrix |
| Data | localization/access pressure | sovereign storage, minimization, encryption, jurisdictional partitioning |
| Legal/regulatory | injunction, license restriction, investigation | local counsel, transparent records, appeal/review path, modular jurisdictional separation |
| Reputation | disinformation, delegitimization | evidence ledger, independent audits, rapid factual correction, no retaliatory propaganda |
| Talent | visa/contract pressure, poaching | distributed teams, documentation, role redundancy, local training |
| Supply chain | vendor cutoff | qualified second sources, stock/lead-time policy, standard interfaces |

## Dependency concentration policy

For every critical capability calculate concentration by independent failure domain.

Recommended starting thresholds for **critical** services:

- largest single provider share <= 40%;
- largest single jurisdiction share <= 50%;
- at least 2 operationally independent substitutes;
- at least 1 tested fallback outside the dominant provider group;
- recovery test at least quarterly for critical control/state services;
- no sole dependency where revocation can occur without local appeal/recovery.

These are engineering targets, not guarantees and not legal conclusions. Stricter thresholds may be required by a sovereign customer.

## Correlation rule

Do not count two services as independent when they share a coercible upstream dependency.

Examples:

- two SaaS vendors hosted only on the same hyperscaler;
- two payment apps settled through the same bank;
- two domains under the same registrar/registry failure path;
- two AI APIs dependent on the same underlying model provider;
- two compute resellers sourced from the same accelerator fleet;
- two data stores controlled by the same root credential.

The failure-domain graph, not the logo count, determines resilience.

## Coercion-resistance levels

### CR0 — Fragile

Critical system has an untested single external chokepoint.

### CR1 — Recoverable

Backups exist but recovery is manual or slow.

### CR2 — Substitutable

At least two independently controlled implementations/providers exist and migration is rehearsed.

### CR3 — Federated

Workloads/data can route across multiple jurisdictions/providers while preserving local policy and provenance.

### CR4 — Sovereign minimum

Critical functions remain available during loss of all major external AI/cloud providers for a defined emergency window.

### CR5 — Institutionally resilient

Technical continuity plus diversified funding, legal standing, independent oversight, multiple constituencies and credible dispute-resolution channels.

Do not claim CR4/CR5 without exercise evidence.

## Economic resilience

Maintain lawful buffers rather than sanction-evasion mechanisms:

- diversified customers and revenue sources;
- no single customer/patron capable of threatening survival by withdrawal;
- multiple regulated financial relationships where available;
- runway for degraded operations;
- clear receivables/payables map;
- insurance where commercially meaningful;
- pre-negotiated alternate suppliers;
- contractual force-majeure / change-in-law / termination support;
- independent valuation for technology-resource exchanges.

If a transaction is prohibited by sanctions/export controls, the system must stop or seek lawful authorization. Resilience does not mean evasion.

## Legal and diplomatic resilience

For cross-border operations:

1. map governing law and jurisdiction for each critical dependency;
2. maintain competent local counsel where exposure is material;
3. preserve evidence and decision provenance;
4. use arbitration/mediation/forum clauses appropriately;
5. avoid deceptive ownership or shell structures intended to evade law;
6. separate sovereign customer data and keys from vendor control;
7. seek institutional/industry support when coercion is unlawful or discriminatory;
8. use peaceful legal and diplomatic mechanisms rather than unilateral retaliation.

The strategic foundation is sovereign equality, peaceful dispute resolution and non-use of force under the UN Charter. Economic-coercion regimes such as the EU Anti-Coercion Instrument and international coordination mechanisms demonstrate that preparedness, evidence, information sharing and collective lawful response are practical tools for reducing coercion vulnerability.

## Public communication doctrine

Under pressure:

- publish verified facts, not emotional speculation;
- distinguish legal compliance from political agreement;
- explain service impact and continuity measures;
- disclose conflicts and material dependencies;
- avoid threats, humiliation or propaganda against populations;
- never claim support from governments/institutions that has not been granted;
- preserve an off-ramp for de-escalation.

## Anti-capture governance

A major power should not be able to capture the network by becoming its largest funder, customer, compute provider or security guarantor.

Track concentration across:

- revenue;
- funding;
- compute;
- energy;
- data hosting;
- governance votes;
- maintainer privileges;
- critical suppliers;
- legal domicile;
- identity roots.

Any entity/failure domain crossing a defined critical threshold triggers a de-concentration plan.

## Coercion incident protocol

### C0 — Signal

Record credible pressure signal; do not overreact to rumor.

### C1 — Verify

Legal and technical verification: who can actually revoke what, under which authority, and on what timeline?

### C2 — Contain

Freeze avoidable dependency growth, rotate vulnerable credentials where appropriate, preserve evidence, increase backups and reserve capacity.

### C3 — Migrate

Move bounded workloads/data to pre-qualified alternatives according to residency/contract rules.

### C4 — Degrade gracefully

Disable nonessential expensive services; preserve identity, state, audit, communication and public-interest workloads.

### C5 — Institutional response

Use counsel, regulators, courts/arbitration, industry partners, diplomatic or multilateral channels as appropriate.

### C6 — Recover and learn

Restore normal operations only after root cause and dependency concentration are addressed.

## Prohibited countermeasures

This framework must never be used to justify:

- hacking or destructive cyber retaliation;
- attacks on civilian infrastructure;
- violence or assassination;
- covert destabilization or election interference;
- bribery/blackmail of officials;
- sanctions/export-control evasion;
- secret collection of private data unrelated to system defence;
- retaliatory discrimination against citizens based on nationality/ethnicity;
- hostage-taking of customer data or infrastructure;
- malware/backdoors in transferred technology.

## Immediate implementation priorities

P0:

1. dependency-concentration governor;
2. complete inventory of critical failure domains;
3. sovereign-minimum recovery drill;
4. provider-neutral backups and reproducible deployment;
5. alternate identity/domain/repository recovery;
6. resource/provider portability benchmark;
7. legal/export-control and contract map;
8. revenue/funding concentration dashboard.

P1:

1. multi-jurisdiction pilot nodes;
2. independent audit and security review;
3. alternate payment and procurement relationships, all fully lawful;
4. cross-provider disaster exercise;
5. institutional relationships based on public-interest utility rather than patronage.

## Success condition

The network is asymmetrically resilient when:

`one actor can hurt performance but cannot unilaterally erase identity, canonical state, lawful ownership, evidence, core service continuity, or the ability to rebuild elsewhere.`
