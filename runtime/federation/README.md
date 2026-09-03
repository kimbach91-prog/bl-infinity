# BL Compute Federation v0.4

A consent-aware control plane for combining small amounts of authorized compute across owner devices, cloud quotas, partner grants and BYOC nodes without treating reachable infrastructure as free infrastructure.

## Core invariant

`reachable != authorized`

A provider is usable only when its grant, capability, data policy, quota, concurrency and task policy all pass. Private data fails closed unless it remains at the declared data location or the grant explicitly permits private egress.

## v0.4 runtime

- policy-aware provider routing
- queue-to-executor orchestration with budget reservations
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
- optional SQLite WAL durable state for queue/cache/budget/ledger/audit restart survival
- PostgreSQL horizontal-state schema and SKIP LOCKED claim contract

## Run

```bash
cd runtime/federation
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

Worker:

```bash
export BL_FEDERATION_SHARED_SECRET='replace-with-a-long-random-secret'
npm run worker
```

The control plane binds to `127.0.0.1` by default. Execution and mutation endpoints remain disabled unless `BL_CONTROL_TOKEN` is set.

## Orchestration API

With the control token configured: `POST /tasks/submit` enqueues work, `POST /orchestrate/run-once` performs one bounded orchestration step, `GET /runtime/status` exposes queue/budget/cache/circuit state, and `GET /ledger` exposes aggregate contribution accounting. `POST /execute` remains available for direct controlled execution.

Cache is opt-in. Public tasks use `cachePolicy=public`; internal tasks use `cachePolicy=tenant`; private tasks require `cachePolicy=private-ok`. Side-effect tasks are never cached.

Side-effect tasks require `authorization.allowSideEffects=true` on the provider. Unless a side-effect task carries an explicit idempotency key and declares retry safety, orchestration collapses its maximum attempts to one.

## Signed provider grants

```bash
npm run keys -- partner-a
node scripts/sign-provider-manifest.mjs provider.json partner-a.private.pem partner-a signed-provider.json
```

Never commit private keys or worker shared secrets.

## Production boundary

Without `BL_STATE_DB`, queue, search index, cache, rate limiter, ledger and audit remain reference in-memory/single-process components. With `BL_STATE_DB`, queue/cache/budget/ledger/audit use the SQLite durable lane; search and rate limiting remain process-local. SQLite is for a single coordinator host, not a substitute for a shared horizontal database.

Horizontal production must replace stateful components with a shared transactional backend while retaining authorization, data-locality, idempotency, budgeting and provenance invariants. `storage/postgres/schema.sql` and `storage/postgres/claim.sql` define the current Postgres state/claim contract, but a live Postgres deployment still requires actual infrastructure and credentials.

Vercel routing is stateless and intentionally does not pretend to be a durable queue/search cluster. Do not depend on serverless local filesystem persistence.

Endpoint DNS/IP checks reduce SSRF exposure but are not a substitute for production egress firewalling, DNS controls and private service networking. Explicit `transport.allowPrivateNetwork=true` should be used only for deliberately provisioned private workers.

The project does not use GitHub Actions, public endpoints, free tiers, browsers, visitor devices or third-party machines as a covert compute farm. A resource becomes a node only through an explicit revocable grant.

See `docs/RESOURCE_SOVEREIGNTY.md`, `docs/PROVIDER_PROTOCOL.md`, `docs/DEPLOY.md`, `docs/FAILURE_SEMANTICS.md`, `docs/NETWORK_SECURITY.md`, and `docs/DURABILITY.md`.
