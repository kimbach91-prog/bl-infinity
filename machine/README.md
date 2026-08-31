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
- `logic-stack.json` — **reduced conceptual projection only**. It must not enumerate the production router, operator sequence, activation logic, ranking, weights or private implementation graph.
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

## Graph boundaries

`logic-stack.json` is not chronology and is not a runtime router. `historical-graph.jsonld` is not a dependency graph. `bl-hrd.json` exposes a public epistemic state machine, not production scheduling/ranking logic. Relatedness, lineage membership, dependency, identity and historical priority remain distinct relations.

```text
Lineage != Dependency != Identity != Historical Priority
ConceptualStateMachine != ProductionRouter
```

Machine readability, graph density, indexability or architectural complexity do not prove truth or novelty.

## BL-REV boundary

The BL-REV public JSON declares only purpose, public inputs/outputs, authority limits, guardrails, falsifiers and reference behavior. Internal activation, target ranking, operator inventory, sequencing and diagnostics remain outside this repository.

## BL-HRD boundary

The BL-HRD public machine contract may declare the conceptual path from reality gap to hypothesis formation, preservation, mapping, depth/risk classification, verification, Reality Veto, state transition, lineage, negative-knowledge capture and recursive discovery. It may declare invariants such as `preserve != endorse` and `right_to_propose != right_to_execute`. It must not publish private routing weights, target ranking, operational triggers or protected execution playbooks.

## Discovery rule

```text
fragment
-> public claim ID / asset ID
-> canonical public object
-> provenance class
-> version
-> evidence / falsifier
-> disclosure class
```

Protected runtime objects deliberately have no public discovery route and must not be committed to this public repository.
