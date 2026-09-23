#!/usr/bin/env python3
"""R277: forensic diagnostic for the single R276 m0r0 frozen-gate mismatch.

This does not repair or promote a solver. It freezes the R276 representation and
p0-p9 fit, then inspects the exact p10-p19 mismatch to identify the discriminating
mechanism class for a later source-free representation change.

Truth boundary: PUBLIC_OFFLINE reused public-development only. The p10-p19 error
may inform a future hypothesis, so no result from this diagnostic is independent
hidden generalization or Kaggle evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274
import public_action_canonical_topology_diag_275 as r275

RUNG = 277
GAME = "m0r0-492f87ba"
MODE = "canon_nodes_ui"


def canon_desc(board: list[list[int]], action: str):
    b = r275.canon_board(board, action, use_ui_mask=True)
    return r274.desc(b, "nodes_coarse")


def node_counter(desc: Any) -> Counter:
    if not desc or desc[0] != "nodes":
        return Counter()
    return Counter(tuple(x) for x in desc[1])


def serial_nodes(counter: Counter) -> list[list[Any]]:
    out: list[list[Any]] = []
    for node, n in sorted(counter.items()):
        for _ in range(n):
            out.append(list(node))
    return out


def annotated_rows(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        prev_action = None
        for i, r in enumerate(r268.rows([p])):
            rr = dict(r)
            rr["trace_row"] = i
            rr["prev_action"] = prev_action
            rr["pnum"] = r246.pnum(p)
            out.append(rr)
            prev_action = r["action"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    ps = sorted(a.input, key=r246.pnum)
    if not ps or any(r246.game_id(p) != GAME for p in ps):
        raise SystemExit(f"exact {GAME} traces required")
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise SystemExit(f"exact p0-p19 required, got {nums}")

    train = annotated_rows(ps[:10])
    hold = annotated_rows(ps[10:])

    obs: dict[Any, Counter] = defaultdict(Counter)
    meta: dict[Any, dict[str, Any]] = defaultdict(lambda: {
        "raw_before": set(),
        "traces": set(),
        "prev_actions": set(),
        "examples": [],
    })
    representative_desc: dict[tuple[Any, str], Any] = {}

    for r in train:
        k = r275.key(r["before"], r["action"], MODE)
        target = r275.key(r["after"], r["action"], MODE)[0]
        obs[k][target] += 1
        representative_desc[(k, target)] = canon_desc(r["after"], r["action"])
        m = meta[k]
        m["raw_before"].add(r["before_digest"])
        m["traces"].add(r["trace"])
        m["prev_actions"].add(r["prev_action"] if r["prev_action"] is not None else "<START>")
        if len(m["examples"]) < 8:
            m["examples"].append({
                "trace": r["trace"],
                "pnum": r["pnum"],
                "trace_row": r["trace_row"],
                "action": r["action"],
                "prev_action": r["prev_action"],
                "raw_before_digest": r["before_digest"],
                "target_key": target,
            })

    tab = {k: next(iter(v)) for k, v in obs.items() if len(v) == 1}

    stats = Counter()
    mismatches = []
    for r in hold:
        stats["transitions"] += 1
        k = r275.key(r["before"], r["action"], MODE)
        pred = tab.get(k)
        if pred is None:
            stats["abstain"] += 1
            continue
        stats["predictions"] += 1
        actual = r275.key(r["after"], r["action"], MODE)[0]
        if pred == actual:
            stats["correct"] += 1
            continue
        stats["wrong"] += 1

        pred_desc = representative_desc[(k, pred)]
        actual_desc = canon_desc(r["after"], r["action"])
        pc = node_counter(pred_desc)
        ac = node_counter(actual_desc)
        m = meta[k]
        hold_prev = r["prev_action"] if r["prev_action"] is not None else "<START>"
        temporal_novel = hold_prev not in m["prev_actions"]
        alias_collision = len(m["raw_before"]) > 1

        if alias_collision and temporal_novel:
            mechanism_class = "COARSE_STATE_ALIAS_PLUS_TEMPORAL_CONTEXT_CANDIDATE"
        elif alias_collision:
            mechanism_class = "COARSE_STATE_ALIAS_CANDIDATE"
        elif temporal_novel:
            mechanism_class = "TEMPORAL_CONTEXT_CANDIDATE"
        else:
            mechanism_class = "UNRESOLVED_NONMARKOV_OR_HIDDEN_STATE_CANDIDATE"

        mismatches.append({
            "trace": r["trace"],
            "pnum": r["pnum"],
            "trace_row": r["trace_row"],
            "action": r["action"],
            "prev_action": r["prev_action"],
            "before_raw_digest": r["before_digest"],
            "after_raw_digest": r["after_digest"],
            "canonical_before_key": {"state": k[0], "action_class": k[1]},
            "predicted_after_key": pred,
            "actual_after_key": actual,
            "train_support": int(sum(obs[k].values())),
            "train_target_count": len(obs[k]),
            "train_distinct_raw_before": len(m["raw_before"]),
            "train_traces": sorted(m["traces"]),
            "train_prev_actions": sorted(m["prev_actions"]),
            "hold_prev_action_seen_in_train_for_key": not temporal_novel,
            "coarse_state_alias_candidate": alias_collision,
            "mechanism_class": mechanism_class,
            "predicted_nodes": [list(x) if isinstance(x, tuple) else x for x in pred_desc[1]],
            "actual_nodes": [list(x) if isinstance(x, tuple) else x for x in actual_desc[1]],
            "added_nodes": serial_nodes(ac - pc),
            "removed_nodes": serial_nodes(pc - ac),
            "train_examples": m["examples"],
        })

    p = stats["predictions"]
    accuracy = round(stats["correct"] / p, 6) if p else None
    if len(mismatches) == 1:
        verdict = "SINGLE_ERROR_DIAGNOSED"
    elif not mismatches:
        verdict = "NO_ERROR_REPRODUCED"
    else:
        verdict = "MULTIPLE_ERRORS_DIAGNOSED"

    out = {
        "schema": "deus/arc3-r277-m0r0-r276-one-error-diagnostic/1",
        "rung": RUNG,
        "lineage": {
            "r276_run": 35809358813,
            "r276_head": "4d7af8f16779712fd2be462bdc751f3022a12e03",
            "r276_artifact": 10729595370,
            "representation_frozen": MODE,
        },
        "protocol": {
            "fit": "p0-p9 exact R276 deterministic table",
            "diagnostic": "p10-p19 reused public-development mismatch localization only",
            "p10_p19_updates_model": False,
            "p10_p19_updates_representation_in_this_run": False,
            "future_hypothesis_may_use_diagnostic": True,
        },
        "game": GAME,
        "stats": {**dict(stats), "accuracy": accuracy},
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "reused_public_development_holdout": True,
            "diagnostic_only": True,
            "independent_hidden_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent_by_r277": False,
            "solver_promotion": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "stats": out["stats"],
        "mismatch_count": len(mismatches),
        "mismatches": [{
            "trace": x["trace"], "pnum": x["pnum"], "trace_row": x["trace_row"],
            "action": x["action"], "prev_action": x["prev_action"],
            "train_support": x["train_support"],
            "train_distinct_raw_before": x["train_distinct_raw_before"],
            "mechanism_class": x["mechanism_class"],
            "added_nodes": x["added_nodes"], "removed_nodes": x["removed_nodes"],
        } for x in mismatches],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
