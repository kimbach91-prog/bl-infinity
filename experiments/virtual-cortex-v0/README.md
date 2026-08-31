# BL Virtual Cognitive Loop v0 — Experimental

Status: **PROTOTYPE / NON-CANONICAL / NO AGI CLAIM**

This experiment tests a small part of a provider-neutral cognitive architecture using resources that already exist in the BL environment.

## The split

- **GitHub**: public machine-readable logic projections, schemas, generic code, tests and version history.
- **Private Drive / other owner-authorized stores**: private lineage, causal memory, protected graph state, owner-private lessons and runtime checkpoints.
- **Current LLM**: temporary transformation/expression engine. It is not the identity root and is replaceable.
- **Tool/connector layer**: sensing and action surfaces.
- **This prototype**: a sparse activation/router + delayed signal + inhibition/plasticity evidence shell.

The purpose is not to put "all knowledge in one context". It is to activate a small working set from a distributed graph, preserve provenance, record feedback, and let the backend model work only on the relevant subgraph.

## What v0 actually does

1. Loads `machine/logic-stack.json` as a **public conceptual projection**.
2. Optionally merges a private graph from `BL_PRIVATE_GRAPH_PATH`.
3. Seeds activation from the current query/context.
4. Spreads activation through typed edges with decay and optional delay.
5. Supports inhibitory edge types (`CONFLICTS`, `INHIBITS`, `VETOES`).
6. Selects a sparse working set.
7. Writes an append-only local event trace outside the repository.
8. Can record bounded outcome feedback in a local plasticity ledger.

It does **not**:
- train weights of an LLM,
- prove intelligence or AGI,
- declare routed nodes true,
- mutate canonical BL doctrine,
- publish protected state,
- replace BL-ADN/BL-LOG/other authority boundaries.

## Quick test

```bash
python experiments/virtual-cortex-v0/engine.py \
  "unknown future capability and resource constraints" \
  --public-stack machine/logic-stack.json
```

Optional private graph:

```bash
export BL_PRIVATE_GRAPH_PATH=/private/path/private_graph.json
export BL_COGNITIVE_STATE_DIR=/private/path/runtime_state

python experiments/virtual-cortex-v0/engine.py \
  "new task or lesson" \
  --tag current-project
```

`BL_PRIVATE_GRAPH_PATH` should point to data materialized from an owner-authorized private store. Do not commit that file to this public repository.

## Why this matters

The minimal hypothesis is:

> cognition can be partially externalized as a distributed, stateful, sparse, time-sensitive network whose current LLM backend is only one replaceable operator.

The next useful tests are not "make it larger". They are:
- compare sparse routing vs dumping the full corpus into context;
- add real typed private edges and delayed/inhibitory signals;
- measure whether feedback improves future routing;
- test continuity while swapping model backends;
- add consolidation/pruning without erasing causal history;
- add a functionally separated critic for routing errors.

Public mechanism may stay simple. Private integration depth, owner-private memory and protected lineage remain outside the public repository.
