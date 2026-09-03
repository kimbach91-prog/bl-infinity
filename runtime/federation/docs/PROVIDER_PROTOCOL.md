# Provider and Worker Protocol

## Signed provider authority

The grant-bearing portion of a provider manifest is signed with Ed25519. Mutable telemetry, runtime status and heartbeat timestamps are outside the provider signature so the coordinator can update observed performance and liveness without invalidating the grant. The operator maintains a trust store mapping `keyId` to public key.

The signed grant includes authority-bearing fields: provider ID/kind, endpoint and transport declaration, capabilities, authorization/consent, data policy, regions/data locations, limits, tags and optional liveness policy. Changing those fields creates a different grant hash and requires a newly verified grant revision.

Telemetry in a submitted manifest is not a source of trust for dynamic registration. New dynamic providers start with neutral telemetry unless an owner-controlled bootstrap explicitly seeds measurements. Routing trust, latency and cost can later be updated from coordinator-observed execution telemetry.

## Signed liveness policy

A grant can require a fresh heartbeat and authorize a provider-scoped HMAC credential by naming an environment variable. The environment-variable name is signed; the secret value is never stored in the manifest or PostgreSQL.

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

`heartbeatTtlMs` is bounded from 5 seconds to 24 hours. When heartbeat enforcement is signed into the grant, the node is effectively disabled before its first heartbeat and whenever the heartbeat TTL expires.

Heartbeat is not authority. It can report bounded runtime occupancy such as `inFlight`, but it cannot add capabilities, change data classes, raise concurrency/cost limits, change endpoint authority, self-raise routing trust or undo revocation.

## Direct worker self-heartbeat

v0.7 adds a provider-scoped self-heartbeat path at `POST /providers/heartbeat/self`. The worker does **not** receive `BL_CONTROL_TOKEN`.

Each request carries:

```text
x-bl-provider-id
x-bl-timestamp
x-bl-nonce
x-bl-heartbeat-signature
```

The signature is:

```text
HMAC-SHA256(providerId.timestamp.nonce.rawBody, providerHeartbeatSecret)
```

The worker body contains the same provider ID and current `inFlight` value. The coordinator resolves the secret environment-variable name from the signed grant, verifies clock skew and signature, then atomically consumes the provider-scoped nonce in PostgreSQL.

Replay protection is intentionally durable. `federation_provider_heartbeat_nonces(provider_id, nonce)` is unique across every coordinator sharing the database, so replaying a valid heartbeat through a different coordinator is rejected.

Bad signatures do not consume a nonce. Nonce retention exceeds the accepted timestamp-skew window, so an old signed request cannot become valid after cleanup.

Use a heartbeat secret separate from both the execution HMAC secret and the control token. See `WORKER_HEARTBEAT.md`.

## Provider state transitions

The shared registry separates signed authority from operational state:

```text
new verified grant -> active stored state
                     |  \
                     |   -> disabled -> active
                     |
                     -> revoked

revoked --X--> heartbeat
revoked --X--> same grant re-submit
revoked ----> explicit new verified grant revision via replace
```

A provider requiring heartbeat can have stored state `active` while its effective routing state is `disabled` because liveness is stale. The stored grant remains intact for provenance and later operator review.

## Worker execution protocol

The reference worker uses a separate HMAC execution envelope with `x-bl-timestamp`, `x-bl-nonce`, and `x-bl-signature`; the signature is HMAC-SHA256 over `timestamp.nonce.body`. The worker checks clock skew and consumes the nonce in a replay guard. The execution shared secret lives in an environment variable, never in the manifest.

`POST /v1/execute` accepts a named capability and payload. The worker only invokes a handler already installed in its local handler map. The reference worker ships with narrowly scoped examples: `compute.echo`, `compute.sha256`, `text.stats`, and `json.project`. There is intentionally no generic shell, eval, arbitrary package import, arbitrary file read, or arbitrary URL fetch capability.

Transport auth modes supported by the coordinator are `hmac-env`, `bearer-env`, `cloudflare-service-token-env`, and `gcp-metadata-oidc`. Remote endpoints must use HTTPS; HTTP is accepted only for localhost development.

## Revocation and replacement

Revocation is durable shared state. Heartbeat cannot reactivate a revoked grant, and submitting the same signed grant again is rejected. A replacement must be an explicit operator action with a newly verified grant payload; the shared registry increments its revision and resets liveness state.

Expired grants are also rejected by the direct self-heartbeat verifier even if the worker still knows an old HMAC secret.

This protects the distinction:

```text
liveness proof != authority grant
runtime telemetry != signed capability
heartbeat credential != control authority
network reachability != permission to execute
```
