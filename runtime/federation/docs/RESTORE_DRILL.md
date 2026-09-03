# PostgreSQL Backup and Restore Verification Drill

BL Compute Federation stores operational state and security-sensitive authority state in PostgreSQL. A backup is not considered useful merely because a dump file exists; a restored database must preserve the invariants that make the federation safe.

## CI restore drill

The federation CI now performs a deterministic PostgreSQL 16 logical restore drill after the test suite:

```text
seed fixture
-> pg_dump custom-format snapshot
-> create separate restore database
-> pg_restore
-> run invariant verifier against restored database
```

The restore database is separate from the source database, so the verifier is not merely reading the original state.

## Restored invariants

`verify-postgres-restore.mjs` checks at least:

- base schema readiness;
- v0.8 provider delta sequence/trigger/index readiness;
- audit hash-chain validity;
- contribution-ledger hash-chain validity;
- durable provider revocation remains revoked;
- revoked authority cannot heartbeat after restore;
- pending queue work survives;
- committed budget accounting survives;
- heartbeat replay nonce state survives the logical snapshot;
- provider change cursor survives and continues monotonically after a new telemetry update.

The deterministic fixture contains one active provider, one revoked provider, a pending job, committed budget state, ledger evidence, audit evidence and a heartbeat nonce.

## What this proves

The CI drill proves that the current PostgreSQL logical schema can be dumped and restored with the critical application invariants intact under PostgreSQL 16.

It is especially important that a restore does **not** resurrect authority:

```text
revoked before backup -> revoked after restore
```

and that provenance remains verifiable:

```text
restored audit chain  -> valid
restored ledger chain -> valid
```

## What this does not prove

The CI logical dump/restore drill is not a claim that production PITR exists or has been tested. Production point-in-time recovery additionally depends on infrastructure outside this repository, such as managed-service backup settings, WAL retention/archive policy, replica topology, storage encryption, retention periods and operator access.

Do not label production backup/PITR as verified until an actual production-like recovery exercise has restored into an isolated environment and passed the same invariant verifier.

## Production recovery sequence

A production recovery exercise should follow this shape:

```text
1. freeze or isolate writers
2. select snapshot / target recovery time
3. restore into an isolated database
4. run schema readiness checks
5. run audit + ledger chain verification
6. verify revoked grants remain revoked
7. verify budget, queue and provider state
8. verify provider change cursor can continue
9. compare expected recovery point / RPO
10. only then promote or reconnect coordinators
```

Never point coordinators at an unverified restored database merely because PostgreSQL reports that recovery completed successfully.

## RPO and RTO

For a live deployment, define explicit targets:

- **RPO**: maximum acceptable state loss between the latest durable recovery point and failure;
- **RTO**: maximum acceptable time to restore, verify and safely resume federation operation.

These values depend on workload and consequences. A system handling side effects or security-sensitive revocations should use stricter recovery targets than a disposable public-data indexing lane.

## Dual backup principle

A backup strategy should avoid a single administrative deletion domain. For critical artifacts, keep versioned copies/snapshots in separate authorized accounts or storage domains and avoid deletion-mirroring as the only backup mechanism.

Database backups still need encryption, access control, retention policy and tested restore procedures. Copying an unreadable or unverified backup to two places does not create recoverability.
