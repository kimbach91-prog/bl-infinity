# BL-CF — Security Architecture & Threat Model v1

Status: IMPLEMENTATION BLUEPRINT

Security objective: contributor participation must never imply blind trust in BL-CF, and BL-CF must never imply blind trust in contributor nodes.

## 1. Zero-trust rule

Trust is evaluated per identity, resource, workload, data class, contract, and request. Network location, account ownership, prior participation, or Founder status does not create implicit execution authority.

## 2. Principal types

- human user;
- Founding Steward;
- operator/admin;
- workload submitter;
- node provider;
- node agent;
- workload identity;
- validator;
- settlement service;
- DEUS planner/router;
- canonical release/signing service.

Each principal receives a distinct identity and least-privilege capability set.

## 3. Identity

### Human/admin

- OIDC for normal federation identity;
- passkeys/WebAuthn for strong authentication;
- step-up authentication for settlement changes, key rotation, registry admission, policy publication and emergency controls;
- no shared admin accounts.

### Node/workload

- bootstrap node identity with signed key material;
- progress toward short-lived workload identities and mTLS, compatible with SPIFFE/SPIRE-style trust domains or equivalent standards;
- credentials expire and rotate; long-lived bearer secrets are avoided.

## 4. Root of trust and anti-capture

No single online credential may be sufficient to redefine canonical BL-CF.

Recommended layers:

1. offline/hardware-backed constitutional root;
2. separate release-signing authority;
3. short-lived CI identity for ordinary release automation;
4. independent domain/trademark account;
5. independent source mirror;
6. recovery manifest stored outside the primary Git host.

For root recovery, use a multi-party or multi-device threshold such as 2-of-3 where legally/operationally appropriate. At least two components should be physically/administratively independent and Founder-controlled or Founder-authorized.

Emergency freeze may stop new privileged actions but must preserve public verification of the last known canonical state.

## 5. Software supply chain

Every production workload artifact should be immutable and attributable.

Target controls:

- OCI/WASM content digest pinning;
- SBOM;
- build provenance;
- signed artifacts, preferably keyless CI signing plus protected root/release policy;
- dependency scanning;
- reproducible builds where practical;
- secure update metadata resistant to rollback/freeze/mix-and-match attacks;
- no execution from mutable `latest` tags in trusted production paths.

The repository's existing MIT-licensed code must not be silently relicensed. Future AGPL coverage requires an explicit rights/scope audit before release.

## 6. Node execution isolation

Preferred isolation tiers:

### Tier A — WASI/WASM

Use for small deterministic or constrained workloads where the runtime supports required computation. Default no ambient filesystem/network authority.

### Tier B — hardened container sandbox

For general CPU workloads:

- non-root user;
- read-only root filesystem;
- ephemeral scratch;
- seccomp/capability drop;
- cgroup resource limits;
- no host mounts by default;
- no Docker socket;
- network default deny;
- stronger userspace/microVM sandbox where risk justifies it.

### Tier C — GPU / high-risk specialized workload

- dedicated device policy;
- strict container/device isolation;
- no arbitrary host driver administration;
- data-locality constraints;
- high-cost job approval/budget ceiling;
- canary/validation before large-scale fan-out.

## 7. Network security

- outbound-pull node model by default;
- TLS 1.3 for network links where available;
- mTLS/short-lived identity for trusted node/control paths;
- egress default deny for jobs;
- explicit hostname/service allowlists when networking is necessary;
- request size/time limits;
- rate limiting by identity/tenant/provider;
- DDoS shielding at public gateways;
- replay protection with nonce, expiry, and idempotency keys.

No official node accepts a naked remote shell command as a workload protocol primitive.

## 8. Secrets

- no plaintext secrets in job manifests or source;
- use a Secret Manager or equivalent protected store;
- issue short-lived per-job credentials with the minimum scope;
- use envelope encryption for stored sensitive material;
- secret access is auditable and separately authorized;
- secret values are never included in public audit receipts.

## 9. Data security

Data policy is fail-closed.

- PUBLIC may use public nodes.
- INTERNAL requires trusted nodes.
- PRIVATE uses trusted or sovereign nodes.
- REGULATED requires jurisdiction/compliance match.
- SEALED must remain in the sovereign environment; move compute to the data.

Raw private prompts/data/results are not logged by default. Telemetry should use minimization, pseudonymous identifiers and bounded retention.

## 10. Malicious node threats

Threats:

- fabricated compute result;
- result tampering;
- Sybil nodes;
- capacity misrepresentation;
- replay of valid result;
- deliberate slowdown/failure;
- exfiltration attempts;
- collusion among validators/providers.

Mitigations:

- cryptographic job/result IDs;
- independent redundancy/quorum when cost permits;
- hidden/gold tests;
- random spot checks;
- deterministic seeds for reproducibility;
- reputation with decay;
- payout/credit holds for new/high-risk nodes;
- independent validators;
- capacity challenge/attestation where economically justified.

No proof-of-work cryptocurrency is required for Sybil resistance.

## 11. Malicious submitter threats

Threats:

- disguised mining;
- malware;
- credential attacks;
- fake engagement/spam;
- unauthorized scanning;
- attempts to exfiltrate node data;
- resource-amplification attacks;
- false common-benefit claims.

Mitigations:

- workload purpose declaration;
- artifact scanning;
- capability/network sandbox;
- resource caps;
- tenant budget;
- AUP enforcement;
- higher scrutiny for network-active tasks;
- Shared-Benefit Contract verification before common-benefit credit is finalized.

## 12. DEUS/control-plane compromise

DEUS must not be able to turn a policy bug into unlimited power.

Guardrails:

- DEUS generates plans within signed policy, not arbitrary root authority;
- provider-side agent independently rechecks grant, expiry, resource cap and allowed workload class;
- canonical-write and key-management authority remain separate;
- settlement has independent readback/reconciliation;
- anomalous allocation rate automatically trips a circuit breaker;
- common-benefit consumption above provider cap is rejected locally even if control plane requests it.

## 13. Economic/fraud security

- meter before settle;
- validate before reward;
- separate workload price from provider payout and protocol share;
- settlement receipts are immutable/idempotent;
- no double settlement for replayed result;
- new providers and new workload classes use bounded canary limits;
- suspicious correlated identities are reviewed before high payouts.

## 14. Incident response

Minimum lifecycle:

`DETECT -> CONTAIN -> FREEZE AFFECTED CAPABILITY -> PRESERVE EVIDENCE -> ROTATE/REVOKE -> RECOVER -> INDEPENDENT READBACK -> DISCLOSE APPROPRIATELY -> LEARN`

Security incidents must not be hidden to preserve appearance. Public communication should disclose confirmed impact without leaking secrets or private victim data.

## 15. Security evolution

Security claims must be evidence-based. Use independent penetration testing and external review before describing production BL-CF as hardened at scale.

A public vulnerability disclosure policy and eventually a funded bug-bounty program should be added when a live service exists.
