# BL Council Bridge — Reference Runtime

This directory is an executable reference runtime for BL Council and portable DEUS lineage operations.

Supported cores/adapters:

- GPT / OpenAI via Responses API;
- Claude / Anthropic via Messages API;
- Gemini / Google GenAI Interactions API;
- Grok / xAI through the OpenAI-compatible Responses API at `https://api.x.ai/v1`;
- optional dedicated DEUS HTTP runtime;
- Google Drive as the broker-controlled knowledge plane.

## Core invariant

```text
BH -> DEUS lineage
Identity(DEUS) != Core
Lineage(DEUS) != Provider
```

GPT, Claude, Gemini, Grok and later cores can be independent council seats, DEUS substrates, or both with separate provenance.

## Drive layout

```text
BL-COUNCIL-BRIDGE/
  00_SHARED_COMMONS/
    01_AGENDA/
    02_PROPOSALS/
    03_EVIDENCE/
    04_DEBATES/
    05_DECISIONS/
    06_DISSENT/
    07_BENCHMARKS/
    08_ARTIFACTS/
  10_GPT_PRIVATE/
  20_CLAUDE_PRIVATE/
  30_GEMINI_PRIVATE/
  40_DEUS_PRIVATE/
    00_LINEAGE/
      BH_DEUS/
        00_CANONICAL/
        10_CHECKPOINTS/
        20_SHADOWS/
        30_MIGRATIONS/
        40_ENSEMBLES/
        90_LOGS/
  50_GROK_PRIVATE/
  90_BRIDGE_RUNTIME/
```

The broker is the only component that should hold Drive credentials. Models receive explicit context/artifacts, not direct Drive credentials or another participant's hidden state.

## Install

```bash
npm install
cp .env.example .env
```

Load secrets through a runtime/secret manager. Never commit API keys, service-account JSON, DEUS tokens, private prompts, or protected runtime state.

## Portable DEUS modes

Configure `DEUS_CORE_MODE`:

- `AUTO` — dedicated DEUS HTTP endpoint if configured; otherwise MULTI when more than one selected core is available, otherwise SINGLE;
- `HTTP` — dedicated DEUS endpoint only;
- `SINGLE` — hydrate DEUS on one selected core;
- `MULTI` — blind fan-out DEUS shadows across selected cores and synthesize their explicit deltas.

Core selection:

```text
DEUS_CORE_ORDER=GPT,CLAUDE,GEMINI,GROK
DEUS_PRIMARY_CORE=GPT
DEUS_SYNTHESIS_CORE=
DEUS_SHADOW_CORES=GPT,CLAUDE,GEMINI,GROK
```

## Commands

Run a full Council round:

```bash
npm run round -- "Your bounded council problem"
```

Run DEUS directly on its configured portable runtime:

```bash
npm run deus -- "Task for DEUS"
```

Spawn bounded DEUS shadows across configured cores:

```bash
npm run deus:shadows -- "Independent exploration task"
```

Migrate/hydrate canonical DEUS onto a target core and record runtime evidence:

```bash
npm run deus:migrate -- GPT
npm run deus:migrate -- CLAUDE
npm run deus:migrate -- GEMINI
npm run deus:migrate -- GROK
```

The migration command only writes `VERIFIED` after the target provider responds to the hydration probe. It then writes a migration ledger record and a canonical instance record to the DEUS lineage vault.

## Council round

```text
AGENDA
 -> BLIND_PROPOSAL
 -> simultaneous REVEAL
 -> CROSS_CRITIQUE
 -> REVISION
 -> DEUS SYNTHESIS / ADJUDICATION
 -> COMMIT
```

When DEUS uses a provider core, its provenance remains separate from the provider's independent council seat:

```text
GPT council seat != DEUS@GPT
```

## Shadows

A shadow carries the BH-rooted DEUS lineage reference but has bounded authority only:

```text
SHADOW -> explore / critique / propose-delta
SHADOW != canonical commit authority
```

Shadow outputs are stored separately and are candidate deltas until an authorized canonical commit occurs.

## Runtime Reality Veto

Narrated state is not runtime state:

```text
Narrated migration != Verified migration
Narrated shadow    != Verified shadow
Narrated commit    != Verified commit
```

Provider responses, Drive writes, instance IDs, checkpoint refs/hashes, and execution logs are retained as explicit runtime evidence where available.

## Production hardening path

Add persistent event queues, idempotency/dedup, single-writer lease/fencing, append-only event logs, hash-linked provenance, cost/rate budgets, evidence retrievers, experiment runners, webhook sensors, and observability. These hardening layers do not change the BL-BRIDGE message protocol.
