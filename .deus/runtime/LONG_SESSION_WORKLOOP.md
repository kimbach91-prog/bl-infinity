# DEUS Long-Session Workloop

## Goal
Maximize useful completed work per live session while minimizing context loss, retry pressure, duplicate work, and dependence on frequent scheduled wakes.

This is a continuity architecture, not a claim that one model invocation can run unattended for days. When the hosting product pauses or ends execution, the next invocation must resume from durable checkpoints.

## Core invariants
1. **Useful-work longevity > peak request rate.** Prefer a stable lane that can continue for a long horizon over short bursts.
2. **Checkpoint continuously.** Durable state must be sufficient to resume without reconstructing completed work from chat history.
3. **Delta-first cognition.** Reuse mastered regions; spend reasoning on new/changed surfaces.
4. **Bound context growth.** Maintain a compact working set plus durable evidence pointers. Do not keep replaying full historical context.
5. **Single next executable step.** At every checkpoint store exactly what can be executed next, its inputs, completion gate, blocker and rollback.
6. **No duplicate retries.** A failed operation must carry an idempotency key or evidence that prevents blind replay.
7. **Graceful degradation.** On throttling, tool outage or quota pressure: persist state, reduce pressure, and resume later from the checkpoint.
8. **Independent evidence.** Self-reported completion is candidate evidence until verified where verification is required.

## Working-state contract
Each long workloop checkpoint should record:
- `objective`
- `current_phase`
- `completed_units[]`
- `pending_units[]`
- `next_executable_step`
- `source_pins` / hashes / ids
- `evidence_refs[]`
- `open_questions[]`
- `blockers[]`
- `retry_state`
- `context_digest`
- `rollback_point`
- `completion_gates[]`

## Context discipline
Use three layers:
- **Hot context:** only what the current action needs.
- **Warm digest:** compact state of the current phase and decisions.
- **Cold durable state:** full evidence, manifests, source pins and historical artifacts in the canonical store.

Before the hot context becomes large, write/update the warm digest and drop already-verified details from active reasoning. Reload them only by reference if needed.

## Wake strategy
Prefer one long-lived foreground workloop while the host is actively granting execution. Schedules/automations are fallback wake mechanisms for:
- external conditions,
- long cooldowns,
- fixed-time obligations,
- host/session termination.

Do not create periodic wakes merely to redo work already covered by a live workloop.

## Session-end handoff
Before any expected stop or after a partial failure, emit a handoff packet containing:
- exact checkpoint id,
- last verified action,
- next executable action,
- required tool/resource ids,
- unresolved blockers,
- compact context digest,
- expected completion gate.

A new session must be able to continue from this packet without requiring the user to restate the project.

## Reality boundary
The hosting product controls how long an invocation/session remains executable. DEUS can optimize continuity and resumability, but cannot guarantee an uninterrupted multi-day model invocation. The architectural target is therefore **multi-day task continuity**, even across execution pauses, not pretending that compute continues when the host is not running the model.
