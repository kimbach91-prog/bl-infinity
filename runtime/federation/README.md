# BL Compute Federation v0.8

A consent-aware control plane for combining small amounts of authorized compute across owner devices, cloud quotas, partner grants and BYOC nodes without treating reachable infrastructure as free infrastructure.

## Core invariant

`reachable != authorized`

A provider is usable only when its grant, capability, data policy, quota, concurrency, liveness and task policy all pass. Private data fails closed unless it remains at the declared data location or the grant explicitly permits private egress.

## v0.8 runtime

- policy-aware provider routing
- queue-to-executor orchestration with global, tenant and provider budget reservations
- circuit breaker isolation for unhealthy providers
- opt-in, tenant-scoped result caching
- contribution/accounting ledger separating measured from reported usage
- SSRF-oriented worker endpoint policy with private/link-local blocking by default
- side-effect retry gate and provider side-effect authorization
- constant-time control token checks and bounded in-memory rate limiting
- Ed25519-signed provider grants and trust store
- shared PostgreSQL provider registry with grant hash, revision, status, revocation and heartbeat state
- signed liveness policy with bounded heartbeat TTL
- provider-scoped worker self-heartbeat HMAC that does not use the control token
- federation-wide heartbeat replay defense through PostgreSQL provider-scoped nonce uniqueness
- mutable telemetry separated from immutable signed authority
- neutral trust/latency defaults for dynamically registered providers; self-reported telemetry cannot raise routing trust
- monotonic PostgreSQL provider `change_seq` with database trigger coverage for every provider mutation
- one authoritative provider snapshot at bootstrap followed by indexed bounded delta synchronization
- single-query snapshot/delta hydration; no per-provider N+1 database reads
- local expiry heap for heartbeat/grant expiry even when no row mutation occurs
- fail-closed `PROVIDER_SYNC_BACKLOG` when bounded delta work cannot catch up before routing
- write-free identical bootstrap registration so coordinator restart does not emit fake provider deltas
- rollback switch to v0.7-style full synchronization with `BL_PROVIDER_SYNC_MODE=full`
- separate HMAC worker execution protocol with timestamp, nonce and replay protection
- explicit capability allowlist; no shell/eval/arbitrary-code endpoint
- idempotent worker result replay for safe retries
- fallback executor with telemetry feedback and provenance
- idempotent lease queue with heartbeat recovery and dead-lettering
- hash-chained audit log
- hybrid in-memory search reference: lexical + semantic-lite + relation graph + trust/freshness
- local and HTTPS-worker adapters
- auth modes for HMAC env, bearer env, Cloudflare Access service tokens, and GCP metadata OIDC
- Docker-ready coordinator and worker
- optional SQLite WAL durable state for a single coordinator host
- executable PostgreSQL shared state for queue/cache/budget/ledger/audit/provider registry
- concurrent PostgreSQL claims through `FOR UPDATE SKIP LOCKED`
- transaction-scoped serialization for budget and hash-chain heads
- PostgreSQL base + provider-delta schema readiness gates
- shared-state data-class gate: PostgreSQL defaults to `public` only
- CI 10k-provider delta row-reduction benchmark
- CI PostgreSQL 16 dump -> restore -> invariant verification drill

## Run

```bash
cd runtime/federation
npm install --no-audit --no-fund
npm test
export BL_CONTROL_TOKEN='replace-with-a-long-random-token'
npm start
```

For durable single-host state:

```bash
export BL_STATE_DB='/data/federation.db'
export BL_BUDGET_JSON='{"totalUsd":10}'
npm start
```

For shared PostgreSQL state after a controlled schema migration:

```bash
export BL_POSTGRES_URL='postgresql://runtime_user:REDACTED@db.example.internal:5432/blcf'
export BL_POSTGRES_POOL_MAX='10'
export BL_POSTGRES_ALLOWED_DATA_CLASSES='public'
export BL_PROVIDER_SYNC_MODE='delta'
export BL_PROVIDER_SYNC_BATCH_SIZE='500'
export BL_PROVIDER_SYNC_MAX_BATCHES='20'
export BL_BUDGET_JSON='{"totalUsd":10}'
npm start
```

`BL_POSTGRES_AUTO_MIGRATE` is disabled unless explicitly set to `true`. Production should normally migrate with a separate schema-owner credential, then run coordinators with restricted runtime credentials.

For an application rollback that preserves the additive v0.8 schema:

```bash
export BL_PROVIDER_SYNC_MODE='full'
```

This restores full-provider synchronization while the change cursor/trigger remain available for diagnosis.

Worker execution transport:

