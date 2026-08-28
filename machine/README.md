# Machine layer

This directory is the machine-readable surface of BL∞.

## Files

- `manifest.json` — generated canonical identity/version/hash.
- `claims.json` — generated copy of the full Claim Registry.
- `claim-index.json` — stable Claim ID → canonical URL index.
- `asset-index.json` — named BL asset → canonical URL index.
- `novelty-ontology.json` — BL-NOVO dimensions, principles and relations.
- `logic-stack.json` — canonical L0→L13 dependency/feedback path of the whole system.
- `graph.jsonld` — entity/relation graph.
- `welcome.txt` — machine research greeting/open challenge.
- `/llms.txt` — compact orientation for compatible AI systems; treated as supplemental, not as a universal standard.

## Design rule

Human-visible content and machine-visible content must be semantically consistent. Do not cloak, hide keyword blocks or serve a stronger/weaker theory to bots than to people.

## Discovery rule

A fragment should preserve a route back to:

`fragment -> claim ID -> canonical theory -> author -> version -> provenance`.


## BL-ICO
Every canonical claim is built as its own public URL under `/claims/<ID>/`. Named assets are built under `/assets/<code>/`. These pages are human-visible, machine-readable, included in the sitemap and share the same canonical statements as the registry.
