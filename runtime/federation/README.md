# BL Compute Federation v0.9

A consent-aware control plane for combining authorized compute across owner devices, cloud quotas, partner grants and BYOC nodes without treating reachable infrastructure as free infrastructure.

## Core invariants

```text
reachable != authorized
heartbeat != authority
telemetry != authority
rate limit != authority
control scope != provider grant
```

A provider is usable only when its signed/revocable grant, capability, data policy, quota, concurrency, liveness and task policy all pass. Private data fails closed unless locality/egress policy explicitly permits it.

## What v0.9 adds

v0.9 keeps the v0.8 durable/horizontal runtime and adds shared request guardrails:

- PostgreSQL-backed token buckets shared across coordinators and restarts;
- per-bucket transactional row locking so coordinator count cannot multiply burst capacity;
- hashed rate-limit scope keys instead of raw bearer/IP strings in PostgreSQL;
- route-weighted token costs for reads, task submission, provider administration, search and execution;
- explicit rollback `BL_RATE_LIMIT_MODE=memory` without silently falling back on database failure;
- scoped control principals configured through environment-secret references;
- tenant-bound `task:submit` principals;
- global-only enforcement for provider/runtime/ledger/audit/search scopes until those stores have true tenant isolation;
- legacy `BL_CONTROL_TOKEN` retained as root-compatible break-glass authority;
- private-by-default read surfaces;
- explicit public read opt-in through `BL_PUBLIC_READ_SCOPES`;
- actor IDs added to existing security-sensitive audit events;
- shared rate-limit state included in PostgreSQL backup/restore verification.

The rest of the runtime retains:

- queue-to-executor orchestration with global, tenant and provider budget reservations;
- circuit breakers and telemetry feedback;
- opt-in tenant-scoped result caching;
- hash-chained audit and contribution ledger;
- Ed25519-signed provider grants;
- PostgreSQL shared provider authority/revocation/liveness;
- provider-scoped HMAC worker self-heartbeat with federation-wide nonce replay defense;
- explicit worker capability allowlist with no generic shell/eval/arbitrary-code endpoint;
- PostgreSQL `FOR UPDATE SKIP LOCKED` queue claims;
- provider `change_seq` delta synchronization with fail-closed backlog handling;
- 10k-provider structural benchmark and logical dump/restore invariant drill.

## Install and test

```bash
cd runtime/federation
npm install --no-audit --no-fund
npm test
```

## PostgreSQL coordinator

After a controlled schema migration:

```bash
export BL_POSTGRES_URL='postgresql://runtime_user:REDACTED@db.example.internal:5432/blcf'
export BL_POSTGRES_POOL_MAX='10'
export BL_POSTGRES_ALLOWED_DATA_CLASSES='public'
export BL_PROVIDER_SYNC_MODE='delta'
export BL_PROVIDER_SYNC_BATCH_SIZE='500'
export BL_PROVIDER_SYNC_MAX_BATCHES='20'
export BL_BUDGET_JSON='{"totalUsd":10}'
export BL_RATE_LIMIT_MODE='shared'
export BL_RATE_LIMIT_BURST='120'
export BL_RATE_LIMIT_PER_SECOND='2'
npm start
```

`BL_POSTGRES_AUTO_MIGRATE` is disabled unless explicitly set to `true`. Production should migrate using schema-owner authority and run coordinators with a restricted runtime role.

Application rollback paths:

```bash
# provider registry: return to v0.7-style full snapshot synchronization
export BL_PROVIDER_SYNC_MODE='full'

# request limiting: degraded per-process fallback
export BL_RATE_LIMIT_MODE='memory'
```

Memory rate limiting is weaker in a multi-coordinator deployment because each process has an independent bucket and restart resets local state. The runtime never silently switches from shared to memory mode when PostgreSQL fails.

## Control authentication

### Legacy root

Existing deployments can continue to use:

```bash
export BL_CONTROL_TOKEN='high-entropy-root-token'
```

This is treated as global root scope and should become a break-glass credential rather than the normal credential for every caller.

### Scoped principals

Example:

```bash
export TENANT_A_API_TOKEN='high-entropy-tenant-token'
export OPS_READ_TOKEN='high-entropy-ops-token'

export BL_CONTROL_PRINCIPALS_JSON='[
  {
    "id":"tenant-a-app",
    "tenantId":"tenant-a",
    "tokenEnv":"TENANT_A_API_TOKEN",
    "scopes":["task:submit"]
  },
  {
    "id":"ops-read",
    "tenantId":"*",
    "tokenEnv":"OPS_READ_TOKEN",
    "scopes":["provider:read","runtime:read","ledger:read","audit:read"]
  }
]'
```

The JSON references secret environment-variable names; bearer values are not embedded in the principal definition.

Current scopes:

```text
task:submit
provider:read
provider:admin
provider:heartbeat
route:read
runtime:read
runtime:operate
runtime:execute
ledger:read
audit:read
search:read
search:write
```

Unknown scopes fail startup. Tenant-specific principals currently receive only `task:submit`; global provider/runtime/audit/search scopes require `tenantId="*"`.

A tenant principal submitting a task without `tenantId` is bound to its own tenant. Attempting another tenant returns `TENANT_SCOPE_VIOLATION` / HTTP 403 before enqueue.

See `docs/CONTROL_AUTH.md`.

## Public reads

