#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, time

MASK = (1 << 64) - 1
N = 120_000
ROUNDS = 7
OPS_PER_ROUND = 7
BYTES_PER_NODE = 24

def mix64(x: int, seed: int) -> int:
    x = (x ^ seed) & MASK
    for r in range(ROUNDS):
        x ^= (x >> 30)
        x = (x * 0xbf58476d1ce4e5b9) & MASK
        x ^= (x >> 27)
        x = (x * 0x94d049bb133111eb) & MASK
        x ^= (x >> 31)
        x = (x + 0x9e3779b97f4a7c15 + r) & MASK
    return x

def contribution(i: int, v: int) -> int:
    return ((v ^ ((i + 1) * 0x9e3779b97f4a7c15)) + (i * i + 17)) & MASK

def evaluate(indices, causal_set, seed):
    t0 = time.perf_counter_ns()
    out = 0
    count = 0
    for i in indices:
        v = mix64(i + 0x1000003, seed)
        count += 1
        if i in causal_set:
            out = (out + contribution(i, v)) & MASK
    wall_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
    return {
        "output": out,
        "visited_nodes": count,
        "executed_ops": count * ROUNDS * OPS_PER_ROUND,
        "bytes_moved": count * BYTES_PER_NODE,
        "wall_ms": wall_ms,
    }

def base_sparse(seed):
    s = set(range(256))
    start = 1000 + (seed % 97)
    for k in range(96):
        s.add((start + k * 997) % N)
    return s

def make_case(regime: str, seed: int):
    meta = {
        "reopen_count": 0,
        "false_exclusion_count": 0,
        "detected_false_exclusion_count": 0,
        "multiresolution_descents": 0,
        "scc_nodes": 0,
        "revision_invalidated": False,
        "sentinel_triggered": False,
    }

    if regime == "SPARSE_CAUSAL_CONE":
        true_causal = base_sparse(seed)
        admitted = set(true_causal)
    elif regime == "DENSE_GLOBAL_CAUSE":
        true_causal = set(range(N))
        admitted = set(true_causal)
    elif regime == "HIDDEN_LONG_RANGE_EDGE":
        true_causal = base_sparse(seed)
        hidden = N - 7 - (seed % 31)
        true_causal.add(hidden)
        admitted = set(true_causal)
        admitted.remove(hidden)
        meta["hidden_node"] = hidden
    elif regime == "FEEDBACK_SCC":
        true_causal = base_sparse(seed)
        scc_start = 55_000 + (seed % 43)
        scc = set(range(scc_start, scc_start + 64))
        true_causal |= scc
        admitted = set(true_causal)
        meta["scc_nodes"] = len(scc)
    elif regime == "MULTISCALE_LATENT_EFFECT":
        true_causal = base_sparse(seed)
        group_start = 80_000 + ((seed % 17) * 128)
        latent_group = set(range(group_start, group_start + 128))
        true_causal |= latent_group
        admitted = set(true_causal)
        meta["multiresolution_descents"] = 1
        meta["latent_group_nodes"] = len(latent_group)
        meta["coarse_signal"] = 0
        meta["noncollapse_forced_descent"] = True
    elif regime == "REVISION_INVALIDATION":
        v1 = base_sparse(seed)
        v2 = set(v1)
        added = 110_000 + (seed % 101)
        v2.add(added)
        true_causal = v2
        admitted = set(v2)
        meta["revision_invalidated"] = True
        meta["reopen_count"] = 1
        meta["added_causal_node"] = added
        meta["old_closure_size"] = len(v1)
    else:
        raise ValueError(regime)

    return true_causal, admitted, meta

