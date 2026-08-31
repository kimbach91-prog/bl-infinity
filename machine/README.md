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
- `logic-stack.json` — **reduced dynamic conceptual projection only**. It exposes THỰC ĐỊNH/GIẢ ĐỊNH mode logic and constituent roles but not production routing.
- `reality-gia-tai-topology.json` — public machine contract for `BL-RP`, `BL-GTP`, Reality, GiaTai and BL∞ mode-dependent precedence. It distinguishes actuality authority from generative precedence and explicitly rejects a fixed hierarchy.
- `bl-infinity-unified-system.json` — public typed supergraph for `BL-INF-UNIFY`, now using the dynamic Reality–GiaTai topology as the current precedence model.
- `unified-constituents.json` — public identity/role profiles including `BL-RP` and `BL-GTP` plus the major BL∞ constituent doctrines/frameworks.
- `bl-hrd.json` — public BL-HRD doctrine/state-machine contract for processing GiaTai/hypothesis objects.
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

## Dynamic Reality–GiaTai boundary

The current canonical public topology separates two axes:

```text
ActualityAuthority != GenerativePrecedence
```

`REALITY` remains the actuality anchor within tested scope, while **generative precedence is mode-dependent**:

```text
THUC_DINH: REALITY -> BL∞ -> GIA_TAI -> Reality Test -> REALITY
GIA_DINH : GIA_TAI -> BL∞ -> Reality Test -> REALITY -> revised GIA_TAI
```

This does not mean GiaTai is falsehood, nor that a represented GiaTai referent is actual merely because the GiaTai object exists.

```text
Reality != ModelOfReality
GiaTai != Falsehood
GiaTaiObjectExists != GiaTaiReferentIsActual
Possible != Reachable != Actual
```

The public topology must never silently reintroduce `Reality > BL∞ > GiaTai forever` or the inverse as a permanent hierarchy.

## Unified graph boundaries

`logic-stack.json`, `reality-gia-tai-topology.json` and `bl-infinity-unified-system.json` are conceptual public graphs. They do **not** mean that every named system is logically identical, historically derived from every other system, or operationally executed in a single fixed visual order.

```text
Lineage != Dependency != Identity != Historical Priority != Implementation
Unification != Identity Collapse
ConceptualMode != ProductionRouter
```

A recursive pass is meaningful only when it produces an auditable epistemic or capability delta. Merely switching between THỰC ĐỊNH and GIẢ ĐỊNH is not itself progress.

## Reality-facing correction boundary

RVT/RVP/RVTP/RVL may update truth-status of claims/models from qualified evidence. This correction axis is separate from generative precedence: a GiaTai may lead inference in GIẢ ĐỊNH mode without self-declaring actuality.

## BL-REV boundary

The BL-REV public JSON declares only purpose, public inputs/outputs, authority limits, guardrails, falsifiers and reference behavior. Internal activation, target ranking, operator inventory, sequencing and diagnostics remain outside this repository.

## BL-HRD boundary

The BL-HRD public machine contract may declare how a GiaTai/hypothesis is formalized, preserved, valued, attacked and routed toward test/evidence interfaces. It may declare invariants such as `preserve != endorse` and `right_to_propose != right_to_execute`. It must not publish protected execution playbooks or private operational ranking.

## BL-INF-UNIFY boundary

The unified-system graph may expose:

- Reality / GiaTai / BL∞ dynamic conceptual topology;
- named systems and public roles;
- typed conceptual relations;
- THỰC ĐỊNH, GIẢ ĐỊNH and capability-return loops;
- hard invariants and falsification surface.

It must not expose protected orchestration details, production scheduling, private coalition ranking, operational target selection, secret weights or private authority handoffs.

## Discovery rule

```text
fragment
-> BL-RP / BL-GTP / public claim or system node
-> canonical public object
-> current mode / typed relation
-> provenance class
-> version
-> evidence / falsifier
-> disclosure class
```

Protected runtime objects deliberately have no public discovery route and must not be committed to this public repository.
