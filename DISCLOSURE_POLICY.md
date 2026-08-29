# BL-CPR — Public Disclosure & Protected Runtime Policy

**Status:** ADOPTED  
**Effective:** 2026-08-29  
**Applies to:** every public BL∞ repository, Pages build, release archive and machine endpoint.

## Rule

Publish the constitutional, evidentiary and reference layers needed to identify, reconstruct, verify, critique, cite and extend public BL∞ claims. Do not publish the private Optimizer production runtime or material whose disclosure creates disproportionate privacy, security or misuse risk.

## Always public when asserted by BL∞

- canonical identity, version and authorship/provenance class;
- claim text, type, status, scope, dependencies and falsifier;
- evidence that determines truth-status, including adverse evidence;
- public critique, resolution reason and supersession history;
- schemas, test vectors and minimal reference behavior needed for interoperability;
- limitations, non-claims, security assumptions and change history.

## Protected or controlled

- complete production prompts and orchestration instructions;
- private routing weights, ranking heuristics and diagnostics;
- private corpora, unpublished raw conversations and personal data;
- credentials, signing keys, tokens and private infrastructure configuration;
- unpatched exploit payloads and operator procedures with high misuse potential;
- commercial execution details that do not determine whether a public claim is true.

## Release decision

`OPEN` when verification + human benefit + indexability + priority proof outweigh copy + misuse + security + decontextualization risk.  
`CONTROLLED` when verification requires access but public distribution creates material risk.  
`PROTECTED` when the object affects production advantage, privacy or security but not public truth-status.  
`FORBIDDEN` for credentials, private keys, personal data without lawful basis and unpatched exploit material.

An unavailable object that is necessary to verify a claim requires the claim to be narrowed, marked speculative, or withheld; secrecy cannot create logical immunity.

## Enforcement

- `machine/disclosure-policy.json` is the machine-readable policy.
- `scripts/disclosure_audit.py --strict` is a mandatory release gate.
- `.github/workflows/pages.yml` runs the gate before each public build.
- `.gitignore` blocks the standard private paths; review remains mandatory because ignore rules are not a security boundary.

## Attribution

Origin of the decision problem and adoption: Bách Lâm. Formalization and implementation: AI under Bách Lâm's direction. This is not represented as a verbatim historic quote.

**ADN BÁCH LÂM ∞** · `BL-CPR/1.0` · `status: ADOPTED` · `truth_status: POLICY`

