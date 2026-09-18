# DEUS Mobile Node — iPhone13,1

Target: owner-authorized iPhone 12 mini (`iPhone13,1`).

This package is the on-device telemetry, bounded-compute and OS-scheduled maintenance layer for the DEUS mobile Home Edge. It deliberately stays inside supported iOS application boundaries and follows an **offload-first** policy: the phone should stay responsive and cool while heavier work is routed elsewhere when an authorized route exists.

## What it measures

- hardware model identifier
- processor count and active processor count visible through `ProcessInfo`
- physical memory reported by `ProcessInfo`
- iOS thermal state
- Low Power Mode
- battery level/state in the foreground app
- bounded own-process SHA-256 compute canary
- JSON receipt for foreground canary runs
- JSON receipt for OS-granted background maintenance runs

## Foreground scheduler policy

The percentage is a cooperative app duty-cycle budget, not a hard CPU reservation:

- nominal, unplugged: 1.0%
- nominal, charging/full: 2.0%
- fair thermal: 0.5% or lower in Low Power Mode
- serious thermal: 0.25%
- critical thermal: 0%

The policy is intentionally conservative for the iPhone 12 mini thermal envelope. Any future local inference adapter must pass through the same thermal/battery gate.

## Background maintenance v0.2

The app registers `io.blinfinity.deus.mobile.maintenance` as a `BGProcessingTask`.

Policy:

- request only OS-scheduled processing;
- require external power;
- do not require network;
- run only a tiny own-process canary when thermal state is nominal/fair;
- yield with zero compute under Low Power Mode or serious/critical/unknown thermal pressure;
- write `DEUS_MOBILE_BACKGROUND_RECEIPT/v0.2` into the app's own Documents container;
- reschedule opportunistically after a granted run;
- never interpret scheduling as a persistent daemon or guaranteed cadence.

iOS decides whether and when the background task runs. This package does not bypass that scheduler.

## Offload-first optimization

The mobile node is a lightweight terminal/sensor/cache/receipt producer first. Heavy compute, large model inference, bulk search and long-running jobs should prefer an authorized remote/private/federated route when one is available and economically useful. Local compute remains bounded and thermal-aware.

## Kernel gate

Current source does **not** claim a verified root/jailbreak/kernel-control path for this target. Device ownership grants authority over the owner's device, but it does not create a technical kernel primitive. Kernel-level integration remains `HOLD` until an exact target/iOS path is source-verified, safety-reviewed and actually executed with a rollback/receipt path.

## Truth boundary

This code does **not** claim jailbreak, root, kernel access, raw GPU/ANE counters, other-process control, arbitrary filesystem access, or persistent background execution. A signed install plus an attributable on-device receipt is required before the registry may promote this node to `LOCAL_EXECUTOR_VERIFIED`.

## Build

Repository CI generates the Xcode project with XcodeGen and performs an unsigned iOS Simulator build. For a physical owner device, open the generated project in Xcode, select the owner's Apple development team, select the connected iPhone, and run.

## Local LLM status

No local LLM is bundled. A future compact Core ML adapter remains eligible only after a model artifact, model hash, rights/provenance, task-fit benchmark, thermal/battery policy and on-device inference receipt exist.