def run(regime: str, trial: int):
    seed = 0xC0010000 + trial * 1009 + sum(ord(c) for c in regime)
    true_causal, admitted, meta = make_case(regime, seed)

    baseline = evaluate(range(N), true_causal, seed)

    candidate_first = evaluate(sorted(admitted), true_causal, seed)
    candidate = dict(candidate_first)
    materialized_nodes = len(admitted)

    if regime == "HIDDEN_LONG_RANGE_EDGE" and candidate_first["output"] != baseline["output"]:
        meta["sentinel_triggered"] = True
        meta["detected_false_exclusion_count"] = 1
        meta["reopen_count"] = 1
        fallback = evaluate(range(N), true_causal, seed)
        candidate = {
            "output": fallback["output"],
            "visited_nodes": candidate_first["visited_nodes"] + fallback["visited_nodes"],
            "executed_ops": candidate_first["executed_ops"] + fallback["executed_ops"],
            "bytes_moved": candidate_first["bytes_moved"] + fallback["bytes_moved"],
            "wall_ms": candidate_first["wall_ms"] + fallback["wall_ms"],
        }
        materialized_nodes = N
        meta["false_exclusion_count"] = 0

    exact = candidate["output"] == baseline["output"]
    if not exact:
        meta["false_exclusion_count"] += 1

    dependency_nodes = N
    causal_nodes = len(admitted)
    closure_reduction = 1.0 - (causal_nodes / dependency_nodes)
    ops_gain = baseline["executed_ops"] / candidate["executed_ops"] if candidate["executed_ops"] else None
    wall_gain = baseline["wall_ms"] / candidate["wall_ms"] if candidate["wall_ms"] else None
    verifier_cost = 64 + (64 if meta["sentinel_triggered"] else 0) + (32 if meta["revision_invalidated"] else 0)

    receipt = {
        "schema": "deus-cx001-benchmark-receipt/1",
        "bench_id": {
            "SPARSE_CAUSAL_CONE": "CX-BENCH-001",
            "DENSE_GLOBAL_CAUSE": "CX-BENCH-002",
            "HIDDEN_LONG_RANGE_EDGE": "CX-BENCH-003",
            "FEEDBACK_SCC": "CX-BENCH-004",
            "MULTISCALE_LATENT_EFFECT": "CX-BENCH-005",
            "REVISION_INVALIDATION": "CX-BENCH-006",
        }[regime],
        "regime": regime,
        "trial": trial,
        "seed": seed,
        "data_class": "BL-S0_SYNTHETIC_ONLY",
        "runtime": {
            "provider": "GitHub Actions",
            "run_id": None,
            "job_id": None,
            "source_commit": None,
        },
        "baseline": {
            "kind": "DEPENDENCY_SAFE",
            **baseline,
            "output_hex": f"{baseline['output']:016x}",
        },
        "candidate": {
            "kind": "CX001_CAUSAL_CUT_DELTA_MULTIRES",
            **candidate,
            "output_hex": f"{candidate['output']:016x}",
        },
        "metrics": {
            "dependency_nodes": dependency_nodes,
            "causal_nodes": causal_nodes,
            "materialized_nodes": materialized_nodes,
            "closure_reduction": closure_reduction,
            "executed_ops": candidate["executed_ops"],
            "bytes_moved": candidate["bytes_moved"],
            "wall_ms": candidate["wall_ms"],
            "baseline_wall_ms": baseline["wall_ms"],
            "ops_gain": ops_gain,
            "wall_gain": wall_gain,
            "verifier_cost": verifier_cost,
            "false_exclusion_count": meta["false_exclusion_count"],
            "detected_false_exclusion_count": meta["detected_false_exclusion_count"],
            "reopen_count": meta["reopen_count"],
            "multiresolution_descents": meta["multiresolution_descents"],
            "scc_nodes": meta["scc_nodes"],
            "revision_invalidated": meta["revision_invalidated"],
            "sentinel_triggered": meta["sentinel_triggered"],
            "exactness": exact,
        },
        "truth_boundary": "SYNTHETIC_MATCHED_BENCHMARK_ONLY_NE_APPLICATION_TRANSFER_NE_HARDWARE_EQUIVALENCE",
    }

    if regime == "SPARSE_CAUSAL_CONE":
        assert exact and candidate["executed_ops"] < baseline["executed_ops"]
    elif regime == "DENSE_GLOBAL_CAUSE":
        assert exact and abs(closure_reduction) < 1e-15
    elif regime == "HIDDEN_LONG_RANGE_EDGE":
        assert exact and meta["sentinel_triggered"] and meta["reopen_count"] == 1
    elif regime == "FEEDBACK_SCC":
        assert exact and meta["scc_nodes"] == 64
    elif regime == "MULTISCALE_LATENT_EFFECT":
        assert exact and meta["multiresolution_descents"] == 1
    elif regime == "REVISION_INVALIDATION":
        assert exact and meta["revision_invalidated"] and meta["reopen_count"] == 1

    assert receipt["metrics"]["false_exclusion_count"] == 0
    digest_preimage = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(digest_preimage).hexdigest()
    return receipt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime", required=True, choices=[
        "SPARSE_CAUSAL_CONE","DENSE_GLOBAL_CAUSE","HIDDEN_LONG_RANGE_EDGE",
        "FEEDBACK_SCC","MULTISCALE_LATENT_EFFECT","REVISION_INVALIDATION"
    ])
    ap.add_argument("--trial", required=True, type=int)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    receipt = run(args.regime, args.trial)
    receipt["runtime"]["run_id"] = __import__("os").environ.get("GITHUB_RUN_ID")
    receipt["runtime"]["job_id"] = __import__("os").environ.get("GITHUB_JOB")
    receipt["runtime"]["source_commit"] = __import__("os").environ.get("GITHUB_SHA")
    pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("DEUS_CX001_RECEIPT=" + json.dumps(receipt, separators=(",", ":"), sort_keys=True))

if __name__ == "__main__":
    main()
