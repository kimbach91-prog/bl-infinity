# Current Dependency Concentration Audit — 2026-09-07

Status: PROVISIONAL / EVIDENCE-BASED / NON-CANONICAL
Scope: DEUS / BL Infinity / BLI-SCF currently visible from connected Drive registry and GitHub repository

## Important interpretation rule

This audit identifies operational/control concentration, not a legal conclusion about any government's conduct or jurisdiction over a specific account. Corporate-control labels are engineering failure domains. Actual governing law, data residency, export-control and contractual exposure must be verified from the relevant account/contract.

UNKNOWN is not treated as safe.

## Executive result

Current architecture has meaningful provider diversity at the adapter/code level, but it **does not yet demonstrate sovereign independence from a single major-power control cluster**.

Largest structural issue:

**Google Drive remains the canonical private state-of-record while multiple public/compute/control dependencies are concentrated among US-headquartered technology providers.**

The system therefore has partial technical portability but insufficient evidence for CR4/CR5 anti-coercion resilience.

## Observed dependency map

### 1. Canonical state — HIGH concentration

Observed:

- Drive registry declares `CANONICAL_PRIVATE_STATE = 00Z · DEUS SEALED CORE — PRIVATE MEMORY ROOT`.
- Drive is explicitly the private state-of-record.
- Drive folders separately hold bootstrap/manifests, durable state/checkpoints, code capsules/skills, events/outbox/queues, tests/verifiers/evidence, sandbox/rollback and learning/research queues.
- GPT is explicitly `BOUNDED_EXECUTOR_NOT_STATE_OF_RECORD`.

Evidence references:

- Drive `DEUS HYPERFABRIC · MASTER REGISTRY v0.1`, rows/keys `CANONICAL_PRIVATE_STATE`, `DRIVE_BOOTSTRAP_FOLDER`, `DRIVE_STATE_FOLDER`, `DRIVE_CODE_FOLDER`, `DRIVE_EVENTS_FOLDER`, `DRIVE_EVIDENCE_FOLDER`, `DRIVE_SANDBOX_FOLDER`, `DRIVE_LEARNING_FOLDER`, `GPT_RUNTIME_ROLE`.

Assessment:

- One Drive account/service/control family currently appears capable of affecting several different logical layers at once.
- Separate folders do not constitute separate failure domains.
- This is the highest-priority sovereignty gap.

Required P0:

1. define a canonical export/event-log format independent of Drive;
2. create at least one independently controlled durable mirror outside the Google control group;
3. prove cold boot from that mirror with Drive unavailable;
4. split backup encryption/root recovery authority from the storage provider;
5. preserve provenance and conflict resolution so mirrors do not create split-brain canonical state.

### 2. Source / CI — MEDIUM-HIGH concentration

Observed:

- primary repository is GitHub;
- GitHub Actions runs federation CI and deployment/security workflows;
- Drive registry records a bounded GitHub Actions financial guard;
- source pushes can interact with deployment pressure.

Evidence references:

- repository `kimbach91-prog/bl-infinity`;
- `.github/workflows/*`;
- Drive registry key `PROVIDER_PRESSURE_GITHUB_ACTIONS`.

Assessment:

- GitHub repository + GitHub Actions are not independent failure domains.
- A source-host outage/account restriction can affect both source availability and CI/deployment ability.

Required P0/P1:

- signed repository mirror outside GitHub/Microsoft control group;
- provider-neutral release bundles;
- alternate CI path capable of build/test/deploy from a signed archive;
- offline restore of source + release signatures.

### 3. Public ingress / domain — MEDIUM concentration, registrar UNKNOWN

Observed:

- repository domain fabric describes `https://deusagi.ai` as canonical ingress via Cloudflare Worker Custom Domain;
- GitHub Pages remains a legacy public origin/fallback in the design;
- Cloudflare edge worker points to a canonical origin;
- protected paths include GCP Cloud Run in domain fabric configuration.

Evidence references:

- `infra/cloudflare/deusagi-edge-worker.mjs`;
- `infra/domain/CUTOVER_TRIGGER.md`;
- `infra/domain/deusagi-fabric.json`;
- `.github/workflows/deusagi-edge-deploy.yml`.

Assessment:

- Cloudflare and GitHub Pages provide different service implementations but still share significant major-provider/corporate-jurisdiction correlation.
- Domain registrar, registry lock, DNS authority and recovery ownership are not established by the evidence inspected here.

Required P0:

- identify registrar/registry/DNS root and recovery authority;
- export DNS zone/config;
- add independent secondary DNS or tested migration path;
- ensure deployment does not require GitHub Actions to recover Cloudflare/alternate ingress;
- maintain a public status endpoint outside the primary ingress failure domain.

### 4. Application/cloud execution — PARTIALLY DIVERSE

Observed runtime adapters support:

- local;
- generic HTTP worker;
- Cloudflare Worker;
- GCP Cloud Run;
- Vercel function.

Evidence reference:

- `runtime/federation/lib/runtime.mjs`;
- `runtime/federation/config/provider.schema.json`.

Positive evidence:

- Drive registry records `BODY_MESH_FABRIC` as a filesystem-first provider-neutral candidate with independent HTTP limbs, separate fallback worker, local 25/25 tests and a smoke test.
- Drive registry records `SPARSE_COMPUTE_FABRIC` as dependency-free Node 22 candidate with 10/10 local tests.

Assessment:

