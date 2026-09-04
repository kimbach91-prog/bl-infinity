# Shared Persistent Search — v0.10

BL Compute Federation v0.10 separates canonical search state from the process that ranks a query.

## Model

```text
PostgreSQL canonical corpus
        |
        | snapshot once + monotonic deltas
        v
HybridSearchFabric materialized in each coordinator
        |
        v
query ranking
```

PostgreSQL is the durable source of document state, deletion tombstones and a monotonic search change cursor. Each coordinator keeps a local materialized `HybridSearchFabric` for fast in-process ranking.

This preserves the existing lexical + semantic-lite + graph ranking behavior while making indexed content persistent and convergent across coordinators.

## Canonical relation

`federation_search_documents` stores:

- document ID;
- canonical JSON document;
- content/state hash;
- tenant ID;
- data class (`public`, `internal`, `private`);
- status (`active`, `deleted`);
- timestamps;
- monotonic `change_seq`.

The database trigger assigns a new `change_seq` to every real INSERT/UPDATE.

Deletion is a tombstone, not a physical delete:

```text
active -> deleted + deleted_at + new change_seq
```

That lets a coordinator which was offline learn that an old local document must be removed. A fresh coordinator bootstrap indexes only active rows, so a tombstoned document cannot reappear merely because the process restarted.

## Write idempotency

Single-document `put()` and batch `putMany()` compare the canonical incoming state to the stored active state.

An identical retry is write-free:

```text
same document state -> no UPDATE -> no trigger -> no fake change_seq
```

`putMany()` supports up to 1000 documents in one SQL statement using `jsonb_to_recordset`. `ON CONFLICT ... DO UPDATE ... WHERE` updates only rows whose canonical state actually changed.

Duplicate IDs inside one request batch are rejected rather than making update order implicit.

## Delta synchronization

A coordinator starts with one authoritative snapshot and records cursor `C`.

Steady-state synchronization is:

```sql
SELECT *
FROM federation_search_documents
WHERE change_seq > C
ORDER BY change_seq
LIMIT ...;
```

`SearchFabricSynchronizer` applies:

```text
active row   -> add/update local HybridSearchFabric
deleted row  -> remove local document
```

Synchronization is bounded by:

```bash
BL_SEARCH_SYNC_BATCH_SIZE=500
BL_SEARCH_SYNC_MAX_BATCHES=20
```

If a query reaches the end of its bounded synchronization budget while more deltas remain, the query fails closed:

```text
SEARCH_SYNC_BACKLOG -> HTTP 503
```

The runtime does not knowingly answer from a local search materialization that is behind a known deletion/update backlog.

## Data-class policy

Shared search storage has its own allowed-class gate:

```bash
BL_SEARCH_ALLOWED_DATA_CLASSES='public,internal'
```

A document outside the configured classes is rejected with `SEARCH_DATA_CLASS_REJECTED` before it reaches the canonical corpus.

In a PostgreSQL deployment, the default search storage classes inherit the shared-state data-class policy unless explicitly narrowed.

## Public search privacy

If `search:read` is exposed through `BL_PUBLIC_READ_SCOPES`, an anonymous/public query is forced to:

```text
allowedDataClasses = [public]
```

Caller-supplied search options cannot widen this.

Classification filtering occurs before all ranking signals:

- BM25 document frequency is computed only over visible documents;
- semantic-lite candidates are only visible documents;
- graph seed IDs outside the visible corpus are ignored;
- graph edges only boost visible targets.

Therefore an internal/private document is not merely removed from the final result list; it is also prevented from influencing public ranking scores through lexical statistics or graph boost.

Public result objects do not expose `tenantId` or `dataClass`, and public `/health` search stats do not expose per-class counts. Protected `/runtime/status` may expose detailed class counts to an authorized global operator.

## Search authorization boundary

v0.10 does **not** claim tenant-scoped search authorization. `search:read` and `search:write` remain global-only control scopes and require `tenantId=*` in the v0.9 principal model.

The corpus stores `tenantId` and the search engine can filter by tenant as a technical primitive, but that is not permission to expose tenant-specific search before an end-to-end tenant authorization model is defined and tested.

## Multi-coordinator convergence

CI starts multiple real control-plane processes against one PostgreSQL database and verifies:

```text
index on coordinator A -> query on B sees it
delete/tombstone on A  -> query on B removes it
fresh coordinator C    -> deleted document stays deleted
```

The same test verifies public vs privileged data-class visibility.

## Restore semantics

The PostgreSQL dump/restore drill includes:

- one active search document;
- one deleted/tombstoned search document;
- the search change sequence.

After `pg_restore`, the verifier requires:

```text
active document remains searchable
tombstone remains deleted
fresh materialization does not resurrect tombstone
new search mutation receives a cursor greater than restored cursor
```

This extends the existing restore invariants for provider revocation, queue, budget, rate bucket, audit and ledger state.

## Rollback

Shared search is the default when PostgreSQL state is present. An application-level rollback is available:

```bash
BL_SEARCH_MODE=memory
```

This leaves the additive PostgreSQL corpus untouched while returning to process-local search behavior.

Memory mode is a degraded convergence mode:

- index state is process-local;
- coordinator restart loses its local corpus;
- coordinator A writes are not automatically visible to B.

Do not describe memory rollback as equivalent persistence semantics.

## Current scale boundary

v0.10 solves persistence and multi-coordinator convergence. It is deliberately **not** described as an Internet-scale search engine.

Current remaining scale limits include:

- startup materializes the full active corpus into each coordinator's RAM;
- local BM25/hash-vector/graph structures are rebuilt from that materialization;
- each query scores the caller-visible local corpus rather than first retrieving a small candidate set from a sharded lexical/ANN index;
- the semantic vector is a deterministic lightweight hashed-token vector, not a production embedding model.

A future layer can add sharded lexical retrieval, ANN/vector search and candidate routing behind the same canonical document/provenance contract. That should be benchmarked independently rather than being implied by v0.10.

## Safety invariant

```text
search persistence != authority
search visibility != provider authority
public corpus != entire corpus
```

A shared search backend never grants compute permission or data egress permission. Provider grants, control scopes and data classification remain separate gates.
