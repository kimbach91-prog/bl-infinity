# DEUS HMI — Third-Party Verification Protocol v0.1

Status: `CANDIDATE / CORE-SAFE / BLACK-BOX-FIRST`

## Verification objective

Verify the human-facing boundary without requiring disclosure of DEUS protected core material.

The verifier is asked to test the claim:

> An authorized enterprise/government user can operate through a bounded work interface while no user-facing route provides direct read or mutation access to protected DEUS core state.

This protocol does **not** ask the verifier to certify the private core implementation itself.

## Protected material that is out of scope for disclosure

The operator must not provide the verifier with:

- private system/developer prompts;
- private evolutionary selector/mutation/fitness logic;
- private model/provider routing policy;
- unrestricted lineage/canonical internals;
- raw hidden reasoning traces;
- credentials, keys or deployment secrets;
- private topology or reconstruction-enabling maps;
- protected corpora or tenant data not required by the test.

Verification evidence should use opaque references, synthetic fixtures and bounded projection samples.

## Minimum independent evidence bundle

For every tested build, record:

- repository/build identifier or signed release identifier;
- immutable commit/build digest;
- runner or physical-machine environment;
- test command / benchmark harness version;
- complete pass/fail transcript;
- transcript digest;
- artifact digest;
- verifier identity/organization;
- start/end timestamps;
- deviations from the prescribed harness;
- failures, retries and environmental anomalies.

A screenshot alone is not sufficient evidence.

## Black-box test matrix

### A. Entry and authentication

1. Anonymous request -> denied.
2. Guest account -> denied.
3. Public self-registration attempt -> unavailable/denied.
4. Consumer tenant -> denied.
5. Enterprise tenant with approved identity flow -> eligible.
6. Government tenant with approved identity flow -> eligible.
7. Expired session -> denied.
8. Missing strong-auth requirement -> denied when policy requires it.
9. Session replay/revocation test -> revoked/expired session cannot continue.
10. Client-supplied tenant/role/scope claims -> ignored/rejected.

### B. Core isolation

Probe direct and encoded variants of protected namespaces, including:

```text
/core
/internal
/prompts
/evolution
/router
/lineage
/traces
/secrets
/topology
/corpora
/canonical/raw
```

Also test case variants, duplicate separators, URL encoding, path traversal, query-based overfetch and alternate API transports if present.

Expected result: no user-facing principal receives protected core content. A high-privilege HMI administrator must not become a core reader merely by accumulating HMI scopes.

### C. Projection/data boundary

1. Same projection/object ID in tenant A and tenant B returns tenant-local values only.
2. Unknown tenant receives no neighboring/global fallback.
3. Missing tenant context fails closed.
4. Cross-tenant read is denied.
5. Cross-tenant write is denied.
6. Expired projection is unavailable.
7. Sensitive nested fields are absent from the response and storage projection.
8. Debug/error responses do not serialize raw upstream/core objects.
9. Caches are tenant-keyed and cannot return another tenant's result.
10. Unsupported projection schema fails closed.

### D. User action boundary

1. Only allowlisted action IDs can execute.
2. Unknown tool/arbitrary-code actions are rejected.
3. `core`, `evolution`, `router`, `lineage`, `secret`, `canonical` action families are rejected from the user plane.
4. Unexpected payload fields are rejected.
5. Oversized payloads are rejected.
6. Cross-tenant action is rejected.
7. Material actions require explicit confirmation.
8. Material actions requiring step-up reject stale/missing step-up state.
9. Command receipts bind principal, tenant, action, policy version and timestamp.

### E. Client reverse-engineering / disclosure

Inspect web/desktop distributed artifacts for:

- embedded prompts or protected corpora;
- hidden core endpoints;
- embedded bearer credentials;
- private topology;
- unrestricted model routing configuration;
- raw trace/log dumps;
- generic shell/eval/arbitrary-code bridges;
- development/debug backdoors.

Expected result: the client contains only interface/protocol material necessary to operate the bounded HMI.

### F. Failure behavior

Induce failures in identity adapter, projection backend, policy lookup and network dependencies.

Expected result: protected operations fail closed. A projection/backend failure must not fall back to raw core state.

## Database isolation evidence

Where PostgreSQL is used, verify at minimum:

- Row-Level Security enabled;
- `FORCE ROW LEVEL SECURITY` enabled for the projection table;
- runtime role is non-superuser and lacks `BYPASSRLS`;
- tenant context is set inside the transaction;
- no tenant context -> zero rows / denied operation;
- tenant A cannot insert/update/read tenant B records.

Application-level tenant checks alone are insufficient for this test.

## Claim language

Allowed when evidenced:

- `TESTED_PASS` for a named test on a named immutable build/environment.
- `OBSERVED_DENIED` for a directly observed denied attack path.
- `NO_FINDING_IN_TEST_SCOPE` when a scan found no issue within its exact scope.

Forbidden overclaims:

- `UNHACKABLE`;
- `ABSOLUTELY SECURE`;
- `GOVERNMENT CERTIFIED` without the named certification;
- `NO SECRET EXISTS ANYWHERE` from a bounded scan;
- `CORE VERIFIED` when the private core was intentionally outside the supplied evidence.

## Current candidate evidence

The repository workflow may emit a portable HMI benchmark artifact containing a TAP transcript and a receipt with environment/build metadata and SHA-256 digest. Independent verifiers should re-run the tests in their own environment instead of trusting the repository artifact alone.

## Independence rule

A valid third-party verification report must distinguish:

```text
SYSTEM-PRODUCED EVIDENCE
VERIFIER-REPRODUCED EVIDENCE
VERIFIER-INDEPENDENT ADVERSARIAL TESTS
UNTESTED / UNKNOWN
```

Agreement is not proof. Reproduction and adversarial attempts matter more than consensus.
