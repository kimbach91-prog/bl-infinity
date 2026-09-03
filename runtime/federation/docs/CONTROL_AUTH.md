# Scoped Control Principals — v0.9

BL Compute Federation v0.9 adds scoped control principals while retaining `BL_CONTROL_TOKEN` as a backward-compatible root credential.

## Authority model

Control-plane identity is separate from provider authority:

```text
control principal -> who may ask the coordinator to perform an operation
provider grant     -> which compute node is authorized to perform which work
```

A broader control scope does not widen a provider grant. `reachable != authorized` remains unchanged.

## Legacy root

Existing deployments may continue to use:

```bash
export BL_CONTROL_TOKEN='high-entropy-root-token'
```

That credential maps to the synthetic principal `legacy-root` with tenant `*` and scope `*`.

Use it as a compatibility/break-glass path, not as the preferred long-term credential for every caller.

## Scoped principals

Principals are configured with `BL_CONTROL_PRINCIPALS_JSON`. The JSON stores the **name** of an environment variable, never the bearer secret itself.

Example:

```bash
export TENANT_A_API_TOKEN='high-entropy-tenant-token'
export OPS_READ_TOKEN='high-entropy-ops-token'

export BL_CONTROL_PRINCIPALS_JSON='[
  {
    "id":"tenant-a-app",
    "tenantId":"tenant-a",
    "tokenEnv":"TENANT_A_API_TOKEN",
    "scopes":["task:submit"]
  },
  {
    "id":"ops-read",
    "tenantId":"*",
    "tokenEnv":"OPS_READ_TOKEN",
    "scopes":["provider:read","runtime:read","ledger:read","audit:read"]
  }
]'
```

The runtime resolves token values from the named environment variables at startup and uses SHA-256 fingerprints for in-process lookup. Raw bearer values are not written to PostgreSQL or embedded in the principal configuration object.

## Known scopes

Current scopes are:

```text
task:submit
provider:read
provider:admin
provider:heartbeat
route:read
runtime:read
runtime:operate
runtime:execute
ledger:read
audit:read
search:read
search:write
```

Unknown scopes fail startup instead of silently becoming unused typo-permissions.

## Tenant boundary

Only `task:submit` is currently allowed for a tenant-specific principal.

A principal such as:

```json
{
  "id":"tenant-a-app",
  "tenantId":"tenant-a",
  "scopes":["task:submit"]
}
```

has these semantics:

```text
missing task.tenantId  -> set to tenant-a
same tenantId          -> accepted
different tenantId     -> TENANT_SCOPE_VIOLATION / HTTP 403
```

Provider administration, runtime operations, audit, ledger, routing and search are currently global stores/surfaces in the reference runtime. Those scopes therefore require `tenantId="*"` until the underlying data paths have true tenant isolation.

Do not work around this restriction by granting a tenant principal global scopes.

## Public read surfaces

v0.9 is private-by-default. If no bearer credential is configured, `/providers`, `/route` and `/search/query` are **not** implicitly public.

To expose a read surface intentionally:

```bash
export BL_PUBLIC_READ_SCOPES='search:read'
```

Supported public scopes are limited to:

```text
provider:read
route:read
search:read
```

Mutation/operation scopes cannot be made public through this setting.

## HTTP outcomes

The reference control plane distinguishes:

```text
401 unauthorized                -> control auth exists, bearer missing/unknown
403 scope-denied                -> known principal lacks required scope
403 TENANT_SCOPE_VIOLATION      -> task tries to cross tenant boundary
503 control-auth-not-configured -> protected operation requested without any control authority configured
```

Health and separately authenticated worker self-heartbeat remain independent of control bearer auth.

## Rotation

Principal token values are resolved at process startup in v0.9. Rotate by:

1. create a new secret value in the secret manager/environment;
2. update the principal `tokenEnv` or the value behind it;
3. restart/redeploy coordinators;
4. verify the new token works and the old token fails;
5. remove the old secret after convergence.

For zero-overlap rotation, temporarily configure a second principal/token with the same intended scope, converge coordinators, then remove the first.

## Audit

Security-sensitive operator actions write actor IDs into the audit log where the endpoint already emits an audit record, including task submission, direct execution and provider administration paths.

Never log bearer token values.

## Current boundary

This is application-level authorization, not a replacement for network identity, TLS, service-mesh policy or GitHub/server administration. Production deployments should also restrict who can read environment secrets and who can modify principal configuration.
