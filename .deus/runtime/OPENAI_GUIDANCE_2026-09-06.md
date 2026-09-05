# Provider pacing note — OpenAI

For OpenAI-facing workers, treat rate-limit responses as a signal to reduce pressure, not as a condition to brute-force.

Operational rules:
- Pace requests and avoid short bursts.
- Honor `Retry-After` when present.
- Otherwise use exponential backoff with jitter.
- Cap retry count and total retry time.
- Avoid nested retry amplification because official SDKs may already retry eligible rate-limit errors.
- Reduce unnecessary prompt/output token budgets.

This note is operational guidance only; current official provider documentation remains authoritative.