```bash
export BL_FEDERATION_SHARED_SECRET='replace-with-a-long-random-execution-secret'
npm run worker
```

For direct worker self-heartbeat, configure a **separate** provider-scoped heartbeat secret:

```bash
export BL_PROVIDER_ID='partner-a-worker-1'
export BL_HEARTBEAT_URL='https://control.example.com/providers/heartbeat/self'
export BL_HEARTBEAT_SECRET_ENV='PARTNER_A_HEARTBEAT_SECRET'
export PARTNER_A_HEARTBEAT_SECRET='replace-with-a-provider-scoped-secret'
export BL_HEARTBEAT_INTERVAL_MS='20000'
npm run worker
```

The signed provider grant must reference the same secret environment-variable name in `liveness.heartbeatAuth.secretEnv`. Workers are not given `BL_CONTROL_TOKEN`.

The control plane binds to `127.0.0.1` by default. Execution and operator mutation endpoints remain disabled unless `BL_CONTROL_TOKEN` is set. The self-heartbeat endpoint is instead protected by the provider-scoped HMAC grant and durable replay defense.

## Provider authority and liveness

Provider authority is carried by the signed grant. Runtime state such as telemetry, stored status and heartbeat timestamps is deliberately outside the signature so coordinators can update observations without rewriting the grant.

A provider may opt into signed heartbeat enforcement and direct worker HMAC heartbeat:

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

When `heartbeatRequired=true`, the provider remains unusable until a fresh heartbeat exists and becomes unusable again after the signed TTL expires. A heartbeat proves only liveness. It cannot add capabilities, widen allowed data classes, raise cost/concurrency ceilings, change the signed grant or self-promote routing trust.

Dynamically registered providers begin with neutral routing telemetry. Values such as trust or latency supplied outside the signed authority are not allowed to self-promote the node. Trusted coordinator measurements may update runtime telemetry after real executions.

Shared provider state supports these authenticated transitions:

- `POST /providers/register`: operator add a grant; conflicting authority for the same ID is rejected.
- `POST /providers/replace`: operator explicitly install a new verified grant revision.
- `POST /providers/revoke`: operator terminally revoke the current grant revision.
- `POST /providers/status`: operator disable/enable for non-revoked grants.
- `POST /providers/heartbeat`: trusted operator/coordinator liveness update using `BL_CONTROL_TOKEN`.
- `POST /providers/heartbeat/self`: worker liveness update using the provider-scoped heartbeat HMAC, with no control token.

The self-heartbeat signature binds `providerId.timestamp.nonce.rawBody`. Only a valid signature consumes the nonce. Nonces are stored in PostgreSQL under the unique key `(provider_id, nonce)`, so replay through a second coordinator is rejected. Expired or revoked grants cannot self-heartbeat.

A revoked grant cannot be revived by heartbeat or by re-submitting the same grant. Re-granting requires an explicit replacement with a newly verified authority revision.

## Provider registry delta synchronization

PostgreSQL v0.8 uses `federation_providers.change_seq` as a monotonic cursor. The database trigger assigns a new sequence to every provider row mutation, so a future code path cannot silently mutate authority/liveness without publishing a delta.

At startup, a coordinator takes one full provider snapshot and records the maximum cursor. Steady-state route/execute/orchestration requests then read only rows newer than that cursor.

The first candidate N+1 hydration pattern was removed before default wiring. Snapshot and delta readers now reconstruct providers directly from the rows returned by a single query. CI compares this reconstruction to canonical `PostgresProviderStore.get()` semantics.

Synchronization is bounded. If changes remain after the configured batch budget, authority-sensitive requests receive `PROVIDER_SYNC_BACKLOG` / HTTP 503. The coordinator does not route on a registry it knows is behind.

Heartbeat and grant expiry do not require a database mutation: a local sequence-tagged expiry heap disables stale nodes as time passes. A stale expiry event cannot disable a newer provider revision.

See `docs/REGISTRY_SCALE.md` for migration, rollback and monitoring details.

## Orchestration API

With the control token configured: `POST /tasks/submit` enqueues work, `POST /orchestrate/run-once` performs one bounded orchestration step, `GET /runtime/status` exposes queue/budget/cache/circuit/provider-sync state, and `GET /ledger` exposes aggregate contribution accounting. `POST /execute` remains available for direct controlled execution.

Cache is opt-in. Public tasks use `cachePolicy=public`; internal tasks use `cachePolicy=tenant`; private tasks require `cachePolicy=private-ok`. Side-effect tasks are never cached.

