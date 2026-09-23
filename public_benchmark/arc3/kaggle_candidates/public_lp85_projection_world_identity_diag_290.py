#!/usr/bin/env python3
"""R290: lp85 projection-based world identity diagnostic after R289 NO_SIGNAL.

R288 localized 88.1179% of aliasing pixels to the world interior. R289 showed
that simply increasing the modal region grid from G=8 to G=16 does not split
those aliases or improve validation. R290 therefore changes representation,
not resolution: append per-color row/column occupancy projections from the
action-canonical, static-UI-masked world. These projections retain thin
structures, density and viewport/layout identity that modal region cells erase.

Protocol: p0-p4 fit/collision analysis -> p5-p9 diagnostic. p10-p19 forbidden.
The projection mechanism is fixed in source before diagnostic traces are staged.
This is PUBLIC_OFFLINE/source-free. It predicts action-canonical exact next
frames only for repeat-supported deterministic keys and cannot promote a solver
or make a Kaggle/hidden-score claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG = 290
TARGET_GAME = "lp85-305b61c3"
MIN_DISTINCT_PRESTATES = 2
BASE_MODE = "canon_regions_ui"


def canon_masked(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def canon_raw(board, action):
    return r275.canon_board(board, action, use_ui_mask=False)


def projection_signature(board, action):
    """Exact per-color row/column occupancy counts in canonical coordinates.

    This is deliberately not another spatial modal grid. Counts preserve thin
    lines and occupancy mass even when a region's modal color is unchanged.
    """
    b = canon_masked(board, action)
    h = len(b)
    w = len(b[0]) if h else 0
    bg = r246.bg(b)
    colors = sorted({int(v) for row in b for v in row if int(v) != bg})
    out = []
    for color in colors:
        rows = tuple(sum(int(v) == color for v in row) for row in b)
        cols = tuple(sum(int(b[r][c]) == color for r in range(h)) for c in range(w))
        out.append((color, rows, cols))
    return tuple(out)


def base_key(r):
    return r278.before_key(r, BASE_MODE)


def candidate_key(r):
    return (
        base_key(r),
        r246.stable(projection_signature(r["before"], r["action"])),
    )


def exact_after(r):
    return r246.digest(canon_raw(r["after"], r["action"]))


def fit_exact(rows, key_fn):
    outcomes = defaultdict(Counter)
    prestates = defaultdict(set)
    for r in rows:
        k = key_fn(r)
        outcomes[k][exact_after(r)] += 1
        prestates[k].add(r246.digest(r["before"]))
    table = {
        k: next(iter(v))
        for k, v in outcomes.items()
        if len(v) == 1 and len(prestates[k]) >= MIN_DISTINCT_PRESTATES
    }
    return table, {
        "keys": len(outcomes),
        "deterministic_keys": sum(len(v) == 1 for v in outcomes.values()),
        "ambiguous_keys": sum(len(v) > 1 for v in outcomes.values()),
        "repeat_supported_keys": sum(
            len(prestates[k]) >= MIN_DISTINCT_PRESTATES for k in outcomes
        ),
        "eligible_exact_keys": len(table),
    }


def evaluate(rows, table, key_fn):
    s = Counter()
    for r in rows:
        s["transitions"] += 1
        pred = table.get(key_fn(r))
        if pred is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        s["correct" if pred == exact_after(r) else "wrong"] += 1
    p = s["predictions"]
    return {
        **dict(s),
        "accuracy": round(s["correct"] / p, 6) if p else None,
        "coverage": round(p / s["transitions"], 6) if s["transitions"] else 0.0,
    }


def collision_stats(rows, key_fn):
    outcomes = defaultdict(set)
    prestates = defaultdict(set)
    for r in rows:
        k = key_fn(r)
        outcomes[k].add(exact_after(r))
        prestates[k].add(r246.digest(r["before"]))
    supported = [k for k in outcomes if len(prestates[k]) >= MIN_DISTINCT_PRESTATES]
    return {
        "keys": len(outcomes),
        "repeat_supported_keys": len(supported),
        "repeat_supported_exact_unique": sum(len(outcomes[k]) == 1 for k in supported),
        "repeat_supported_exact_ambiguous": sum(len(outcomes[k]) > 1 for k in supported),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by) != {TARGET_GAME}:
        raise SystemExit(f"exact target required, got {sorted(by)}")
    ps = sorted(by[TARGET_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise SystemExit(f"exact p0-p9 required, got {nums}")

    train = r278.annotated_rows(ps[:5])
    val = r278.annotated_rows(ps[5:])

    base_tab, base_fit = fit_exact(train, base_key)
    cand_tab, cand_fit = fit_exact(train, candidate_key)
    base_val = evaluate(val, base_tab, base_key)
    cand_val = evaluate(val, cand_tab, candidate_key)
    base_col = collision_stats(train, base_key)
    cand_col = collision_stats(train, candidate_key)

    bc = int(base_val.get("correct", 0) or 0)
    cc = int(cand_val.get("correct", 0) or 0)
    cw = int(cand_val.get("wrong", 0) or 0)
    cp = int(cand_val.get("predictions", 0) or 0)
    ambiguity_reduction = (
        base_col["repeat_supported_exact_ambiguous"]
        - cand_col["repeat_supported_exact_ambiguous"]
    )

    if cp > 0 and cw == 0 and cc > bc:
        verdict = "ZERO_WRONG_EXACT_FRAME_GAIN"
    elif cp > 0 and cw > 0:
        verdict = "REJECT_MISMATCH"
    else:
        verdict = "NO_SIGNAL"

    out = {
        "schema": "deus/arc3-r290-lp85-projection-world-identity-diagnostic/1",
        "rung": RUNG,
        "game": TARGET_GAME,
        "mechanism": {
            "base": "R279 action-canonical static-UI-masked G8 regions + pooled action class",
            "delta": "append exact per-color row/column occupancy projections in canonical masked world",
            "projection": "per-color exact row counts + exact column counts",
            "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
            "prediction_target": "action-canonical exact next-frame digest",
        },
        "protocol": {
            "fit_collision_analysis": "p0-p4 only",
            "diagnostic": "p5-p9 only",
            "p10_p19_staged_or_read": False,
            "candidate_fixed_before_diagnostic": True,
            "threshold_sweep": False,
            "promotion_in_r290": False,
            "signal_rule": "candidate predictions>0 AND wrong=0 AND candidate correct>base correct",
        },
        "base": {"fit": base_fit, "validation": base_val, "collisions": base_col},
        "candidate": {"fit": cand_fit, "validation": cand_val, "collisions": cand_col},
        "delta": {
            "repeat_supported_exact_ambiguity_reduction": ambiguity_reduction,
            "validation_correct_delta": cc - bc,
            "validation_wrong_delta": cw - int(base_val.get("wrong", 0) or 0),
            "validation_prediction_delta": cp - int(base_val.get("predictions", 0) or 0),
        },
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p10_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "whole_game_policy_claim": False,
            "solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r290": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "base_collision": base_col,
        "candidate_collision": cand_col,
        "base_validation": base_val,
        "candidate_validation": cand_val,
        "delta": out["delta"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
