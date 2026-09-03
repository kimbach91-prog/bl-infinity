# Provider and Worker Protocol

## Signed provider authority

The grant-bearing portion of a provider manifest is signed with Ed25519. Mutable telemetry, runtime status and heartbeat timestamps are outside the provider signature so the coordinator can update observed performance and liveness without invalidating the grant. The operator maintains a trust store mapping `keyId` to public key.

The signed grant includes the things that are allowed to change authority: provider ID/kind, endpoint and transport declaration, capabilities, authorization/consent, data policy, regions/data locations, limits, tags and optional liveness policy. Changing those fields creates a different grant hash and requires a newly verified grant revision.

Telemetry in a submitted manifest is not a source of trust for dynamic registration. New dynamic providers start with neutral telemetry unless an owner-controlled bootstrap explicitly seeds measurements. Routing trust, latency and cost can later be updated from coordinator-observed execution telemetry.

## Optional signed liveness policy

A grant can require a fresh heartbeat:

```json
{
  "liveness": {
    "heartbeatRequired": true,
    "heartbeatTtlMs": 60000
  }
}
```

`heartbeatTtlMs` is bounded from 5 seconds to 24 hours. When heartbeat enforcement is signed into the grant, the node is effectively disabled before its first heartbeat and whenever the heartbeat TTL expires.

Heartbeat is not authority. A heartbeat may report bounded runtime occupancy such as `inFlight`, but it cannot add capabilities, change data classes, raise concurrency/cost limits, change endpoint authority or undo revocation. In v0.6 heartbeat mutations are accepted only through the authenticated control plane/trusted coordinator path; workers are not given the control token.

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

The reference worker uses an HMAC envelope with `x-bl-timestamp`, `x-bl-nonce`, and `x-bl-signature`; the signature is HMAC-SHA256 over `timestamp.nonce.body`. The worker checks clock skew and consumes the nonce in a replay guard. The shared secret lives in an environment variable, never in the manifest.

`POST /v1/execute` accepts a named capability and payload. The worker only invokes a handler already installed in its local handler map. The reference worker ships with narrowly scoped examples: `compute.echo`, `compute.sha256`, `text.stats`, and `json.project`. There is intentionally no generic shell, eval, arbitrary package import, arbitrary file read, or arbitrary URL fetch capability.

Transport auth modes supported by the coordinator are `hmac-env`, `bearer-env`, `cloudflare-service-token-env`, and `gcp-metadata-oidc`. Remote endpoints must use HTTPS; HTTP is accepted only for localhost development.

## Revocation and replacement

Revocation is durable shared state. Heartbeat cannot reactivate a revoked grant, and submitting the same signed grant again is rejected. A replacement must be an explicit operator action with a newly verified grant payload; the shared registry increments its revision and resets liveness state.

This protects the distinction:

```text
liveness proof != authority grant
runtime telemetry != signed capability
network reachability != permission to execute
```
