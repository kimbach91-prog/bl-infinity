# PostgreSQL production lane

BL Compute Federation v0.5 can use PostgreSQL as shared transactional state for multiple coordinators. This is a state backend, not a source of compute authority: every provider still needs an explicit revocable grant and must pass capability, data, cost, locality and concurrency policy.

## Required environment

```bash
export BL_POSTGRES_URL='postgresql://runtime_user:REDACTED@db.example.internal:5432/blcf'
export BL_POSTGRES_POOL_MAX='10'
export BL_POSTGRES_ALLOWED_DATA_CLASSES='public'
export BL_CONTROL_TOKEN='replace-with-a-long-random-token'
```

`BL_POSTGRES_ALLOWED_DATA_CLASSES` defaults to `public`. Add `internal` or `private` only after the database region, contract, encryption, access controls, retention policy and data-residency requirements are explicitly approved. The queue stores task JSON, so enabling a class means payloads in that class may be persisted in PostgreSQL.

Do not print or commit `BL_POSTGRES_URL`. Do not embed database credentials in provider manifests.

## Migration

`BL_POSTGRES_AUTO_MIGRATE` is off by default. Production should normally separate migration authority from runtime authority.

A controlled one-shot migration can temporarily use a schema-owner credential:

```bash
BL_POSTGRES_URL="$MIGRATION_DATABASE_URL" \
BL_POSTGRES_AUTO_MIGRATE=true \
BL_POSTGRES_ALLOWED_DATA_CLASSES=public \
BL_CONTROL_TOKEN="$CONTROL_TOKEN" \
node dev-server.mjs
```

Stop that process after the schema has been applied, then run normal coordinators with a restricted runtime role and `BL_POSTGRES_AUTO_MIGRATE=false`. When auto-migrate is disabled, startup runs a readiness check and fails if any required federation relation is missing.

## Least privilege

Use a separate schema owner for DDL. A runtime role needs only the database/schema access required for federation tables and sequences. A typical grant shape is:

```sql
GRANT CONNECT ON DATABASE blcf TO blcf_runtime;
GRANT USAGE ON SCHEMA public TO blcf_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO blcf_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO blcf_runtime;
```

Scope these grants more tightly to the federation tables/sequences when the database contains unrelated application data. The runtime does not need superuser, replication, role-management or schema-creation privileges.

## TLS and networking

Use verified TLS supported by the managed PostgreSQL provider and restrict database ingress to the coordinator network. Do not solve certificate errors by setting `rejectUnauthorized=false`. Prefer private service networking or tightly scoped firewall rules rather than a public database endpoint.

The federation network policy protecting worker endpoints is separate from database network security. PostgreSQL access must be protected at the infrastructure layer as well.

## Concurrency model

v0.5 uses:

- `FOR UPDATE SKIP LOCKED` so concurrent coordinators claim different pending jobs;
- transaction-scoped advisory locks for budget reservation/settlement;
- separate transaction-scoped advisory locks for audit and contribution-ledger hash heads;
- database uniqueness on `(tenant_id, idempotency_key)`;
- normal row locks for lease completion/failure and reservation settlement.

The budget lock is intentionally conservative: correctness is preferred over maximum throughput at this stage. It can later be sharded by budget namespace after contention is measured.

PostgreSQL sequences can have gaps after rollback. Audit/ledger verification therefore requires strictly increasing sequence numbers plus a valid `prevHash`/hash chain; it does not require gapless integers.

## Backups and failover

A database becoming durable does not make it immortal. Production should configure managed backups, point-in-time recovery, retention, restore testing, monitoring and a documented failover procedure. Test restoration using a non-production copy before relying on it.

Do not automatically retry a task merely because the database failed after the provider already executed it. v0.4+ treats provider-success plus settlement failure as non-retryable/dead-letter because an external side effect may already have happened.

## Pooling

`BL_POSTGRES_POOL_MAX` defaults to 10 per coordinator. Total database connections are approximately:

```text
coordinators × pool_max
```

Set the value against the real database connection limit. Transaction pooling is compatible with the transaction-scoped advisory locks used here; session-scoped state must not be introduced accidentally.

## Current boundary

CI validates this adapter against an isolated PostgreSQL 16 service. That proves the code path and concurrency invariants, not that a production database has been provisioned. A live environment still requires explicit infrastructure, credentials, region/data-policy approval and operational ownership.
