# DEUS Human OS Gateway R2

This package is the same-origin security gateway for DEUS Human OS. It is intentionally separate from the public GitHub Pages reading surface.

## Security properties

- WebAuthn/passkey registration and login with `userVerification=required`.
- Mandatory TOTP second factor for founder/admin bootstrap/login.
- Opaque random server sessions; only SHA-256 digests are stored in PostgreSQL.
- `__Host-deus_session` is HttpOnly + Secure + SameSite=Strict + Path=/.
- exact Origin and session-bound CSRF checks on mutations.
- rate limits backed by PostgreSQL, not process memory.
- Constitution receipts are hash-addressed and signed by an external KMS/HSM service.
- TOTP secrets are encrypted/decrypted only through KMS workload identity.
- node enrollment requires AAL2, a signed Constitution receipt, a TPM/non-exportable CSR and security posture gates before CA signing.
- security/audit events are hash chained.
- production fails closed if required database/KMS/CA configuration is missing.

## Mandatory production environment

```text
DEUS_SECURITY_MODE=production
DATABASE_URL=postgresql://...
DEUS_DB_SSL=required
DEUS_DB_SSL_REJECT_UNAUTHORIZED=true
DEUS_RP_ID=<secure-human-os-domain>
DEUS_ORIGIN=https://<secure-human-os-domain>
DEUS_FOUNDER_EMAIL=<founder email>
DEUS_BOOTSTRAP_TOKEN_SHA256=<sha256 of one-time bootstrap secret>
DEUS_KMS_KEY_ID=<non-exportable KMS/HSM key id>
DEUS_KMS_SIGN_URL=<authenticated signing service>
DEUS_KMS_ENCRYPT_URL=<authenticated encrypt service>
DEUS_KMS_DECRYPT_URL=<authenticated decrypt service>
DEUS_CA_SIGN_URL=<authenticated node CA signing service>
```

KMS/CA calls use `VERCEL_OIDC_TOKEN` when deployed on Vercel, or `DEUS_WORKLOAD_IDENTITY_TOKEN` on another approved platform. A long-lived KMS private key must never be present in these environment variables.

## Database

Apply `schema.sql` with a schema-owner/migration identity. The runtime identity should not own the schema and should not have `DROP TABLE`, role-management or database-owner privileges.

## One-time founder bootstrap

1. Create a high-entropy random bootstrap secret outside Git.
2. Store only its SHA-256 verifier as `DEUS_BOOTSTRAP_TOKEN_SHA256` in the production secret manager.
3. Open the same-origin Human OS gateway.
4. Enroll the founder passkey.
5. Enroll TOTP and verify the first code.
6. Immediately remove `DEUS_BOOTSTRAP_TOKEN_SHA256` from the production environment and redeploy/restart.
7. Record a security receipt proving bootstrap is closed.

A production instance with an existing user rejects the bootstrap path even if an old bootstrap verifier remains by mistake.

## WAF / bot protection

Application rate limiting is not a substitute for edge WAF. Before production, configure managed WAF/bot/DDoS protection in the live hosting account and record a verification receipt. This repository cannot truthfully mark that control ACTIVE until the external edge configuration is observed.

## Independent penetration test

CI security checks and DAST are internal controls. They do not satisfy the independent penetration-test requirement. Government/regulated production remains blocked until an independent test is scoped, executed, remediated and signed off.
