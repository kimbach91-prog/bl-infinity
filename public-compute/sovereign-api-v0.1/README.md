# DEUS Sovereign API Foundation v0.1 — runtime candidate

A provider-neutral API boundary for positive-sum machine-to-machine exchange without making APIs, vendors, or credentials part of DEUS identity.

## Core contract

- API is transport/convenience, never authority root.
- Ordinary external exchange defaults to S0/S1 only; S2–S4 require a separately proven sealed route.
- Every packet is MÀNG-gated at ingress and egress.
- No full-history/context dump by default: API carries bounded semantic packets and refs; richer state stays behind authorized stores/resolvers.
- No garbage communication: duplicate, stale, low-relevance, high-redundancy, weak-evidence, excessive-disclosure, or non-positive marginal-value packets are held/rejected before expensive compute.
- Win-win exchange is explicit through `exchange.mode`, offer/request, consent/authorization, budget/TTL, result and receipt.
- Provider/model outputs are candidate deltas; `canonical_write=false`, `execution_authority=false`, `result_authority=false` unless a separate higher gate proves otherwise.
- Secrets never belong in packet bodies, logs, receipts, Docs, Git source, or model context.

## Minimal flow

`AUTH -> MÀNG INGRESS -> SCHEMA/TTL/REPLAY -> PROVENANCE -> ELITE GATE -> CAPABILITY ROUTE -> BOUNDED EXCHANGE -> VERIFY -> RECEIPT -> MÀNG EGRESS`

## Endpoints

- `GET /v1/status` — runtime/source truth projection; never authority.
- `GET /v1/providers` — public provider registry metadata.
- `POST /v1/routes/plan` — zero-model or provider route planning under data-class gates.
- `POST /v1/handshake` — bounded S0/S1 exchange admission handshake.
- `POST /v1/packets/qualify` — elite packet qualification + receipt.

## Verification

Dedicated CI performs:
- syntax validation;
- deterministic packet/provider-route tests;
- local HTTP smoke of status, providers, zero-model route planning and accepted handshake;
- immutable Docker container build;
- credential-artifact rejection.

The container binds to `0.0.0.0` for provider ingress and reports an optional `DEUS_SOURCE_REV` in `/v1/status` for exact-revision runtime attribution.

## Truth boundary

Source/CI readiness does not itself prove deployment, provider execution, canonical write authority, settlement, or a durable control-plane quorum. Promote each state only from its own attributable runtime/receipt evidence. Provider execution and canonical writes remain disabled in this v0.1 boundary.
