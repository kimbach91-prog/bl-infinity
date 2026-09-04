# BL-CF — Digital Contract Stack v0.4

Status: FOUNDER-DIRECTED IMPLEMENTATION DRAFT

BL-SCA/BL-CF binds official participants through versioned, auditable digital agreements while keeping contributor property, compute grants, strategic reinvestment, commercial settlement, DCC obligations and knowledge-value claims legally distinct.

## 1. Contract objects

### 1.1 Node Contribution Agreement (NCA)

Required for an official Node Provider.

Minimum terms:

- authenticated provider identity and authority to grant the resource;
- bounded CPU/GPU/RAM/storage/network/time/energy envelope;
- permitted workload/data/source-use classes;
- `allowCommercialWorkloads` opt-in/opt-out;
- `allowStrategicReinvestment` opt-in/opt-out;
- provider-specific `maxStrategicReinvestmentShare`, never silently above the constitutional default ceiling;
- `allowPrivateFederationReturn` opt-in/opt-out;
- compatibility aliases for v0.3 `allowCommonBenefit`, `maxCommonBenefitShare`, `allowPrivateSharedBenefit` when needed;
- data-locality, retention and egress constraints;
- grant start, expiry, suspension and revocation;
- settlement modes accepted: cash / DCC / reciprocal compute / hybrid;
- explicit statement that hardware, account, data, energy, network and ungranted capacity remain the provider's property;
- audit/fraud/dispute terms appropriate to the relationship.

### 1.2 Resource Offer & Acquisition Agreement (ROAA)

Required when BL-SCA acquires or auto-activates a resource offer beyond a standing NCA.

Minimum terms:

- `offerId` and provider identity;
- `sourceUseClass`;
- evidence that platform/provider terms permit the declared use;
- acquisition price/bid and compensation mode;
- whether prior authorization permits automatic enrollment;
- resource, duration and revocation bounds;
- expected settlement/use class;
- provider value preview disclosure;
- margin/risk policy version;
- no credential reuse or hidden resource capture;
- renewal/expiry conditions.

### 1.3 Workload Submitter Agreement (WSA)

Minimum terms:

- submitter identity;
- declared purpose/workload class;
- lawful rights to code/data;
- data class/locality;
- resource/network ceiling;
- validation/reproducibility method;
- prohibition on hidden mining, spam/fake engagement, credential attacks, malware, unauthorized scanning, denial-of-service activity and other abuse;
- payment/DCC authorization;
- statement whether Strategic Compute Reinvestment is requested;
- liability/indemnity/governing-law provisions appropriate to the real Operator/jurisdiction.

### 1.4 Research Admission Record (RAR)

For H0–H3 work where research/public outputs are relevant:

- question/project identity;
- expected human/research/federation value;
- methodology/baseline;
- dataset rights/ethics status where applicable;
- benchmark/falsifier/verification method;
- reproducibility/output policy;
- funding/strategic-return basis;
- requested compute/reinvestment band;
- limitations/UNKNOWN and independent review where required.

Research classification does not imply free compute.

### 1.5 Commercial Compute Addendum (CCA)

For H4 commercial work:

- ECSV definition/billing basis;
- default **10% Official Protocol Commercial Share**, unless another explicit agreement applies;
- node commercial opt-in requirement;
- provider payout/credit schedule;
- value-first baseline/reference-price method where used;
- minimum margin and risk provisions where disclosed;
- service level/queue class;
- tax, refund/chargeback and pass-through treatment;
- confidentiality/data-processing terms;
- no ownership right over provider infrastructure;
- ordinary 10% protocol payment alone does not automatically entitle the job to Strategic Compute Reinvestment.

### 1.6 Federation Return Contract (FRC)

Canonical v0.4 contract when private/commercial/PFR work asks to use Strategic Compute Reinvestment capacity.

Minimum fields:

- `returnType`;
- `returnCommitment`;
- `returnMetric`;
- `verificationMethod`;
- `deliveryDeadline`;
- `minimumFederationReturnScore` or acceptance threshold;
- confidentiality/publication boundary;
- remedy if promised return is not delivered;
- independent validator/auditor where material.

Possible returns include:

- added lawful compute/credits;
- measurable revenue share;
- reusable security/protocol improvement;
- verified cost/latency/failure reduction;
- benchmark/evaluation assets;
- provider/customer acquisition value;
- other independently auditable federation value.

The v0.3 `Verified Shared-Benefit Contract` remains a compatibility name for historical receipts.

### 1.7 Knowledge Value / Performance Addendum (KVPA)

Used where DEUS is paid for measured knowledge or intelligence value rather than only raw compute.

Minimum terms:

- knowledge/decision artifact identifier;
- baseline and counterfactual methodology;
- value components permitted in settlement;
- overlap/double-counting exclusions;
- evidence/verification method;
- measurement window;
- success/performance fee rate and cap/floor;
- rights/licensing/confidentiality;
- treatment of negative or inconclusive results;
- explicit distinction between realized value and unbooked projected option value.

No self-assessed DEUS knowledge value is payable merely because DEUS reports a large estimate.

### 1.8 DCC Service Credit Terms

Required before a participant accepts, earns, buys or redeems DEUS Compute Credit.

Minimum terms:

- DCC is initially a compute-service credit, not a guaranteed investment;
- reference settlement unit/value policy;
- backing classes permitted;
- minimum backing ratio in force;
- issuance/mint receipt;
- redemption/burn rules;
- expiry rules if any;
- transferability restrictions;
- no guaranteed cash redemption unless separately contracted;
- suspension treatment during emergency freeze;
- applicable tax/accounting/regulatory disclosures;
- no public speculative trading implied by federation membership.

