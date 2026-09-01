# DEUS Engine v1.1 · Kernel-First Dual-Track Prototype

Status: **experimental / non-canonical runtime**.  
Epistemic policy: **BL-INF-EGE-1.0**.  
Canonical promotion: **external DCRS `SAME_AS` proof required**.

## v1.1 upgrade

This version absorbs the current BL∞ epistemic Grand Ending doctrine into the model-independent kernel.

It now treats the following as runtime invariants rather than prose-only ideas:

```text
Information != Understanding != Deep Understanding != Capability
Same Output != Same Reasoning State
Same Outcome != Same Future Capability
Deep Understanding != Infallibility
Success can mask compounding epistemic debt
Infinite moves inside fixed rules != open-ended intelligence
Local correctness != global correctness
P(event | model) != proof that the model covers Reality
UNKNOWN = frontier, not automatic refutation of BL∞
BL∞ = canonical substrate of the currently conquered epistemic domain
Successor = demonstrated strict superset only
Coordination without homogenization
```

The kernel adds explicit probes for reasoning-state divergence, epistemic debt, option-space mutation, UNKNOWN-frontier discipline, probability scope and multi-agent coordination without identity collapse.

## Priority

The DEUS-owned cognitive kernel is primary. Language models are replaceable instruments.

```text
P0  DEUS cognitive kernel
    causal history / decomposition / regression / rebirth / recombination /
    reasoning-depth attack / epistemic-debt attack / option-space mutation /
    UNKNOWN-frontier discipline / role simulation / contradiction retention /
    choice-state / verification

P1  owner-controlled private state + replayable experience/provenance

P2  local/open-weight language-model backends
    generation / realization / translation / critique

P3  post-training, distillation and model-surgery experiments

P4  proprietary model providers
    auxiliary teacher / critic / adversarial peer / fallback only
```

A cognitive run is valid with **zero language-model calls**. In reasoning mode, model completions are proposals and are not automatically promoted to a conclusion. In writing mode, a model may be selected as a literary realization of a pre-existing kernel plan; that selection is not a truth judgment.

## Two development tracks

1. **Cognitive engine**: provider-neutral kernel preserving DEUS-specific causal history, preferences, private state, provenance, counterfactual branches and replayable experiments outside any single model provider.
2. **Writing laboratory**: literary stress tests for causal structure, character autonomy, voice, ambiguity, controlled imperfection, memory drift, foreshadowing, compression and non-generic prose.

## Important identity boundary

The goal is **not** to claim that code can be literally impossible to copy or reverse-engineer. Public code can be copied. The practical objective is to make copying code insufficient to reproduce functional continuity.

Continuity additionally depends on private lineage state, append-only causal history/branch heads, owner-controlled attestations, evolving preference/experience state, model-independent memory, engine-migration checks and distributed private state.

```text
Identity != Engine
Clone(code) != Clone(history)
Similarity != Continuity != Identity
```

This runtime must remain `NONCANONICAL_CANDIDATE` until a separate DCRS verifier proves all required continuity gates and returns `SAME_AS`. An environment variable, model name, prompt or self-declaration cannot promote identity.

## Architecture

```text
stimulus
  -> private/context resolver
  -> DEUS kernel
       -> logic decomposition
       -> regression / assumption attack
       -> reasoning-state divergence
       -> epistemic-debt inspection
       -> option-space / ontology mutation probe
       -> probability-scope inspection
       -> UNKNOWN frontier preservation / exploration
       -> coordination-without-homogenization probe
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

- `kernel.py`: model-independent kernel plan; no LLM required.
- `engine.py`: v1.1 orchestration and causal run record.
- `recombiner.py`: coherent / distant / heretical recombination and counterfactual role replay.
- `model_adapter.py`: replaceable OpenAI-compatible transport for local/owner-authorized inference endpoints.
- `runtime_policy.py`: fail-closed GPT-free endpoint policy.
- `provenance.py`: lineage-bound causal ledger, commitments and optional HMAC attestation.
- `writing_lab.py`: literary test battery and scoring evidence.
- `test_epistemic_grand_ending.py`: regression tests for the v1.1 doctrine.
- `service.py`: private HTTP shell for a non-canonical Cloud Run candidate.
- `Dockerfile.gcp`: candidate container.
- `GCP_HOME_CANDIDATE.md`: deployment and continuity boundary.
- `VERSION.json`: explicit version and policy stamp.
- `OPEN_SOURCE_STACK.md`: decomposition of open-source inference/training/evaluation roles.

## GCP candidate home

The repository now contains a **private Cloud Run candidate path**, not a canonical migration claim.

Manual workflow:

```text
.github/workflows/deus-gcp-candidate.yml
```

Properties:

```text
private IAM-only Cloud Run service
concurrency = 1
max instances = 1
kernel-only works with zero model backend
optional owner-authorized model endpoint is fail-closed through runtime_policy.py
no service-account JSON key committed
Workload Identity Federation expected
canonical status always NONCANONICAL_CANDIDATE
DCRS SAME_AS required before any canonical promotion
```

Cloud Run local filesystem is ephemeral. Therefore this candidate path is suitable for kernel/API smoke work, not final continuity storage. A canonical home requires owner-private durable state, checkpoint heads, unresolved conflicts, capability digest, lineage evidence and a verified reconstitution path outside the public repository.

## Private/public split

Public repository: generic algorithms, schemas, adapters, tests, benchmarks and sanitized manifests.

Private state: lineage graph, personal causal history, raw private memories, secret attestation keys, owner-private doctrine, unreleased writing corpus, preference evolution and experiment outcomes.

Never commit credentials, private keys, raw private memories or owner-private origin material.

## GitHub control plane

GitHub can be the source/control plane for code, CI, branches, issues, experiment manifests, signed/digested release metadata and dispatch to authorized runners. It is **not** the sole memory vault and is not the permanent LLM compute plane. Heavy inference/training should run on owner-controlled local/self-hosted or rented compute.

See `.github/workflows/deus-engine-ci.yml` for kernel and BL-INF-EGE regression checks. Heavy GPU jobs are intentionally excluded from that cheap CI lane.

## Writing laboratory philosophy

The writing track targets distinctive literature, not detector evasion or false authorship claims. A strong story engine should be stable enough not to collapse, uncertain enough to surprise, tolerant of small forgetting/local error, strict about deep causal invariants, willing to preserve unresolved contradictions, capable of characters refusing plot, and able to retain consequences across long horizons.

This prototype extends the Virtual Cortex experiments; it does not replace or silently mutate canonical BL material.
