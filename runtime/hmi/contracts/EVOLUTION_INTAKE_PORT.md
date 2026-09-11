# DEUS Evolution Intake Port v0.1

Status: `CANDIDATE / PUBLIC-SAFE CONTRACT`

The private DEUS evolutionary core is not a user API and must never be linked into app/web client bundles.

## Boundary

```text
user action / external outcome
  -> HMI evidence receipt
  -> tenant-safe learning event
  -> private intake gateway
  -> Reality / provenance gates
  -> PRIVATE evolutionary process
  -> candidate delta
  -> private selection / promotion
  -> optional sanitized user-facing effect projection
```

## Public-safe learning event

An intake event may contain only the minimum fields required to bind an observed outcome:

```text
eventId
schemaVersion
tenantScope or approved global-learning classification
sourceTaskRef (opaque)
outcomeReceiptRef (opaque)
outcomeClass
userFeedback class/value when authorized
timestamp
dataClassification
consent/policy reference
retention rule
```

It must not contain private mutation state, private fitness functions, hidden prompts, provider-selection heuristics, internal genealogy, raw reasoning traces or secret topology.

## Invariants

- `FEEDBACK != TRUTH`: user feedback is evidence, not canonical truth.
- `OUTCOME != CAUSATION`: observed success/failure does not by itself prove causal attribution.
- `TENANT_DATA != GLOBAL_TRAINING_RIGHT`: tenant data cannot be promoted to shared/global learning without an explicit policy/consent basis.
- `INTAKE != PROMOTION`: accepting an event does not modify canonical DEUS behavior.
- `NO_CLIENT_MUTATION`: clients cannot request arbitrary mutations, fitness weights or lineage rewrites.
- `NO_CORE_READBACK`: the intake gateway never returns private evolutionary internals.
- `SCAR_PRESERVATION`: failures relevant to future selection remain represented in private causal history even when a runtime change is rolled back.
- `REALITY_VETO`: missing or contradictory evidence may block promotion while preserving the candidate for later testing.

## Required response surface

The client may receive only operationally useful statuses such as:

```text
ACCEPTED_FOR_EVALUATION
REJECTED_POLICY
REJECTED_PROVENANCE
DUPLICATE_EVENT
QUARANTINED
```

No response reveals private scoring, hidden hypotheses, competing lineages or internal selector state.
