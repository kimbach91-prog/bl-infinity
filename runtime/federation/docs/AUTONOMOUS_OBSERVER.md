# Bounded canonical observer

The canonical observer is the first unattended LiveBus loop. It watches the canonical boot capsule and its exact primary job, then appends one deduplicated state checkpoint only when the canonical fingerprint changes.

It does **not** execute the job, register providers, spend money, accept terms, change IAM, use arbitrary shell commands, or copy the job objective/next action into machine receipts.

## Enable

The Google service-account credential and `DEUS_LIVEBUS_SPREADSHEET_ID` must already be configured for the Drive machine bridge.

```bash
DEUS_AUTONOMOUS_OBSERVER_ENABLED=true
DEUS_AUTONOMOUS_OBSERVER_JOB_SCAN_ROWS=250
DEUS_AUTONOMOUS_OBSERVER_CHECKPOINT_SCAN_ROWS=500
```

The two row limits are explicit safety bounds. If the primary job is outside the configured range, a required header changes, the primary job is duplicated, or the checkpoint scan fills, the observer fails closed and `/readyz` reports not ready.

## Canonical writes

The worker only appends to `53_FLOW_CHECKPOINTS!A:L` under:

```text
FLOW_ID = DEUS-MACHINE-CONTINUITY
NODE_ID = PRIMARY-JOB-STATE
```

Every new row is read back exactly before the runtime reports `CHECKPOINT_APPENDED`. An unchanged fingerprint returns `UNCHANGED` and performs no checkpoint write. The pre-existing machine-bridge heartbeat remains separate in `54_MACHINE_BRIDGE_HEALTH`.

The fingerprint is semantic: boot/job timestamps, lease owner, lease expiry and lease heartbeat are deliberately excluded. Lease renewal without a state, phase, receipt, result, context or canonical invalidation change therefore does not create checkpoint noise.

## Truth boundary

`CHECKPOINT_APPENDED` proves that this machine identity read the bounded canonical ranges and appended/read back one state checkpoint. It does not prove that the primary job was executed, that a provider granted compute, or that any external action succeeded.
