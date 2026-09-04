# DEUS Independent Penetration Test Scope R2

Status: REQUIRED BEFORE GOVERNMENT / REGULATED PRODUCTION

## Independence

The tester must be organizationally independent from the implementation team and must not rely on DEUS self-attestation as evidence of security.

## In scope

- Human OS same-origin web application and API.
- WebAuthn registration/login, MFA, session lifecycle, logout and step-up.
- CSRF, origin checks, cookie attributes, cache behavior and browser isolation headers.
- Founder bootstrap closure and account recovery paths.
- authorization and role/tenant boundaries.
- Constitution receipt creation, KMS signing and replay resistance.
- PostgreSQL access control, injection, race conditions, challenge/session replay and durable audit integrity.
- node enrollment, CSR handling, posture validation, certificate issuance/revocation and mTLS node ingress.
- BL-CF task admission/routing boundaries relevant to the gateway.
- SSRF, request smuggling, deserialization, file/path handling, dependency/supply-chain exposure and secret leakage.
- WAF/rate-limit bypass attempts within the agreed safe test window.
- privilege escalation from ordinary member -> admin/founder/M3/M4.
- protected-core disclosure attempts through public UI/API/errors/logging.

## Out of scope unless separately authorized

- destructive denial of service.
- social engineering of unrelated staff.
- attacks against third-party providers outside the DEUS-owned test tenancy.
- persistence on production customer devices.
- data exfiltration beyond synthetic test fixtures.

## Required deliverables

1. signed scope and rules of engagement;
2. methodology and tester identity/company;
3. findings with severity, reproduction steps and affected component;
4. evidence that critical/high findings are remediated or explicitly accepted by accountable humans;
5. retest results;
6. final signed closure statement;
7. hashes/URLs of the exact tested release and infrastructure configuration.

## Release rule

Government/regulated production may not mark `independent_penetration_test.verified=true` until the final independent closure artifact is archived in the protected evidence store and linked from the security receipt registry.
