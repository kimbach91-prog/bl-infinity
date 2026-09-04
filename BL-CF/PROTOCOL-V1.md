# BL-CF — Federation Protocol v1

Status: PROTOCOL BLUEPRINT

The protocol exposes bounded compute capabilities. It does not expose general remote administration.

## 1. Transport profile

Initial production profile:

- HTTPS with TLS 1.3 where supported;
- HTTP/2 for control/job APIs;
- mTLS or equivalent short-lived workload identity for trusted node links;
- outbound node polling/long-poll/SSE for job offers;
- WebSocket only where bidirectional streaming is necessary.

Future edge/mobile profile may use HTTP/3/QUIC/WebTransport after interoperability and operational evidence justify it.

Transport is replaceable. Message semantics and security invariants are not.

## 2. Message envelope

Every signed control message contains:

```json
{
  "protocol": "bl-cf/1",
  "messageType": "JOB_OFFER",
  "messageId": "uuid",
  "senderId": "spiffe-or-blcf-id",
  "receiverId": "blcf-node:...",
  "createdAt": "ISO-8601",
  "expiresAt": "ISO-8601",
  "nonce": "random-nonce",
  "policyHash": "sha256:...",
  "contractHash": "sha256:...",
  "bodyHash": "sha256:...",
  "signature": "detached-or-transport-bound-signature-reference"
}
```

Canonical serialization rules are versioned. Receivers reject expired, replayed, malformed, wrong-policy, or unauthorized messages.

## 3. Core messages

- `NODE_ENROLL` — register initial node identity and agreement references;
- `CAPABILITY_MANIFEST` — publish signed capabilities and provider policy;
- `COMPUTE_GRANT` — create/update bounded resource authorization;
- `HEARTBEAT` — availability and health without unnecessary personal telemetry;
- `JOB_OFFER` — signed immutable job proposal;
- `JOB_ACCEPT` — accept a job under a specific lease;
- `LEASE_RENEW` — renew execution lease with monotonic attempt identity;
- `CHECKPOINT` — announce resumable state hash/location under policy;
- `RESULT_RECEIPT` — return artifact/result hashes and metering data;
- `VALIDATION_RECEIPT` — verifier outcome and evidence references;
- `SETTLEMENT_RECEIPT` — payment/credit/protocol-share breakdown;
- `SHARED_BENEFIT_RECEIPT` — proof of promised common return;
- `REVOKE` — provider/control-plane revocation of a grant/lease/key;
- `POLICY_UPDATE` — signed policy/version notification;
- `FREEZE` — emergency capability freeze under authorized root policy.

## 4. Capability Manifest

Reference payload:

```json
{
  "manifestVersion": "bl-cf-provider/v2",
  "providerId": "node-123",
  "capabilities": ["wasm.execute", "oci.cpu.batch"],
  "resources": {
    "cpuClass": "x86_64/general",
    "cpuLogical": 16,
    "ramMiB": 32768,
    "gpu": [],
    "scratchMiB": 102400
  },
  "allocationPolicy": {
    "allowCommercialWorkloads": false,
    "allowCommonBenefit": true,
    "maxCommonBenefitShare": 0.05,
    "allowPrivateSharedBenefit": false,
    "emergencyOverrideMaxShare": 0.05
  },
  "dataPolicy": {
    "allowedClasses": ["public"],
    "regions": ["VN"],
    "egressDefault": "deny"
  },
  "grant": {
    "consentRef": "...",
    "expiresAt": "..."
  }
}
```

Provider policy is authoritative for that provider unless a later explicitly accepted grant changes it.

## 5. Job Manifest

Reference payload:

