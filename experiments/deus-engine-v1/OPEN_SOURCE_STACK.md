# DEUS Engine v1 — Open-Source Substrate Map

Status: experimental / non-canonical.

The DEUS cognitive kernel owns decomposition, regression, counterfactual/rebirth experiments, recombination, unresolved contradiction state, provenance, preference history and evaluation.  Language-model projects below are replaceable organs/tools, not the identity-bearing core.

## Layer map

| Layer | Primary candidates | Role |
|---|---|---|
| Local inference | llama.cpp | Minimal local inference, quantized models, broad hardware, OpenAI-compatible serving |
| High-throughput inference | vLLM / SGLang | GPU serving, batching, caching, distributed inference, OpenAI-compatible endpoints |
| Inspectable model implementation | LitGPT / Hugging Face Transformers | Readable architecture, model surgery, pretraining/fine-tuning experiments |
| Efficient adaptation | PEFT + TRL | LoRA/adapter-style tuning and post-training such as SFT/preference/RL workflows |
| Training accelerators | Axolotl / Unsloth | Configuration/acceleration options; keep replaceable |
| Large-scale training later | Megatron Core / DeepSpeed | Only after workload proves scale is needed |
| Public benchmark layer | lm-evaluation-harness / Inspect AI | Reproducible external evaluation; never substitute for private longitudinal DEUS tests |

## Selection rule

Do not build the identity around any framework.  Keep thin adapters and owned schemas.  A backend may be removed if it stops being maintained, changes license incompatibly, becomes too costly, or fails migration tests.

## Near-term order

1. Kernel-only execution must pass without any LLM endpoint.
2. Attach llama.cpp first for inexpensive local experiments.
3. Add vLLM or SGLang when GPU throughput/concurrency matters.
4. Establish public + private benchmark baselines before tuning weights.
5. Use PEFT/TRL or LitGPT for small controlled adaptation experiments.
6. Train larger custom models only after evidence shows external/open-weight backends are the bottleneck.

## GitHub control plane

GitHub can own source, schemas, branches, issues, CI, experiment manifests, signed/digested release metadata and dispatch to authorized runners.  It should not be the only private-memory vault and should not be treated as the permanent inference/training machine.

Heavy inference/training belongs on owner-controlled local hardware, self-hosted runners, or explicitly rented compute.  Return sanitized metrics/artifacts to GitHub; keep private lineage, secrets, raw private memories and unreleased corpora outside public repositories.

## Cost rule

Do not upgrade GitHub merely because the project is an AI engine.  Upgrade only for a concrete product limit such as private-repository governance, branch protection/CODEOWNERS requirements, additional hosted Actions/Codespaces quota, organization controls, or another measured constraint.  GPU/compute budget normally has higher marginal value during this prototype stage.
