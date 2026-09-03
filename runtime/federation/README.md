# BL Compute Federation v0.1

A small control plane for aggregating **authorized** compute from many independent providers without pretending they are one machine.

## Core rule

No node is usable until it carries an explicit authorization/consent reference, scope, limits, and telemetry. The fabric is designed for owner devices, paid/free cloud quotas permitted by provider terms, research/partner grants, and BYOC resources contributed by customers or partners.

It is **not** designed to consume third-party CPUs, browsers, bandwidth, credentials, public endpoints, free tiers, or CI runners outside their owner/provider authorization and terms.

## Routing model

For a task `q`, filter providers by authorization, capability, quota, data class, concurrency and region. Rank eligible nodes using trust, data locality, availability, latency, cost and optional carbon intensity.

`provider* = argmax score(provider, q)`

The goal is useful information or work per unit of latency, compute and money, not raw utilization.

## Included

- provider registry with consent references
- deterministic eligibility gate
- cost/concurrency/data-policy gates
- multi-provider scoring and routing plan
- Vercel-compatible `/api/health` and `/api/route`
- local dev server
- zero-dependency Node tests

## Run locally

```bash
npm test
npm start
curl http://localhost:8787/health
curl -X POST http://localhost:8787/route \
  -H 'content-type: application/json' \
  -d '{"id":"demo-1","capability":"embed","dataClass":"public","dataLocation":"local"}'
```

## Next adapters

1. Cloudflare Worker adapter for low-cost edge sensors/cache.
2. GCP Cloud Run adapter using short-lived workload identity/OIDC.
3. Local worker agent for private/high-value tasks.
4. Partner/BYOC worker with signed capability manifest and revocable grant.
5. Shared queue + idempotency keys + telemetry feedback.
6. Index fabric: lexical + vector + graph, with expensive reasoning only after retrieval narrowing.

## Resource sovereignty

Every provider retains sovereignty over its own quota. A grant can expire or be revoked; the router must fail closed. Compute is federated, not seized.