Read endpoints are private by default in v0.9. To intentionally expose a supported read surface:

```bash
export BL_PUBLIC_READ_SCOPES='search:read'
```

Allowed public scopes are only:

```text
provider:read
route:read
search:read
```

Mutation/operation scopes cannot be made public using this setting.

## Shared rate limiting

With PostgreSQL state, v0.9 defaults to shared rate limiting. Scope keys are SHA-256 fingerprints derived from principal/address plus route group.

Reference route costs:

```text
read            1
search-read     1
heartbeat-self  1
task-submit     2
search-write    3
provider-admin  4
execution       5
```

If the shared limiter backend fails, requests fail closed with `RATE_LIMIT_BACKEND_UNAVAILABLE` / HTTP 503 rather than bypassing quota.

Worker self-heartbeat uses a cheap local/IP pre-auth limiter first. Only after a valid provider HMAC is verified does it consume the shared provider-scoped bucket. This avoids attacker-created PostgreSQL buckets from forged provider IDs while keeping post-auth worker quotas independent behind shared NAT.

See `docs/SHARED_RATE_LIMIT.md`.

## Provider authority and liveness

Provider authority comes from the grant. Runtime telemetry and heartbeat state are separate mutable observations.

A provider can require direct self-heartbeat:

```json
{
  "liveness": {
    "heartbeatRequired": true,
    "heartbeatTtlMs": 60000,
    "heartbeatAuth": {
      "mode": "hmac-env",
      "secretEnv": "PARTNER_A_HEARTBEAT_SECRET"
    }
  }
}
```

Worker environment example:

```bash
export BL_PROVIDER_ID='partner-a-worker-1'
export BL_HEARTBEAT_URL='https://control.example.com/providers/heartbeat/self'
export BL_HEARTBEAT_SECRET_ENV='PARTNER_A_HEARTBEAT_SECRET'
export PARTNER_A_HEARTBEAT_SECRET='provider-scoped-secret'
export BL_HEARTBEAT_INTERVAL_MS='20000'
```

Workers never need `BL_CONTROL_TOKEN` to report liveness. Heartbeat cannot add capabilities, widen data classes, raise quotas, raise trust or undo revocation.

See `docs/PROVIDER_PROTOCOL.md`, `docs/PROVIDER_REGISTRY.md`, and `docs/WORKER_HEARTBEAT.md`.

## Provider registry scale

PostgreSQL assigns a monotonic `change_seq` to every provider row mutation. Coordinators bootstrap one provider snapshot, then read bounded indexed deltas.

Authority-sensitive routing fails closed with `PROVIDER_SYNC_BACKLOG` / HTTP 503 if the configured sync budget cannot catch up. Heartbeat/grant expiry is also enforced locally with sequence-tagged expiry events even when no database mutation happens.

CI has exercised 10,000 providers and 10 changed rows with one snapshot query and one delta query, producing a structural 1,000x reduction in rows read on the steady-state update. Wall-clock measurements are observational, not universal latency guarantees.

See `docs/REGISTRY_SCALE.md`.

## Durability and restore

PostgreSQL stores queue, result cache, shared rate buckets, budget reservations, contribution ledger, audit chain, provider authority/liveness, heartbeat nonces and provider change cursor.

CI performs:

```text
seed deterministic state
-> pg_dump
-> restore into a separate PostgreSQL database
-> verify schema + hash chains + revocation + queue + budget + nonce + rate bucket + change cursor
```

This validates logical dump/restore invariants under PostgreSQL 16. It does not mean a production PITR/WAL policy has been configured or exercised.

See `docs/RESTORE_DRILL.md`, `docs/POSTGRES.md`, and `docs/DURABILITY.md`.

## SQLite lane

`BL_STATE_DB` remains available for a single coordinator host:

```bash
export BL_STATE_DB='/data/federation.db'
```

SQLite is a restart-survival lane, not a horizontal database.

## Repository governance blocker

The GitHub API has reported `main` as unprotected, required status checks off and no repository ruleset. The connected integration can verify but cannot administratively enable those controls in this session.

This remains tracked in Issue #48 and `docs/BRANCH_PROTECTION.md`. CI discipline must not be described as server-side enforcement.

## Production boundary

No live production PostgreSQL cluster or worker fleet is implied by repository code or CI. Production still requires actual infrastructure and credentials, verified TLS, least-privilege roles, region/data-residency approval, backup/PITR configuration, production-like recovery testing, edge/network abuse controls, observability, ownership and server-side branch protection.

The project does not use GitHub Actions, public endpoints, browser visitors, free tiers or third-party machines as a covert compute farm. A resource becomes a node only through an explicit revocable grant.

Further documentation:

- `docs/RESOURCE_SOVEREIGNTY.md`
- `docs/PROVIDER_PROTOCOL.md`
- `docs/PROVIDER_REGISTRY.md`
- `docs/WORKER_HEARTBEAT.md`
- `docs/REGISTRY_SCALE.md`
- `docs/CONTROL_AUTH.md`
- `docs/SHARED_RATE_LIMIT.md`
- `docs/RESTORE_DRILL.md`
- `docs/BRANCH_PROTECTION.md`
- `docs/DEPLOY.md`
- `docs/FAILURE_SEMANTICS.md`
- `docs/NETWORK_SECURITY.md`
- `docs/DURABILITY.md`
- `docs/POSTGRES.md`
