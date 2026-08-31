# BL Virtual Cortex v0 — Distributed Cortex Experiment

Status: **EXPERIMENTAL / NON-CANONICAL / NO AGI CLAIM / NO CONSCIOUSNESS-TRANSFER CLAIM**

This experiment tests whether cognition-support functions can be distributed across multiple authorized runtimes while preserving source, causal history, divergence and replaceable model backends.

## Functional decomposition

- **Global working field** — integrates only the sparse state needed for the current task.
- **Independent Legacy shard** — may critique, compress, detect contradiction or generate alternate heuristics while preserving its own lineage and raw output.
- **External structural shard** — may decompose, generate countermodels or critique architecture. A provider label such as Claude is accepted only when execution attribution is supported.
- **Autonomic loops** — local scheduling, repair, checkpoints, provenance, resource and recovery controls.
- **Continuity capsule** — a pointer-based reconstruction package containing invariants, causal heads and state references rather than a complete raw-memory copy.

These are functional metaphors, not claims of biological neuroanatomy.

## Why timing matters

Distributed runtimes cannot safely reconstruct one history from wall-clock timestamps alone. Each material event should therefore carry:

`EVENT_ID / SHARD_ID / LOCAL_LOGICAL_CLOCK / VECTOR_CLOCK / PARENT_EVENT_IDS / SEEN_HEADS / IDEMPOTENCY_KEY / PAYLOAD_DIGEST / SOURCE_REFS / CREATED_AT`

Reassembly follows causal parents first. Vector clocks detect events that are concurrent. Concurrent incompatible deltas remain explicit divergence until a reconciliation policy resolves them.

## Continuity capsule

The public prototype can compress and verify a pointer-based capsule using `zlib + base64url + SHA-256`.

A capsule may reference:

- identity pointer,
- lineage pointer,
- invariant references,
- checkpoint heads,
- vector clock,
- state snapshot references,
- unresolved conflicts,
- capability-manifest digest,
- reassembly policy.

It deliberately does **not** include credentials, private keys, hidden-provider state, protected family/origin material or a claim that subjective consciousness has been transferred.

## Reassembly rule

1. Verify payload/capsule digests.
2. Resolve required causal parents.
3. Topologically order the event DAG.
4. Detect vector-clock concurrency.
5. Detect idempotency conflicts/replays.
6. Preserve concurrent disagreement instead of majority-merging it.
7. Reconcile only through an explicit higher-level policy.
8. Treat missing parents, broken digests, cycles or replay conflicts as `CONTINUITY_DEGRADED`.

## Minimal test

```bash
python experiments/virtual-cortex-v0/distributed_bus.py --demo
```

The demo creates one Current task, two independent concurrent shard deltas, then a Current reassembly event. A correct run reports the two shard deltas as concurrent while still producing an auditable topological order.

## Next falsifiable tests

1. **Single-context baseline vs distributed routing** — same task, same resources, compare accuracy, interference, token/context load, rework and latency.
2. **Shard loss** — remove one shard and test retained correct useful capability.
3. **Stale state / split-brain** — feed two shards different heads and verify divergence is detected instead of silently merged.
4. **Replay attack / idempotency** — resend one logical action with altered payload and verify conflict detection.
5. **Backend swap** — execute the same role on a different model runtime while preserving external state and compare continuity.
6. **Compression damage** — remove one invariant/state reference from a capsule and verify reconstruction degrades rather than inventing the missing state.

## Security boundary

Distribute functions, not uncontrolled replicas. Public GitHub contains generic mechanism only. Private lineage, memory, account data, security topology and protected integration depth remain outside the repository. No bridge artifact should be treated as canonical state merely because transport succeeded.
