# Deployment Notes

## Coordinator
Build `runtime/federation/Dockerfile`. Production should set `HOST=0.0.0.0`, platform `PORT`, a strong `BL_CONTROL_TOKEN`, provider configuration via `BL_PROVIDERS_JSON` or a mounted file, and for partner/BYOC registration `BL_REQUIRE_SIGNED_MANIFESTS=true` plus `BL_TRUST_STORE_JSON`.

The included in-memory search/audit/queue components are one-process reference implementations. Before horizontal scaling, replace them with shared durable stores while retaining the policy and provenance interfaces.

## Worker
Build `worker.Dockerfile` and set `BL_FEDERATION_SHARED_SECRET`, `BL_WORKER_MAX_CONCURRENCY`, and platform `HOST/PORT`. Prefer a private service. GCP-to-Cloud-Run can use `transport.auth=gcp-metadata-oidc`; Cloudflare Access can use `cloudflare-service-token-env`.

## Vercel
`/api/health` and `/api/route` are stateless. `BL_PROVIDERS_JSON` must be configured in the Vercel project environment. Do not use function memory as a durable queue or index.

## Durable scale-out
Recommended replacements when load justifies them: managed Redis/Postgres/PubSub for queue/idempotency, Postgres or append-only object storage for metadata/audit, OpenSearch/Postgres FTS for lexical retrieval, pgvector/Qdrant/managed vector storage for semantic retrieval, and object storage near the data owner for raw artifacts.
