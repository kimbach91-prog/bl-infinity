# BL Compute Federation v0.2

A consent-aware control plane for combining small amounts of authorized compute across owner devices, cloud quotas, partner grants and BYOC nodes without treating reachable infrastructure as free infrastructure.

## Core invariant

`reachable != authorized`

A provider is usable only when its grant, capability, data policy, quota, concurrency and task policy all pass. Private data fails closed unless it remains at the declared data location or the grant explicitly permits private egress.

## v0.2 runtime

- policy-aware provider routing
- Ed25519-signed provider grants and trust store
- HMAC worker protocol with timestamp, nonce and replay protection
- explicit capability allowlist; no shell/eval/arbitrary-code endpoint
- fallback executor with telemetry feedback and provenance
- idempotent lease queue with heartbeat recovery and dead-lettering
- hash-chained audit log
- hybrid in-memory search reference: lexical + semantic-lite + relation graph + trust/freshness
- local and HTTPS-worker adapters
- auth modes for HMAC env, bearer env, Cloudflare Access service tokens, and GCP metadata OIDC
- Docker-ready coordinator and worker

## Run

```bash
cd runtime/federation
npm test
export BL_CONTROL_TOKEN='replace-with-a-long-random-token'
npm start
```

Worker:

```bash
export BL_FEDERATION_SHARED_SECRET='replace-with-a-long-random-secret'
npm run worker
```

The control plane binds to `127.0.0.1` by default. Execution and mutation endpoints remain disabled unless `BL_CONTROL_TOKEN` is set.

## Signed provider grants

```bash
npm run keys -- partner-a
node scripts/sign-provider-manifest.mjs provider.json partner-a.private.pem partner-a signed-provider.json
```

Never commit private keys or worker shared secrets.

## Production boundary

The included queue, search index and audit store are reference in-memory/single-process components. Horizontal production deployment must replace them with shared durable backends while retaining the same authorization, data-locality, idempotency and provenance invariants. Vercel routing is stateless and intentionally does not pretend to be a durable queue/search cluster.

The project does not use GitHub Actions, public endpoints, free tiers, browsers, visitor devices or third-party machines as a covert compute farm. A resource becomes a node only through an explicit revocable grant.

See `docs/RESOURCE_SOVEREIGNTY.md`, `docs/PROVIDER_PROTOCOL.md`, and `docs/DEPLOY.md`.
