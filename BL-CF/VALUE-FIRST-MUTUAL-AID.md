# BL-SCA / BL-CF — Value-First Mutual Aid & Capacity Expansion v0.1

Status: `NON-CANONICAL / PILOT CANDIDATE`

## 1. Purpose

This lane operationalizes the BL-SCA adoption principle **“Trao giá trị trước. Chủ quyền luôn thuộc người sở hữu.”**

BL-SCA may provide bounded, useful technical assistance to people, teams, public-interest projects, researchers, small organizations and prospective infrastructure partners **before** asking for any Compute Grant.

Receiving help creates **no obligation** to join BL-SCA, provide compute, accept DCC, pay a fee, disclose credentials, or transfer IP/data. Any later compute participation requires a separate explicit, revocable grant under the Founding Constitution and BL-CF protocol.

## 2. Why this expands the federation

The federation should grow by demonstrated usefulness, not by demanding access to idle machines.

A Value-First interaction can produce one or more of:

- a fixed CI/build failure;
- a reproducible benchmark or test harness;
- a resource/thermal/cost profile;
- a security-hardening or recovery checklist;
- a backup/continuity improvement;
- a public-data processing result;
- a bounded performance optimization;
- a documented deployment/runbook improvement;
- an open-source bug fix or review;
- a validated estimate of what a machine/cloud quota could safely contribute.

Only after the recipient has received the result may BL-SCA invite them to explore provider participation.

## 3. Eligible help classes

Initial pilot classes:

- `VH-CI` — build/test/CI diagnosis and bounded repair;
- `VH-SEC` — defensive security baseline and exposure reduction;
- `VH-PERF` — performance, cost, energy and thermal profiling;
- `VH-RECOVERY` — backup, restore, checkpoint and continuity design;
- `VH-DATA-PUBLIC` — public/open-data cleanup, indexing or reproducibility work;
- `VH-OSS` — open-source maintenance, tests, docs or bounded bug fixing;
- `VH-COMPUTE-READINESS` — capability profiling and safe BL-CF onboarding plan.

A help request can also map to constitutional workload classes `H0`–`H3` or Strategic Compute Reinvestment when separately admitted by policy.

## 4. Hard gates before helping

A Value-First task is accepted only when:

1. the requester has authority to ask for the work/artifact access involved;
2. no secret, credential or unnecessary personal data is posted publicly;
3. the task is lawful and non-deceptive;
4. scope, time/resource ceiling and deliverable are bounded;
5. data source/use rights are declared;
6. harmful operations, unauthorized scanning, malware, credential attacks, spam/fake engagement and hidden mining are rejected;
7. output can be verified or at least independently inspected;
8. any side effect outside a sandbox has explicit authority.

## 5. Help is not a disguised Compute Grant

The following are forbidden:

- treating a help recipient's device as available compute because assistance was provided;
- asking for passwords, cloud keys or remote shell as a condition of help;
- installing a worker without explicit separate consent;
- silently turning a diagnostic agent into a federation node;
- inferring consent from inactivity or gratitude;
- tying completion of promised help to later enrollment;
- claiming ownership, canonical authority or IP merely because BL-SCA helped.

## 6. Optional transition to provider participation

After a useful result is delivered, the recipient may choose one of:

- `NO_FEDERATION` — close the interaction; no follow-up resource request;
- `LEARN_MORE` — receive a capability/value preview only;
- `PROFILE_ONLY` — run a local-safe resource profile with no remote execution authority;
- `PILOT_GRANT` — create a small, expiring Compute Grant;
- `PROVIDER_DISCOVERY` — discuss enterprise/BYOC/cloud-credit participation.

Any Compute Grant must identify at least:

- provider identity/authority;
- `consentRef`;
- capability manifest;
- exact workload/data/source-use classes;
- CPU/GPU/RAM/storage/network/time/energy/thermal ceilings;
- region/data-locality rules;
- settlement/reinvestment policy if any;
- expiry and revocation path;
- heartbeat/telemetry scope;
- rights explicitly **not** granted.

## 7. Public issue safety

Public issue forms collect only coarse, non-secret information. Never post:

- API keys, passwords, access tokens, private keys or recovery codes;
- private IPs/VPN details/internal topology that creates material risk;
- personal identifiers that are not needed;
- private datasets or confidential customer data;
- privileged logs containing secrets.

If private handling is genuinely needed, public intake must stop at a sanitized pointer and move to an authorized private channel.

## 8. Receipt

Every completed pilot should create a Value-First Help Receipt containing:

- request/artifact reference;
- help class;
- declared authority/source-use basis;
- bounded scope;
- before/after evidence where possible;
- deliverable/result references;
- verification state;
- unresolved UNKNOWN;
- whether any federation invitation was made;
- recipient's independently chosen next state;
- explicit statement that help did not itself create a Compute Grant.

Machine-readable schema: `BL-CF/value-first-help-receipt.schema.json`.

## 9. Success metrics

Optimize for:

- useful tasks completed and independently verifiable;
- recipient satisfaction/correction rate;
- security incidents prevented;
- reproducibility/uptime/cost improvements;
- voluntary `LEARN_MORE` / `PROFILE_ONLY` conversions;
- verified compute capacity added through explicit grants;
- provider retention and revocation success;
- zero unauthorized resource use.

Raw outreach count and raw install count are not success metrics.

## 10. Relationship to constitutional economics

This lane does **not** amend the Founding Constitution.

Unpaid help can be Founder-funded, H0–H3 admitted, open-source contribution, or a bounded strategic-reinvestment activity when its expected federation return is positive. The Constitution does not require unpaid public-benefit work, and this pilot must not consume provider capacity outside the provider's explicit opt-in.

## 11. Default operating sequence

`REQUEST → RIGHTS/SAFETY GATE → BOUNDED HELP → VERIFY → RECEIPT → OPTIONAL VALUE PREVIEW → OPTIONAL EXPLICIT COMPUTE GRANT`

At every stage:

`HELP != CONSENT`

`ACCESS != OWNERSHIP`

`IDLE != AVAILABLE`

`CONTRIBUTION != AUTHORITY`

`REVOCATION MUST WORK`
