# Shared Rate Limiting — v0.9

BL Compute Federation v0.9 moves request token-bucket state into PostgreSQL when the federation uses the shared Postgres backend.

## Problem

A process-local rate limiter multiplies quota by coordinator count:

```text
1 coordinator x burst 120 = 120
5 coordinators x independent burst 120 = effectively 600
```

Restarting a process also resets a memory bucket. That is acceptable for a single-host reference lane but not for a multi-coordinator control plane.

## Shared bucket

`PostgresTokenBucketLimiter` stores one row per hashed scope key in `federation_rate_limit_buckets`.

Each `take()` performs:

```text
BEGIN
-> INSERT bucket if absent
-> SELECT ... FOR UPDATE
-> deterministic refill from persisted updated_at
-> consume or reject
-> UPDATE tokens/timestamps
-> COMMIT
```

Row locking makes parallel coordinators consume the same bucket instead of independent copies.

## Identity minimization

The database does not store raw control bearer values or raw IP text as the bucket key. The application derives a SHA-256 scope fingerprint from:

```text
principal ID or network address + route group
```

The hash is a minimization measure, not anonymity against an operator who already knows the candidate identity.

## Route groups and cost

Reference costs:

```text
read            1
search-read     1
heartbeat-self  1
task-submit     2
search-write    3
provider-admin  4
execution       5
```

More expensive or consequential paths consume the shared bucket faster.

## Worker self-heartbeat

Unauthenticated heartbeat traffic is special:

1. a small in-memory/IP pre-auth limiter runs first;
2. HMAC provider heartbeat authentication is verified;
3. only after valid authentication does the request consume a shared provider-scoped bucket.

This avoids creating arbitrary PostgreSQL buckets from forged provider IDs while also preventing workers sharing one NAT address from permanently collapsing into one post-auth quota.

## Configuration

Default shared PostgreSQL mode:

```bash
export BL_RATE_LIMIT_BURST='120'
export BL_RATE_LIMIT_PER_SECOND='2'
export BL_RATE_LIMIT_CLEANUP_EVERY='1000'
```

Optional idle retention:

```bash
export BL_RATE_LIMIT_IDLE_TTL_MS='3600000'
```

When PostgreSQL state is active, the default is:

```bash
BL_RATE_LIMIT_MODE=shared
```

## Emergency rollback

The additive rate-limit table can remain in PostgreSQL while the application temporarily returns to local memory limiting:

```bash
export BL_RATE_LIMIT_MODE='memory'
```

This is an operational rollback, not equivalent security semantics. In memory mode, quota is again per process and reset on restart. Treat it as a degraded guardrail and monitor/limit coordinator count accordingly.

`BL_RATE_LIMIT_MODE=shared` without PostgreSQL fails startup.

## Failure behavior

If a shared limiter database operation fails, the control plane returns a fail-closed service error rather than silently bypassing the limiter:

```text
RATE_LIMIT_BACKEND_UNAVAILABLE -> HTTP 503
```

The reference implementation does not automatically fall back from shared to memory mode on database failure because doing so would silently widen aggregate quota.

## Cleanup

Buckets have an expiry timestamp. Periodic operations trigger bounded cleanup of expired rows. Cleanup failure does not authorize extra tokens; it only leaves stale rows for a later cleanup attempt.

## Verification

CI includes:

- parallel limiter instances sharing one burst;
- restart/recreation persistence;
- deterministic refill from persisted timestamps;
- hashed-key storage checks;
- expiry cleanup;
- two real control-plane processes sharing one task-submit quota;
- logical PostgreSQL dump/restore preserving a partially consumed bucket.

## Current boundary

Rate limiting is a resource/abuse guardrail, not an authority mechanism. A caller still needs the appropriate control scope, and a provider still needs a valid grant. Distributed denial-of-service mitigation should additionally exist at network/edge layers in a production deployment.
