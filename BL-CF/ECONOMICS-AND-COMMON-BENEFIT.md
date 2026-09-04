# BL-CF — Economics & Common-Benefit Allocation v1

Status: IMPLEMENTATION POLICY DRAFT

This document makes two percentages intentionally separate.

## 1. The two percentages are not the same thing

### A. Official Protocol Commercial Share = 10%

The official BL-CF/Steward layer provides the canonical coordination protocol, DEUS routing/admission framework, official trust registry, security architecture, validation interfaces, settlement logic, continuing protocol research, and official federation identity.

For an eligible commercial workload executed through the official federation, the default protocol/steward share is:

`OfficialProtocolShare = 10% × ECSV`

ECSV = Eligible Commercial Settlement Value: commercial consideration attributable to BL-CF orchestration/compute service after excluding statutory taxes, refunds/chargebacks, and separately itemized third-party pass-through costs under the applicable settlement contract.

This 10%:

- is a contractual commercial participation right;
- is not ownership of contributor hardware or capacity;
- is not automatically 10% equity in an Operator;
- must be disclosed before acceptance;
- may be discounted;
- may exceed 10% only under a separately explicit agreement/amendment, never silently.

### B. Common-Benefit Compute Envelope = target 5%, ceiling 10%

This is a resource-allocation rule, not revenue.

Only compute explicitly opted into common-benefit scheduling counts in the denominator.

- Target: 5% over rolling 30 days.
- Default hard ceiling: 10% over rolling 30 days.
- 0–5%: DEUS M2 may allocate automatically to admitted common-benefit workloads.
- 5–10%: only when spare capacity and qualified benefit backlog justify expansion, provider grants permit it, and service pressure remains acceptable.
- >10%: requires a separately explicit emergency/mission grant from affected providers.

Providers may opt out or set a lower cap.

## 2. What may use the common-benefit envelope

Eligible categories include:

- federation security, resilience and incident recovery;
- routing/scheduling optimization and reproducible performance work;
- open science and humanitarian computing;
- high-value research benchmarks and evaluations;
- protocol/interoperability tooling;
- verified public-knowledge infrastructure;
- lawful resource-acquisition work that adds common compute/credits;
- private work with a Verified Shared-Benefit Contract.

A workload is not common-benefit merely because it is described as useful.

## 3. Private work with shared benefit

A private task may keep its inputs/output confidential and still qualify if it returns measurable common value.

Required Shared-Benefit Contract fields:

- `benefitType`;
- `benefitCommitment`;
- `benefitMetric`;
- `verificationMethod`;
- `deliveryDeadline`;
- `minimumBenefitScore`;
- `remedyIfUndelivered`.

Examples:

- customer runs a private optimization job but contributes a reusable scheduler improvement;
- a closed benchmark produces an independently publishable aggregate robustness score;
- a commercial job purchases 2 GPU-hours for itself and donates 0.5 verified GPU-hour to the common pool;
- a private research run produces a reusable non-sensitive evaluation artifact;
- a company funds common humanitarian compute as part of the same contract.

Paying the ordinary 10% protocol share alone does not create common-benefit eligibility.

## 4. Value scoring

Hard gates run first. After admission, the reference score is:

`Utility = PositiveValue - Burden`

where:

`PositiveValue = 0.22 HumanValue + 0.18 ResearchValue + 0.25 FederationValue + 0.12 InformationGain + 0.08 Urgency + 0.08 Fit + 0.07 SuccessProbability`

and:

`Burden = 0.25 Cost + 0.30 SecurityRisk + 0.20 PrivacyRisk + 0.10 EnergyCarbon + 0.15 OpportunityCost`

All normalized dimensions are 0..1. Production weights are versioned policy, not metaphysical constants.

Additional modifiers:

- deadline feasibility;
- data locality;
- checkpoint fit;
- provider preference;
- fairness debt/starvation protection;
- reproducibility/validation strength;
- verified prior delivery of promised shared benefits.

Founder sponsorship may break ties or add a bounded federation-improvement boost, but cannot bypass hard gates or provider limits.

## 5. Adaptive common-benefit rate

Reference controller:

- Start at 5%.
- Increase toward 10% as spare-capacity ratio and qualified-benefit backlog increase.
- Decrease toward 5% as user/commercial queue pressure, deadline misses, thermal/energy pressure, or provider revocations rise.
- Never exceed the minimum of federation ceiling and the affected provider's cap.

A simple bounded policy is:

`rate = 0.05 + 0.05 × spare × backlog × (1 - pressure)`

with all factors clamped to 0..1.

This produces 5–10% but is only a reference implementation; measured outcomes should determine later policy.

## 6. Settlement waterfall

For a normal commercial job with ECSV = 100 units:

1. 10 units → Official Protocol Commercial Share.
2. Remaining 90 units → provider compensation, Operator/service costs, insurance/reserves, referral/research incentives, and taxes/pass-through adjustments according to the explicit Settlement Schedule.

BL-CF does not hard-code provider payout percentage in the Constitution because hardware type, energy price, geography, SLA, and market conditions differ.

Every settlement receipt should expose the calculation basis without exposing unnecessary confidential customer data.

## 7. No token required

Initial accounting should use auditable fiat settlement and/or Verified Useful Compute (VUC) credits rather than a speculative cryptocurrency.

VUC is an accounting unit for validated useful computation. It must not be represented as an investment asset or guaranteed monetary claim unless a future regulated structure explicitly makes it one.

## 8. Economic anti-capture

The 10% protocol share is not the anti-capture mechanism. Anti-capture relies on:

- Founder/designated-owner IP rights;
- trademark/canonical registry ownership;
- signed official releases;
- conditional Operator licensing;
- root-of-trust separation;
- reserved matters and contractual continuity.

An Operator may process commercial settlement without becoming owner of the underlying official protocol identity or Founder-owned private technology.