### 1.9 Data Processing Addendum (DPA)

Required where personal, confidential, regulated or customer-controlled data is processed.

SEALED data remains at its sovereign boundary; compute goes to data unless a separately lawful, explicit rule says otherwise.

### 1.10 Settlement Schedule

Defines as applicable:

- ECSV and 10% Official Protocol Commercial Share;
- provider payout/credit method;
- DCC settlement/redemption method;
- validated resource units and price vectors;
- intelligence/knowledge performance fee;
- validation/metering requirements;
- taxes/invoices/pass-through/refund treatment;
- idempotent settlement receipt and dispute rules;
- strategic-reinvestment/Federation Return accounting.

### 1.11 DEUS Mandate Schedule

Defines:

- M0 audit/recommend;
- M1 classify/plan/queue/discover offers;
- M2 route/allocate and perform only pre-authorized acquisitions within active grants/contracts/caps;
- M3 financial settlement, DCC mint/redeem or other external economic action only within explicit authority/backing/budget limits;
- M4 not delegated unilaterally to DEUS.

## 2. Digital acceptance record

Each agreement produces an append-only receipt, for example:

```json
{
  "agreementType": "NCA",
  "agreementVersion": "0.4.0",
  "agreementHash": "sha256:...",
  "partyId": "verified-account-or-legal-id",
  "consentRef": "blcf-consent:...",
  "acceptedAt": "ISO-8601",
  "expiresAt": "ISO-8601-or-null",
  "signatureMethod": "clickwrap|e-signature|digital-signature",
  "policyRefs": ["CONSTITUTION:v0.4", "AUP:...", "DCC:..."],
  "resourceGrant": {
    "allowCommercialWorkloads": true,
    "allowStrategicReinvestment": true,
    "maxStrategicReinvestmentShare": 0.05,
    "allowPrivateFederationReturn": false
  },
  "settlementPreferences": {
    "acceptedModes": ["cash", "dcc"],
    "allowDcc": true
  },
  "revocationEndpoint": "..."
}
```

The exact accepted text must remain retrievable by version/hash.

## 3. Contract formation

- Do not infer consent from browsing, IP visibility, credentials found in configuration, or a machine appearing on the network.
- Low-risk participation may use robust affirmative clickwrap when legally suitable and identity/exact terms/timestamp/durable evidence are preserved.
- Material commercial, regulated, equity/IP-transfer, DCC, large-value or high-risk agreements should use an electronic/digital signature method appropriate to the actual jurisdiction/transaction.
- Automated systems may execute only inside authority already granted by a participant agreement.

## 4. Automated execution boundary

Permitted examples:

- a node renews a short grant inside a pre-authorized ceiling;
- DEUS routes an admitted workload under active NCA/WSA/FRC terms;
- acquisition engine activates a profitable resource offer only when `preAuthorizedGrant=true` and `autoEnrollAllowed=true`;
- controller adjusts Strategic Compute Reinvestment between target and provider cap;
- settlement computes disclosed 10% protocol share from validated ECSV;
- DCC is minted only if the treasury remains above the required backing ratio.

Automation may not silently:

- create ownership rights;
- expand data access;
- increase provider resource caps;
- repurpose source-use class;
- change material pricing terms;
- mint unbacked DCC;
- book projected knowledge value as realized cash/compute backing.

## 5. Versioning

Each material contract has a semantic version and content hash.

- PATCH: non-material clarification where allowed;
- MINOR: prospective operational additions not materially reducing participant rights;
- MAJOR: material payment, ownership, data, liability, reinvestment, DCC or governance change requiring renewed acceptance unless existing contract/law validly provides otherwise.

Old receipts retain the meaning of the text actually accepted.

## 6. Provider sovereignty API

Every provider should be able to read, in human and machine form:

- resource currently granted;
- current job/purpose/workload class;
- whether it is commercial/strategic reinvestment;
- data/network requirements;
- rolling reinvestment use vs provider cap;
- source-use class;
- resources consumed and expected settlement;
- DCC/cash settlement state where applicable;
- grant expiry;
- immediate suspend/revoke control.

Provider-side enforcement should fail closed if central requests exceed the locally accepted grant.

## 7. Treasury transparency API

Without exposing confidential customer/provider data, the system should be able to prove or report:

- DCC outstanding;
- eligible backing by class;
- reserved liabilities;
- backing ratio;
- protocol revenue booked;
- verified efficiency/knowledge profit booked;
- unbooked projected option value;
- expired/revoked compute backing removed from solvency calculations.

## 8. Founder/canonical boundary

Founder final interpretive authority applies to official constitutional meaning and prospective policy. It does not retroactively rewrite a concluded bilateral agreement outside its amendment/consent mechanism or mandatory law.

## 9. Anti-capture clauses

Where lawful, Operator/IP-license agreements should provide:

- no assignment of Founder-owned IP except by explicit signed instrument;
- no automatic transfer of official marks/canonical registry merely because Operator shares change hands;
- breach-triggered suspension/termination rights for official IP licenses;
- continuity rights to appoint/authorize a replacement Operator;
- portable export of non-secret operational records subject to privacy/confidentiality;
- no lien/security interest over Founder-owned IP unless explicitly approved.

## 10. Human-readable summary

Every agreement gets a concise companion summary stating:

- what the participant gives;
- what they keep;
- commercial/reinvestment choices and caps;
- what BL-CF/DEUS may do;
- how to revoke;
- what happens to data;
- how cash/DCC/reciprocal-compute settlement works;
- how knowledge/performance value is measured if applicable;
- who operates the service;
- dispute route.

No dark-pattern consent.
