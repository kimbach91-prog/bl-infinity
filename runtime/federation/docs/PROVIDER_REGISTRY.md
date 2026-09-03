# Shared Provider Registry

BL Compute Federation v0.6 stores provider authority and liveness in PostgreSQL so multiple coordinators converge on the same authorized computational ecology.

## Invariant

```text
reachable != authorized
heartbeat != authority
telemetry != authority
```

The registry never infers permission from network reachability, a successful health check or self-reported performance. Authority comes from the verified provider grant and its explicit consent reference.

## Two-layer model

### 1. Authority layer

Persisted in `grant_json` plus signature metadata:

- provider ID and kind
- endpoint/transport declaration
- capabilities
- authorization and consent reference
- data classes and data policy
- regions/data locations
- cost/concurrency/execution limits
- side-effect permission
- tags
- optional liveness requirement

The canonical grant is hashed into `grant_hash`. Replacing any authority-bearing field changes that hash and requires an explicit verified replacement. Grant revisions are monotonic and retained as an operational provenance marker.

### 2. Runtime layer

Mutable state stored separately:

- stored status: `active`, `disabled`, `revoked`
- neutral or coordinator-measured telemetry
- last heartbeat and heartbeat expiry
- heartbeat sequence
- revocation time/reason
- registration/update timestamps

Updating runtime state never rewrites `grant_json`.

## Effective routing state

A row can have stored status `active` and still be unusable. The reconstructed provider is effectively disabled when any of these holds:

```text
stored status is not active
OR grant is expired
OR grant is revoked
OR signed heartbeatRequired=true and heartbeat is stale/missing
```

The normal routing policy then sees `status=disabled` and rejects that provider.

## State transitions

```text
                 operator disable
        +-------------------------------+
        |                               v
verified grant --> ACTIVE <---------- DISABLED
        |           |                   |
        |           |                   |
        +-----------+-------> REVOKED <-+

REVOKED --X--> heartbeat
REVOKED --X--> same-grant registration
REVOKED --> explicit verified replacement --> new revision
```

Revocation is intentionally stronger than disable. Disable is operational and reversible. Revocation means the current authority is no longer valid and cannot be resurrected by liveness signals.

## Registration rules

A provider ID is stable identity within the registry.

- First verified grant for an ID is stored.
- Re-submitting the exact same grant hash is idempotent and does not overwrite measured telemetry.
- A different grant for the same ID is rejected as a conflict unless the operator explicitly uses replacement.
- A revoked grant rejects ordinary re-registration.
- Explicit replacement installs a newly verified grant revision, clears revocation state, resets heartbeat state and increments `revision`.

For dynamic registration, telemetry supplied by the caller is not trusted. The provider starts from neutral routing telemetry:

```json
{
  "inFlight": 0,
  "trust": 0.5,
  "availability": 0.5,
  "p95LatencyMs": 1000,
  "costPerUnitUsd": 0
}
```

Owner-controlled bootstrap may explicitly seed telemetry because it is a local operator action, not a provider self-claim.

## Heartbeat rules

Heartbeat enforcement is optional and must be signed into the grant. Example:

```json
{
  "liveness": {
    "heartbeatRequired": true,
    "heartbeatTtlMs": 60000
  }
}
```

The allowed TTL is 5 seconds through 24 hours. A heartbeat refreshes liveness and can update bounded occupancy such as `inFlight`. It does not modify trust, capability, quota, data policy or grant authority.

v0.6 exposes heartbeat only through the authenticated control plane/trusted coordinator path. Do not give workers `BL_CONTROL_TOKEN`. A future direct worker heartbeat must use a separate narrowly scoped credential/envelope with replay protection.

## Multi-coordinator convergence

Each coordinator keeps a local `ProviderRegistry` for fast route evaluation. Before route/execute/orchestration operations, PostgreSQL shared state is synchronized into the local registry.

- effective active shared providers are registered/refreshed;
- inactive or revoked providers already known locally are disabled;
- revocation therefore propagates across coordinators at the next synchronization boundary.

The shared PostgreSQL row remains the authority/liveness source of truth. The in-process registry is a routing projection, not the canonical grant store.

## Telemetry provenance

Coordinator execution telemetry may update runtime measurements in PostgreSQL. A provider cannot use heartbeat or unsigned manifest telemetry to raise its own trust score.

Operationally distinguish:

```text
GRANT: what the owner allows
HEARTBEAT: whether the node is currently alive
TELEMETRY: how the coordinator has observed it behaving
LEDGER: what work/cost was actually attributed
```

Do not collapse these into one mutable manifest.

## Failure and recovery

If PostgreSQL is unavailable, a coordinator must not invent shared provider authority. Existing in-process bootstrap grants may still exist according to deployment design, but dynamic shared registration/revocation/heartbeat cannot be claimed synchronized until the store is available again.

Revocation should be treated as security-sensitive state. PostgreSQL backup/PITR and restore procedures must preserve `federation_providers` along with audit and ledger tables.

## Current production boundary

CI validates registry semantics against PostgreSQL 16, including heartbeat gating, neutral telemetry, propagation to multiple local registries, durable revocation and explicit re-grant revision. This is not evidence that a production provider registry/database has been provisioned.
