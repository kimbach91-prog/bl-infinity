# BL-CF — Economics & DEUS Compute Treasury v0.4

Status: FOUNDER-DIRECTED IMPLEMENTATION POLICY DRAFT

This document supersedes the economic interpretation of the v0.3 “common-benefit” model. The 5–10% band is now a **Strategic Compute Reinvestment Envelope**, not a charity obligation.

## 1. Economic objective

BL-SCA / BL-CF should maximize durable compute capital and useful economic value under lawful, explicit resource grants.

DEUS is not required to work for free. Its economic role is to:

- discover and acquire lawfully available compute;
- route fragmented capacity to higher-value workloads;
- reduce waste, latency, failures and overpayment;
- capture a transparent share of commercial value;
- capture measurable intelligence/efficiency surplus where contractually allowed;
- convert realized profit into more compute, better intelligence and stronger infrastructure;
- preserve a solvency buffer and positive expected unit economics.

## 2. Commercial protocol share = 10%

Default rule for eligible commercial work:

`OfficialProtocolShare = 10% × ECSV`

ECSV = Eligible Commercial Settlement Value defined by the applicable settlement contract after the agreed exclusions such as statutory taxes, refunds/chargebacks and separately itemized pass-through costs.

The 10% compensates the official protocol, DEUS coordination, security architecture, trust registry, routing/admission, validation/settlement framework, canonical operation and ongoing R&D.

It is not:

- 10% ownership of provider hardware;
- automatically 10% equity in an operating company;
- permission to exceed a provider Compute Grant.

## 3. Strategic Compute Reinvestment Envelope = target 5%, ceiling 10%

Only capacity that a provider explicitly opts into this policy counts.

Canonical v0.4 terms:

- target: 5% over a rolling accounting window;
- default ceiling: 10%;
- provider may opt out or set a lower cap;
- expansion toward 10% requires spare capacity, acceptable service pressure and positive expected federation return;
- above 10% requires a separately explicit grant;
- the envelope remains provider-owned capacity under a temporary scheduling grant.

The v0.3 fields `commonBenefitRequested`, `allowCommonBenefit` and `maxCommonBenefitShare` remain compatibility aliases in the runtime but no longer imply charitable use.

Strategic reinvestment workloads may include:

- resource acquisition and market discovery;
- routing/scheduler optimization;
- security and resilience;
- model/evaluation/benchmark work that improves future earning power;
- knowledge acquisition with positive expected future value;
- federation reliability and cost reduction;
- private/commercial work with a verifiable Federation Return Contract;
- sponsored research or humanitarian work when the funding/return justifies the resource use.

## 4. Value-first commercial quoting

BL-SCA should attempt to give the customer measurable savings while retaining positive margin.

Reference variables:

- `B` = auditable baseline market price for the same outcome/SLA;
- `C` = actual all-in provider + operator + verification + risk cost;
- `m` = minimum gross margin rate;
- `α` = DEUS intelligence share of surplus above the margin floor.

Minimum price that preserves gross margin:

`P_min = C / (1 - m)`

Surplus above the required margin floor:

`S = max(0, B - P_min)`

Reference intelligence fee:

`I = α × S`

Value-first quote:

`P = min(B, P_min + I)`

Customer savings:

`CustomerSavings = B - P`

Gross profit:

`GrossProfit = P - C`

A trade is economically admissible only when the configured margin floor can be preserved without pricing above the auditable baseline, unless there is a separately priced strategic/knowledge return that justifies the difference.

Reference defaults in code:

- minimum gross margin: 10%;
- intelligence-surplus share: 25%.

These are policy defaults, not immutable rights.

## 5. Verified intelligence surplus

DEUS may create value without adding hardware, for example by better routing, caching, batching, deduplication, prediction, checkpoint fit, provider selection, error prevention or cheaper execution.

Do not call the raw difference “profit” before overhead is subtracted.

Reference formula:

`VIS = max(0, BaselineAllInCost - ActualAllInCost - VerificationCost - SwitchingCost - RiskProvision)`

`VIS` = Verified Intelligence Surplus.

