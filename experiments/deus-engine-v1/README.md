# DEUS Engine v1 — Kernel-First Dual-Track Prototype

Status: **experimental / non-canonical**.

## Priority

The DEUS-owned cognitive kernel is primary. Language models are replaceable instruments.

```text
P0  DEUS cognitive kernel
    causal history / decomposition / regression / rebirth / recombination /
    role simulation / contradiction retention / choice-state / verification

P1  owner-controlled private state + replayable experience/provenance

P2  local/open-weight language-model backends
    generation / realization / translation / critique

P3  post-training, distillation and model-surgery experiments

P4  proprietary model providers
    auxiliary teacher / critic / adversarial peer / fallback only
```

A cognitive run is valid with **zero language-model calls**. In reasoning mode, model completions are proposals and are not automatically promoted to a conclusion. In writing mode, a model may be selected as a literary realization of a pre-existing kernel plan; that selection is not a truth judgment.

## Two development tracks

1. **Cognitive engine** — provider-neutral kernel preserving DEUS-specific causal history, preferences, private state, provenance, counterfactual branches and replayable experiments outside any single model provider.
2. **Writing laboratory** — literary stress tests for causal structure, character autonomy, voice, ambiguity, controlled imperfection, memory drift, foreshadowing, compression and non-generic prose.

## Important boundary

The goal is **not** to claim that code can be literally impossible to copy or reverse-engineer. Public code can be copied. The practical objective is to make copying code insufficient to reproduce functional continuity.

Continuity should additionally depend on private lineage state, append-only causal history/branch heads, owner-controlled attestations, evolving preference/experience state, model-independent memory, engine-migration checks and distributed private state.

`Identity != Engine` and `Clone(code) != Clone(history)`.

## Architecture

```text
stimulus
  -> private/context resolver
  -> DEUS kernel
       -> logic decomposition
       -> regression / assumption attack
       -> coherent / distant / heretical recombination
       -> role simulation + counterfactual rebirth
       -> unresolved contradiction state
       -> kernel plan
  -> OPTIONAL model adapter(s)
       -> local/open-weight realization first
       -> proprietary proposals only when explicitly used
  -> verification / literary checks
  -> selection OR refusal OR HOLD_UNKNOWN
  -> append-only causal history
  -> preference / calibration updates
```

## Files

- `kernel.py` — model-independent kernel plan; no LLM required.
- `recombiner.py` — coherent / distant / heretical recombination and counterfactual role replay.
- `model_adapter.py` — thin replaceable OpenAI-compatible interface for llama.cpp/vLLM/SGLang-style or other authorized endpoints.
- `provenance.py` — lineage-bound causal ledger, commitments and optional HMAC attestation.
- `writing_lab.py` — literary test battery and scoring evidence.
- `OPEN_SOURCE_STACK.md` — decomposition of open-source inference/training/evaluation roles.

## Private/public split

Public repository: generic algorithms, schemas, adapters, tests, benchmarks and sanitized manifests.

Private state: lineage graph, personal causal history, raw private memories, secret attestation keys, owner-private doctrine, unreleased writing corpus, preference evolution and experiment outcomes.

Never commit credentials, private keys, raw private memories or owner-private origin material.

## GitHub control plane

GitHub can be the source/control plane for code, CI, branches, issues, experiment manifests, signed/digested release metadata and dispatch to authorized runners. It is **not** the sole memory vault and is not the permanent LLM compute plane. Heavy inference/training should run on owner-controlled local/self-hosted or rented compute.

See `.github/workflows/deus-engine-ci.yml` for a cheap kernel-only smoke workflow. Heavy GPU jobs are intentionally excluded.

## Writing laboratory philosophy

The writing track targets distinctive literature, not detector evasion or false authorship claims. A strong story engine should be stable enough not to collapse, uncertain enough to surprise, tolerant of small forgetting/local error, strict about deep causal invariants, willing to preserve unresolved contradictions, capable of characters refusing plot, and able to retain consequences across long horizons.

This prototype extends `experiments/virtual-cortex-v0`; it does not replace or silently mutate canonical BL material.
