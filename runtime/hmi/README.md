# DEUS Human OS / HMI Access Gateway v0.1

Status: `CANDIDATE / NON-CANONICAL / THIRD-PARTY-TESTABLE`

This package is the human-facing trust boundary for DEUS. It intentionally contains **no DEUS core prompts, evolutionary logic, private routing policy, lineage internals, raw reasoning traces, secrets, private topology or protected corpora**.

## Product boundary

DEUS is not a public consumer product.

Eligible tenant classes:

- `enterprise`
- `government`

Forbidden entry modes:

- anonymous access
- guest access
- public self-signup
- consumer tenant creation
- direct core read APIs

Every user interaction must pass:

```text
verified identity
  -> active organization/tenant
  -> strong authentication policy
  -> role + policy version
  -> session validity
  -> data classification clearance
  -> explicit HMI surface scope
  -> projection gateway
  -> user-facing workspace/result
```

Authentication proves identity. It does **not** grant core visibility.

## Non-bypassable core isolation

The HMI policy denies protected namespaces before evaluating role or scope. Therefore a root-like administrator cannot obtain a direct core read by accumulating HMI permissions.

Protected examples:

```text
/core/**
/prompts/**
/evolution/**
/router/**
/lineage/**
/traces/**
/secrets/**
/topology/**
/corpora/**
/canonical/raw/**
```

Administrative operation on DEUS must use a separately defined, audited operator/control plane and must not be implemented as a hidden HMI core-reader role.

## Identity adapter contract

`authorizeHmiRequest()` MUST receive a server-side verified session from a trusted identity adapter. The browser/client must never be allowed to self-assert `identityId`, `tenantId`, roles, scopes, authentication methods, or clearance.

A production identity adapter must verify, as applicable:

- issuer and cryptographic signature;
- audience / client binding;
- nonce/state and authorization-code flow integrity;
- token/session expiry and revocation posture;
- organization membership / tenant binding;
- MFA/passkey/hardware-backed authentication requirements;
- role/policy claims from an authoritative server-side source;
- anti-replay/session fixation controls.

For government deployments, deployment policy may require phishing-resistant authentication such as passkeys, FIDO2 hardware keys, smart cards or equivalent approved controls.

## Projection contract

The DEUS core must not be serialized and then "hidden in the UI". That is not isolation.

The required flow is:

```text
core/private state
  -> dedicated projection builder in trusted server boundary
  -> allowlisted HMI envelope
  -> defense-in-depth sanitizer
  -> authorized user surface
```

The current public-safe sanitizer only allows these top-level categories:

- workspace
- task
- status
- evidence
- results
- availableActions
- warnings
- unknowns
- userMessages
- timestamps

This sanitizer is defense in depth, **not** permission to connect it directly to raw core state.

## Tenant isolation

A session is bound to exactly one active tenant for the request. Cross-tenant identifiers fail closed. Application/data stores must enforce tenant isolation independently; HMI authorization is not a substitute for database row-level or physical isolation.

## Third-party benchmark claims allowed by this package

A verifier may test and report only what is directly evidenced, for example:

1. anonymous/guest/public-self-signup attempts are denied;
2. consumer tenant class is denied;
3. enterprise/government tenants can be admitted when authentication and policy gates pass;
4. expired/weak sessions are denied;
5. cross-tenant requests are denied;
6. protected core paths are denied even for high-privilege HMI roles;
7. unregistered user surfaces fail closed;
8. projection sanitization removes sensitive fields in supplied projection candidates.

This package alone does **not** prove:

- production IdP integration;
- production database tenant isolation;
- absence of secrets elsewhere in the full deployment;
- absence of side channels;
- security of a private DEUS core implementation not supplied to the verifier;
- compliance with any government certification regime.

Those require deployment-specific evidence and independent testing.