```json
{
  "schema": "bl-cf-job/v1",
  "jobId": "job-...",
  "tenantId": "tenant-...",
  "idempotencyKey": "...",
  "workloadClass": "H2",
  "purpose": {
    "code": "research.benchmark",
    "summary": "Reproducible Vietnamese reasoning benchmark"
  },
  "artifact": {
    "type": "oci",
    "digest": "sha256:...",
    "provenanceRef": "..."
  },
  "resources": {
    "cpu": 4,
    "ramMiB": 8192,
    "gpuClass": null,
    "scratchMiB": 20480,
    "maxSeconds": 1800
  },
  "network": {
    "mode": "deny",
    "allow": []
  },
  "data": {
    "class": "public",
    "locality": []
  },
  "valuePolicy": {
    "commonBenefitRequested": true,
    "sharedBenefitRef": null
  },
  "verification": {
    "method": "replicated-quorum",
    "quorum": 2
  },
  "contracts": {
    "workloadAgreementHash": "sha256:...",
    "policyHash": "sha256:..."
  },
  "deadline": "...",
  "expiresAt": "..."
}
```

## 6. Lease semantics

A job is executed only under an explicit lease.

Lease contains:

- `leaseId`;
- `jobId`;
- `attempt`;
- node identity;
- start/expiry;
- max resource envelope;
- expected artifact digest;
- current policy/contract hashes.

A lease expiry does not automatically authorize continued execution. The node must checkpoint/stop according to the job contract.

## 7. Idempotency and replay defense

- submitters provide idempotency keys;
- queue deduplicates by tenant + idempotency key;
- each execution attempt has an immutable attempt ID;
- settlement key binds job + attempt + result hash + validator receipt;
- duplicate settlement is rejected;
- nonce/expiry prevents control-message replay;
- provider heartbeat nonces are one-time or time-bounded.

## 8. Result protocol

`RESULT_RECEIPT` should contain:

- result/artifact digest;
- execution attempt/lease;
- wall time;
- metered CPU/GPU/memory/network/storage units;
- runtime version;
- checkpoint/result object references;
- node signature/identity;
- privacy-safe telemetry;
- error category if failed.

Large result objects stay in object storage or compute-to-data location; control plane carries hashes and authorized references rather than arbitrary large blobs.

## 9. Validation protocol

A validator never trusts provider self-attestation alone for materially rewarded work.

Validation methods include:

- exact digest/expected result;
- N-of-M replicated quorum;
- deterministic re-execution;
- statistical confidence test;
- hidden benchmark/gold case;
- proof/attestation of shared-benefit delivery.

A validation receipt states what was verified and what remains UNKNOWN.

## 10. Settlement protocol

Commercial settlement uses a versioned Settlement Schedule.

A receipt contains:

- ECSV calculation basis;
- 10% Official Protocol Commercial Share by default;
- provider credit/payment;
- Operator and pass-through components where applicable;
- common-benefit subsidy/return if contractually present;
- currency/VUC units;
- tax status where known;
- validator and meter receipt references;
- idempotent settlement ID.

## 11. Common-benefit accounting

A common-benefit job must include:

- whether the request is from the 0–5% target band or 5–10% expansion band;
- provider policy match;
- resource-class accounting bucket;
- common-benefit admission receipt;
- Shared-Benefit Contract if private/PGB;
- common-return verification receipt before final benefit credit.

Nodes independently reject a common-benefit lease if it would violate their configured cap.

## 12. Version negotiation

Protocol versions are explicit. Breaking changes require a new major protocol version.

Nodes advertise supported versions. Control plane selects the highest mutually supported version within policy.

Security-critical deprecation may reject an old version after a signed migration window.

## 13. Extension mechanism

Vendor/private extensions use namespaced keys and cannot redefine core security semantics.

Example:

`extensions.blcf.deus.routeHint`

Unknown extensions are ignored only when explicitly marked non-critical. Unknown critical extensions cause fail-closed rejection.

## 14. No invented cryptography

BL-CF uses established cryptographic protocols and libraries. The project may innovate in coordination, admission, allocation, verification and governance, but must not invent a new cipher/signature scheme for novelty.