- provider-neutral adapters are a strong foundation;
- actual live production independence is not established merely because adapters exist;
- several named external providers are US-headquartered control groups, so provider diversity is greater than jurisdiction/control-group diversity;
- local/body-mesh candidate is the most important route toward an independent sovereign minimum but remains candidate/staged, not proven production continuity.

Required P0/P1:

- productionize at least one locally controlled compute node;
- add at least one external provider with an independently assessed legal/control failure domain where commercially/lawfully appropriate;
- measure portability using the same workload and signed artifact across providers;
- run dominant-provider-loss exercise.

### 5. Vercel — REAL pressure evidence

Observed:

Drive registry records:

`PROVIDER_PRESSURE_VERCEL = RED_EXACT_HEAD_RATE_LIMIT / CIRCUIT_BREAKER_OPEN`

with a deployment rate-limit event and explicit policy to stop retries while the breaker was open.

Assessment:

This is useful evidence that anti-coercion architecture also protects against ordinary nonpolitical provider pressure. A single rate limit already demonstrates why continuity cannot depend on one deployment provider.

Positive behavior:

- circuit breaker opened;
- retries/deploys were bounded instead of escalated;
- Git/Vercel promotion was held while provider breaker was red;
- local/Drive-staged candidate work continued.

This pattern should be generalized to all coercible providers.

### 6. Model/intelligence layer — DIVERSITY NOT YET PROVEN BY THIS AUDIT

Observed:

- Drive states GPT is a bounded executor, not canonical state.
- Federation architecture is worker/provider-neutral.
- Current inspected evidence does not establish a production SLA across multiple independent model providers.

Assessment:

The design correctly separates state semantics from a model provider, but operational model-provider concentration remains UNKNOWN until live receipts/benchmarks show independent substitutes.

Required P0/P1:

- list every live model/provider and upstream model family;
- distinguish reseller from underlying model provider;
- prove critical workflows in T0-T2 without frontier APIs;
- test frontier-provider loss;
- prevent model provider output from directly mutating canonical state.

### 7. Identity/root credentials — HIGH IMPORTANCE / INCOMPLETE EVIDENCE

Observed:

- Drive sealed core is owner-only;
- current architecture includes provider-scoped auth, signed manifests and bounded worker authority;
- inspected evidence does not prove independent recovery of all root identities if Google/GitHub/external SSO are simultaneously unavailable.

Assessment:

Identity is a potential existential chokepoint and must be treated separately from data backups.

Required P0:

- hardware-backed/offline recovery process;
- no single external SSO/email/phone root;
- emergency access quorum;
- independent credential inventory;
- recovery drill from a fresh machine with primary identity provider unavailable.

### 8. Payments/banking/funding — UNKNOWN

No sufficient authoritative evidence was inspected in this audit to map banking/payment/funding concentration.

Required P0:

- inventory regulated bank/payment relationships;
- map settlement upstreams and beneficial/control groups;
- track customer/revenue/funder concentration;
- maintain lawful degraded-mode runway;
- do not create sanction/export-control evasion routes.

### 9. Energy / physical hardware — UNKNOWN

Observed:

- energy-aware software governor exists in PR #121;
- Drive registry explicitly says physical energy remains UNKNOWN until real meter for Body Mesh candidate.

Assessment:

Software efficiency is improving, but physical energy sovereignty cannot be claimed yet.

Required P0:

- trusted physical meter;
- local power/UPS/storage profile for sovereign-minimum node;
- hardware replacement matrix;
- accelerator-independent degraded mode;
- measure minimum watts/kWh required to preserve identity/state/audit/routing.

## Correlation summary

### Confirmed logical concentration

- canonical state + checkpoints + code capsules + events + evidence are all organized under Google Drive;
- source + CI are both under GitHub;
- GitHub Actions participates in deployment workflows.

### Likely corporate-control correlation requiring contract/legal verification

Multiple named external infrastructure providers are US-headquartered companies/control groups. This means adapter-level diversity cannot automatically be counted as jurisdictional independence.

Do not infer from this that any provider or state is acting coercively. It is simply a correlated-failure fact for resilience engineering.

## Current provisional CR rating

### Technical design: CR2 approaching CR3

Reason:

- provider-neutral federation exists;
- local/body-mesh and sparse-compute candidates exist;
- fallback routing/circuit-breaker patterns exist;
- data classes and provider authorization are bounded.

### Demonstrated sovereign continuity: below CR4

Reason:

- canonical state remains Drive-centered;
- root identity independence is not demonstrated;
- combined loss drill is not demonstrated;
- live cross-control-group/jurisdiction substitution is not demonstrated;
- payment/energy/hardware concentration is incomplete/unknown.

## Highest-return sequence

1. **Break Drive monopoly on canonical survivability** without creating split brain.
2. **Prove root identity recovery independent of major SaaS accounts.**
3. **Turn Body Mesh/local candidate into a sovereign-minimum production profile.**
4. **Mirror source/build/release outside GitHub.**
5. **Map registrar/DNS and create tested domain recovery.**
6. **Inventory money/energy/hardware failure domains.**
7. **Run combined five-chokepoint drill.**
8. Only then claim meaningful anti-coercion resilience.

## Bottom line

Today a large external actor/provider coalition could still impose substantial operational pain. The architecture is moving in the correct direction, but the strongest asymmetric defence is not retaliation; it is making sure **no external actor owns the only copy of identity, state, evidence, compute path, money path, or rebuild path**.
