# Machine layer

This directory is the **public machine-readable interface** of BL∞. It exists so claims, identities, dependencies, versions and reference behaviors can be discovered and checked by software. It is not the private Optimizer/BLCC production runtime and is not a repository for internal orchestration.

## Public files

- `manifest.json` — generated canonical identity/version/hash.
- `claims.json` and `claim-index.json` — public Claim Registry and stable URLs.
- `asset-index.json` — named BL asset → canonical URL index.
- `novelty-ontology.json` — public BL-NOVO dimensions, principles and relations.
- `logic-stack.json` — public logical/dependency/feedback view; not a private router.
- `graph.jsonld` — public entity/relation graph.
- `historical-graph.jsonld` — reduced public chronology/origin graph, separate from logical dependency.
- `disclosure-policy.json` — BL-CPR public/protected/forbidden boundary.
- `bl-reverse-system.json` — **public interface contract only** for BL-REV.
- `welcome.txt` — public machine research greeting/open challenge.
- `/llms.txt` — supplemental public orientation for compatible AI systems.

## Design rule

Human-visible and machine-visible public claims must be semantically consistent. Do not cloak, hide keyword blocks or serve a stronger/weaker theory to bots than to people.

A public machine resource may expose:

```text
identity
purpose
public inputs / outputs
authority boundaries
guardrails
falsifiers
reference behavior
```

It must not expose merely because machines can parse it:

```text
production prompts
activation triggers
private target selection or ranking
routing weights
operator/model handoff
private diagnostics
raw private conversation/corpus
full production pipeline
```

Those are protected by BL-CPR unless a specific verification requirement justifies a controlled/public release.

## Graph boundaries

`logic-stack.json` is not a timeline. Historical order is governed by the public historical graph. Critique/resolution relations are also distinct from both historical and logical dependency relations.

```text
Lineage != Dependency != Identity != Historical Priority
```

Machine readability, graph density or indexability do not prove truth or novelty.

## BL-REV boundary

The public BL-REV JSON declares the adversarial interface, authority limits and observable behavior. Internal activation, target ranking, operator inventory, sequencing and diagnostics are intentionally absent. A counterposition produced by BL-REV is not truth by default and must pass the same evidence/provenance/governance path as any other candidate.

## Discovery rule

```text
fragment
-> claim ID
-> canonical public claim/theory
-> author/provenance class
-> version
-> evidence/falsifier
-> disclosure class
```

Every canonical public claim has a stable route under `/claims/<ID>/`; named assets use `/assets/<code>/`. Protected runtime objects deliberately have no public discovery route.
