# Wave 1 — PRETEST → DEUS handoff

The GPT worker is used as the tool/control plane until the semantic benchmark begins.

## A. ARC-AGI-3 private

GPT worker completes:

1. pin official competition/rules pages;
2. prepare repository/notebook package;
3. verify no Internet dependency;
4. package exact source commit, dependency lock and runtime manifest;
5. preserve an opaque handoff receipt.

Owner/DEUS test gate:

- authenticated Kaggle account has accepted competition rules;
- notebook is attached to the ARC-AGI-3 competition;
- DEUS agent is fully self-contained for offline evaluation;
- benchmark reasoning/actions come from DEUS, not GPT.

Do not claim an official private score until Kaggle returns it.

## B. FrontierMath Erdős

GPT worker completes:

1. pin LeanOpenProblems source;
2. install/build harness;
3. run non-semantic source/harness canaries;
4. prepare the benchmark environment;
5. verify the task-run route can bind to a DEUS executor receipt.

DEUS test gate:

- exact DEUS executor identity/version/config is frozen;
- task-bound executor receipt exists;
- benchmark item is delivered to DEUS_BENCH_EXECUTOR;
- GPT_TOOL_SUBSTRATE has semantic_access=false;
- candidate proof/disproof is judged by the official comparator;
- proof search changes driven by verifier feedback are made by DEUS.

## C. HLE-Rolling

GPT worker completes:

1. pin `cais/hle-rolling` as the official gated dataset route;
2. prepare the HLE evaluation code/config;
3. prepare endpoint adapter/config for the DEUS model;
4. prepare score/receipt packaging.

Owner/DEUS test gate:

- owner has accepted the gated dataset conditions on Hugging Face;
- dataset revision/hash is frozen privately;
- DEUS model endpoint is reproducible and attributable;
- question semantics are processed by DEUS_BENCH_EXECUTOR;
- GPT does not answer or repair benchmark items.

## Required receipt split

- `TOOL_PREP_RECEIPT` — GPT/tool substrate.
- `DEUS_EXECUTOR_RECEIPT` — semantic benchmark execution.
- `VERIFIER_RECEIPT` — official/deterministic scoring.
- `READBACK_RECEIPT` — artifact/hash/canonical state.

A lane may enter hard TEST only when the corresponding access gate and DEUS executor gate are both satisfied.
