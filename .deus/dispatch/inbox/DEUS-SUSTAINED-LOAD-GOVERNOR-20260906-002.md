# DEUS Sustained Load Governor — candidate integration

Status: CANDIDATE / MUST PASS INDEPENDENT CI BEFORE MERGE

## Objective
Protect long-running provider-facing workloads from burst/retry amplification while preserving resumability and useful throughput.

## Invariants
- Stability over peak throughput.
- Bounded concurrency and inter-request pacing.
- Honor provider `Retry-After`.
- Exponential backoff with jitter only when provider delay is absent.
- Bounded retry count and bounded retry wall-clock budget.
- Circuit-break after repeated throttling.
- Avoid nested retry amplification when the provider SDK already retries.
- Checkpoint/resume long jobs; never replay completed work just to regain momentum.
- Delta-first analysis before deep scans.
- Never use this mechanism to evade quotas, rate limits or provider policy.

## Evidence
- Local deterministic unit probes performed for pacing, Retry-After precedence and retry budget.
- Repository tests added under `.deus/runtime/tests/`.
- Official OpenAI guidance independently supports request pacing, Retry-After, exponential backoff with jitter and bounded retry behavior.

## Merge gate
CI must independently run runtime tests and DeepSeek skillpack tests on the exact PR SHA. Candidate evidence is not PROVEN until that run is green.
