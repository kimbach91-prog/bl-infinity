# Provider Registry Delta Synchronization — v0.8

BL Compute Federation v0.7 made provider authority and liveness shared in PostgreSQL. v0.8 replaces repeated full-provider refreshes on the request path with a monotonic change cursor, bounded delta application and local time-expiry enforcement.

## Runtime shape

The default PostgreSQL path is now:

```text
startup -> authoritative provider snapshot -> cursor C
request -> indexed rows where change_seq > C -> apply deltas -> route
```

The rollback path remains available:

```bash
export BL_PROVIDER_SYNC_MODE=full
```

`full` restores the v0.7 full-table synchronization behavior without requiring an immediate schema rollback.

## Authority invariant

Delta synchronization changes **how** coordinators learn shared provider state. It does not change what grants authority.

```text
reachable != authorized
heartbeat != authority
telemetry != authority
change_seq != authority
```

The signed grant plus shared revocation/status/liveness state remain canonical. The local `ProviderRegistry` is only a routing projection.

## Change cursor

The v0.8 base schema and upgrade migration create:

- sequence `federation_provider_change_seq`;
- non-null `federation_providers.change_seq`;
- `BEFORE INSERT OR UPDATE` trigger `bl_cf_provider_change_seq_trigger`;
- index `federation_providers_change_seq_idx`.

Every provider mutation therefore receives a new sequence value at the database boundary, including register, replacement, heartbeat, measured telemetry, status and revoke paths.

Sequence values are monotonic but may contain gaps. Gaplessness is not an invariant.

## Single-query hydration

The first candidate implementation selected provider IDs and then called `store.get()` per row. That was an N+1 database pattern and was rejected before default wiring.

v0.8 now reconstructs all providers directly from the rows returned by the snapshot/delta query:

```text
snapshot: one SELECT -> N current provider rows
steady delta: one indexed SELECT -> only changed provider rows
```

CI includes semantic parity tests against canonical `PostgresProviderStore.get()` and query-count tests so this optimization cannot silently change provider authority/liveness reconstruction.

## Bounded synchronizer

`ProviderRegistrySynchronizer` maintains one cursor per coordinator.

Configuration:

```bash
export BL_PROVIDER_SYNC_MODE=delta
export BL_PROVIDER_SYNC_BATCH_SIZE=500
export BL_PROVIDER_SYNC_MAX_BATCHES=20
```

`BL_PROVIDER_SYNC_BATCH_SIZE` is capped at 5000. `BL_PROVIDER_SYNC_MAX_BATCHES` bounds work performed by one synchronization call.

### Fail-closed backlog

A bounded synchronizer must not become permission to route stale security state. Therefore route, direct execution and orchestration fail closed if the bounded sync budget ends while `hasMore=true`:

```text
PROVIDER_SYNC_BACKLOG -> HTTP 503
```

Subsequent requests continue advancing the cursor. Routing resumes only after the coordinator catches up.

Read-only provider/status surfaces may expose partial synchronization diagnostics while catching up, but authority-sensitive routing does not proceed on a known backlog.

## Expiry without database mutations

Heartbeat expiry and grant expiry are caused by time passing. They may occur even when no provider row changes.

The synchronizer therefore keeps a local min-heap of known expiry deadlines. Every expiry entry carries the provider's `changeSeq`. A stale heap event cannot disable a newer heartbeat/re-grant revision because its sequence no longer matches the latest provider sequence.

```text
no database delta != liveness remains valid forever
```

This keeps time-based liveness fail-closed without full-table polling.

## Idempotent bootstrap

An identical provider grant already present in PostgreSQL is now a write-free registration when its effective signature metadata is unchanged. Coordinator restart/bootstrap therefore does not create fake `change_seq` churn merely by re-reading the same grant.

Authority changes, signature changes, real telemetry changes, heartbeats, status transitions and revocations still produce deltas.

## 10k-provider CI benchmark

The integration suite seeds 10,000 providers into PostgreSQL 16, takes one initial snapshot, modifies 10 providers, then reads the steady-state delta.

The benchmark gates structural work rather than unstable wall-clock thresholds:

```text
initial snapshot rows = 10,000
changed rows          = 10
snapshot queries      = 1
delta queries         = 1
row reduction         >= 1,000x
```

Wall-clock measurements are emitted for observation but do not decide pass/fail because shared CI timing is noisy.

## Schema readiness

When delta mode is enabled, startup checks for:

- the provider change sequence;
- non-null `change_seq` column;
- change trigger;
- change-seq index.

Missing objects fail startup with `POSTGRES_PROVIDER_DELTA_SCHEMA_MISSING`. The runtime does not silently pretend delta synchronization is active.

## Migration and rollback

For controlled upgrades, migration `storage/postgres/migrations/008_provider_change_seq.sql` remains idempotent and additive.

Apply with migration authority, not the restricted runtime credential:

```bash
psql "$MIGRATION_DATABASE_URL" \
  -v ON_ERROR_STOP=1 \
  -f storage/postgres/migrations/008_provider_change_seq.sql
```

Operational rollback should first switch the application:

```bash
export BL_PROVIDER_SYNC_MODE=full
```

Then verify provider convergence. Do not drop the sequence/column/trigger during an incident unless a separate schema rollback is actually necessary.

## Metrics

Monitor at least:

- provider count;
- changes per second;
- rows read per sync;
- queries per sync;
- number of batches;
- `hasMore` / backlog failures;
- coordinator cursor;
- heartbeat/grant expiry disables;
- revocation propagation latency;
- delta vs full-mode database load;
- time until every coordinator stops routing a revoked provider.

The security metric is convergence of authority state, not raw cursor arithmetic.

## Current boundary

v0.8 is tested against PostgreSQL 16 in CI and is wired into the reference control plane. It still does not imply that a live production database or worker fleet exists. Production activation requires controlled schema migration, verified TLS, least-privilege roles, restore testing, monitoring and an explicit rollback plan.
