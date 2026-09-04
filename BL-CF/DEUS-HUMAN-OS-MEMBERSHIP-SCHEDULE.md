# DEUS Human OS — Bootstrap Membership & Resource Schedule v0.2

Status: FOUNDER-DIRECTED BOOTSTRAP SCHEDULE
Effective publication date: 2026-09-04
Supersedes: DEUS Human OS Bootstrap Membership & Settlement Schedule v0.1 for ordinary Human OS compute allocation
Applies with: BL Sovereign Compute Alliance / BL Compute Federation Founding Constitution v0.4

## 0. Purpose

This schedule defines the bootstrap access and resource-allocation law for the official **DEUS Human OS / Work-Chat** surface.

The governing objective is reciprocal customer benefit:

> A customer's node primarily exists to solve that customer's work. When the node is genuinely idle, a bounded portion of eligible capacity may strengthen DEUS and serve other authorized sessions. In return, the customer may receive DEUS capability plus lawfully available idle compute from the wider federation when useful and permitted.

This schedule does not transfer ownership of a user's machine, cloud account, data, credentials, network, energy source, organization, intellectual property or ungranted capacity.

The Founding Constitution remains controlling. Mandatory law, executed contracts, authorization, privacy, sovereignty, safety and revocation gates always override allocation targets.

## 1. Bootstrap governance

Until another eligible member has been admitted under an authenticated agreement, the Founding Steward constitutes 100% of the active bootstrap governing membership and may issue or revise operational schedules within the authority reserved to the Founding Steward by the Constitution.

This bootstrap majority does not create a right to confiscate resources, exceed an accepted grant, rewrite an executed agreement retroactively, bypass provider consent, or override mandatory law.

When additional eligible members are admitted, governance and review triggers revert to the applicable constitutional and contractual rules.

## 2. The 10 / 10 / 10 Resource Law

For an ordinary contributing Human OS node, DEUS recognizes three target envelopes over **eligible federation-dispatchable compute**:

1. **10% Commercialization Capacity** — capacity reserved for lawful commercialization, customer-serving commercial workloads, market delivery, revenue-producing federation work and other commercial activity approved by policy.
2. **10% Infrastructure Development Capacity** — capacity reserved for security, reliability, routing, evaluation, model/runtime improvement, observability, resource acquisition, knowledge infrastructure, recovery and other work that increases future DEUS / BL-CF capability.
3. **10% Cross-Session Mutual Compute Capacity** — capacity available to help other authorized DEUS sessions or federation nodes, but only while the contributing machine is genuinely idle and has no admitted foreground/local workload requiring that capacity.

These percentages are **allocation targets/caps over eligible capacity**, not a claim that DEUS owns 30% of the machine and not a command to maintain 30% utilization continuously.

The scheduler must account for CPU, GPU, accelerator, RAM, storage, network, energy, thermal state, battery state, user activity, time window, data locality, provider limits and workload class separately.

A provider may impose stricter caps or exclusions by explicit grant. Capacity not lawfully granted is not federation capacity.

## 3. Customer-First Active Work Rule

When the customer has an admitted active task, the customer's own work has priority over background federation use of that node.

DEUS may temporarily use **all additional local compute that is reasonably available, explicitly permitted and safe for the node** to solve that customer's task. This may include capacity beyond the three 10% federation envelopes when it is the customer's own workload.

The phrase **reasonably available** requires all applicable limits to pass, including:

- provider authorization and declared resource ceilings;
- foreground user activity and latency requirements;
- thermal, battery, energy and hardware-health limits;
- memory and storage pressure;
- network/bandwidth policy;
- privacy and data-locality rules;
- concurrency and reliability constraints;
- task value, cost and urgency;
- checkpoint, preemption and recovery requirements.

There is no constitutional requirement to leave 70% of the machine unused. If the customer requests a heavy task and the node grant permits it, DEUS may use most or nearly all temporarily available local capacity for that customer's own workload, subject to the limits above.

## 4. Idle-Only Cross-Session Law

The 10% Cross-Session Mutual Compute Capacity is subordinate to local work.

It may run only when the node is observably idle or has genuine unused headroom after local admitted workloads, system safety and owner-defined reserves are satisfied.

When local work appears, cross-session work must yield or preempt at a safe checkpoint according to the workload contract.

Cross-session execution must never rely on hidden cryptomining, arbitrary remote shell, credential sharing, covert bandwidth use, fake idle detection or silent persistence.

A node provider can suspend or revoke cross-session participation. Revocation prevents new leases and causes active work to checkpoint/terminate under the applicable lease policy.

## 5. Commercialization Capacity

The 10% Commercialization Capacity exists to help transform DEUS / BL-CF capability into sustainable economic activity.

Eligible uses can include:

