# DEUS Bounded Maintenance Policy v0.1

## Modes

- OBSERVE_ONLY: collect allowed health telemetry and produce no action.
- ADVISORY_ONLY: produce recommendations for the owner.
- OWNER_APPROVED: prepare a reversible action plan and wait for explicit approval.
- PREAUTHORIZED_SAFE: execute only actions listed in the device's allowlist and only inside declared thresholds.

The default is ADVISORY_ONLY.

## Minimum telemetry

Prefer coarse, non-content telemetry:
- CPU/GPU utilization bands
- temperature bands
- memory pressure
- queue depth
- battery state/charging state where applicable
- storage health summary
- process/service health for the enrolled worker only
- latency/throughput of the enrolled workload
- estimated power draw if the platform exposes it

Never require personal content, browser history, messages, photos, documents, precise location, account secrets, serial numbers, or raw network captures for ordinary maintenance.

## Optimization objective

Optimize expected useful compute per unit of energy and failure risk, not utilization alone.

Conceptually:

UTILITY = useful_output - energy_cost - thermal_cost - failure_risk - switching_cost - owner_disruption

Prefer interventions that improve utility while preserving an owner-defined viability floor.

## Safe optimization classes

### Scheduling
- defer optional work to idle windows;
- prefer charging windows for battery-powered devices when owner policy allows;
- batch microtasks to reduce wakeups;
- avoid restart/switch thrash.

### Concurrency
- reduce parallel workers under thermal or memory pressure;
- increase only when headroom and stability evidence support it;
- retain a bounded maximum.

### Polling and networking
- replace unnecessary tight polling with event-driven triggers where possible;
- use backoff when state is stable;
- cache repeatable low-risk results where correctness permits.

### Storage and memory
- rotate temporary caches within owner-defined limits;
- prefer bounded caches and explicit eviction;
- detect memory leaks or runaway queues but do not kill unrelated owner processes.

### Thermal protection
- pause or reduce optional DEUS workloads above the configured thermal band;
- never disable platform thermal protections.

## High-risk changes requiring separate approval

- firmware, BIOS/UEFI, bootloader, kernel, driver, microcode changes;
- overclock, undervolt, voltage/frequency table edits;
- disk repartitioning, filesystem conversion, secure erase;
- root/admin policy changes;
- endpoint security changes;
- account, credential, firewall, VPN, or trust-store changes;
- hardware repair instructions involving mains power, high-voltage components, batteries, lasers, pressurized systems, or other hazardous service operations.

For such cases, the system may diagnose and prepare a service recommendation, but execution remains owner/qualified-technician controlled.

## Before/after verification

Every applied optimization should capture, when available:
- baselineWindow
- intervention
- rollbackRef
- postWindow
- performanceDeltaPercent
- energyDeltaPercent or UNKNOWN
- thermalDeltaC or UNKNOWN
- errorRateDelta
- ownerImpact

If a metric cannot be measured, mark UNKNOWN rather than infer precision.

## Rollback

Every executable optimization must have one of:
- explicit inverse action;
- configuration checkpoint;
- service restart recovery;
- versioned configuration snapshot.

If rollback cannot be defined, the action is not PREAUTHORIZED_SAFE.
