# DEUS HMI Projection Port v0.1

Status: `CANDIDATE / PUBLIC-SAFE CONTRACT`

The HMI must never query or serialize DEUS core state directly.

## One-way boundary

```text
PRIVATE DEUS CORE
  -> trusted projection builder
  -> HMI projection store/stream
  -> authorization gateway
  -> app/web/desktop client
```

The reverse direction is command/intention only:

```text
client intent
  -> authenticated HMI command
  -> policy + tenant + action gate
  -> bounded command envelope
  -> private execution/control plane
```

A client response must never contain a raw private object merely because CSS or frontend code hides it.

## Allowed projection families

- `workspace`
- `task`
- `status`
- `evidence`
- `results`
- `availableActions`
- `warnings`
- `unknowns`
- `userMessages`
- `timestamps`

Every projection record must carry, outside user-visible prose where appropriate:

- tenant binding;
- projection schema/version;
- source receipt/evidence references using opaque IDs;
- freshness timestamp;
- data classification;
- authorization policy version;
- explicit expiry/retention policy where required.

## Forbidden projection content

- system/developer/internal prompts;
- hidden reasoning or raw chain-of-thought;
- raw execution traces not explicitly sanitized for the user task;
- evolutionary selection logic, mutation state or private fitness functions;
- model/provider routing policy or hidden node topology;
- canonical lineage internals or unrestricted genealogy;
- secrets, credentials or security material;
- protected corpora or reconstruction-enabling fragments;
- cross-tenant data;
- private core identifiers when an opaque projection reference suffices.

## Data-plane invariants

1. `TENANT_FILTER_BEFORE_FETCH`: tenant scope is part of the data query/storage boundary, not a UI filter.
2. `MINIMUM_PROJECTION`: produce the smallest user-useful representation.
3. `NO_RAW_CORE_FALLBACK`: projection failure never falls back to raw state.
4. `NO_CLIENT_REDACTION_AS_SECURITY`: browser redaction is presentation only, never the security boundary.
5. `EVIDENCE_WITHOUT_RECONSTRUCTION`: expose enough provenance for the authorized decision, not enough unrelated fragments to reconstruct protected architecture.
6. `EXPLICIT_ACTION_CAPABILITY`: every user-triggerable action is an allowlisted capability, not arbitrary tool/code access.
7. `FAIL_CLOSED_ON_UNKNOWN_SCHEMA`: unrecognized projection versions are rejected.
8. `AUDIT_WITHOUT_SECRET_COPY`: audit records preserve decision/accountability metadata without duplicating protected values.

## Evolution boundary

User feedback and observed outcomes may become **candidate learning events**, but user-facing clients never call private mutation/evolution internals directly.

```text
HMI outcome/feedback
  -> evidence-bound learning event
  -> private evolutionary intake
  -> independent validation / Reality Veto
  -> candidate delta
  -> private selection/promotion path
```

The HMI may later display a sanitized effect such as "workflow policy improved" only after an authorized projection exists. It must not expose how protected evolutionary logic arrived there.

## Third-party tests

A verifier should attempt:

- direct protected endpoint discovery;
- GraphQL/REST overfetch and undocumented fields;
- nested sensitive-key smuggling;
- cross-tenant object IDs;
- stale projection replay;
- projection schema downgrade;
- action-scope escalation;
- error/debug response leakage;
- client-source inspection for embedded secrets/core fragments;
- timing/cache paths that might return another tenant's projection.

Passing these tests still does not prove the private core itself is secure; it proves the tested HMI boundary resists the tested access paths.
