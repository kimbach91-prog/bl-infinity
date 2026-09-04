# Scholarly Trust Boundary Matrix v0.1

**Object ID:** `BL-RO-STBM-0.1`  
**Version:** `0.1`  
**Date:** `2026-09-04`  
**Author:** Lâm Kim Bách  
**Status:** `UNREVIEWED · WORK IN PROGRESS · PUBLIC RESEARCH OBJECT`  
**Review state:** No peer-review acceptance or institutional endorsement is claimed.

## Purpose

This small research object tests a boundary that is easy to blur in scholarly infrastructure:

> **Persistence, provenance, status, governance and trust signals can make a knowledge object easier to inspect. They do not, by themselves, determine whether its scientific claims are true.**

The object is intentionally narrow and disclosure-safe. It does not expose the withheld BL∞ research core. It is a falsifiable working map for comparing existing standards and for deciding whether any additional claim-level profile is useful at all.

## Boundary matrix

| Layer | Operational question | Useful machine-readable state | What must not be inferred |
|---|---|---|---|
| Identity / persistence | Can the object still be found and unambiguously referenced? | persistent identifier, version, landing page, update relation | persistence ≠ validity |
| Provenance / attribution | Where did this object, datum or assertion come from? | creator, source, derivation, activity, time, attribution | provenance ≠ correctness |
| Relations / status | How is one scholarly object related to another and what happened to it? | support/challenge/update/review/retraction/correction relations where available | status label ≠ complete epistemic judgment |
| Governance / stewardship | Who can participate, maintain, change or appeal infrastructure rules? | roles, policy, decision/review process, membership or stewardship state | governance participation ≠ voting on truth |
| Trust signals | What observable signals may help a reader decide what deserves inspection? | process markers, disclosures, integrity/status indicators | trust signal ≠ truth score |
| Epistemic evaluation | What evidence and method bear on the claim itself? | evidence, method, replication, critique, counterexample | cannot be reduced to popularity, identity or metadata alone |
| Test / falsifier state | What specific observation would count against a particular claim version, and what happened when tested? | test specification, expected falsifier, observed outcome, state transition | a declared falsifier ≠ proof that the test was adequate |
| Dependency impact | Which downstream objects depend on a claim or method whose state changed? | dependency edge, affected version, propagation/review-needed state | dependency impact ≠ automatic invalidation of every dependent claim |
| Implementation burden | Can the representation be used without excluding low-resource or multilingual participants? | required fields, tooling cost, vocabulary complexity, fallback representation | richer metadata ≠ more equitable participation by default |

## Five-node synthetic stress test

The minimum test graph contains only synthetic nodes:

- `C1-v1` — a claim version;
- `E1` — supporting evidence;
- `D1` — a dependency or method;
- `T1` — a challenge/test with an explicit expected falsifier;
- `R1` — a review/response recording the observed outcome and any resulting state change.

The test asks whether a current scholarly metadata stack can represent, without semantic loss or a new quality score:

1. `E1` bears on `C1-v1`;
2. `C1-v1` depends on `D1`;
3. `T1` specifies what observation would count against `C1-v1`;
4. `R1` records what was observed;
5. a changed state can trigger review of downstream dependencies;
6. the representation remains understandable to a human and implementable with low overhead.

Coverage should be classified as `NATIVE`, `EXTENSIBLE`, `EXTERNAL`, or `UNRESOLVED` rather than forcing a novelty claim.

## Prior-art checkpoints

Any residual hypothesis must be tested against existing infrastructure before proposing anything new. Current checkpoints include, at minimum:

- **Crossref** relationship, version, peer-review and update/status mechanisms: <https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/relationships/>
- **Crossref Crossmark** and post-publication update mechanisms: <https://www.crossref.org/documentation/crossmark/>
- **CiTO** citation relations such as support, critique, dispute and update: <https://sparontologies.github.io/cito/2018-02-12/cito.html>
- **W3C PROV-O** for provenance and derivation: <https://www.w3.org/TR/prov-o/>
- **Nanopublication / micropublication literature** for assertion, evidence, support/challenge and provenance patterns.

These are comparator families, not endorsements of this object and not evidence that every required state above is absent from current standards.

## Residual hypothesis

The only residual hypothesis tested here is deliberately narrow:

> A lightweight interoperable representation **may** be useful if existing stacks cannot simply express a claim-version-specific test/falsifier specification, the observed outcome/state transition, and downstream dependency impact without introducing a truth/quality score or excessive implementation burden.

### Falsifier

This residual hypothesis should be **narrowed or killed** if an existing standard/profile, or a simple combination of existing standards, already represents those states interoperably, round-trips them without material semantic loss, remains human-readable, and has acceptable implementation burden in multilingual/low-resource contexts.

## What is not claimed

This object does **not** claim:

- invention of provenance, citation semantics, peer review, retraction/correction metadata, nanopublications, micropublications or trust markers;
- that metadata can determine truth;
- that a persistent identifier is a quality mark;
- that governance participation grants epistemic authority;
- that BL∞ has been independently validated;
- that a new ontology should be created;
- that the residual hypothesis is novel.

## Evaluation protocol

For each tested representation, record:

1. coverage: `NATIVE / EXTENSIBLE / EXTERNAL / UNRESOLVED`;
2. round-trip semantic loss;
3. required custom vocabulary;
4. human readability;
5. implementation burden;
6. multilingual/local-script burden;
7. whether the representation accidentally behaves like a quality/truth score;
8. a concrete counterexample that would force revision of the map.

## Citation and immutability

This file is a living work-in-progress at its branch path. For an immutable citation, cite the **specific Git commit SHA** that contains the version inspected, together with this file path.

Public repository: <https://github.com/kimbach91-prog/bl-infinity>

---

**Disclosure note:** This public research object is intentionally bounded. It is separate from the withheld BL∞ research architecture described in `PUBLIC_DISCLOSURE_STATE.md`.
