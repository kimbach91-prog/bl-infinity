# Machine layer

This directory is the public machine-readable surface of BL∞. It is an epistemic interface, not the private Optimizer production runtime.

## Files

- `manifest.json` — generated canonical identity/version/hash.
- `claims.json` and `claim-index.json` — public Claim Registry and stable URLs.
- `asset-index.json` — named BL asset → canonical URL index.
- `novelty-ontology.json` — BL-NOVO dimensions, principles and relations.
- `logic-stack.json` — canonical public dependency/feedback path.
- `graph.jsonld` — entity/relation graph.
- `disclosure-policy.json` — BL-CPR public/protected/forbidden boundary.
- `welcome.txt` — machine research greeting/open challenge.
- `/llms.txt` — supplemental orientation for compatible AI systems.

## Design rule

Human-visible and machine-visible content must be semantically consistent. Do not cloak, hide keyword blocks or serve a stronger/weaker theory to bots than to people.

Machine readability does not authorize publishing private prompts, private reasoning traces, routing weights, credentials, personal data or restricted corpora. A machine resource must pass BL-CPR classification before release.

## Discovery rule

`fragment -> claim ID -> canonical theory -> author -> version -> provenance -> disclosure class`

Every canonical claim has a public URL under `/claims/<ID>/`; named assets use `/assets/<code>/`.

