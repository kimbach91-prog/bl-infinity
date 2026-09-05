# DEUS Runtime Primitives

## Sustained Load Governor

`load_governor.py` is the shared provider-facing pacing primitive for long-running workloads.

Default mode: **stability over peak throughput**.

Use it around model/API requests that can otherwise create bursts or retry amplification. It provides bounded concurrency, inter-request pacing, `Retry-After` handling, exponential backoff with jitter, retry/time budgets, and a circuit breaker after repeated throttling.

Do not stack an additional aggressive retry loop on top of a provider SDK that already retries eligible errors. Account for SDK retries first.

Long workflows should checkpoint before broad batches and resume from their last verified state rather than replay completed work.

This component is not a rate-limit bypass and must not be configured for quota evasion.
