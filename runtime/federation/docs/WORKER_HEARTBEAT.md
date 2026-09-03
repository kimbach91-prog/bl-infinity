# Secure Worker Self-Heartbeat

BL Compute Federation v0.7 lets a worker refresh its own provider liveness without receiving the coordinator control token.

## Security boundary

A worker heartbeat proves only that a node holding a provider-scoped heartbeat secret is alive. It does not grant compute authority.

```text
signed provider grant = authority
heartbeat HMAC       = liveness credential
execution HMAC       = task transport credential
BL_CONTROL_TOKEN     = operator/control-plane authority
```

Keep these credentials separate. Do not give a worker `BL_CONTROL_TOKEN`. Prefer a dedicated heartbeat secret instead of reusing `BL_FEDERATION_SHARED_SECRET`.

## Signed grant

The provider grant can authorize direct HMAC heartbeat by naming the environment variable that the coordinator will read. The name is signed; the secret value is not stored in the manifest or database.

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

`heartbeatTtlMs` is bounded to 5 seconds through 24 hours. Choose an interval comfortably below the TTL; for a 60-second TTL, 15-20 seconds is reasonable.

## Coordinator environment

The coordinator must contain the secret referenced by the signed grant:

```bash
export PARTNER_A_HEARTBEAT_SECRET='use-a-random-secret-from-a-secret-manager'
```

The secret must not be committed to the repository, written into the provider manifest or returned by APIs.

Direct self-heartbeat requires PostgreSQL because replay protection is shared across coordinators.

## Worker environment

The worker needs the same secret, but it discovers it indirectly from a local env-name setting:

```bash
export BL_PROVIDER_ID='partner-a-worker-1'
export BL_HEARTBEAT_URL='https://control.example.com/providers/heartbeat/self'
export BL_HEARTBEAT_SECRET_ENV='PARTNER_A_HEARTBEAT_SECRET'
export PARTNER_A_HEARTBEAT_SECRET='same-provider-scoped-secret'
export BL_HEARTBEAT_INTERVAL_MS='20000'
export BL_HEARTBEAT_TIMEOUT_MS='5000'
```

`BL_PROVIDER_ID`, `BL_HEARTBEAT_URL` and `BL_HEARTBEAT_SECRET_ENV` are all-or-nothing. Partial configuration fails worker startup rather than silently disabling liveness reporting.

The client refuses plaintext HTTP except for localhost development.

## Envelope

Each request signs the exact body:

```text
HMAC-SHA256(
  providerId + "." + timestamp + "." + nonce + "." + rawBody,
  providerHeartbeatSecret
)
```

Headers:

```text
x-bl-provider-id
x-bl-timestamp
x-bl-nonce
x-bl-heartbeat-signature
```

Body:

```json
{
  "providerId": "partner-a-worker-1",
  "inFlight": 1
}
```

The body provider ID must match `x-bl-provider-id`.

## Replay defense

The coordinator verifies timestamp skew and HMAC before consuming the nonce. Valid nonces are inserted into `federation_provider_heartbeat_nonces` with a provider-scoped unique key.

That database uniqueness is important: an in-memory replay cache on coordinator A would not stop the same request from being replayed through coordinator B. PostgreSQL makes the replay boundary federation-wide.

A bad signature does not consume the nonce. A valid replay does not refresh liveness.

Nonce retention is longer than the accepted timestamp-skew window, so an old signed request cannot become valid again after nonce cleanup.

## What a heartbeat may update

The self-heartbeat path only accepts bounded runtime occupancy (`inFlight`) and refreshes availability/liveness timestamps. It does not accept provider-supplied trust, cost, latency, capability, region, data policy, concurrency ceiling or authorization changes.

Coordinator-measured execution telemetry remains a separate trusted update path.

## Revocation and expiry

A revoked or expired grant cannot self-heartbeat. Heartbeat cannot undo disable/revocation or create a new authority revision.

If a heartbeat credential is suspected to be exposed:

1. revoke or disable the provider as appropriate;
2. rotate the secret in the secret manager;
3. issue a new signed grant when the signed `secretEnv` reference or authority needs to change;
4. update worker and coordinator secret environments;
5. verify the old credential can no longer refresh liveness.

## Operational monitoring

Monitor at least:

- last heartbeat timestamp and expiry;
- heartbeat sequence progression;
- authentication failures by reason;
- replay rejections;
- provider transition to stale/disabled;
- database errors in nonce consumption;
- divergence between worker-reported `inFlight` and coordinator-observed concurrency.

Do not automatically turn repeated heartbeat failures into broader permissions or looser authentication. A stale node should fail closed.

## Current boundary

v0.7 authenticates direct worker heartbeat with provider-scoped HMAC and PostgreSQL replay protection. It does not establish mutual TLS, hardware attestation or a public anonymous volunteer-compute network. Those would require separate threat models and explicit authorization.
