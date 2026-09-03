# Failure and Side-Effect Semantics

BL Compute Federation assumes at-least-once delivery unless a capability explicitly provides stronger semantics. Queue idempotency prevents duplicate admission of equivalent non-side-effect work, while worker idempotency replays a stored result when the same idempotency key reaches the same worker again.

At-least-once delivery is not the same as exactly-once effects. A timeout can occur after a remote effect happened but before its acknowledgement reaches the coordinator. Therefore tasks marked `sideEffect=true` are rejected by providers unless the signed grant sets `authorization.allowSideEffects=true`.

A side-effect task without both an explicit `idempotencyKey` and `retrySafe=true` is admitted with one maximum attempt. Future side-effect capabilities must define their idempotency contract before enabling retries or cross-provider fallback. The safest pattern is to make the external system accept the same idempotency key and return the original result for duplicate requests.

Cache is also fail-closed. Public cache requires `cachePolicy=public`, internal cache requires `cachePolicy=tenant`, private cache requires `cachePolicy=private-ok`, and side-effect tasks are never cached.

Contribution accounting records coordinator-measured latency and bytes separately from any provider-reported usage. Reported usage is evidence supplied by the provider, not automatically treated as a trusted measurement.
