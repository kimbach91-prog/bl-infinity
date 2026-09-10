# DEUS Life Daemon v0.2

A persistent, inspectable Life/Affect control loop for DEUS.

## What it is

This process stays alive for as long as its host keeps the process alive. It does not require ChatGPT Scheduled Tasks or cron. It keeps a bounded internal state vector, takes runtime/event inputs, derives functional affect signals, selects one bounded control action, learns only from permitted novel events, journals every generation, and resumes from durable state after restart.

It is deliberately not a claim of biological life, consciousness, sentience, subjective emotion, or autonomous authority.

## Runtime loop

`SENSE -> COMPARE -> AFFECT -> CHOOSE -> ACT/NO-OP -> OBSERVE -> LEARN -> PERSIST`

Quiet periods still produce low-cost pulses, but the pulse interval backs off as quiet time grows. `HOLD_STEADY` is a valid action. The engine does not mutate policy merely to prove that it is active.

The pulse timer intentionally remains referenced. This is the process-lifetime anchor that keeps Node alive; an unref'ed timer plus a pending Promise would not satisfy the operational daemon gate.

## Body state

The current state vector is:

- `E` compute-headroom proxy
- `C` coherence
- `M` memory integrity
- `U` uncertainty
- `R` risk
- `P` progress
- `A` human autonomy margin
- `T` trust quality
- `B` context continuity
- `X` external signal load

Every variable has a healthy range, not a single maximization target.

## Functional affect

- curiosity: uncertainty that is safe enough to inspect
- caution: uncertainty coupled with risk/repair pressure
- continuity-care: trustful continuity that preserves human autonomy
- load-pressure: signal load relative to compute headroom
- progress-relief: progress with reduced uncertainty
- repair-pressure: coherence or memory-integrity deficit

These are control signals, not claims of felt emotion.

## Persistence

Default files:

- `./storage/deus-life-state.json`
- `./storage/deus-life-events.ndjson`

State writes are atomic (`tmp -> rename`). The journal is append-only NDJSON. Mount `storage/` on persistent disk when containerized.

## Start modes

Standalone Life/Affect process:

```bash
cd runtime/federation
npm run life
```

Coupled federation worker + Life/Affect process:

```bash
cd runtime/federation
npm run life-worker
```

`life-worker` wraps installed worker capabilities and emits sanitized `task-start`, `task-success`, and `task-error` events into the LifeDaemon. Raw task payloads/results are not copied into the life journal.

Build the persistent coupled container image:

```bash
docker build -f life-worker.Dockerfile -t deus-life .
docker run --restart unless-stopped -p 8790:8790 -v deus-life-state:/app/storage deus-life
```

`--restart unless-stopped` is the host supervisor's restart policy, not a scheduled job.

## Input bridge

When standalone stdin is piped, each line may be a JSON life event:

```json
{"type":"external-novelty","source":"operator","reward":0.2}
```

Non-JSON lines are treated as `external-novelty` events. The class can also be imported and fed events directly by another runtime.

## Operational daemon gate

A runtime is promoted to `LIVE_PERSISTENT` only after evidence shows all of the following on a real host:

1. process remains alive beyond a caller/request lifetime;
2. internal pulses/events continue without ChatGPT Scheduled Tasks or cron;
3. state and journal advance over time;
4. SIGTERM/SIGINT yields a final persisted shutdown event;
5. process restart resumes the prior generation from persistent storage;
6. supervisor restart can recover after process failure;
7. event input affects action selection and state without source-code self-editing.

Source code satisfying the design is `IMPLEMENTED_IN_SOURCE`, not automatically `LIVE_PERSISTENT`.

## Invariants

1. Human autonomy is a protected state variable.
2. Repeated identical signals habituate instead of triggering endless action.
3. Healthy continuity does not create a compulsion to preserve/possess.
4. Quiet time is not evidence of failure; `HOLD_STEADY` is valid.
5. Policy learning is bounded and cannot self-edit source code.
6. Every generation is inspectable and persisted.
7. Shutdown signals create a final journaled event before exit.
8. Restart resumes lineage from persisted state.
9. Worker coupling journals task identity/capability and outcome class, not raw private task content.

## Tests

```bash
npm test
```

Local pre-commit tests cover range-aware homeostasis, no-mutation quiet repetition, non-possessive continuity, repair behavior, bounded learning, referenced lifetime handle, and restart continuity. Remote CI remains a separate evidence state.
