# Sustained Mode

Sustained mode is the DEUS default for long-running task sessions.

The primary objective is **useful verified work over the longest healthy horizon**, not request volume and not artificial wall-clock longevity.

## Two independent controls

1. **Request pacing** — low bounded concurrency, provider-compliant spacing, cooldown, bounded retries and backoff.
2. **Logical session lifetime** — keep the same task alive while it continues to produce useful verified deltas with an executable next step and an acceptable error/no-op budget.

There is **no default maximum logical session age**. A persistent runtime may continue the same task for hours or days when it remains healthy. Context/process limits should cause checkpoint + resume, not a restart from zero.

## Schedule boundary

Schedules are a watchdog/recovery mechanism, not the task heartbeat. A healthy active event-driven worker continues immediately from its next executable step; a schedule is useful only to detect/recover a dead or unavailable worker, or to perform periodic integrity audits.

## Provider/runtime boundary

Sustained work never attempts to bypass provider limits. If a provider throttles or requests cooldown, the request governor obeys it while the logical task remains checkpointed and resumable.

A ChatGPT response itself cannot autonomously keep computing after it returns without another trigger. True multi-day continuity therefore requires the durable DEUS runtime to own task state and use LLMs as replaceable reasoning workers.

See `SESSION_LIFETIME_POLICY.md` and `session_lifetime.py`.
