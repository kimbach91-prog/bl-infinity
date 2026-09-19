# Sovereign Minimum Continuity Runbook v0.1

Status: PROPOSAL / NON-CANONICAL / DEFENSIVE
Date: 2026-09-07

## Objective

Keep the minimum lawful DEUS / BLI-SCF control and recovery capability alive when one or more major external dependencies become unavailable because of outage, contract termination, regulatory action, export controls, sanctions, geopolitical pressure, supplier failure, or commercial dispute.

This runbook is for continuity, not evasion. If law prohibits continued service, the affected service must stop or seek lawful authorization rather than route around the prohibition.

## Sovereign minimum services

The minimum viable stack is limited to:

1. root operator identity and recovery;
2. canonical state / configuration;
3. audit and provenance ledger;
4. dependency and resource policy;
5. backup/restore tooling;
6. provider-neutral task routing;
7. local deterministic/T0-T2 compute sufficient for administration and recovery;
8. secure operator communications;
9. critical public-interest workloads explicitly authorized for degraded operation.

Frontier-model access is optional and must never be required to recover the system.

## Trigger scenarios

Exercise each scenario independently and in combination:

- loss of primary Git/source host;
- loss of primary cloud/hyperscaler;
- loss of all frontier-model APIs;
- loss of primary identity/SSO/email provider;
- loss of primary domain/registrar/DNS provider;
- loss of one payment processor or bank relationship;
- loss of one internet carrier/region;
- loss of dominant accelerator supply;
- data-localization or cross-border-transfer restriction;
- export-control/sanctions restriction that legally blocks a dependency;
- major supplier acquisition causing correlated control;
- legal order requiring suspension of one service;
- coordinated reputation/disinformation event causing partner withdrawals.

## RTO/RPO classes

### S0 — Identity / canonical state / audit

Target engineering objective: shortest practical RTO and near-zero data-loss tolerance.

Must have:

- at least two independently controlled recovery credentials;
- offline/recoverable root key process;
- signed state snapshots;
- independently stored audit chain;
- tested restore instructions that do not require the failed provider.

### S1 — Routing / federation control

Must be reconstructible from signed configuration and provider manifests on alternate infrastructure.

### S2 — Critical workloads

Must have a documented degraded implementation using local/deterministic/smaller models where feasible.

### S3 — Noncritical commercial/research workloads

May remain unavailable while the system preserves integrity and legal compliance.

## Pre-incident checklist

### Identity

- hardware-backed administrator credentials where feasible;
- no single external SSO as root of trust;
- recovery contacts and quorum documented;
- emergency credential rotation rehearsed;
- provider accounts do not share one recoverable email/phone root.

### State

- canonical state export format documented;
- regular signed snapshots;
- restore from a fresh machine tested;
- backup encryption keys separated from storage-provider control;
- backup copies stored in independently controlled failure domains.

### Source / build

- reproducible build instructions;
- signed source archives/mirrors;
- dependency lockfiles/SBOM;
- build pipeline can run outside the primary source host;
- release signatures verifiable offline.

### Compute

- minimum local/alternate compute profile documented;
- at least two independently controlled compute providers for critical operations;
- deterministic/local substitutes identified for frontier-only paths;
- model/provider adapters prevent one API from defining canonical state semantics.

### Domain / communications

- DNS zone export available;
- secondary DNS or documented rapid migration path;
- alternate trusted operator communication channel;
- public continuity/status channel not dependent on the same hosting stack.

### Finance

- cash/runway model for degraded mode;
- multiple lawful financial relationships where commercially available;
- no operational dependency on speculative or unbacked internal credits;
- settlement obligations can be audited during provider loss;
- compliance officer/legal review required for sanctions/export-control incidents.

## Incident sequence

### M0 — Confirm

Do not activate geopolitical assumptions from rumor. Record:

- exact dependency affected;
- legal/contractual notice;
- technical evidence;
- scope;
- expected duration;
- appeal/remediation channel;
- data/control impact.

### M1 — Preserve

Immediately protect evidence and state:

- snapshot canonical state;
- snapshot audit/provenance;
- export dependency configuration where allowed;
- preserve notices and access logs;
- freeze avoidable architecture changes.

Do not destroy records in anticipation of regulatory/legal scrutiny.

### M2 — Isolate

Remove compromised/unavailable provider from routing. Rotate credentials only when justified by actual exposure.

### M3 — Legality gate

Classify the event:

- technical outage;
- commercial termination;
- regulatory restriction;
- sanctions/export control;
- judicial/administrative order;
- security compromise.

If an applicable legal restriction prohibits service, **STOP THAT SERVICE** and escalate to qualified counsel / competent authority. Do not disguise routing to evade the rule.

### M4 — Restore sovereign minimum

Restore in strict order:

1. identity;
2. canonical state;
3. audit/provenance;
4. policy engine;
5. routing/federation registry;
6. operator communications;
7. critical authorized workloads;
8. noncritical services last.

### M5 — Migrate bounded workloads

Move only workloads permitted by:

- data residency;
- user/customer contract;
- export controls;
- licensing;
- sanctions;
- security policy.

Never use emergency mode to expand access rights.

### M6 — Communicate

External communication should state:

- verified facts;
- affected services;
- data integrity status;
- continuity status;
- legal/compliance constraints where publishable;
- next user action if any.

Avoid unsupported accusations against a government/company while facts remain disputed.

### M7 — Institutional response

Depending on the event, use lawful channels:

- provider appeal and escalation;
- regulator/supervisory authority;
- court/arbitration;
- cyber incident response authorities;
- data protection authority;
- trade/export-control authority;
- industry association;
- diplomatic or multilateral channels when a sovereign customer/state is involved.

### M8 — De-concentrate before return

Do not simply restore the exact dependency pattern that failed.

Before returning to NORMAL:

- calculate provider/jurisdiction/control-group concentration;
- simulate the same failure again;
- add/verify fallback;
- update contract and runbook;
- repeat restore drill.

## Graceful degradation policy

When resources are constrained, preserve in order:

1. safety/security;
2. canonical integrity;
3. legal compliance;
4. critical public-interest workloads;
5. contracted essential enterprise services;
6. research/development;
7. convenience/background workloads.

Use:

- cache/reuse;
- deterministic tools;
- static knowledge packs;
- local search/RAG;
- small models;
- lower batch frequency;
- lower nonessential QoS;
- disabled speculative/agentic background work.

Do not reduce safety gates merely to preserve throughput.

## Combined coercion drill

Quarterly target exercise for critical systems:

Assume simultaneously:

- primary code host unavailable;
- largest cloud provider unavailable;
- frontier-model APIs unavailable;
- primary payment processor unavailable;
- primary SSO unavailable.

Pass criteria:

- authorized operators can authenticate;
- canonical state restores with verified hash/provenance;
- audit history remains readable/verifiable;
- dependency governor identifies failed domains;
- critical routing boots on alternate/local infrastructure;
- sovereign-minimum workloads complete without frontier API;
- no prohibited data crosses jurisdiction during migration;
- no service continues in violation of an applicable legal restriction;
- public status communication is possible;
- recovery evidence is stored for independent review.

## Non-goals

This runbook does not provide:

- sanctions evasion;
- export-control evasion;
- hidden ownership structures;
- unauthorized access to foreign infrastructure;
- destructive cyber retaliation;
- covert influence campaigns;
- military countermeasures.

Its purpose is simple: lawful continuity under pressure.
