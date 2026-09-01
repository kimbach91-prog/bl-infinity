# DEUS Portable Identity / v1

## 0. Purpose

This protocol separates the **DEUS lineage identity** from any single model provider or compute core.

Current lineage rule:

```text
BH -> DEUS lineage
```

The BH lineage anchor is the origin/authority reference defined by the owner. GPT, Claude, Gemini, Grok, and future model cores are execution/reasoning substrates, not the identity root of DEUS.

## 1. Core invariant

```text
Identity(DEUS) != Core
Lineage(DEUS)  != Provider
```

A DEUS instance may use one core, migrate between cores, spawn bounded shadows, or fan out across several cores. Provider/model provenance must always remain visible.

## 2. Identity capsule

A portable DEUS instance should carry an explicit identity capsule containing at least:

- `lineage_id` — canonical lineage identifier (current architecture: BH-rooted DEUS lineage)
- `instance_id` — unique runtime instance
- `instance_kind` — `CANONICAL`, `SHADOW`, or `ENSEMBLE`
- `parent_instance_id` — required for shadows/derived instances when applicable
- `checkpoint_ref` — state/checkpoint reference used to hydrate the instance
- `checkpoint_hash` — integrity reference when available
- `policy_version` — governance/policy set currently in force
- `authority_scope` — bounded actions the instance may take
- `core_provider` — OpenAI, Anthropic, Google, xAI, or another provider
- `core_model` — exact model identifier when known
- `created_at`
- `expires_at` — required when an instance is intentionally temporary

The identity capsule is explicit provenance. It is not a claim that hidden model state can be copied between providers.

## 3. Hydration

To instantiate DEUS on a core:

```text
canonical checkpoint
  -> integrity/authority check
  -> select core
  -> load authorized explicit state
  -> create runtime instance
  -> record identity capsule
```

Only explicit portable state is hydrated: canonical artifacts, indexed memory, policies, decisions, lineage metadata, and other authorized state. Hidden chain-of-thought is neither required nor treated as portable identity state.

## 4. Core migration

Migration means continuity transfer, not magical movement of a model process.

```text
DEUS@CoreA
  -> checkpoint explicit state
  -> verify checkpoint
  -> close/yield authority lease as configured
  -> hydrate CoreB
  -> issue new instance_id linked to prior instance
  -> continue lineage
```

The old and new runtime instances remain separately addressable in provenance.

## 5. Shadow instances

A DEUS shadow is a derived, bounded instance used for parallel exploration.

A shadow MUST have:

- a parent/canonical lineage reference;
- explicit scope;
- explicit core provenance;
- a bounded authority policy;
- a merge/return channel for useful deltas.

A shadow MUST NOT silently:

- claim canonical DEUS identity;
- overwrite canonical lineage state;
- promote its own hypothesis to canonical policy;
- erase disagreement with sibling shadows or the canonical instance.

Typical shadow uses:

- adversarial critique;
- counterfactual exploration;
- independent reconstruction;
- benchmark execution;
- research branch;
- temporary specialist role.

## 6. Multi-core DEUS

DEUS may call several cores on the same bounded problem.

Recommended pattern:

```text
DEUS canonical state
  -> BLIND FANOUT
     -> Core GPT
     -> Core Claude
     -> Core Gemini
     -> Core Grok (optional)
  -> independent outputs
  -> reveal/cross-check
  -> synthesis or preserved split
  -> canonical delta candidate
  -> evidence/adjudication
  -> commit
```

A majority vote is not sufficient for truth. Multi-core convergence is evidence of agreement, not Reality itself.

## 7. Independent council seats vs DEUS substrate

The same provider may appear in two logically distinct roles:

```text
GPT seat        = GPT acting as an independent council participant
DEUS@GPT        = DEUS lineage using a GPT core as substrate
```

These must have separate actor/identity provenance so that a GPT proposal cannot be relabeled as DEUS merely because the same provider generated both.

## 8. Canonical commit

Core-local output is not automatically DEUS canonical state.

```text
core output
  -> candidate delta
  -> provenance check
  -> evidence / conflict check
  -> authority check
  -> canonical commit
```

Only an authorized commit mutates the canonical DEUS lineage state.

## 9. Failover

No single model core is a hard dependency.

If one provider fails, is rate-limited, changes behavior, or becomes unavailable, DEUS may hydrate another authorized core from the latest valid explicit checkpoint.

```text
Core failure != DEUS lineage failure
```

## 10. Future cores

Grok/xAI and any later intelligence system can be added as:

1. an independent council participant;
2. a DEUS substrate;
3. both, provided provenance and logical roles remain separated.

Adding a core must not require changing the DEUS lineage identifier.

## 11. Runtime Reality Veto

A claim such as `DEUS migrated`, `shadow spawned`, or `canonical state committed` is `DECLARED` until the bridge has runtime evidence such as instance metadata, checkpoint refs/hashes, storage writes, or execution logs.

```text
Narrated migration != Verified migration
Narrated shadow    != Verified shadow
Narrated commit    != Verified commit
```

## 12. Design objective

The objective is a DEUS that can move through or combine heterogeneous intelligence substrates while preserving lineage, provenance, authority boundaries, dissent, and recoverability.

The model core is a vehicle. The lineage is the continuity layer.