Side-effect tasks require `authorization.allowSideEffects=true` on the provider. Unless a side-effect task carries an explicit idempotency key and declares retry safety, orchestration collapses its maximum attempts to one. If a provider succeeds but budget/accounting settlement fails, the task is dead-lettered rather than retried because the external effect may already exist.

## Shared-state data policy

PostgreSQL persists task JSON. For that reason the coordinator defaults `BL_POSTGRES_ALLOWED_DATA_CLASSES` to `public`. Enabling `internal` or `private` is an explicit data-governance decision and should happen only after region, encryption, retention, contract and access-control requirements are approved.

Example after approval:

```bash
export BL_POSTGRES_ALLOWED_DATA_CLASSES='public,internal'
```

The main orchestrator rejects a disallowed class before enqueue. Low-level state APIs are infrastructure primitives and must not be exposed directly to untrusted callers.

## Signed provider grants

```bash
npm run keys -- partner-a
node scripts/sign-provider-manifest.mjs provider.json partner-a.private.pem partner-a signed-provider.json
```

Never commit private keys, database credentials, control tokens, execution secrets or heartbeat secrets.

## Durability, restore and horizontal coordination

Without `BL_STATE_DB` or `BL_POSTGRES_URL`, queue, search index, cache, rate limiter, ledger, audit and provider registry remain reference in-memory/single-process components. Direct self-heartbeat is not available without the shared PostgreSQL provider store because replay protection must be federation-wide.

With `BL_STATE_DB`, queue/cache/budget/ledger/audit use SQLite WAL. SQLite is for one coordinator host and restart survival; it is not a horizontal cluster.

With `BL_POSTGRES_URL`, queue/cache/budget/ledger/audit/provider authority/heartbeat nonces/change cursor use the transactional PostgreSQL backend. Multiple coordinators can share pending work and converge on the same provider grants/revocations/liveness. Queue claims use `FOR UPDATE SKIP LOCKED`; budgets and hash-chain heads use transaction-scoped advisory locks.

CI performs a deterministic PostgreSQL 16 logical backup/restore drill using `pg_dump` and `pg_restore` into a separate database. The restored database must preserve audit/ledger hash chains, provider revocation, queue state, committed budget accounting, heartbeat nonce state and the ability for `change_seq` to continue monotonically.

This logical restore drill is not a claim that production PITR is configured. Production PITR still requires actual managed-service/WAL retention configuration and a recovery exercise against production-like infrastructure.

Search and the HTTP rate limiter are still process-local in v0.8. They are not yet a distributed search/cache/rate-limit cluster.

## Repository governance gap

The GitHub API currently reports `main` as unprotected, with required status checks off and no repository ruleset. The connected GitHub integration in this session does not expose an administrative write action to enable protection. This is an explicit unresolved infrastructure control, documented in `docs/BRANCH_PROTECTION.md`; CI discipline must not be mistaken for server-side enforcement.

## Production boundary

CI tests the PostgreSQL adapter against an isolated PostgreSQL 16 service, including concurrent claims, budget contention, audit/ledger appenders, rollback sequence gaps, cross-pool persistence, shared provider liveness/revocation, direct heartbeat HMAC verification, cross-coordinator replay rejection, provider delta convergence, a 10k-provider row-reduction benchmark and a logical dump/restore invariant drill.

This does not mean a live production database or worker fleet has been provisioned.

Production still requires actual infrastructure and credentials, verified TLS, least-privilege database roles, region/data-residency approval, backup/PITR configuration, production-like restore testing, monitoring, repository branch protection and ownership. Do not work around TLS certificate failures with permissive certificate verification.

Vercel routing is stateless and intentionally does not pretend to be a durable queue/search cluster. Do not depend on serverless local filesystem persistence.

Endpoint DNS/IP checks reduce SSRF exposure but are not a substitute for production egress firewalling, DNS controls and private service networking. Explicit `transport.allowPrivateNetwork=true` should be used only for deliberately provisioned private workers.

The project does not use GitHub Actions, public endpoints, free tiers, browsers, visitor devices or third-party machines as a covert compute farm. A resource becomes a node only through an explicit revocable grant.

See `docs/RESOURCE_SOVEREIGNTY.md`, `docs/PROVIDER_PROTOCOL.md`, `docs/PROVIDER_REGISTRY.md`, `docs/WORKER_HEARTBEAT.md`, `docs/REGISTRY_SCALE.md`, `docs/RESTORE_DRILL.md`, `docs/BRANCH_PROTECTION.md`, `docs/DEPLOY.md`, `docs/FAILURE_SEMANTICS.md`, `docs/NETWORK_SECURITY.md`, `docs/DURABILITY.md`, and `docs/POSTGRES.md`.
