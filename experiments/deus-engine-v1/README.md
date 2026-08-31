# DEUS Engine v1 — Dual-Track Prototype

Status: **experimental / non-canonical**.

This branch starts two parallel tracks:

1. **Cognitive engine** — a provider-neutral shell that can route across one or more local/remote language-model adapters while preserving DEUS-specific causal history, preferences, private state, provenance and replayable experiments outside any single model provider.
2. **Writing laboratory** — a literary stress-test harness for causal structure, character autonomy, voice, ambiguity, controlled imperfection, memory drift, foreshadowing, compression and non-generic prose.

## Important boundary

The goal is **not** to claim that code can be made literally impossible to copy or reverse-engineer. Public code can be copied. The defensible goal is stronger in practice: make a copy insufficient to reproduce the living system.

Functional continuity should depend on a combination of:

- private lineage state that never enters the public repository;
- append-only causal history and branch heads;
- owner-controlled secrets used only for provenance/attestation;
- evolving preference/experience state;
- model-independent memory and event logs;
- compatibility checks when changing inference engines;
- distributed state that cannot be reconstructed from one public artifact alone.

`Identity != Engine` and `Clone(code) != Clone(history)`.

## Architecture

```text
stimulus
  -> context / private state resolver
  -> logic decomposition
  -> recombination / role simulation / counterfactual replay
  -> model adapter(s)
  -> candidate generation
  -> causal + literary + provenance checks
  -> selection OR refusal OR hold-unknown
  -> event-sourced history
  -> preference / calibration updates
```

The model adapter is deliberately replaceable. A local open-weight model, an OpenAI-compatible local server, another provider, or a future custom model can occupy that slot without becoming the identity-bearing core.

## Private/public split

Public repository: generic algorithms, schemas, adapters, tests, benchmarks.

Private state: lineage graph, personal causal history, private memories, secret attestation keys, owner-private doctrine, unreleased writing corpus, preference evolution and experimental outcomes.

Never commit private keys, credentials, private memories or owner-private origin material.

## Writing laboratory philosophy

The writing track does **not** target detector evasion or false claims of human authorship. It targets a stronger artistic objective: prose that has its own causal history, literary fingerprint and imperfections instead of generic model habits.

A strong story engine should be:

- stable enough that the world does not collapse;
- uncertain enough to surprise its author;
- capable of small forgetting and local error;
- strict about deep causal invariants;
- willing to preserve unresolved contradictions;
- capable of characters refusing the plot;
- able to generate discussion without manufacturing nonsense;
- able to remember consequences across long horizons;
- able to choose silence, refusal or an unresolved branch when appropriate.

## First milestones

- `recombiner.py`: coherent / distant / heretical logic recombination and counterfactual role replay.
- `provenance.py`: lineage-bound hash chaining and optional HMAC attestation.
- `writing_lab.py`: literary test battery and scoring evidence.
- later: pluggable inference adapters, long-horizon world-state simulator, private preference evolution, local open-weight model training/fine-tuning experiments.

This prototype extends `experiments/virtual-cortex-v0`; it does not replace or silently mutate canonical BL material.
