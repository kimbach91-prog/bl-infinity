# DEUS Session Lifetime Policy

## Objective
Keep a useful task session alive as long as it continues to make verified progress. Session age by itself is not a reason to terminate work.

## Core invariant
`CONTINUE_WHILE_USEFUL_AND_HEALTHY`

A session earns longevity from successful useful work, not from request volume or wall-clock time.

## Separation of concerns
- **Load governor** controls request pacing, concurrency, retries and provider cooldown.
- **Session lifetime governor** controls whether the logical task should remain active, checkpoint/yield, or terminate.
- **Scheduler/watchdog** is a recovery/wake mechanism only. It is not the primary heartbeat of a healthy active task.

## Positive signals
- Verified task progress / completed milestones.
- New useful delta or capability acquisition.
- Evidence quality remains stable or improves.
- Low error and rollback rate.
- Remaining executable work exists.
- Checkpoints remain recoverable.

## Negative signals
- Repeated no-op cycles or semantic loops.
- Consecutive failures beyond the configured error budget.
- Evidence regression or unresolved integrity failure.
- Provider/resource hard stop.
- No executable next step.

## Lifetime rule
There is no default maximum session age. A session may run for hours or days in an external persistent runtime when positive signals remain strong and negative signals remain below gates.

When context or process lifetime becomes constrained, checkpoint durable state and resume the same logical session from the checkpoint rather than resetting the task to zero.

## Chat/runtime boundary
A ChatGPT response cannot autonomously keep computing after it has returned without another trigger. Multi-day continuous execution therefore belongs in a persistent external worker/runtime. ChatGPT/other LLMs are replaceable reasoning workers attached to that durable task state.

## Schedule role
Schedules are used only for:
1. dead-session detection,
2. recovery/restart after provider/process loss,
3. periodic integrity/checkpoint audit when event-driven triggers are unavailable.

A live healthy session should not wait for a schedule tick to continue.
