# Machine verification layer

This page is the **public verification boundary** of BL∞ — not a publication of the private Optimizer/BLCC runtime.

Because the `bl-infinity` repository and its GitHub Pages site are public, **anything committed to this repository must be treated as exposed**. A file is not private merely because it is absent from the sitemap, hidden from navigation, or described as “internal”. Therefore this repository may contain only `OPEN/P0` material or deliberately reduced `CONTROLLED/P1` projections. `PROTECTED/P2` and `FORBIDDEN/P3` material must live outside the public repository.

## Verification endpoints

### OPEN/P0 — required for public verification

- `manifest.json` — canonical identity, version, release hash and verification metadata.
- `claim-index.json` — stable public claim IDs and canonical URLs.
- `asset-index.json` — stable public asset names and canonical URLs.
- `disclosure-policy.json` — machine-readable BL-CPR publication boundary.
- public claim/theory pages — the statements actually being asserted, together with scope, status and falsifiers.

### CONTROLLED/P1 — reduced public projections only

- `claims.json` — public claim registry; not private reasoning traces.
- `novelty-ontology.json` — public ontology required to interpret novelty labels.
- `logic-stack.json` — **reduced unified conceptual projection only**. It describes the BL∞ public reasoning/integration route but must not enumerate the production router, operator sequence, activation logic, ranking, weights or private implementation graph.
- `bl-infinity-unified-system.json` — public typed supergraph for `BL-INF-UNIFY`: roles and conceptual relations among RVT/RVP/RVTP/RVL, BLEE, Academic Democracy, BL-HRD, BL-ADN, BL-PCRO/OODP/BLOK, BL-NOVO, BL-REV/AEGIS, BL-SFRET, OPT-HKRP, OHAS, KAT and release/feedback mechanisms. It is **not** an execution router.
- `bl-hrd.json` — public BL-HRD doctrine/state-machine contract: hypothesis-object schema, public conceptual state sequence, invariants, rights boundaries, reality-depth classes and anti-collapse guards. It is **not** the private routing implementation or weighting system.
- `graph.jsonld` — reduced public entity/relation graph.
- `historical-graph.jsonld` — reduced public chronology/origin projection; no raw conversation or private provenance payload.
- `bl-reverse-system.json` — public interface contract only; no adversarial production runtime.
- `welcome.txt` and `/llms.txt` — public orientation/discovery material.

## Never published here

```text
production prompts / boot prompts
activation triggers
private target selection or ranking
routing weights
operator/model handoff packages
private diagnostics
full operator inventories or production sequencing
raw or reconstructed private conversations
private corpora or unpublished source material
credentials / tokens / signing private keys
commercial execution details unrelated to public truth-status
```

## Publication invariant

```text
PUBLIC REPOSITORY != PRIVATE STORAGE
absence from sitemap != privacy
machine-readable != permission to disclose
verification need -> smallest sufficient projection
P2/P3 -> outside the public repository
```

A machine resource may expose only the minimum information required to identify, verify, critique, cite or interoperate with a **public** BL∞ claim. If a richer internal object is not needed to verify the public claim, it is withheld.

## Unified graph boundaries

`logic-stack.json` and `bl-infinity-unified-system.json` are conceptual public graphs. They do **not** mean that every named system is logically identical, historically derived from every other system, or operationally executed in the listed visual order.

```text
Lineage != Dependency != Identity != Historical Priority != Implementation
Unification != Identity Collapse
ConceptualCycle != ProductionRouter
```

The unified cycle is considered meaningful only when a pass produces an auditable epistemic or capability delta. Graph density, integration complexity or recurrence do not prove truth.

## Reality Veto boundary

The public graph may state that Reality Veto is a cross-system sovereign correction constraint and may expose the public relation `ValidRealityConflict -> ModelRevision`. It must not represent system authority as superior to external evidence.

## BL-REV boundary

The BL-REV public JSON declares only purpose, public inputs/outputs, authority limits, guardrails, falsifiers and reference behavior. Internal activation, target ranking, operator inventory, sequencing and diagnostics remain outside this repository.

## BL-HRD boundary

The BL-HRD public machine contract may declare the conceptual path from reality gap to hypothesis formation, preservation, mapping, depth/risk classification, verification, Reality Veto, state transition, lineage, negative-knowledge capture and recursive discovery. It may declare invariants such as `preserve != endorse` and `right_to_propose != right_to_execute`. It must not publish private routing weights, target ranking, operational triggers or protected execution playbooks.

## BL-INF-UNIFY boundary

The unified-system graph may expose:

- named systems and public roles;
- typed conceptual relations such as `GOVERNS`, `FEEDS`, `FORMALIZES`, `IMPLEMENTS`, `VERIFIES`, `ROUTES_TO`, `PREPARES`, `CONVERTS` and `LEARNS_FROM`;
- the public epistemic loop and capability loop;
- hard invariants and falsification surface.

It must not expose protected orchestration details, production scheduling, private coalition ranking, operational target selection, secret weights or private authority handoffs.

## Discovery rule

```text
fragment
-> public claim ID / asset ID / unified-system node
-> canonical public object
-> provenance class
-> version
-> evidence / falsifier
-> typed relations
-> disclosure class
```

Protected runtime objects deliberately have no public discovery route and must not be committed to this public repository.