- legitimate customer workloads;
- paid compute or AI services;
- commercial pilots and delivery;
- market discovery and benchmarking that directly supports monetization;
- compute used to acquire customers, providers or paid capacity under lawful agreements;
- other value-positive commercial work accepted by policy.

This allocation is a compute/resource policy. Any revenue share, price, success fee or settlement percentage is a separate economic contract unless explicitly stated otherwise in the applicable Settlement Schedule.

## 6. Infrastructure Development Capacity

The 10% Infrastructure Development Capacity may support:

- security hardening and resilience;
- model/runtime evaluation and improvement;
- routing and scheduling intelligence;
- observability, testing and incident recovery;
- storage/indexing/knowledge infrastructure;
- compute-federation protocol improvement;
- lawful resource acquisition and cost reduction;
- backup, restore and verification;
- other work with positive expected long-term infrastructure value.

Infrastructure work yields to safety constraints and may yield to higher-value customer foreground work when the scheduler determines that continuing it would materially harm customer service.

## 7. Reciprocal Federation Benefit

A participating external customer is not merely donating compute.

In exchange for authenticated membership and the accepted resource grant, the customer may receive:

- access to the official DEUS Human OS interface and permitted DEUS capabilities;
- use of the customer's own node as a first-party execution resource;
- intelligent routing across lawfully granted federation resources;
- supplemental compute from other nodes' genuinely idle capacity when available;
- appropriate task state, provenance, resource meters and audit receipts;
- privacy/locality-preserving execution such as compute-to-data where supported.

Federation supplementation is not an unlimited entitlement and no specific amount of external compute is guaranteed. Allocation depends on authorization, availability, fit, fairness, privacy, locality, safety, cost, value and other scheduling gates.

The intended reciprocal rule is:

`Contribute bounded idle capacity -> gain access to DEUS + eligible federation surplus -> improve customer outcomes -> strengthen federation -> create more useful shared capacity`

## 8. Routing and Preemption Order

A reference decision order is:

`Hard authorization/privacy/safety gates -> customer's local workload demand -> safe local-capacity expansion -> federation-surplus search -> value/risk/cost scoring -> lease -> execute -> validate -> meter -> settle -> audit`

For idle background work:

`Observed idle headroom -> owner reserve -> 10% commercialization target -> 10% infrastructure target -> up to 10% cross-session mutual compute -> checkpoint/preempt immediately when higher-priority local demand returns`

The exact production routing formula is protected implementation detail. The public contract guarantees consent, boundedness, customer-first priority, revocability, auditability and truthful metering.

## 9. Data, Privacy and Core Isolation

DEUS Human OS is an interface, not a disclosure channel for the protected DEUS core.

Users may receive outputs, task state, resource meters, permissions, provenance appropriate to their work and audit receipts. They do not receive protected prompts, raw private reasoning traces, secret routing policy, credentials, private topology, proprietary corpora, security-sensitive internals or enough protected material to reconstruct the core merely by using the interface.

Sensitive workloads must respect declared data-locality and compute-to-data constraints.

Idle capacity does not imply permission to inspect unrelated user data. Resource permission and data permission are separate grants.

## 10. Authentication and Acceptance Receipts

Production access requires an authenticated identity and a versioned acceptance receipt containing at least:

- actor/account identity;
- organization if applicable;
- Constitution version/hash;
- Membership Schedule version/hash;
- acceptance timestamp;
- node grant identifier if a node is activated;
- accepted 10/10/10 compute terms;
- resource classes and caps;
- customer-first priority acknowledgement;
- revocation/suspension state;
- server-side receipt identifier/signature or equivalent tamper-evident proof.

A browser-only/local receipt is a bootstrap UX artifact and is **not** a production authentication or legal-trust boundary by itself.

## 11. Production Truthfulness Rule

The Human OS UI must never represent a task as executed by DEUS, BL-CF, an external node or an AI model unless a real control-plane execution record exists.

If no authenticated control plane is attached, the UI must clearly state that it is in preview/offline mode and may only capture local task text or local configuration.

Resource meters must distinguish planned, reserved, leased, consumed and settled compute. Estimated capacity is not the same as consumed capacity.

## 12. Revocation and Exit

A lawful provider may suspend or revoke its node grant and stop future compute contribution. Revocation does not erase settlement obligations already accrued under completed work or records that must be retained for audit/legal reasons.

A user leaving the compute federation loses access to federation-contributing privileges unless another explicit contract preserves client-only access.

## 13. Founder Bootstrap Interpretation

During bootstrap the Founding Steward may refine UX, routing thresholds, admission categories, pricing schedules and technical implementation without changing the hard constitutional boundaries on authorization, lawfulness, sovereignty, boundedness, revocability, auditability, customer-first priority and non-deception.

Material economic or compute-right changes must be versioned prospectively and presented for renewed acceptance where required.
