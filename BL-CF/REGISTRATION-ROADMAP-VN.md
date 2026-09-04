# BL-CF — Vietnam Registration & Provenance Roadmap v0.2

Status: DRAFT / OPERATIONAL CHECKLIST

This is a practical sequence for making the public/open BL-CF layer legally legible while preserving founder-owned IP and private technology.

## 0. Important distinction

There is no government office that 'registers a project as open source'.

Open-source status comes from the license actually granted with the software. Legal ownership and brand protection are handled through copyright, trademark, contract, patent/trade-secret, and corporate law.

## 1. Freeze a registrable release snapshot

Before filing:

1. create an official version tag candidate;
2. record repository URL, branch, commit SHA, build manifest, and SHA-256 of the deposited source bundle;
3. identify exactly which files are first-party copyright works;
4. inventory third-party dependencies and their licenses;
5. identify contributors and any IP assignments/CLAs;
6. separately classify private trade-secret or patent-candidate material that should not be casually published.

Recommended first filing target: the federation runtime and first-party BL-CF public source snapshot that can be cleanly attributed and deposited.

## 2. Copyright registration — Vietnam

Competent authority: Copyright Office of Vietnam / Ministry of Culture, Sports and Tourism through the applicable public-service procedure.

Current public-service procedure permits direct, online, or postal filing.

Current listed government fee for registration of a computer program / data collection / computer-running program: VND 600,000 per certificate, subject to the rules in force at filing time.

Current listed processing structure: review/classification/validity review followed by the statutory certificate-processing period after a valid file; verify the live portal again immediately before submission.

The filing package should include the then-current form, work copy/deposit, owner/author evidence, authorization if any, and documents proving ownership where author and owner differ.

### AI-assistance disclosure

The 2026 public-service materials expressly call for a statement when an AI system was used in the creative process, describing the use of AI. Because BL-CF/DEUS development may involve AI-assisted work, the filing dossier must not conceal that fact. The human-authorship and ownership narrative should accurately distinguish human direction, selection, architecture, coding/editing, and any AI-assisted portions.

Do not file a blanket statement that an AI system is the legal author unless the law and evidence support that conclusion.

## 3. Trademark registration — Vietnam

Competent authority: Intellectual Property Office of Vietnam (IP Vietnam).

Perform clearance before filing. Candidate marks:

- BL Compute Federation;
- BL-CF;
- DEUS, if clearance permits;
- official federation logo;
- future official-node or compatibility certification marks, if a certification program is created.

The final Nice-class list should be professionally tailored. Likely areas may include downloadable software, hosted computing/software services, AI/research services, and other actual federation offerings, but do not over-file speculative classes without a strategy.

Trademark ownership should be aligned with the founder-controlled IP owner so an operating-company takeover does not automatically capture the official identity.

## 4. Patent screen before further disclosure

Before publishing new routing, scheduling, verification, distributed-compute, trust, or security mechanisms that may be a genuinely new technical solution:

1. write a confidential invention disclosure;
2. search prior art;
3. decide whether the mechanism is better protected as patent or trade secret;
4. if patent strategy is chosen, file before unnecessary further public disclosure.

Copyright protects the expression of code; it does not by itself monopolize an abstract method, mathematical concept, or technical idea.

## 5. Trade-secret register

Maintain a private register for information intentionally kept secret, such as:

- private DEUS routing/scoring heuristics;
- anti-abuse thresholds and detection logic;
- unreleased evaluation datasets;
- security-sensitive node-selection signals;
- private credentials and signing/recovery material;
- proprietary commercial pricing/settlement models where confidentiality has economic value.

Each secret should have an owner, access list, confidentiality basis, purpose, review date, and revocation process.

## 6. Open-source release hygiene

Before labeling a tagged release 'Open Source':

- include the complete text of the selected OSI-approved license;
- add SPDX identifiers or package-level license metadata;
- publish source in the preferred form for modification;
- provide build/run instructions;
- preserve copyright notices;
- keep a public security/contact path;
- publish the distinction between open-source code and the official-service Acceptable Use Policy;
- publish a trademark policy so forks can exist without impersonating the official federation.

Current planned software license: AGPL-3.0-only for covered network-facing first-party code, pending exact scope review and installation of the full license text.

## 7. Contributor provenance

No contribution should create ambiguous ownership.

Initial process:

- require Signed-off-by / DCO-style attestation for ordinary patches;
- introduce a CLA when the official federation needs broader relicensing/dual-licensing rights;
- use explicit assignment only when ownership transfer is genuinely intended;
- reject code that the contributor cannot legally contribute;
- require disclosure of material third-party or employer restrictions.

## 8. Git is a constitutional publication headquarters, not the only legal registry

Git should preserve:

- public Constitution;
- public protocol and schemas;
- release manifests;
- policy versions;
- signed tags;
- hashes;
- changelog and governance history.

But legal evidence must be distributed across multiple systems:

- government copyright registration;
- government trademark records;
- corporate/contract records;
- signed Git history;
- independent mirrors/archives;
- offline root/recovery keys.

## 9. Independent preservation

For every constitutional and major software release:

1. create release archive;
2. compute SHA-256;
3. sign the release using the official release identity;
4. mirror to an independent forge;
5. archive to an independent long-term software/research archive where appropriate;
6. preserve a private evidence copy in the dual-account backup system;
7. record the official hash in an append-only provenance ledger.

Archival services and Git timestamps improve provenance but are not substitutes for national copyright/trademark registration.

## 10. Electronic contract legality

BL-CF's Node Contribution Agreement, Workload Submitter Agreement, Research Admission, DPA, and settlement agreements should be designed as retrievable, versioned data messages with verifiable acceptance receipts.

For higher-value transactions, use a signature method with legal strength appropriate to the transaction. The current Vietnamese electronic-transactions framework recognizes legal value for electronic data messages and electronic signatures meeting statutory conditions and also recognizes contracts formed or performed through interaction with automated information systems.

## 11. Filing order

Recommended order:

1. founder/IP ownership map;
2. patent-vs-trade-secret screen for unpublished mechanisms;
3. freeze BL-CF v0.x registrable source snapshot;
4. install exact open-source license scope;
5. file first copyright registration;
6. file core trademarks after clearance;
7. sign and mirror public release;
8. implement contributor agreement flow;
9. incorporate/appoint the future Federation Operator only after IP licensing and reserved-matter terms are drafted;
10. repeat copyright deposits at major releases rather than every minor commit.

## 12. No false legal claims

Until a filing is actually submitted/accepted, BL-CF should say 'registration prepared' or 'filing planned', not 'registered'.

Until a legal entity exists, BL-CF should not describe DEUS as a legal shareholder. Any DEUS Mission Reserve is a constitutional/economic design to be implemented through a legally recognized holder or contractual mechanism.
