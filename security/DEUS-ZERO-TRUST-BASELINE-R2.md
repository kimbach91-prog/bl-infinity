# DEUS Zero-Trust Production Baseline R2

Status: SECURITY HARDENING CONTRACT

This document is a fail-closed production contract for DEUS Human OS, BL Compute Federation and physical nodes. A control is not considered ACTIVE merely because code or documentation exists. ACTIVE requires a live configuration plus a verification receipt.

## Mandatory production gates

1. PASSKEY: WebAuthn resident credential, phishing-resistant, userVerification=required.
2. MFA: privileged sessions require a second factor after WebAuthn. Bootstrap and M3/M4 actions require AAL2.
3. SERVER SESSION: opaque random session IDs; only SHA-256 digests are stored server-side. Browser receives `__Host-deus_session` with HttpOnly, Secure, SameSite=Strict, Path=/ and no Domain attribute.
4. CSRF/ORIGIN: mutating requests require exact trusted Origin plus a session-bound CSRF token.
5. SERVER RECEIPTS: Constitution acceptance is hash-addressed, append-only and signed by a KMS/HSM-backed key. Production fails closed when the signing service is unavailable.
6. DATABASE: PostgreSQL is mandatory for users, WebAuthn credentials, challenges, MFA state, sessions, receipts, node enrollment and audit state. In-memory state is forbidden in production.
7. APPEND-ONLY AUDIT: security-sensitive events are hash chained. Audit deletion is not an application capability.
8. WAF/BOT: production ingress requires managed WAF/bot/DDoS controls, request size ceilings and route-specific rate limits.
9. DEVICE ENROLLMENT: a node is not active from browser detection alone. Production enrollment requires a non-exportable device key, signed grant, posture/attestation record and revocation path.
10. SECRET MANAGEMENT: no production credential, CA private key, receipt signing key, database password or bootstrap token is committed to Git. Long-lived root secrets are forbidden in browser storage.
11. KMS/HSM: receipt/CA keys are remote/non-exportable. Runtime receives only signing/decryption capability, preferably through short-lived workload identity.
12. NODE IDENTITY: local/partner nodes use mTLS or equivalent workload identity. Generic inbound remote shell is forbidden.
13. CORE ISOLATION: protected prompts, raw private reasoning, private routing/scoring, secrets, private topology and protected corpora never enter the public client bundle.
14. SUPPLY CHAIN: lockfiles, pinned CI actions, dependency/security scanning and release provenance are required.
15. PEN TEST: automated security tests are necessary but not equivalent to an independent penetration test. Government/regulated production is blocked until an independent test has a signed scope, findings record and closure receipt.
16. RECOVERY: backup/restore, key rotation, credential revocation, emergency freeze and founder/root recovery must be exercised, not merely documented.

## Bootstrap rule

The first Founder passkey enrollment may use a one-time bootstrap secret only while the user database contains zero users. The server stores only a SHA-256 verifier for that bootstrap secret. After the first founder passkey and MFA enrollment succeed, the bootstrap verifier must be removed/disabled and cannot be used as a standing login method.

## Session policy

- Normal Human OS work: AAL2 for founder/admin; organizations may define lower-risk AAL policy only for non-privileged users.
- M3 economic actions and any security/admin action: fresh AAL2 step-up.
- M4 constitutional/ownership/canonical identity actions: Human approval plus separate signing authority; never delegated to a browser session alone.
- Idle timeout, absolute timeout, revocation and single-session/device policy are server-side.

## KMS/HSM policy

Production code must not contain an embedded private signing key. The gateway calls an approved KMS/HSM signer/encryptor over authenticated workload identity. The private key must be non-exportable. A local software key is allowed only in explicitly labeled development and must cause a production-startup failure.

## Node policy

A browser-created node profile is descriptive only. A production node must present an enrollment certificate or approved workload identity derived from a signed, revocable grant. Windows founder nodes should generate a non-exportable key using the Microsoft Platform Crypto Provider/TPM when available, keep worker listeners loopback/private by default, and pull work outbound.

## WAF policy

Required edge controls: managed rule set, bot protection, per-route rate limits, body-size limits, geo/ASN policy where justified, DDoS protection, TLS-only, HSTS and an emergency deny-all/freeze rule. WAF configuration requires a live edge account and must have a separate verification receipt.

## Truthfulness state

`CODE_PRESENT != CONTROL_ACTIVE`

`CONFIGURED != VERIFIED`

`VERIFIED_ONCE != CONTINUOUSLY_SAFE`

The runtime and UI must expose these distinctions rather than claiming production security from source code alone.