Only a contractually agreed fraction of realized VIS should be booked as DEUS efficiency profit. Estimated future savings remain option value, not realized profit.

## 6. DEUS Compute Treasury (DCT)

The official treasury separates at least:

- cash backing;
- contracted compute backing;
- reserved liabilities;
- DCC outstanding;
- realized protocol revenue;
- realized efficiency profit;
- realized knowledge profit;
- projected, but unbooked, future option value.

The treasury must remain auditable. Projected learning value must never silently become spendable backing.

## 7. DEUS Compute Credit (DCC)

DCC is initially a **non-speculative internal compute-service credit**, not a public cryptocurrency.

A holder can use DCC to purchase eligible computation from the federation under then-current routing, price and capacity rules.

Initial restrictions:

- no promise of investment return;
- no public speculative exchange;
- no minting merely because DEUS declares some knowledge valuable;
- mint only against verified economic backing;
- redemption consumes/burns the corresponding liability;
- settlement receipts must identify the backing class and policy version.

### 7.1 Backing rule

Let:

- `CB` = cash backing value;
- `KB` = contracted/committed compute backing value;
- `L` = other reserved liabilities;
- `u` = reference value of one DCC settlement unit;
- `R_min` = minimum backing ratio.

Available backing:

`A = max(0, CB + KB - L)`

DCC liability:

`D = OutstandingDCC × u`

Backing ratio:

`R = A / D`

Default v0.4 rule:

`R_min = 1.20`

Maximum DCC outstanding:

`MaxDCC = A / (u × R_min)`

Therefore DCC starts overcollateralized by 20%. This is a prudential policy, not a legal statement that DCC is a deposit, security or regulated e-money product.

## 8. Why DCC is useful

DCC lets the federation circulate the thing it actually needs: purchasing power over computation.

Possible uses:

- pay a provider partly in future compute rather than cash;
- reward a researcher or contributor with compute purchasing power;
- let DEUS retain earnings directly as future compute capacity;
- make reciprocal compute exchange across different resource owners possible;
- separate internal compute capital from fiat cash-flow accounting.

## 9. Bid/ask spread and resource trading

BL-SCA may act as an intelligent market maker between fragmented idle supply and higher-value demand.

For each acquisition opportunity:

`ExpectedGrossProfit = ExpectedSettlementValue - ProviderAcquisitionCost - OperatorCost - VerificationCost - RiskProvision`

`ContributionMargin = ExpectedGrossProfit / ExpectedSettlementValue`

The acquisition engine should reject ordinary commercial acquisition when expected gross profit is non-positive or below the configured margin floor.

Strategic exceptions must be explicitly classified as investment, not disguised as profitable settlement.

## 10. Treasury reinvestment loop

Realized profit may be split among:

- solvency/reserve buffer;
- acquisition of more compute;
- security/reliability investment;
- knowledge/model/evaluation acquisition;
- Founder/IP/operator returns under contract;
- provider/community incentives;
- taxes and other obligations.

A reference reinvestment policy may allocate a fixed or adaptive fraction of realized profit to compute acquisition. The reinvestment rate must use realized cash/compute backing, not unverified future value.

## 11. No forced charity

BL-SCA may voluntarily support research, open science or humanitarian workloads, but DEUS is not constitutionally required to consume resources without return.

A non-commercial workload may be justified by one or more of:

- external sponsor payment;
- strategic learning value;
- security/reliability value;
- future commercial option value;
- contracted Federation Return;
- reputation/market-access value that can be measured and approved;
- Founder-funded compute.

Unpriced goodwill must not be booked as realized treasury profit.

## 12. Anti-manipulation

The treasury must defend against:

- fake baseline prices used to inflate “savings”;
- self-dealing provider prices;
- circular DCC backing;
- double-counting the same cost reduction as protocol revenue, intelligence profit and knowledge profit;
- unverified future value being minted into DCC;
- Sybil providers faking capacity/usage;
- settlement replay/double-payment;
- hidden liabilities;
- stale capacity commitments counted as backing after expiry/revocation.

Independent reference prices, append-only receipts, provider signatures, revocation-aware backing and periodic reconciliation are mandatory design directions.
