# BL-CPR — Public Disclosure & Protected Runtime Policy

**Status:** ADOPTED  
**Version:** 1.2  
**Effective:** 2026-08-31  
**Applies to:** every public BL∞ repository, branch, Pages build, machine endpoint and release artifact.

## Rule

Publish what a reader needs to identify, verify, critique, cite and extend a public BL∞ claim. Do **not** publish the private production runtime, operator handoff, detailed private reasoning trace, raw conversation, private orchestration logic or security-sensitive material merely because it is technically convenient to keep it beside the public theory.

Public verifiability does not require full runtime disclosure.

## Public repository boundary

A public Git repository is itself an exposure boundary. **Anything committed to a public repository must be treated as public/exposed**, even when it is absent from the website navigation, excluded from the sitemap, or described as “internal”. Therefore:

- `OPEN/P0` objects may live in the public repository when they are required for verification/interoperability.
- `CONTROLLED/P1` objects may live there only as deliberately reduced projections.
- `PROTECTED/P2` and `FORBIDDEN/P3` objects must live outside the public repository.
- absence from navigation, sitemap or search indexing is **not** a privacy control;
- machine-readable form is not permission to disclose a richer internal object;
- when verification needs a machine interface, publish the **smallest sufficient projection**.

## Always public when asserted by BL∞

- canonical identity, version and authorship/provenance class;
- claim text, type, status, scope, dependencies and falsifier;
- evidence that determines truth-status, including adverse evidence;
- public critique, resolution reason and supersession history;
- public definitions, assumptions and derivations needed to assess a claim;
- schemas, test vectors and minimal reference behavior needed for interoperability;
- limitations, non-claims, security assumptions and change history;
- a **sanitized provenance summary** sufficient to establish the claimed public origin/status without exposing private conversation or operator traces.

## Protected or controlled

The following are not part of the public release unless a specific verification need outweighs the disclosure cost:

- complete production prompts, boot prompts and orchestration instructions;
- model-to-model or operator handoff packages;
- private routing/ranking heuristics, activation triggers and diagnostics;
- asset-level production architecture or runtime composition;
- full internal adversarial operator lists or production decision pipelines;
- private refinement/playbook procedures whose disclosure mainly increases execution-copy risk;
- raw or reconstructed private conversations beyond the minimum public provenance summary;
- detailed generative reasoning traces that are not required to verify the final public claim;
- private corpora, personal data and unpublished source material;
- commercial execution details that do not determine whether a public claim is true.

A public machine contract may expose purpose, inputs/outputs, authority boundaries, guardrails and reference behavior. It must not silently become a dump of the production runtime behind that contract.

## Forbidden in public

- credentials, signing/private keys, tokens and private infrastructure configuration;
- personal/private data without a lawful and explicit publication basis;
- unpatched exploit payloads or high-misuse operator procedures;
- raw private transcripts/conversation dumps;
- production runtime directories or files explicitly classified `PROTECTED/P2` or `FORBIDDEN/P3`;
- public branches retained solely to preserve protected handoff/runtime snapshots.

## Four disclosure states

`OPEN/P0` — needed for verification/interoperability and safe to publish.  
`CONTROLLED/P1` — a reduced interface or summary is public; the richer internal object is not published.  
`PROTECTED/P2` — retain privately; public truth-status does not depend on disclosure.  
`FORBIDDEN/P3` — credentials, private keys, unlawfully exposed personal data, unpatched exploit material or equivalent.

## Release decision

`OPEN` when verification + human benefit + indexability + priority proof outweigh copy + misuse + security + decontextualization risk.  
`CONTROLLED` when verification benefits from an interface but full disclosure adds material risk.  
`PROTECTED` when the object mainly affects production advantage, private reasoning, privacy or internal orchestration rather than public truth-status.  
`FORBIDDEN` for material that must not be public.

If an unavailable object is necessary to verify a claim, the claim must be narrowed, marked speculative/insufficiently evidenced, withheld, or supplied through an appropriate controlled review. Secrecy cannot create logical immunity.

## Machine/public projections

The public machine layer is an attestation/verification surface, not a mirror of the internal system. In particular:

- `manifest.json`, claim/asset indexes and the disclosure policy are `OPEN/P0` verification artifacts;
- claim registries, novelty ontology, entity/history graphs and public adversarial contracts are `CONTROLLED/P1` when they are reduced to what public verification needs;
- `logic-stack.json` must remain a coarse conceptual projection and must not enumerate the asset-level runtime architecture, router, activation logic, target ranking, weights, operator sequence or private diagnostics;
- public provenance graphs must not contain raw conversations or detailed private reconstruction payloads.

## Build and repository enforcement

- `machine/disclosure-policy.json` is the machine-readable policy.
- `scripts/disclosure_audit.py --strict` is a mandatory release gate.
- `.github/workflows/pages.yml` runs the gate before each public build.
- provenance and critique pages use explicit public allowlists; they do not publish every Markdown file found in a directory.
- `.gitignore` blocks standard protected paths and production-prompt filename families.
- the gate rejects operator/handoff/raw-conversation paths and rejects public references that would route readers back to removed protected files.
- machine contracts are checked for production-only fields that exceed their public interface.

Ignore rules are not a security boundary.

## Historical exposure response

If protected material was previously committed publicly:

1. preserve the object privately with source identity/hash when appropriate;
2. remove or sanitize it in the active public tree;
3. rebuild the public branch from a clean ancestry anchor when feasible;
4. move remaining public branch refs away from the exposed commits;
5. regenerate Pages/search artifacts so cached public pages stop serving the removed material;
6. record the purge as a causal event without republishing the protected payload.

Git hosting providers may retain unreachable objects/caches for a period after refs are rewritten. When byte-level eradication is legally/security necessary, provider-side sensitive-data purge may still be required; the public repository must not pretend a normal deletion commit alone erased history.

## Attribution

Origin of the decision problem and adoption: Bách Lâm. Formalization and implementation: AI under Bách Lâm's direction. This is not represented as a verbatim historic quote.

**ADN BÁCH LÂM ∞** · `BL-CPR/1.2` · `status: ADOPTED` · `truth_status: POLICY`
