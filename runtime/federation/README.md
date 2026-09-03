# BL Compute Federation v0.5

A consent-aware control plane for combining small amounts of authorized compute across owner devices, cloud quotas, partner grants and BYOC nodes without treating reachable infrastructure as free infrastructure.

## Core invariant

`reachable != authorized`

A provider is usable only when its grant, capability, data policy, quota, concurrency and task policy all pass. Private data fails closed unless it remains at the declared data location or the grant explicitly permits private egress.

## v0.5 runtime

- policy-aware provider routing
- queue-to-executor orchestration with global, tenant and provider budget reservations
- circuit breaker isolation for unhealthy providers
- opt-in, tenant-scoped result caching
- contribution/accounting ledger separating measured from reported usage
- SSRF-oriented worker endpoint policy with private/link-local blocking by default
- side-effect retry gate and provider side-effect authorization
- constant-time control token checks and bounded in-memory rate limiting
- Ed25519-signed provider grants and trust store
- HMAC worker protocol with timestamp, nonce and replay protection
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
- executable PostgreSQL shared state for queue/cache/budget/ledger/audit
- concurrent PostgreSQL claims through `FOR UPDATE SKIP LOCKED`
- transaction-scoped serialization for budget and hash-chain heads
- PostgreSQL schema readiness gate
- shared-state data-class gate: PostgreSQL defaults to `public` only

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
export BL_BUDGET_JSON='{"totalUsd":10}'
npm start
```

`BL_POSTGRES_AUTO_MIGRATE` is disabled unless explicitly set to `true`. Production should normally migrate with a separate schema-owner credential, then run coordinators with restricted runtime credentials.

Worker:

```bash
export BL_FEDERATION_SHARED_SECRET='replace-with-a-long-random-secret'
npm run worker
```

The control plane binds to `127.0.0.1` by default. Execution and mutation endpoints remain disabled unless `BL_CONTROL_TOKEN` is set.

## Orchestration API

With the control token configured: `POST /tasks/submit` enqueues work, `POST /orchestrate/run-once` performs one bounded orchestration step, `GET /runtime/status` exposes queue/budget/cache/circuit state, and `GET /ledger` exposes aggregate contribution accounting. `POST /execute` remains available for direct controlled execution.

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

Never commit private keys, database credentials or worker shared secrets.

## Durability and horizontal coordination

Without `BL_STATE_DB` or `BL_POSTGRES_URL`, queue, search index, cache, rate limiter, ledger and audit remain reference in-memory/single-process components.

With `BL_STATE_DB`, queue/cache/budget/ledger/audit use SQLite WAL. SQLite is for one coordinator host and restart survival; it is not a horizontal cluster.

With `BL_POSTGRES_URL`, queue/cache/budget/ledger/audit use the transactional PostgreSQL backend. Multiple coordinators can share pending work. Queue claims use `FOR UPDATE SKIP LOCKED`; budgets and hash-chain heads use transaction-scoped advisory locks. PostgreSQL sequence gaps after rollback are valid, so ledger/audit verification checks strictly increasing sequence numbers plus the hash chain rather than requiring gapless integers.

Search and the HTTP rate limiter are still process-local in v0.5. They are not yet a distributed search/cache cluster.

## Production boundary

CI tests the PostgreSQL adapter against an isolated PostgreSQL 16 service, including concurrent claims, concurrent budget contention, concurrent audit/ledger appenders, rollback sequence gaps and cross-pool persistence. This does not mean a live production database has been provisioned.

Production still requires actual infrastructure and credentials, verified TLS, least-privilege database roles, region/data-residency approval, backups/PITR, restore testing, monitoring and ownership. Do not work around TLS certificate failures with permissive certificate verification.

Vercel routing is stateless and intentionally does not pretend to be a durable queue/search cluster. Do not depend on serverless local filesystem persistence.

Endpoint DNS/IP checks reduce SSRF exposure but are not a substitute for production egress firewalling, DNS controls and private service networking. Explicit `transport.allowPrivateNetwork=true` should be used only for deliberately provisioned private workers.

The project does not use GitHub Actions, public endpoints, free tiers, browsers, visitor devices or third-party machines as a covert compute farm. A resource becomes a node only through an explicit revocable grant.

See `docs/RESOURCE_SOVEREIGNTY.md`, `docs/PROVIDER_PROTOCOL.md`, `docs/DEPLOY.md`, `docs/FAILURE_SEMANTICS.md`, `docs/NETWORK_SECURITY.md`, `docs/DURABILITY.md`, and `docs/POSTGRES.md`.
