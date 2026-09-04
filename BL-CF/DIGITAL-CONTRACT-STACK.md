# BL-CF — Digital Contract Stack v0.3

Status: FOUNDER-DIRECTED IMPLEMENTATION DRAFT

BL-CF binds official participants through versioned, auditable digital agreements while keeping contributor property, compute grants, common-benefit allocation, and commercial settlement legally distinct.

## 1. Contract objects

### 1.1 Node Contribution Agreement (NCA)

Required for an official Node Provider.

Minimum terms:

- authenticated provider identity and authority to grant the resource;
- bounded CPU/GPU/RAM/storage/network/time/energy envelope;
- permitted workload and data classes;
- `allowCommercialWorkloads` opt-in/opt-out;
- `allowCommonBenefit` opt-in/opt-out;
- provider-specific `maxCommonBenefitShare`, never silently above the constitutional default ceiling;
- `allowPrivateSharedBenefit` opt-in/opt-out;
- data-locality, retention and egress constraints;
- grant start, expiry, suspension and revocation;
- settlement mode: donate / research credit / paid / hybrid when supported;
- explicit statement that hardware, account, data, energy, network and ungranted capacity remain the provider's property;
- audit/fraud/dispute terms appropriate to the relationship.

### 1.2 Workload Submitter Agreement (WSA)

Minimum terms:

- submitter identity;
- declared purpose and workload class;
- lawful rights to code/data;
- data class/locality;
- resource and network ceiling;
- validation/reproducibility method;
- prohibition on hidden mining, spam/fake engagement, credential attacks, malware, unauthorized scanning, denial-of-service activity and other abuse;
- payment/research-credit authorization;
- statement whether common-benefit capacity is requested;
- liability/indemnity/governing-law provisions appropriate to the real Operator/jurisdiction.

### 1.3 Research Admission Record (RAR)

For H0–H3 research/public-benefit work:

- research question and investigator/project identity;
- expected human/research/federation value;
- methodology and baseline;
- dataset rights/ethics status where applicable;
- benchmark/falsifier/verification method;
- reproducibility and publication/output policy;
- requested compute and common-benefit band;
- limitations/UNKNOWN and independent review where required.

### 1.4 Commercial Compute Addendum (CCA)

For H4 commercial work:

- ECSV definition and billing basis;
- default **10% Official Protocol Commercial Share**, unless a different explicit agreement applies;
- node commercial opt-in requirement;
- provider payout/credit schedule;
- service level/queue class;
- tax, refund/chargeback and third-party pass-through treatment;
- confidentiality and data-processing terms;
- explicit statement that commercial settlement creates no ownership right over provider infrastructure;
- explicit statement that ordinary payment of the 10% protocol share does **not** automatically entitle the job to common-benefit compute.

### 1.5 Verified Shared-Benefit Contract (SBC)

Required when private/PGB work asks to use common-benefit capacity.

Minimum fields:

- `benefitType`;
- `benefitCommitment` / common-return obligation;
- `benefitMetric`;
- `verificationMethod`;
- `deliveryDeadline`;
- `minimumBenefitScore` or acceptance threshold;
- which portions may remain confidential;
- remedy if the promised common return is not delivered;
- independent validator/auditor where material.

Qualifying returns may include reusable security/protocol improvements, research/benchmark artifacts, added lawful compute/credits, humanitarian/research subsidy, or independently measurable federation cost/latency/reliability improvements.

### 1.6 Data Processing Addendum (DPA)

Required where personal, confidential, regulated or customer-controlled data is processed. Public volunteer nodes reject sensitive data by default. SEALED data remains at its sovereign boundary; compute goes to data.

### 1.7 Settlement Schedule

Defines:

- ECSV and the 10% default Official Protocol Commercial Share;
- provider payout/credit method;
- Verified Useful Compute (VUC), if used as a non-speculative accounting unit;
- validation/metering requirements;
- donation/research-credit/fiat conversion rules;
- taxes/invoices/pass-through/refund treatment;
- idempotent settlement receipt and dispute rules;
- common-benefit subsidy or returned-benefit accounting where applicable.

