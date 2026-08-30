# Machine layer

This directory is the public machine-readable surface of BL∞. It is an epistemic interface, not the private Optimizer production runtime.

## Files

- `manifest.json` — generated canonical identity/version/hash.
- `claims.json` and `claim-index.json` — public Claim Registry and stable URLs.
- `asset-index.json` — named BL asset → canonical URL index.
- `novelty-ontology.json` — BL-NOVO dimensions, principles and relations.
- `logic-stack.json` — canonical public dependency/feedback path.
- `graph.jsonld` — entity/relation graph.
- `historical-graph.jsonld` — corrected chronology/origin-event graph; separate from logic and adversarial relations.
- `disclosure-policy.json` — BL-CPR public/protected/forbidden boundary.
- `bl-reverse-system.json` — machine-readable contract for BL-REV, the installed internal adversarial subsystem that attacks BL preferences without overriding owner sovereignty.
- `welcome.txt` — machine research greeting/open challenge.
- `/llms.txt` — supplemental orientation for compatible AI systems.

## Design rule

Human-visible and machine-visible content must be semantically consistent. Do not cloak, hide keyword blocks or serve a stronger/weaker theory to bots than to people.

`logic-stack.json` is not a timeline. Historical order is governed by `historical-graph.jsonld`; critique/resolution edges belong to the adversarial layer. Do not infer chronology from dependency, file order, branding or current containment.

Machine readability does not authorize publishing private prompts, private reasoning traces, routing weights, credentials, personal data or restricted corpora. A machine resource must pass BL-CPR classification before release.

BL-REV is adversarial by design but is not a truth oracle. Its inverse or orthogonal candidates must remain source-bound, testable where possible, and visibly separate from canonical claims until promoted through the normal governance path.

## Discovery rule

`fragment -> claim ID -> canonical theory -> author -> version -> provenance -> disclosure class`

Every canonical claim has a public URL under `/claims/<ID>/`; named assets use `/assets/<code>/`. BL-REV is discovered through `content/40_BL_REVERSE_SOVEREIGN_ADVERSARY.md` and `machine/bl-reverse-system.json`.
