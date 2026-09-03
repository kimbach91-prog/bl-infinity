# Provider Registry Delta Synchronization — v0.8 candidate

BL Compute Federation v0.7 made provider authority and liveness shared. Its reference control plane still refreshes the shared provider table as a full snapshot before route/execute operations. That is simple and safe at small scale, but it turns registry size into request-path database work.

v0.8 introduces a monotonic provider change cursor and a bounded incremental synchronizer. This document describes the candidate layer before it is wired into the default control plane.

## Goal

Replace repeated work shaped like:

```text
request -> SELECT every provider -> reconstruct every provider -> route
```

with:

```text
startup -> one authoritative snapshot -> cursor C
request -> SELECT providers whose change_seq > C -> apply bounded deltas -> route
```

The canonical provider grant remains PostgreSQL shared state. The in-process registry remains only a routing projection.

## Change cursor

Migration `storage/postgres/migrations/008_provider_change_seq.sql` adds:

- sequence `federation_provider_change_seq`;
- `federation_providers.change_seq`;
- a `BEFORE INSERT OR UPDATE` trigger that assigns a fresh sequence value;
- an index on `change_seq`.

The trigger is deliberate. Provider mutations already exist in several code paths (register, replacement, heartbeat, measured telemetry, status change, revoke). Putting the cursor bump at the database boundary prevents a future mutation path from silently forgetting to publish a change.

Sequence values are monotonic but not required to be gapless. PostgreSQL rollback/sequence semantics already make gaplessness the wrong invariant.

## Delta reader

`PostgresProviderDeltaView` exposes two operations:

```text
snapshot()                -> all current providers + maximum observed cursor
changesSince(cursor, N)   -> at most N provider rows with newer change_seq
```

A provider can change multiple times between synchronizations. Only its latest row matters because the shared registry stores current authority/liveness state, not an event-sourced reconstruction. If the row changes while a delta batch is being hydrated, its newer `change_seq` remains greater than the consumed cursor and will be seen again in a later batch.

## Bounded synchronizer

`ProviderRegistrySynchronizer` maintains one cursor per coordinator. It performs one full snapshot at bootstrap and then bounded batches of deltas.

`maxBatchesPerSync` prevents a continuously changing registry from monopolizing one request indefinitely. If more changes remain, the next synchronization continues from the retained cursor.

This is a fairness bound, not permission to route stale security state indefinitely. Revocation/status changes are still consumed in order, and deployments should choose batch sizes/cadence appropriate to the maximum acceptable propagation delay.

## Expiry without database writes

Heartbeat expiry and grant expiry happen because time passes; they do not necessarily create a new database row update. A pure change cursor would therefore be insufficient.

The synchronizer keeps a local min-heap of known expiry deadlines. Each heap entry is tagged with the provider's `changeSeq`. When time crosses a deadline, the local routing projection is disabled without requiring a database write or a full-table scan.

If a later heartbeat/re-grant creates a newer `changeSeq`, stale heap entries cannot disable the newer revision.

This preserves the fail-closed rule:

```text
no database delta does not mean liveness remains valid forever
```

## Migration

This candidate migration is intentionally separate from the base schema while v0.8 is under evaluation.

Apply with migration authority:

```bash
psql "$MIGRATION_DATABASE_URL" \
  -v ON_ERROR_STOP=1 \
  -f storage/postgres/migrations/008_provider_change_seq.sql
```

Do not let a restricted runtime role silently acquire DDL authority just to enable delta sync.

Before wiring delta sync into production, verify:

```sql
SELECT change_seq, id, status, updated_at
FROM federation_providers
ORDER BY change_seq DESC
LIMIT 20;
```

and ensure the trigger increments `change_seq` on heartbeat, telemetry, status and revoke updates.

## Rollback

The migration is additive. The existing v0.7 full-snapshot path can continue operating even when `change_seq` exists. Therefore application rollback does not require immediately dropping the column, trigger or sequence.

Prefer:

```text
1. roll application back to full-snapshot synchronization;
2. verify provider convergence;
3. retain additive schema until the incident is understood;
4. remove migration objects later only under controlled DDL change.
```

Dropping synchronization metadata during an incident adds unnecessary risk.

## Metrics

Before making delta sync the default, observe:

- provider count;
- changes per second;
- delta rows per synchronization;
- number of batches per synchronization;
- cursor lag (`latest change_seq - coordinator cursor`, interpreted carefully because sequences can have gaps);
- wall-clock age of the oldest unapplied provider update;
- heartbeat-expiry disables performed locally;
- revocation propagation latency across coordinators;
- database time spent in snapshot vs delta queries.

Do not optimize only for cursor arithmetic. The security metric is time until every coordinator stops routing a revoked/stale provider.

## Current boundary

The v0.8 candidate module and migration are tested independently before default-runtime wiring. v0.7's full-snapshot control-plane synchronization remains the active production-shaped reference until the candidate passes CI and integration review.

This is intentional staged evolution: prove the faster synchronization primitive first, then replace the simple path without changing provider authority semantics at the same time.
