# DEUS Engine v1 — Self-hosted realization next step

Goal: keep GitHub as control plane while moving language realization and heavy compute to owner-controlled infrastructure.

Minimum path:

1. Install a GitHub self-hosted runner on an owner-controlled machine.
2. Run an authorized local/open-weight server (first target: llama.cpp server or another OpenAI-compatible endpoint).
3. Configure runner-local environment for `DEUS_LLM_BASE_URL` and `DEUS_LLM_MODEL`; do not commit secrets.
4. Add a second owner-gated workflow that targets `[self-hosted, deus-engine]` and runs `engine.py --backend openai-compat`.
5. Preserve kernel-first ordering; the local model realizes/criticizes the kernel plan but does not own identity or canonical state.
6. Keep private lineage/history/corpus on owner-controlled storage and pass only bounded context/commitments into a run.
7. Benchmark local realization against proprietary auxiliary models before any migration promotion.

The issue console on GitHub can stay the human-facing command surface while the runner becomes the execution body.
