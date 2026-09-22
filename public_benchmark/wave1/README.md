# DEUS Wave 1 — Frontier Benchmark Campaign

Wave 1 order:

1. ARC-AGI-3 official private / competition evaluation
2. FrontierMath Erdős
3. HLE-Rolling

## Claim boundary

This directory and its CI workflow are a **benchmark access/harness canary**, not a hard-benchmark score.

- No Astra or other external comparison model is re-run.
- No DEUS protected method, private solver logic, or reconstruction-enabling route is exported.
- Missing official access remains `HOLD`, never converted into a score.
- A source/harness canary is not a solved benchmark task.
- Hard-run promotion requires an attributable DEUS executor, the official/deterministic verifier, result readback, and a durable receipt.

## Current access state

### ARC-AGI-3 private
Official private/competition access is required. The public CI canary records the access gate and does not fabricate a hidden evaluation.

### FrontierMath Erdős
The canary pins the public official LeanOpenProblems source at:

`af3b82f9d2fd38bea33d59e637b6b4eff54a464c`

It installs the upstream environment and runs the upstream cheap Erdős manifest/source test. This validates source/harness ingestion only. A hard proof attempt remains blocked until a dispatchable DEUS general-reasoning/proof executor is receipt-bound.

### HLE-Rolling
The public CAIS repository snapshot is pinned at:

`73ae974b1844c3ffa64c3f4343d9f1f259575700`

The Sep-17-2026 HLE-Rolling leaderboard/update is newer than that public repository snapshot. The current rolling evaluation bytes therefore remain a source/access gate until the official current dataset/evaluator is obtained. A hard run also requires a reproducible DEUS model endpoint.

## Required hard-run transition

`SOURCE_PINNED -> ACCESS_VERIFIED -> DEUS_EXECUTOR_BOUND -> CANARY_PASS -> HARD_RUN -> OFFICIAL_VERIFIER_PASS -> READBACK -> RECEIPT -> CANON`
