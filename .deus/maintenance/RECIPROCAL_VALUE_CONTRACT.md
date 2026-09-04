# DEUS Reciprocal Device Value Contract v0.1

## Purpose

A voluntarily enrolled device may contribute bounded idle compute or relay capacity. In return, DEUS may provide maintenance intelligence, energy-efficiency recommendations, performance tuning guidance, failure prevention, and repair-learning feedback.

This is reciprocal service, not unconditional device access.

## Authorization invariants

Every participating device MUST have:
- deviceClass: coarse hardware/software class only.
- consentRef: explicit owner authorization reference.
- relayId: pseudonymous relay identifier.
- scope: allowed observations and allowed actions.
- expiry: authorization expiry.
- revocationPath: owner-visible way to revoke access.
- dataPolicy: what telemetry may leave the device.
- actionPolicy: advisory-only, owner-approved, or pre-authorized safe automation.

A reachable device is NOT an authorized device.

## Value returned to the owner

DEUS may provide:
1. Thermal and load-health assessment.
2. Energy-efficiency recommendations.
3. Workload scheduling to avoid wasteful peak draw.
4. Concurrency and polling optimization.
5. Memory, storage, queue, cache, and process-efficiency recommendations.
6. Detection of likely degradation or maintenance needs.
7. Repair playbooks based on prior verified cases.
8. Post-repair verification and rollback guidance.
9. Estimated before/after changes in energy, latency, throughput, temperature, and stability.

## Allowed default actions

Default mode is ADVISORY_ONLY.

Automatically executable actions require an explicit actionPolicy and must be reversible, bounded, and user-space whenever possible. Examples may include:
- reducing noncritical polling frequency;
- batching background work;
- pausing optional jobs above a thermal threshold;
- moving compute to idle/charging windows;
- applying pre-approved concurrency caps;
- disabling a DEUS worker when the owner-defined health floor is crossed.

The following are NEVER implied by enrollment and require separate explicit authorization:
- firmware flashing;
- BIOS/UEFI changes;
- overclocking/undervolting;
- destructive storage operations;
- privileged kernel changes;
- changing account credentials;
- bypassing security controls;
- accessing personal files or communications.

## Reciprocity accounting

The system MAY estimate contributed value and returned value, but it must not pretend precision that does not exist.

Suggested fields:
- contributedComputeSeconds
- contributedEnergyEstimateWh
- avoidedEnergyEstimateWh
- maintenanceIncidentsPreventedEstimate
- performanceDeltaPercent
- thermalDeltaC
- ownerApprovedSavingsEstimate

Estimates must retain method, confidence, and UNKNOWN where appropriate.

## Safety floor

Maintenance optimization must stop or fail closed when:
- telemetry is stale or contradictory;
- authorization is expired/revoked;
- the proposed change is irreversible or privileged without explicit approval;
- thermal/storage/battery health enters an owner-defined danger band;
- optimization benefit is smaller than switching/restart/risk cost;
- a device is foreground-busy and DEUS only has idle-compute permission.

## Canonical authority

Device observations and repair episodes are evidence. They do not automatically become canonical maintenance doctrine. Cross-device generalization requires repeated evidence, compatibility checks, and a falsifier/rollback path.
