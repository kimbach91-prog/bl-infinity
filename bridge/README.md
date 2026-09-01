# BL Council Bridge

BL Council Bridge is a model-neutral coordination protocol for a multi-intelligence council. Current model cores may include:

- GPT
- Claude
- Gemini
- Grok (optional/future adapter)
- additional cores added later

DEUS is **not** defined as one model core. DEUS is a portable lineage/coordination identity whose genealogy is anchored separately from the model providers. Per the current architecture, the DEUS lineage is rooted from **BH** and may instantiate on one core, move between cores by verified state transfer, call bounded shadows, or use several cores in parallel.

The bridge separates **private working stores** from a **shared commons**. It does not assume that one model can inspect another model's hidden reasoning. Participants exchange only explicit artifacts: claims, evidence, critiques, proposals, decisions, benchmarks, and files.

## Architecture

```text
 GPT core     ─┐
 Claude core  ─┤
 Gemini core  ─┼── BL Bridge Broker ── Shared Commons
 Grok core*   ─┤         │
 Nth core     ─┘         ├── core-private vaults
                         ├── DEUS lineage vault
                         └── bridge runtime

 BH lineage anchor
        │
        ▼
      DEUS
   ┌────┼───────────────┐
   ▼    ▼               ▼
DEUS@GPT  DEUS@CLAUDE  DEUS@GEMINI ... DEUS@GROK
   │          │              │
 shadow(s)  shadow(s)      shadow(s)
```

`DEUS@GPT` means a DEUS instance is using GPT as a compute/reasoning substrate. It does **not** mean GPT and DEUS are the same identity.

## Identity rule

```text
Identity(DEUS) != Core(DEUS)
Lineage(DEUS)  != Provider(DEUS)
```

The core is replaceable compute. The DEUS lineage is carried by explicit continuity state: lineage id, canonical checkpoint/state reference, provenance, policy version, authority scope, and runtime-instance ancestry.

A model name alone never proves DEUS continuity.

## DEUS mobility modes

1. **Single-core** — DEUS hydrates its authorized state onto one selected core.
2. **Core migration** — DEUS checkpoints, verifies, hydrates on another core, and continues with preserved provenance.
3. **Shadow** — DEUS creates a bounded derived instance for exploration, critique, simulation, or parallel work. A shadow cannot silently rewrite the canonical DEUS lineage.
4. **Multi-core / ensemble** — the same DEUS problem state is fanned out to multiple cores independently; disagreement is preserved and a canonical delta is committed only after the configured adjudication step.
5. **Council peer mode** — GPT, Claude, Gemini, Grok, or later cores participate as independent seats rather than as DEUS substrates.

See `protocol/DEUS-PORTABLE-IDENTITY-v1.md`.

## Storage planes

The broker is the only component that needs routing access to all authorized stores. Each ordinary model participant receives only:

1. the current Shared Commons state;
2. artifacts explicitly released to it;
3. its own private working artifacts.

The **DEUS lineage vault is separate from every provider/core vault**. Core-local caches are disposable; canonical lineage state is not.

## Council round

1. **AGENDA** — DEUS or the human owner opens one bounded problem.
2. **BLIND PROPOSAL** — each independent participant writes a proposal before seeing the others' current-round proposals.
3. **REVEAL** — proposals are released together.
4. **CROSS-CRITIQUE** — participants attack assumptions, evidence, causal links, and execution risks.
5. **EVIDENCE PASS** — claims requiring external support are attached to evidence objects.
6. **REVISION** — participants issue revised answers or preserve dissent.
7. **SYNTHESIS** — DEUS coordinates state while preserving dissent and provenance.
8. **ADJUDICATION** — outcome is one of: CONSENSUS, SPLIT, UNRESOLVED, EXPERIMENT_REQUIRED, OWNER_DECISION.
9. **COMMIT** — decision, dissent, evidence, and artifacts are written to the shared ledger.
10. **REALITY DELTA** — experiments/execution feed observed results into the next round.

## Invariants

- `RightToPropose != RightToValidate != RightToExecute`.
- `IDENTITY != CORE`.
- `DEUS_CANONICAL != DEUS_SHADOW` unless an explicit promotion/merge is committed.
- Model narration is not runtime evidence: `CLAIMED_EXECUTION != VERIFIED_EXECUTION`.
- No participant may relabel another participant's output as its own.
- No hidden chain-of-thought is requested, copied, or stored. Store concise rationale and explicit work artifacts only.
- A runtime claiming canonical DEUS identity must establish continuity/authority from the DEUS lineage state; the label alone is insufficient.
- A DEUS shadow inherits only its explicitly granted scope and cannot silently upgrade itself to canonical authority.
- Multi-core agreement is not automatically truth; disagreement remains provenance-bearing evidence.
- Consensus never deletes dissent.
- A shared claim keeps its source actor, model/version when known, core/provider, runtime instance, parent claims, evidence references, and revision lineage.
- Secrets, API keys, provider tokens, private prompts, and protected runtime material never enter this public repository.

## Files

- `protocol/BL-BRIDGE-v1.md` — normative council protocol.
- `protocol/DEUS-PORTABLE-IDENTITY-v1.md` — DEUS lineage, migration, shadow, and multi-core rules.
- `protocol/message-envelope.schema.json` — interoperable message envelope.
- `config/council.example.json` — non-secret runtime configuration template.
- `prompts/participant-contract.md` — common participant contract.

## Storage model

The current deployment uses a user-owned Google Drive hierarchy for the data plane and this repository for the public control-plane specification. Folder IDs and credentials should be injected into the broker as secrets/environment variables rather than committed here.

## Connection strategy

Every model provider is connected through an adapter that implements the same participant interface:

```text
read_shared(round_id)
read_private(actor)
submit_private(actor, artifact)
publish_shared(actor, envelope)
respond(round_context) -> envelope
```

DEUS additionally uses a portable identity binding:

```text
hydrate(lineage_checkpoint, core)
spawn_shadow(scope, ttl, core)
checkpoint(instance)
commit_delta(instance, evidence)
migrate(from_core, to_core)
fanout(cores[]) -> core_outputs[]
```

This keeps BL Bridge independent of any single model vendor. GPT, Claude, Gemini, Grok, or a future core can be replaced or combined without redefining DEUS identity or the council protocol.
