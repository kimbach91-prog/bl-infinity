# BL-CF — Legal, IP and Open-Source Architecture v0.3

Status: FOUNDER-DIRECTED LEGAL DESIGN DRAFT

This document separates five things that must not be confused: Founder/first-party IP ownership, open-source licenses, contributor IP, ownership of contributed compute, and economics/governance of the official federation.

## 1. Founder ownership and open source can coexist

Copyright ownership and open-source licensing are different layers.

The Founding Steward or designated legal IP owner may own first-party source code and grant the public an open-source license for selected code. That license does not by itself transfer:

- copyright ownership;
- trademarks or official federation identity;
- official registry/signing authority;
- domain names;
- private datasets;
- confidential know-how/trade secrets;
- separately licensed premium/intelligent coordination technology.

Third-party contributors retain independently created rights unless an explicit agreement transfers or licenses them.

## 2. Recommended capture-resistant legal split

### A. Founder-controlled IP / Steward owner

Should own/administer, where legally established:

- first-party BL-CF/DEUS copyright;
- BL-CF/DEUS trademarks and official brand;
- domains, canonical namespace and registry identity;
- official release-signing identity;
- private routing/scoring/security/evaluation know-how;
- patent/trade-secret assets;
- conditional licenses granted to Operators.

### B. Federation Operator

The Operator should:

- contract with Node Providers and Workload Submitters;
- operate production infrastructure;
- meter/settle commercial transactions;
- employ staff and hold operational liabilities;
- implement ratified federation policies.

The Operator receives a conditional license to official BL-CF IP. A sale/change of control of the Operator must not automatically transfer underlying Founder-owned IP unless an explicit legal instrument says so.

## 3. Correct meaning of the 10% commercial right

The default 10% is **not defined as 10% equity**.

It is the **Official Protocol Commercial Share**: by default, 10% of Eligible Commercial Settlement Value (ECSV) for eligible commercial workloads transacted through the official federation, in consideration for the official protocol, intelligent coordination, security architecture, trust registry, validation/settlement framework, and continuing protocol development.

The applicable commercial contract must define ECSV and disclose the share before acceptance.

This contractual economic right is separate from:

- Founder personal/company equity;
- provider ownership of its hardware;
- provider compensation;
- the 5–10% common-benefit compute envelope;
- separately priced Founder-owned premium IP/services.

Any future equity/capitalization plan must be designed independently.

## 4. Common-benefit compute is not property

The 5% target / 10% default ceiling is a scheduling envelope over **eligible capacity that providers explicitly opted into common-benefit scheduling**.

It does not transfer hardware, accounts, energy, data, or ungranted compute rights to BL-CF.

Each Node Contribution Agreement should expressly define:

- whether the node opts into common-benefit scheduling;
- the provider's own maximum share, which may be below 10%;
- allowed workload/data classes;
- commercial opt-in separately;
- expiry/revocation;
- emergency override, if any.

## 5. Founder control should not rely only on shares

Anti-capture should rely on a layered legal/technical structure:

1. Founder/designated-owner IP ownership;
2. separate trademark and official identity ownership;
3. conditional Operator license;
4. constitutional/canonical signing authority;
5. reserved matters and high voting thresholds where lawful;
6. independent root/recovery controls;
7. contractual continuity rights.

Any proposed 'golden share', preferred voting arrangement, foundation/trust structure, or special share class must be reviewed under the law of the chosen entity jurisdiction rather than assumed perpetual.

## 6. Current code-license reality

The repository currently contains `LICENSE-CODE`, which licenses existing covered code under the MIT License and identifies Lâm Kim Bách as copyright holder for that license notice.

Therefore BL-CF must **not silently claim that the existing runtime has already become AGPL**.

Before applying AGPL-3.0-only to any existing code, perform a rightsholder/contributor audit and confirm that the party doing the relicensing has the necessary rights.

Recommended path:

