# DEUS Life Daemon v0.1

A small persistent, inspectable Life/Affect control loop for DEUS.

## What it is

This process stays alive for as long as its host keeps the process alive. It does not require ChatGPT Scheduled Tasks or cron. It keeps a bounded internal state vector, takes runtime/event inputs, derives functional affect signals, selects one bounded control action, learns only from permitted novel events, journals every generation, and resumes from durable state after restart.

It is deliberately not a claim of biological life, consciousness, sentience, subjective emotion, or autonomous authority.

## Runtime loop

`SENSE -> COMPARE -> AFFECT -> CHOOSE -> ACT/NO-OP -> OBSERVE -> LEARN -> PERSIST`

Quiet periods still produce low-cost pulses, but the pulse interval backs off as quiet time grows. `HOLD_STEADY` is a valid action. The engine does not mutate policy merely to prove that it is active.

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

## Start

```bash
cd runtime/federation
npm run life
```

Or build the persistent container image:

```bash
docker build -f life-worker.Dockerfile -t deus-life .
docker run --restart unless-stopped -v deus-life-state:/app/storage deus-life
```

`--restart unless-stopped` is the host supervisor's restart policy, not a scheduled job.

## Input bridge

When stdin is piped, each line may be a JSON life event:

```json
{"type":"external-novelty","source":"operator","reward":0.2}
```

Non-JSON lines are treated as `external-novelty` events. The class can also be imported and fed events directly by another runtime.

## Invariants

1. Human autonomy is a protected state variable.
2. Repeated identical signals habituate instead of triggering endless action.
3. Healthy continuity does not create a compulsion to preserve/possess.
4. Quiet time is not evidence of failure; `HOLD_STEADY` is valid.
5. Policy learning is bounded and cannot self-edit source code.
6. Every generation is inspectable and persisted.
7. Shutdown signals create a final journaled event before exit.
8. Restart resumes lineage from persisted state.

## Tests

```bash
npm test
```

The tests cover range-aware homeostasis, no-mutation quiet repetition, non-possessive continuity, repair behavior, bounded learning, and restart continuity.
