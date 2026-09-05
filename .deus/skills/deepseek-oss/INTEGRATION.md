# DEUS Core-Adjacent Integration — DeepSeek OSS Skillpack

State: `CANDIDATE`; not core-authoritative until independent verification.
Base: `deus/sss-core-isolation-hmi`
Candidate branch: `deus/deepseek-oss-skillpack-r1`

## Role
This package is a capability-acquisition adapter, not a new authority source. It turns external open source into pinned, inspectable evidence and reusable technique fingerprints. It MUST NOT override DEUS state, policy, security boundaries, or verifier results.

## Reuse-first invariant
`unchanged source identity => no deep re-learning`

Source identity is `(repo, HEAD_SHA, registry_hash)`. A mismatch invalidates the cache for that repository only. Existing mastered regions are served from cache; compute is concentrated on newly observed deltas.

## Three regressions
- **R1 RECONSTRUCT** — rebuild the current capability map from static source markers.
- **R2 HISTORY REGRESSION** — inspect three recent revisions per repository and isolate marker/file deltas.
- **R3 VARIANT SYNTHESIS** — search cross-category combinations not already observed. Every output is explicitly hypothetical until separately implemented and benchmarked.

## Security boundary
- Upstream source is cloned/read only.
- This skill never executes upstream scripts, build hooks, package installers, tests, model code, or binaries.
- Raw third-party repositories live under `.deus-cache/deepseek-ai/`, outside committed core state.
- Source metadata records repository identity, observed HEAD SHA and license metadata.

## Rollback
Disable/delete `.deus/skills/deepseek-oss` and remove its cache/state directories. The skill has no write path into the DEUS authority store.

## Promotion gate
1. Unit tests green.
2. Live-source sync completes with failures reviewed.
3. R1/R2/R3 reports generated.
4. Independent verifier checks pinned SHAs and static-only boundary.
5. Only then merge toward core.