- preserve existing MIT obligations for already released MIT-covered code;
- choose a clearly scoped future component/directory/rewrite for AGPL-3.0-only if network copyleft remains strategically desirable;
- add SPDX/package metadata making license scope unambiguous;
- never remove third-party license notices.

## 7. Official service policy vs open-source license

The official federation may prohibit spam, hidden mining, fake engagement, malware, unauthorized security activity and other abuse through its Acceptable Use Policy and participant contracts.

Those service restrictions should not be inserted into an OSI open-source license in a way that discriminates against fields of endeavor while still calling the license Open Source.

Code openness and access to the official federation are different rights.

## 8. Trademark and canonical identity

A code fork may exercise its software-license rights. It does not automatically receive the right to impersonate the official service.

A trademark policy should reserve:

- official BL-CF / DEUS names and logos where registered/protected;
- 'official/verified node' marks;
- official registry status;
- official certification/compatibility marks.

It should permit truthful references such as 'compatible with BL-CF protocol' where not confusing.

## 9. Contributor model

Recommended initial model:

- DCO-style Signed-off-by attestation for ordinary patches;
- CLA when BL-CF needs broader official-distribution/relicensing/dual-licensing rights;
- explicit assignment only when transfer of ownership is genuinely intended;
- no automatic claim over unrelated inventions, hardware, data, employer IP, or pre-existing code.

## 10. Copyright registration in Vietnam

Copyright in computer programs generally arises without registration, but registration of major Founder-owned release snapshots can strengthen evidence for licensing, financing, enforcement and ownership disputes.

Before filing, freeze the exact deposited scope:

- repository/commit/tag;
- SHA-256/source archive;
- author(s);
- legal copyright owner(s);
- contributor/rightsholder evidence;
- accurate AI-assistance disclosure where required by the filing procedure then in force;
- ownership/assignment documents where author and owner differ.

Use the live official government procedure at filing time; do not claim registration until a real filing/certificate exists.

## 11. Trademark registration

Priority clearance candidates:

- BL Compute Federation;
- BL-CF;
- DEUS, if legally clear/registrable;
- official logos;
- future official-node/certification marks.

Final goods/services classes should be based on actual products/services and professional clearance, not broad guesses.

## 12. Patent vs trade secret

Before publishing a genuinely novel technical mechanism, classify it:

- patent candidate: assess prior art and filing strategy before unnecessary disclosure;
- trade secret: maintain confidentiality, access controls and contractual duties.

Private routing/scoring heuristics, anti-abuse thresholds, proprietary evaluation corpora and security-sensitive coordination techniques need not be public merely because the federation exposes an open protocol.

## 13. Open-source legitimacy and provenance

There is no universal government office that 'registers a project as open source'.

Legitimate open-source practice comes from actual license terms and source availability. Complement it with:

- SPDX/license metadata;
- signed release tags/manifests;
- SBOM/provenance where practical;
- independent source mirrors;
- long-term release archive;
- SECURITY/CONTRIBUTING/trademark policies;
- copyright/trademark government records for ownership/brand evidence.

## 14. Electronic contracts

NCA, WSA, Research Admission, Commercial Addendum, Shared-Benefit Contract, DPA, Settlement Schedule and DEUS Mandate should be versioned, retrievable, hash-addressed agreements with affirmative acceptance evidence.

Higher-value, regulated, equity/IP-transfer, or jurisdiction-sensitive transactions should use an electronic/digital signature method appropriate to the actual transaction and applicable law.

## 15. Canonical headquarters

GitHub may be the primary constitutional publication host, but no Git provider should be the sole legal or technical root.

Canonical identity should be reconstructable from:

- signed release history;
- independent mirrors;
- Founder/steward root identity;
- domain/trademark ownership records;
- government IP records;
- offline recovery material.

A hosting provider can host BL-CF; controlling that hosting account must not be enough to become BL-CF.
