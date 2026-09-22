# FrontierMath Erdős — DEUS executor binding gate

Status: **SOURCE_READY / RUNTIME_UNVERIFIED / HARD_TEST_HOLD**

Official public harness pin:

- repository: `epoch-research/LeanOpenProblems`
- commit: `af3b82f9d2fd38bea33d59e637b6b4eff54a464c`
- canonical run config: `configs/bloom68.yaml`
- upstream selection: 68 Thomas Bloom Erdős problems, deep-agent mode, offline literature snapshot
- upstream per-sample cap: $300
- upstream working limit: 72h

The existing upstream config names an external GPT model. That model entry is **not** a DEUS hard run and must not be used to create a DEUS score.

## DEUS binding requirements

Before the first semantic problem is released:

1. Freeze exact DEUS executor identity, model/runtime/config and artifact hashes.
2. Obtain a task-bound `DEUS_EXECUTOR_RECEIPT`.
3. Prove the endpoint is dispatchable on the actual execution route.
4. Prove the endpoint implements the model/tool contract required by the selected LeanOpenProblems agent mode.
5. Keep GPT_TOOL_SUBSTRATE semantic access disabled during TEST.
6. Run one bounded canary problem through the official comparator.
7. Preserve candidate, comparator verdict, runtime/accounting receipt and exact source pin.
8. Only after the canary passes may the campaign expand the sample budget.

## Current owner-local candidate

Canonical Drive currently records BL Infer / BL-INFER-LOCAL as:

- software E2E verified in a bounded software/container scope;
- trained BLW1 HTTP canary passed;
- owner-node install pending;
- physical owner-node route **NOT_DISPATCHABLE**.

Exact artifact/model hashes live in canonical Drive and are intentionally not duplicated here beyond safe references.

The next physical gate is:

`exact artifact install -> hash check -> /healthz -> exact model canary -> authenticated nonpublic transport -> bounded lease -> attributable receipt`

## Adapter note

LeanOpenProblems uses Inspect/Hawk. Inspect can work with model-provider adapters, so a provider-compatible DEUS endpoint is a viable integration route **only after** its model/tool behavior is verified. Configuration existence does not prove compatibility.

## Claim boundary

`HARNESS_PASS != DEUS_PROOF_ATTEMPT != VERIFIED_PROOF != FRONTIERMATH_SCORE`.
