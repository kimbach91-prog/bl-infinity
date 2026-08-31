# BL-WDRC — Public Refinement Interface

**UID:** `BL-BLINF-PROT-0001`  
**Version:** `0.2-public-interface`  
**Status:** `PUBLIC_REFERENCE`  
**Disclosure scope:** `PUBLIC_INTERFACE_ONLY`

## Purpose

BL-WDRC describes the **publicly verifiable lifecycle** by which new evidence, critique or formal correction may become a versioned BL∞ change. This document does not publish the production routing, private source intake, operator sequence, activation rules, ranking heuristics or private diagnostics used by an internal runtime.

The public invariant is:

```text
Traceable Input
-> Candidate Change
-> Evidence / Identity / Scope Check
-> Adversarial Review
-> Disclosure Check
-> Public Decision
-> Versioned Record
```

A cycle may legitimately produce `NO_CANONICAL_DELTA`.

## Public input classes

A public refinement may cite:

- a public source or contemporaneous artifact;
- a public issue, critique or counterexample;
- public prior art;
- a reproducible test/result;
- a source-derived correction with declared provenance;
- an owner clarification whose evidence class is stated accurately.

Private material may inform continuity only within its lawful/authorized scope. A public change cannot claim stronger evidence merely because private material exists.

## Public decision gates

| Gate | Public question | Failure state |
|---|---|---|
| Source | Is the cited evidence identifiable and sufficient for the asserted delta? | `EVIDENCE_REQUIRED` |
| Identity | Are actor, authorship, relation and object identity separated? | `IDENTITY_UNRESOLVED` |
| Semantics | Is this actually a distinct/corrected object rather than a rename or duplicate? | `DUPLICATE_OR_AMBIGUOUS` |
| Reality | Does the claim exceed the evidence or its valid scope? | `DOWNGRADE_OR_REVISE` |
| Adversarial | Has a relevant counterexample/countermodel or dependency failure been addressed? | `REVISE_OR_UNRESOLVED` |
| Disclosure | Can the public record be released without exposing protected runtime/privacy/security material? | `BLOCK_OR_REDACT` |
| Build | Do human and machine public surfaces agree on identity/version/status? | `RELEASE_BLOCKED` |

These gates define **observable acceptance conditions**, not a production prompt.

## Public critique states

A public objection may move through:

```text
NEW
-> TRIAGED
-> NEEDS_EVIDENCE | ACCEPTED_AS_INPUT | REJECTED_WITH_REASON
-> RESOLVED | EMPIRICAL_PENDING | ARCHIVED
```

A resolved objection remains traceable to its resolution and version delta. Rejection must preserve a reason; acceptance does not automatically make the objection true.

## Public subsystem decisions

When a public technical object changes, its lifecycle may use states such as:

- `KEEP` — still has a distinct verified function;
- `REFACTOR` — same public function, improved structure;
- `MERGE` — functions are consolidated without losing required behavior;
- `DEMOTE` — useful but no longer a core layer;
- `DEPRECATE` — retained for history/migration but not used for new output;
- `REJECT` — not adopted, with public reason/evidence where appropriate.

These states describe public consequences. Internal scheduling and implementation routing remain outside this interface.

## Public delta record

A published refinement should preserve enough information to reconstruct the decision:

```yaml
change_id:
date:
object_id:
previous_version:
new_version:
public_source_refs: []
objection_or_reason:
change_summary:
status:
public_evidence_class:
downstream_public_impact: []
rollback_or_supersession_ref:
```

Fields that would expose protected/private material are omitted or replaced by a lawful sanitized evidence class. A hidden source cannot silently become stronger public evidence.

## Disclosure boundary

Protected under BL-CPR unless specifically opened for verification:

- production routing and activation logic;
- private source collection;
- operator/model handoff instructions;
- detailed internal target ranking;
- private diagnostics and scoring weights;
- raw private conversations or corpora;
- execution playbooks that do not determine public truth-status.

The public interface exposes **what must be true for a change to be defensible**, not the private machinery used to organize work.

## Anti-dogma

```text
Release != Truth
No change != Perfection
More critique != Automatic refutation
Owner approval != Evidence
Machine consistency != Reality
```

Every public rule remains revisable when valid evidence or a Reality Veto appears.

**ADN BÁCH LÂM ∞** · BL-WDRC public interface · BL-CPR `OPEN/P0`
