# Throttle Policy

429/rate-limit events are backpressure. The correct response is to reduce pressure and preserve state.

1. Read error code and `Retry-After`.
2. If retryable, wait at least the provider-requested delay; otherwise exponential backoff with jitter.
3. Bound retries and elapsed retry time.
4. Open a cooldown circuit after repeated throttles.
5. Resume from checkpoint rather than replaying finished work.
6. Do not use multiple nested retry loops.
7. Do not attempt to bypass limits by key/account rotation or traffic disguising.
