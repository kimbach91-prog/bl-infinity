# BL-CF — Lawful Resource Acquisition Protocol v0.4

Status: FOUNDER-DIRECTED IMPLEMENTATION DRAFT

BL-SCA should continuously search for economically attractive compute, but “automatic” never means unauthorized.

## 1. Acquisition doctrine

The resource-acquisition loop is:

`Discover lawful offer -> verify rights/terms -> give provider value preview -> calculate unit economics -> obtain/verify grant -> activate -> route -> validate -> settle -> measure -> renew/revoke`

The system is allowed to be aggressive about discovery and optimization. It is not allowed to be aggressive about consent.

## 2. Sources

Potential sources include:

- user-owned local machines;
- workstations/lab nodes with explicit owner grants;
- enterprise spare capacity;
- BYOC cloud accounts;
- cloud credits/grants whose terms allow the declared workload;
- contracted GPU/CPU providers;
- research infrastructure under an authorized agreement;
- edge/worker resources where the platform's terms permit the actual use;
- reciprocal-compute agreements with other members.

## 3. Source-use classes

Every source must carry a `sourceUseClass`.

Initial classes:

- `general-compute` — may be routed to compatible general workloads;
- `ci-only` — only CI/build/test work allowed by the underlying terms;
- `control-plane-only` — coordination/API/control tasks only;
- `interactive-admin-only` — human/admin use, not a resale compute pool;
- `research-only` — only qualifying research workloads under the applicable grant.

A `ci-only` or `interactive-admin-only` entitlement must never be silently converted into general compute simply because the runtime can technically execute code there.

## 4. Hard rights gate

An acquisition offer is invalid unless the system has evidence for:

- `authorized = true`;
- `termsPermitDeclaredUse = true`;
- `revocable = true`;
- non-empty `consentRef`;
- bounded resource limits;
- declared source-use class;
- settlement terms;
- expiry/revocation mechanism where applicable.

Credentials discovered by accident are not authorization.

## 5. Value first

Before asking a provider for a durable resource grant, BL-SCA should provide measurable value where practical, for example:

- local performance profile;
- idle-capacity estimate;
- thermal/energy-aware schedule recommendation;
- expected revenue range;
- expected DCC/reciprocal-compute value;
- cost optimization opportunity;
- benchmark against comparable nodes;
- security/configuration findings that do not require unnecessary data extraction.

This preview is explicitly an estimate, not guaranteed income.

## 6. Auto-enrollment rule

Auto-enrollment is allowed only when the provider has already signed/pre-authorized all of:

- `preAuthorizedGrant = true`;
- `autoEnrollAllowed = true`;
- current terms still permit the declared use;
- the offer remains inside resource/time/data limits;
- the current economics pass the configured margin gate.

Otherwise the engine produces a proposal and waits for explicit acceptance.

## 7. Positive-margin gate

Reference unit economics:

`ExpectedGrossProfit = ExpectedSettlementValue - ProviderAcquisitionCost - OperatorCost - VerificationCost - RiskProvision`

`ContributionMargin = ExpectedGrossProfit / ExpectedSettlementValue`

Reference default acquisition floor:

`MinimumContributionMargin = 10%`

An ordinary commercial acquisition is rejected if expected gross profit is non-positive or the contribution margin is below the configured floor.

Strategic investments may temporarily violate the margin floor only when explicitly classified, budgeted and justified by expected future value. They must not be mislabeled as profitable trades.

## 8. Provider compensation

Initial supported settlement concepts:

- cash;
- DCC;
- reciprocal compute;
- hybrid.

The Node Contribution Agreement decides what the provider accepts.

DCC settlement is permitted only if the treasury can mint/transfer the credit without violating the DCC backing ratio.

## 9. Routing after acquisition

Acquired capacity enters the normal BL-CF pipeline and does not gain a privileged bypass:

`Grant -> Registry -> Admission -> Route -> Lease -> Execution -> Validation -> Meter -> Settlement -> Audit`

The node rechecks its own local policy before execution.

## 10. Automatic search priorities

The acquisition engine should prioritize sources with high:

- legal certainty / grant clarity;
- trust and liveness;
- expected margin;
- price advantage;
- workload fit;
- locality/data fit;
- availability predictability;
- revocation safety;
- energy efficiency where economically relevant;
- strategic learning value.

It should penalize:

- hidden/ambiguous terms;
- volatile capacity;
- poor provenance;
- expensive egress;
- high failure rate;
- high integration cost;
- vendor lock-in;
- uncertain ownership;
- inability to verify usage;
- large switching/restart cost.

## 11. No prohibited harvesting

BL-SCA must not use:

- stolen/leaked credentials;
- covert browser cryptomining;
- malware/botnets;
- unauthorized corporate devices;
- abusive free-tier account farming;
- identity/payment evasion to multiply quotas;
- ToS circumvention;
- fake user traffic to obtain credits;
- hidden use of another party's electricity/network.

## 12. Resource acquisition as a DEUS learning problem

Every acquisition produces evidence:

- bid accepted/rejected;
- realized availability;
- realized resource cost;
- failure/revocation rate;
- provider satisfaction/retention;
- workload fit;
- settlement disputes;
- realized gross margin;
- DCC redemption behavior;
- renewal probability.

DEUS uses this evidence to learn which resource sources create the highest risk-adjusted long-term compute capital.

## 13. Initial known-resource classification rule

Not every resource already available to the project should be placed in the general pool.

Examples of the intended distinction:

- a local owner-authorized worker can become `general-compute` after the node client/grant is installed;
- a CI service remains `ci-only` unless its terms explicitly permit broader use;
- Cloud Shell-like interactive/admin environments remain `interactive-admin-only`;
- serverless/control products may be `control-plane-only` or narrow workload providers depending on their terms and technical limits;
- a contracted GCP/other cloud account may become general/trusted compute if the owner grant and service terms allow it.

## 14. First pilot

The first production acquisition pilot should prove the entire loop on a resource the Founder clearly controls:

1. provider manifest + authorization;
2. value-first profile;
3. economic quote;
4. explicit grant;
5. registration;
6. one bounded job;
7. independent result validation;
8. exact metering;
9. settlement receipt;
10. revocation test;
11. realized margin report.

Only after this works should automatic third-party acquisition expand.
