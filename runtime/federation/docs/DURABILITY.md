# Durability and Horizontal Scale

v0.4 adds an optional SQLite state backend for a single coordinator host. Set `BL_STATE_DB=/data/federation.db` and mount `/data` on persistent storage. Queue leases, idempotency keys, result cache, budget reservations, contribution ledger and audit chain then survive process restart.

The SQLite backend enables WAL mode, foreign keys and a busy timeout. It is intended for one VM/container host or another deployment where the database file is on a local durable filesystem. It is not the horizontal multi-region backend and should not be placed on an arbitrary network filesystem and treated as a distributed database.

`node:sqlite` is still marked experimental in the Node 22 runtime used by the reference implementation. Pin and test the Node release used in production before relying on it for long-lived deployments.

For multiple coordinators, use a shared transactional database. `storage/postgres/schema.sql` defines the current state contract and `storage/postgres/claim.sql` shows the `FOR UPDATE SKIP LOCKED` claim pattern. A live Postgres adapter still requires an actual database connection/credential and should be validated against the chosen managed service before being called production.

Serverless routing endpoints remain stateless. Do not rely on a serverless function's local filesystem for durable federation state. On Vercel, `/api/route` can remain stateless while orchestration state lives in an external durable service.

Backups must preserve the audit/ledger sequence and hashes. Restore tests should verify both hash chains before the restored state is promoted.
