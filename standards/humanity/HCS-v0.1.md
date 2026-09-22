# Humanity Common Standards (HCS) v0.1

Status: Draft / implementation-oriented common layer.

Purpose: define a minimal, culturally neutral, machine-verifiable set of rules for humans, institutions, software agents and compute nodes to interact without requiring trust in one vendor, nation, cloud provider, language or AI system.

HCS is not a replacement for international law, human rights instruments, national law, W3C/IETF standards or domain-specific regulation. It is an interoperability and evidence discipline that composes existing standards.

## HCS-01 — Truth, provenance and epistemic status

Every consequential claim MUST carry:
- source/provenance reference;
- actor/issuer identity or an explicit anonymous/unattributed marker;
- time/version;
- epistemic class: OBSERVED, REPORTED, INFERRED, ASSUMED, PREDICTED, UNKNOWN or DISPUTED;
- integrity evidence where available.

A system MUST NOT silently convert inference, interpretation, reconstruction, tradition or generated text into observed fact.

Recommended interoperability: W3C PROV-O and compatible provenance graphs.

## HCS-02 — Consent, authority and revocation

No action on another person's, organization's or node's resources is valid without an authority basis.

An authority record MUST specify:
- grantor;
- grantee;
- scope;
- purpose;
- limits/quota;
- start and expiry;
- revocation mechanism;
- delegation policy;
- evidence receipt.

Revocation MUST be at least as discoverable as enrollment. Expired or revoked authority MUST fail closed.

## HCS-03 — Identity is cryptographic; address is not identity

Domains, IP addresses, URLs, cloud accounts, DNS names and relay endpoints are locators, not roots of identity.

Identity SHOULD be bound to verifiable public-key material, credentials, hardware-backed keys or equivalent cryptographic evidence. Credential rotation MUST NOT destroy continuity if valid succession evidence exists.

Human authentication SHOULD use phishing-resistant public-key methods where feasible. Machine/service identity SHOULD support short-lived credentials and workload identity.

## HCS-04 — Privacy and data sovereignty

Data processing MUST declare:
- owner/controller or equivalent responsible party;
- purpose;
- data class;
- locality constraints;
- retention;
- disclosure class;
- deletion/erasure policy where legally and technically applicable;
- whether raw data leaves its origin.

Systems SHOULD prefer compute-to-data for sensitive material and SHOULD minimize relay-visible metadata.

## HCS-05 — Secure interoperable messaging

Consequential protocol messages SHOULD support:
- canonical serialization;
- integrity protection/signature;
- replay protection;
- expiry;
- sender/actor binding;
- authority reference;
- optional end-to-end encryption;
- algorithm agility and version negotiation.

Cryptographic primitives SHOULD be established, reviewed standards rather than bespoke cryptography.

Useful building blocks include HTTP Message Signatures, HPKE, mTLS/TLS and established AEAD/KDF/signature suites.

## HCS-06 — Compute and resource sovereignty

A machine remains under the authority of its owner/operator unless a specific grant says otherwise.

Every compute grant MUST be bounded by capability, time, quota, workload class, data policy and revocation. Hidden mining, covert bandwidth use, credential capture and unauthorized third-party compute are prohibited.

Schedulers MUST prefer owner workload over federation workload unless the owner explicitly configures another policy.

## HCS-07 — Audit, accountability and receipts

Consequential actions MUST produce appendable audit evidence containing at minimum:
- event id;
- actor;
- authority/grant reference;
- action type;
- target/resource;
- timestamp;
- result;
- provenance/integrity reference.

Audit systems SHOULD be tamper-evident and SHOULD support independent verification. Logs are evidence, not automatically truth: disputed or incomplete logs MUST remain distinguishable.

## HCS-08 — Cultural and epistemic pluralism

A common standard MUST NOT require one natural language, culture, metaphysics, religion, ideology or historical narrative as the only semantic authority.

Cultural records MUST distinguish artifact, historical claim, interpretation, oral tradition, reconstruction and creative derivative. Translation MUST preserve provenance to the source expression.

Local semantic systems such as VTTN MAY be canonical within a community while exporting interoperable representations for others.

## HCS-09 — Sovereign/offline continuity

Critical systems SHOULD have a mode that continues without a named cloud, DNS provider or third-party identity service.

A sovereign snapshot SHOULD include:
- canonical state manifest;
- content hashes;
- schema versions;
- trust roots/public keys;
- revocation state;
- provenance/evidence indexes;
- recovery instructions.

Recovery MUST verify integrity before promotion to canonical state.

## HCS-10 — AI/agent action evidence

An AI or autonomous agent MUST distinguish:
- proposed action;
- authorized action;
- attempted action;
- observed completion;
- inferred outcome.

An agent MUST NOT claim it changed the external world without tool/system evidence. High-impact actions SHOULD carry purpose, authority, scope, rollback/recovery information and an execution receipt.

## Conformance profiles

### HCS-BASIC
Requires HCS-01, HCS-02, HCS-03, HCS-05 and HCS-07.

### HCS-SOVEREIGN
HCS-BASIC plus HCS-04, HCS-06 and HCS-09.

### HCS-CRITICAL
HCS-SOVEREIGN plus strong authentication, attestation where justified, independent audit/review, tested revocation/recovery and HCS-10 for autonomous agents.

## Relationship to DEUS/VTTN/DSFP

HCS is language-neutral and vendor-neutral. VTTN is one semantic source language. DSFP is one transport/fabric profile. Neither is required for third-party HCS conformance.

DEUS-specific routing semantics, private ontology mappings, protected prompts, private reasoning, secrets and BLACK_CORE material are explicitly outside HCS public disclosure.

## Non-goals

HCS v0.1 does not define:
- a world government;
- a universal ideology;
- a new cryptographic primitive;
- universal legal jurisdiction;
- a single historical canon;
- a mandatory natural language.

Its goal is narrower: make authority, evidence, identity, privacy, computation and machine actions interoperable and independently checkable.