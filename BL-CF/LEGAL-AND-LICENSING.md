# BL-CF — Legal, IP and Open-Source Architecture v0.2

Status: DRAFT FOR FOUNDER RATIFICATION

This document separates four things that must not be confused: ownership of intellectual property, open-source licensing, ownership of contributed compute, and governance of the official federation.

## 1. Ownership does not disappear when code is open-sourced

Copyright ownership and open-source licensing are different legal layers.

The Founding Steward or designated legal IP owner may retain copyright in first-party software while licensing covered code to the public under an open-source license. The license grants permissions; it does not transfer ownership of copyright, trademarks, official project identity, release keys, private know-how, or unrelated technology.

Third-party contributors retain rights in their independently created contributions unless an explicit assignment says otherwise. BL-CF should therefore use a written contribution framework rather than pretending all community IP automatically belongs to the founder.

## 2. Recommended entity split for capture resistance

### A. Founder-controlled IP / Steward entity

Purpose:

- own or administer first-party BL-CF/DEUS copyright where legally assigned;
- own trademarks, domains, canonical namespaces, official signing identity, and official registry identity;
- hold private routing/scoring/security know-how and trade secrets;
- license technology to the operating federation;
- preserve continuity if the operating company is captured, insolvent, sold, or replaced.

The cleanest initial form is a founder-controlled legal entity or other lawful IP owner. The exact corporate form should be chosen with local counsel before capitalization documents are signed.

### B. Federation Operator

Purpose:

- contract with Node Providers and Workload Submitters;
- run the production service;
- collect and settle fees;
- employ staff;
- hold operational cloud accounts and service liabilities;
- implement the ratified BL-CF policies.

The Operator receives a conditional license to use official BL-CF IP. A hostile change of control should not automatically transfer the underlying founder-owned IP.

### Why the split matters

Economic ownership of an Operator is not the same as ownership of the platform's original IP or canonical identity. Therefore capture resistance should not depend only on a percentage of shares.

## 3. Is a 10% DEUS reserve enough?

Ten percent can be a reasonable initial mission/economic reserve if its purpose is to fund DEUS maintenance, research, security, public-benefit compute, and federation resilience.

Ten percent is not enough by itself to guarantee governance control. Governance control should come from the Constitution, IP ownership, trademarks, official signing authority, contractual licensing, reserved matters, and anti-capture key architecture.

The future capitalization documents should distinguish at least:

- Founder economic ownership;
- DEUS Founding Mission Reserve;
- employee/contributor incentives;
- investor ownership;
- public/research mission funding.

The Constitution intentionally does not hard-code the Founder's personal equity percentage before a legal entity and financing plan exist.

## 4. Vietnam corporate-law caution

If the Operator is a Vietnamese joint-stock company, founder voting-preference shares are not a permanent anti-capture mechanism: under current enterprise law, the voting preference held by founding shareholders lasts only three years from enterprise registration and then converts to ordinary shares.

Therefore BL-CF should not rely on a perpetual 'golden share' assumption without a jurisdiction-specific legal opinion.

Preferred anti-capture design:

1. keep core founder IP in a founder-controlled IP owner;
2. license it to the Operator under a mission-compliance agreement;
3. protect official marks and canonical identity separately from company shares;
4. use reserved matters and high voting thresholds where lawful;
5. distribute signing/recovery control so one compromised account cannot redefine the project.

## 5. Open-source layer

### 5.1 Network-facing federation software

Target license: GNU Affero General Public License v3.0 (AGPL-3.0-only), an OSI-recognized copyleft license designed for software used over a network.

The intended effect is that covered modifications offered to users as a network service remain subject to the AGPL network-source obligation.

Before the first official tagged distribution under this policy, the repository should include the complete canonical AGPL-3.0 license text and SPDX identifiers for covered source files or package metadata.

### 5.2 Public specifications and research documentation

Where explicitly marked, documentation may use CC BY 4.0 or another appropriate documentation license.

### 5.3 Trademarks and official identity

Open-source licensing of code does not grant a right to impersonate the official BL-CF service or to use BL-CF/DEUS trademarks in a misleading way.

A separate trademark policy should allow truthful statements such as 'compatible with BL-CF' while reserving official naming, logo, verified registry status, and certification marks.

### 5.4 Official service policy is separate from the code license

