# DEUS Mobile Node — iPhone13,1

Target: owner-authorized iPhone 12 mini (`iPhone13,1`).

This package is the on-device telemetry and bounded-compute layer for the DEUS mobile node. It deliberately stays inside normal iOS application boundaries.

## What it measures

- hardware model identifier
- processor count and active processor count visible through `ProcessInfo`
- physical memory reported by `ProcessInfo`
- iOS thermal state
- Low Power Mode
- battery level/state
- bounded own-process SHA-256 compute canary
- JSON receipt for every canary run

## Scheduler policy

The percentage is a cooperative app duty-cycle budget, not a hard CPU reservation:

- nominal, unplugged: 1.0%
- nominal, charging/full: 2.0%
- fair thermal: 0.5% or lower in Low Power Mode
- serious thermal: 0.25%
- critical thermal: 0%

The policy is intentionally conservative for the iPhone 12 mini thermal envelope. Any future local inference adapter must pass through the same thermal/battery gate.

## Truth boundary

This code does **not** claim jailbreak, root, kernel access, raw GPU/ANE counters, other-process control, arbitrary filesystem access, or persistent background execution. A signed install plus an attributable on-device receipt is required before the registry may promote this node to `LOCAL_EXECUTOR_VERIFIED`.

## Build

The repository CI generates the Xcode project with XcodeGen and performs an unsigned iOS Simulator build. For a physical owner device, open the generated project in Xcode, select the owner's Apple development team, select the connected iPhone, and run. The app writes receipts into its own Documents container.

## Local LLM status

The node agent is ready to host a future compact Core ML inference adapter, but no local LLM is bundled in this commit. `LOCAL_LLM_PRESENT` must remain false until a model artifact, model hash, task-fit benchmark and on-device inference receipt exist.