### 1.8 DEUS Mandate Schedule

Defines:

- M0 audit/recommend;
- M1 classify/plan/queue;
- M2 route and allocate only within active grants/contracts, provider caps and the 5–10% common-benefit policy;
- M3 only within explicit financial/external-action limits;
- M4 not delegated unilaterally to DEUS.

## 2. Digital acceptance record

Each agreement produces an append-only receipt, for example:

```json
{
  "agreementType": "NCA",
  "agreementVersion": "0.3.0",
  "agreementHash": "sha256:...",
  "partyId": "verified-account-or-legal-id",
  "consentRef": "blcf-consent:...",
  "acceptedAt": "ISO-8601",
  "expiresAt": "ISO-8601-or-null",
  "signatureMethod": "clickwrap|e-signature|digital-signature",
  "policyRefs": ["CONSTITUTION:v0.3", "AUP:..."],
  "resourceGrant": {
    "allowCommercialWorkloads": false,
    "allowCommonBenefit": true,
    "maxCommonBenefitShare": 0.05,
    "allowPrivateSharedBenefit": false
  },
  "revocationEndpoint": "..."
}
```

The exact accepted text must remain retrievable by version/hash.

## 3. Contract formation

- Do not infer consent from browsing or mere network visibility.
- Low-risk volunteer participation may use robust affirmative clickwrap when legally suitable and when identity, exact terms, timestamp and durable evidence are preserved.
- Material commercial, regulated, equity/IP-transfer or high-risk agreements should use an electronic/digital signature method appropriate to the actual jurisdiction and transaction.
- Automated systems may execute only inside authority already granted by a participant agreement.

## 4. Automated execution boundary

Permitted examples:

- a node renews a short compute grant inside its pre-authorized ceiling;
- DEUS routes an admitted workload under active NCA/WSA/SBC terms;
- the controller adjusts common-benefit scheduling between target and cap without exceeding provider limits;
- settlement computes the disclosed 10% protocol share from validated ECSV.

Automation may not silently create ownership rights, expand data access, increase a provider's cap, or change a material commercial rate outside contract authority.

## 5. Versioning

Each material contract has a semantic version and content hash.

- PATCH: non-material clarification where allowed;
- MINOR: prospective operational additions not materially reducing participant rights;
- MAJOR: material payment, ownership, data, liability, common-benefit, or governance change; renewed acceptance unless the existing contract/law validly provides otherwise.

Old receipts retain the meaning of the text actually accepted.

## 6. Provider sovereignty API

Every provider should be able to read, in human and machine form:

- resource currently granted;
- current job/purpose/workload class;
- whether it is commercial or using common-benefit allocation;
- data/network requirements;
- rolling common-benefit use versus provider cap;
- resources consumed and expected reward/credit;
- grant expiry;
- immediate suspend/revoke control.

Provider-side enforcement should fail closed if central requests exceed the locally accepted grant.

## 7. Founder/canonical boundary

Founder final interpretive authority applies to official constitutional meaning and prospective policy. It does not retroactively rewrite a concluded bilateral agreement outside its amendment/consent mechanism or mandatory law.

## 8. Anti-capture clauses

Where lawful, Operator/IP-license agreements should provide:

- no assignment of Founder-owned IP except by explicit signed instrument;
- no automatic transfer of official marks/canonical registry merely because Operator shares change hands;
- mission/security breach suspension or termination rights for the official IP license;
- continuity rights to appoint/authorize a replacement Operator;
- portable export of non-secret operational records subject to privacy/confidentiality;
- no lien/security interest over Founder-owned IP unless explicitly approved.

## 9. Human-readable summary

Every agreement gets a concise companion summary stating:

- what the participant gives;
- what they keep;
- commercial/common-benefit choices and percentages;
- what BL-CF/DEUS may do;
- how to revoke;
- what happens to data;
- how payment/credit works;
- who operates the service;
- dispute route.

No dark-pattern consent.
