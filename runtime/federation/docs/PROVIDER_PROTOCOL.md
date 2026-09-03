# Provider and Worker Protocol

The grant-bearing portion of a provider manifest is signed with Ed25519. Mutable telemetry and runtime status are outside the provider signature so the coordinator can update observed performance without invalidating the grant. The operator maintains a trust store mapping `keyId` to public key.

The reference worker uses an HMAC envelope with `x-bl-timestamp`, `x-bl-nonce`, and `x-bl-signature`; the signature is HMAC-SHA256 over `timestamp.nonce.body`. The worker checks clock skew and consumes the nonce in a replay guard. The shared secret lives in an environment variable, never in the manifest.

`POST /v1/execute` accepts a named capability and payload. The worker only invokes a handler already installed in its local handler map. The reference worker ships with narrowly scoped examples: `compute.echo`, `compute.sha256`, `text.stats`, and `json.project`. There is intentionally no generic shell, eval, arbitrary package import, arbitrary file read, or arbitrary URL fetch capability.

Transport auth modes supported by the coordinator are `hmac-env`, `bearer-env`, `cloudflare-service-token-env`, and `gcp-metadata-oidc`. Remote endpoints must use HTTPS; HTTP is accepted only for localhost development.
