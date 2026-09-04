# BL-CF — Digital Contract Stack v0.2

Status: DRAFT FOR FOUNDER RATIFICATION

BL-CF should bind legal participants through versioned, auditable digital agreements while keeping machine ownership and compute allocation separate.

## 1. Contract objects

### 1.1 Node Contribution Agreement (NCA)

Required for a Node Provider to join the official federation.

Minimum terms:

- provider legal/account identity;
- authority to grant the resource;
- machine/account class without unnecessary personal data;
- permitted CPU/GPU/RAM/storage/network envelope;
- permitted workload classes;
- commercial-workload opt-in or opt-out;
- energy/thermal/time-window constraints;
- data-locality constraints;
- grant start, expiry, suspension, and revocation;
- settlement mode: donate / research credit / paid / hybrid;
- explicit statement that no hardware, account, data, or ungranted capacity is transferred to BL-CF;
- audit and fraud provisions;
- applicable law / dispute mechanism appropriate to the provider relationship.

### 1.2 Workload Submitter Agreement (WSA)

Minimum terms:

- submitter identity;
- declared workload purpose;
- lawful rights to code and data;
- permitted data classes;
- resource ceiling;
- verification method;
- prohibition on hidden mining, spam, fake engagement, credential attacks, malware, unauthorized scanning, or other abuse;
- payment or research-credit authorization;
- indemnity/liability treatment appropriate to the legal entity and jurisdiction.

### 1.3 Research Admission Record (RAR)

For H0–H3 research/public-benefit jobs:

- research question;
- investigator/project identity;
- expected human/scientific value;
- methodology;
- dataset rights and ethics status where applicable;
- benchmark or falsifier;
- reproducibility requirements;
- publication/output policy;
- requested compute grant;
- independent admission/review receipt for high-impact jobs.

### 1.4 Commercial Compute Addendum (CCA)

For H4 workloads:

- price/credit schedule;
- service level and queue class;
- node commercial opt-in requirement;
- billing unit;
- dispute/chargeback rules;
- data processing terms;
- confidentiality terms;
- no implied ownership of provider infrastructure.

### 1.5 Data Processing Addendum (DPA)

Required where personal, confidential, regulated, or customer-controlled data is processed.

The default public-volunteer pool should reject sensitive data unless a separately designed trusted-compute/data-locality policy explicitly permits it.

### 1.6 Settlement Schedule

Defines:

- Verified Useful Compute (VUC) or successor accounting unit;
- measurement method;
- anti-fraud validation;
- conversion to donation, research credit, or money;
- tax/invoice treatment where applicable;
- minimum payout / expiry / dispute rules.

### 1.7 DEUS Mandate Schedule

Defines the machine authority boundary:

- M0 audit/recommend;
- M1 planning;
- M2 compute allocation and routing;
- M3 only within explicit financial/action limits;
- M4 prohibited without Founder/human legal authority.

## 2. Digital acceptance record

Each accepted agreement should produce an append-only receipt containing at least:

```json
{
  "agreementType": "NCA",
  "agreementVersion": "0.2.0",
  "agreementHash": "sha256:...",
  "partyId": "verified-account-or-legal-id",
  "consentRef": "blcf-consent:...",
  "acceptedAt": "ISO-8601",
  "expiresAt": "ISO-8601-or-null",
  "signatureMethod": "clickwrap|e-signature|digital-signature",
  "policyRefs": ["AUP:0.2", "PRIVACY:0.2"],
  "revocationEndpoint": "..."
}
```

The agreement text itself must be retrievable by version/hash so BL-CF can prove what terms were accepted.

## 3. Contract formation rules

The official system should be designed to support legally meaningful electronic contracting under applicable law.

For low-risk volunteer participation, a robust clickwrap flow may be appropriate if identity, affirmative acceptance, exact terms, timestamp, and durable evidence are preserved.

For higher-risk commercial, regulated, or IP-transfer contracts, use an electronic-signature or digital-signature method appropriate to the jurisdiction and transaction.

Do not infer consent from mere site browsing or from a machine appearing on the network.

## 4. Automated contracting

BL-CF may allow automated systems to form or execute bounded agreements only where the underlying participant contract authorizes such automation.

Examples:

- a node automatically renews a 24-hour grant within a pre-authorized ceiling;
- DEUS allocates an accepted job to a qualifying provider under the existing NCA/WSA;
- the settlement engine credits verified compute according to a published schedule.

Automation must not create new ownership rights, expand sensitive-data access, or raise spending/credit limits beyond the participant's pre-authorized envelope.

## 5. Versioning and amendment

Every material contract has semantic versioning and a content hash.

- PATCH: clarifications with no material rights change, where the existing agreement permits such updates;
- MINOR: prospective operational additions that do not remove material participant rights;
- MAJOR: material rights, payment, data, liability, ownership, or governance change and requires renewed acceptance unless law/contract clearly allows otherwise.

A future version may not silently rewrite the meaning of an old receipt.

## 6. Provider sovereignty API

Every Node Provider should be able to obtain a machine-readable answer to:

- what resource is currently granted;
- what job is running;
- why the job was admitted;
- what data class it uses;
- how much resource has been consumed;
- expected reward/credit;
- when the grant expires;
- how to suspend/revoke immediately.

Revocation should fail closed for new work and stop current work at the safest available checkpoint permitted by the job class.

## 7. Founder / official federation contract boundary

The Founding Steward's final interpretive authority applies to the official constitutional meaning and prospective policy implementation.

It does not permit an already executed bilateral contract to be rewritten retroactively without the amendment/consent mechanism specified by that contract and applicable law.

This distinction protects both Founder authority and federation legitimacy.

## 8. Anti-capture contract clauses

Operator agreements should include, where lawful:

- no assignment of founder IP except by explicit signed instrument;
- no transfer of official marks/canonical registry merely because company shares change hands;
- mission-breach suspension/termination of the official IP license;
- continuity rights allowing the Founding Steward to appoint a replacement Operator if the current Operator loses authorization;
- requirement to export provider/workload records in a portable format while respecting privacy and confidentiality;
- no lien/security interest over founder-owned IP unless explicitly approved by the Founding Steward.

## 9. Human-readable first

Every contract should have a short human-readable summary paired with the controlling full legal text.

The summary must clearly state:

- what the participant is giving;
- what they keep;
- what BL-CF may do;
- how to stop participation;
- whether the workload may be commercial;
- how payment/credit works;
- what happens to data;
- who operates the service;
- where disputes go.

No dark-pattern consent.