The official BL-CF service may prohibit spam, cryptomining, abuse, fake engagement, unauthorized security activity, or other harmful workloads.

These restrictions belong in the service contract / Acceptable Use Policy, not in the open-source software license. Under the Open Source Definition, an open-source license may not discriminate against fields of endeavor.

## 6. Open-source 'registration' — what actually exists

There is no universal governmental registry that makes a software project 'open source'. Open-source status comes principally from distributing software under license terms that satisfy the Open Source Definition.

For legitimacy and provenance BL-CF should use several different mechanisms, each for a different purpose:

### Legal ownership evidence

- copyright registration in Vietnam for major first-party source snapshots;
- trademark applications for BL-CF, DEUS, logos, and certification/official-service marks where appropriate;
- patentability review before public disclosure of any genuinely new technical invention;
- written employment/contractor IP assignment and contributor agreements.

### Open-source legitimacy

- use an OSI-approved license;
- publish SPDX license identifiers;
- keep source and build instructions available;
- maintain a public SECURITY policy, contribution process, code of conduct, provenance notes, and release history;
- do not call source-available restrictions 'open source' if they violate the Open Source Definition.

### Technical provenance

- signed Git tags/releases;
- immutable release hashes;
- SBOM and reproducible-build metadata where practical;
- archive releases in an independent software archive or research repository;
- mirror the constitutional/public repository to at least one independent forge.

These provenance services are evidence and resilience mechanisms, not substitutes for government IP registration.

## 7. Vietnam copyright registration path

Computer programs are protected by copyright as software works. Copyright protection arises automatically; registration is not the source of the right.

Nevertheless, for BL-CF the recommended evidence strategy is to register major first-party release snapshots with the Copyright Office of Vietnam because a certificate can materially help in ownership, licensing, financing, and dispute evidence.

Initial registration bundle should include:

- application form required at filing date;
- two copies or the required software-work deposit;
- author and owner information;
- evidence showing why the applicant is the copyright owner;
- assignment/employment/commission documents if author and owner differ;
- a release manifest identifying repository, commit, version, hash, and the exact deposited scope;
- confidential annex handling for any source material that should not be unnecessarily published, subject to filing requirements and legal advice.

Do not use an unofficial website claiming to provide 'international copyright registration'. WIPO does not operate a global copyright registry.

## 8. Trademark path

Apply through the Intellectual Property Office of Vietnam for the names and marks that identify the official federation.

Priority candidates:

- BL Compute Federation / BL-CF;
- DEUS, if clearance supports registration;
- official BL-CF logo;
- any future certification mark used to identify verified federation nodes or compatible services.

Likely goods/services classes should be selected after a professional clearance and scope review. Software, hosted computing, AI/research, and related operational services may fall across multiple Nice classes; the final list should be tailored rather than guessed broadly.

## 9. Patent and trade-secret split

Copyright protects source-code expression, not the underlying abstract idea or mathematical method as such.

Before publicly disclosing a new technical mechanism that may qualify as a patentable technical solution, perform a patent screen. Public disclosure can affect patent strategy in many jurisdictions.

Anything that is valuable because competitors do not know it should be consciously classified as either:

- patent candidate — disclose through the patent process after filing strategy is set; or
- trade secret — keep access-controlled, documented, and subject to confidentiality duties.

Private DEUS routing heuristics, abuse thresholds, proprietary evaluation corpora, and security-sensitive coordination logic should not be pushed into the public repo merely to make the public layer 'more open'.

## 10. Contribution model

Recommended initial model:

- DCO-style signed-off commits for ordinary community contributions;
- a Contributor License Agreement where BL-CF needs additional rights for official distribution, relicensing, certification, or dual licensing;
- explicit assignment only when ownership transfer is actually desired and agreed;
- no automatic claim over a contributor's unrelated inventions, hardware, datasets, employer IP, or pre-existing code.

This preserves the founder's ownership of founder-created IP without falsely appropriating community-created IP.

## 11. Canonical repository and mirrors

GitHub may host the canonical public constitutional repo, but GitHub itself must not be the sole root of legal or technical ownership.

Canonical release identity should be established by:

- repository history;
- signed release/tag;
- founder/steward signing identity;
- mirrored release hash;
- offline recovery material;
- external legal ownership records for copyright/trademark/domain/IP.

A hosting provider can host the project; it should not be able to become the project merely by controlling an account.
