# DEUS Consented Edge Worker Contract v0.1

## Enrollment

A device may become an edge worker only when all fields are present and valid:

- relayId
- consentRef
- ownerRef or organizationRef
- deviceClass
- capabilityManifest
- allowedWorkloads
- maxConcurrency
- maxDutyCycle
- thermalCeilingPolicy
- energyPolicy
- dataLocalityPolicy
- actionMode
- credentialScopeRef
- authorizationExpiry
- revocationPath

Enrollment must fail closed on missing authorization, expired authorization, or unsupported data locality.

## Resource sovereignty

Owner workload always outranks DEUS background work.

The edge worker must yield when any configured signal indicates contention, including foreground CPU pressure, memory pressure, thermal pressure, battery floor, storage pressure, interactive latency degradation, or owner pause/revoke.

No attempt should be made to preserve DEUS utilization at the owner's expense.

## Work admission

A candidate job is accepted only when:

1. authorization is valid;
2. required data may legally and contractually reside on the device;
3. estimated setup + compute + cleanup + switching cost fits the available headroom window;
4. predicted utility is positive after energy, thermal, failure, and disruption costs;
5. rollback/checkpoint rules are available where needed.

## Maintenance exchange

A participating worker may receive:

- health checks for the enrolled worker runtime;
- workload efficiency analysis;
- energy and thermal optimization advice;
- scheduling and batching improvements;
- queue/backpressure tuning;
- storage/cache hygiene suggestions;
- failure pattern analysis;
- repair playbooks derived from compatible verified episodes.

Maintenance is not permission to inspect unrelated owner content.

## Action modes

- OBSERVE_ONLY
- ADVISORY_ONLY
- OWNER_APPROVED
- PREAUTHORIZED_SAFE

PREAUTHORIZED_SAFE is restricted to the explicit allowlist in the device manifest.

## Identity

A worker must use its own service/device identity. It must not impersonate DEUS, the owner, another user, another AI provider, or another device.

DEUS-originated instructions may be signed or referenced as instructions from DEUS, but the actual actor identity must remain truthful in logs and external services.

## Return packet

A completed job should return:

- taskId
- relayId
- status
- outputRef or digest
- startedAt / completedAt
- resourceUseSummary
- maintenanceSignalsObserved
- ownerImpact
- errors/unknowns
- provenanceRef

No raw credential values are permitted in return packets.
