# Wave 1 — GPT Tool-Substrate Contract

Status: operational projection for the Wave 1 benchmark campaign.

This file implements the already-canonical DEUS boundary that GPT/ChatGPT is a replaceable work interface and tool substrate, while DEUS remains the benchmark subject/executor.

## Roles

### GPT_TOOL_SUBSTRATE

Allowed uses include:

- public-source research and currentness checks;
- Google Drive / Docs / Sheets operations;
- GitHub source, branch, PR, CI, artifact and receipt operations;
- public web retrieval;
- access-route discovery;
- environment and harness setup;
- deterministic file conversion, hashing, packaging and transport;
- running benchmark-owned validators/verifiers without interpreting them into a solution;
- receipt collection, readback and canonical indexing;
- drafting operational packets and runbooks.

GPT output remains attributed to GPT_TOOL_SUBSTRATE where it materially contributes.

### DEUS_BENCH_EXECUTOR

Owns semantic benchmark work:

- deciding benchmark actions;
- producing answers;
- producing Lean proofs/disproofs;
- model reasoning over HLE items;
- ARC-AGI-3 exploration/modeling/goal/action decisions;
- any adaptive response to verifier feedback that changes the candidate solution.

A hard benchmark result is attributable to DEUS only when the task-bound DEUS executor receipt identifies the executed benchmark/version/configuration.

## Phase split

1. PREP — GPT_TOOL_SUBSTRATE allowed.
2. HANDOFF — GPT_TOOL_SUBSTRATE may prepare opaque refs/hashes/config, but not solve.
3. TEST — semantic execution must be DEUS_BENCH_EXECUTOR. GPT may remain control-plane-only if it cannot inspect/modify semantic task content.
4. VERIFY — official/deterministic verifier may be launched by GPT_TOOL_SUBSTRATE. Any adaptive reasoning based on verifier output belongs to DEUS_BENCH_EXECUTOR.
5. POST — GPT_TOOL_SUBSTRATE may package receipts, compare public metrics and update canon.

## Taint rule

If GPT or another external model materially reads a test item and proposes an answer, proof, action plan or benchmark-specific correction, that item is not counted as an independent DEUS result.

Infrastructure debugging that never consumes semantic benchmark content does not taint the benchmark.

## Protected-data rule

GPT tool access does not create permission to export protected DEUS methods, private raw memory, credentials, private topology, hidden evaluator data or reconstruction-enabling core combinations.

Use minimum necessary references/hashes. Secrets remain outside source control and ordinary chat.

## Truth boundary

- TOOL_SUBSTRATE_USED != GPT_SOLVED_THE_BENCHMARK.
- HARNESS_READY != HARD_RUN_EXECUTED.
- DEUS_EXECUTOR_CONFIGURED != DEUS_EXECUTED.
- VERIFIER_LAUNCHED != VERIFIER_PASSED.
- SCORE_OBSERVED != SCORE_CANONIZED.

Hard result promotion requires: pinned source/version + attributable DEUS executor receipt + official/deterministic verifier + preserved evidence + readback receipt.
