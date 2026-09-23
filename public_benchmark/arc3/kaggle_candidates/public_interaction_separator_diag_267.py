#!/usr/bin/env python3
"""R267: source-free relational separator diagnostic for re86 R266 mismatches.

R266 showed that exact local source/destination context still mixed correct and
wrong outcomes and therefore selected no zero-wrong action. This diagnostic
changes representation rather than retrying thresholds: it asks whether the
R266 validation mismatch class can be separated by compact pre-action
relational/topological quantities (object count/area, destination occupancy,
source/destination ring occupancy, edge distance, and transport footprint).

Protocol:
  * p0-p4 fit the unchanged R266 transport + residual rules;
  * p5-p9 only diagnose correct-vs-wrong predictions;
  * p10-p19 are NOT read;
  * labels are used only to discover/falsify separator hypotheses here;
  * no solver promotion, packaging, Kaggle execution, score, or submission.
"""
from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257
import public_contextual_object_interaction_gate_266 as r266

RUNG = 267
FEATURES = (
    "moved_count",
    "moved_area_sum",
    "moved_area_max",
    "moved_color_count",
    "all_component_count",
    "dest_collision_count",
    "dest_source_overlap_count",
    "source_ring_nonbg",
    "dest_ring_nonbg",
    "ring_delta",
    "min_edge_distance",
    "transport_delta_cells",
    "nonbg_total",
)


def prep(path: Path) -> list[dict[str, Any]]:
    return r266.prep(path)


def nonbg_ring(board, comp, *, vector=(0, 0), pad=1, exclude=None):
    bg = int(r246.bg(board))
    dr, dc = vector
    r0, r1 = comp["r0"] + dr, comp["r1"] + dr
    c0, c1 = comp["c0"] + dc, comp["c1"] + dc
    h, w = len(board), len(board[0])
    exclude = exclude or set()
    n = 0
    for rr in range(r0 - pad, r1 + pad + 1):
        for cc in range(c0 - pad, c1 + pad + 1):
            if not (0 <= rr < h and 0 <= cc < w) or (rr, cc) in exclude:
                continue
            if int(board[rr][cc]) != bg:
                n += 1
    return n


def feature_vector(row, model) -> dict[str, int] | None:
    vector, _ = model
    if not vector:
        return None
    base = r257.render(row["before"], model[0], model[1], r266.MAX_AREA)
    comps = r266.movable_components(row["before"], model)
    if base is None or not comps:
        return None
    board = row["before"]
    bg = int(r246.bg(board))
    dr, dc = vector
    h, w = len(board), len(board[0])
    all_comps = r254.components(board)
    source_cells = set()
    dest_cells = set()
    source_ring = 0
    dest_ring = 0
    min_edge = 10**9
    for c in comps:
        src = {(c["r0"] + rr, c["c0"] + cc) for rr, cc in c["shape"]}
        dst = {(rr + dr, cc + dc) for rr, cc in src}
        source_cells |= src
        dest_cells |= dst
        source_ring += nonbg_ring(board, c, vector=(0, 0), pad=1, exclude=src)
        dest_ring += nonbg_ring(board, c, vector=vector, pad=1, exclude=dst)
        min_edge = min(
            min_edge,
            c["r0"], c["c0"], h - 1 - c["r1"], w - 1 - c["c1"],
        )
    collision = sum(
        1 for rr, cc in dest_cells
        if int(board[rr][cc]) != bg and (rr, cc) not in source_cells
    )
    overlap = len(dest_cells & source_cells)
    transport_delta = sum(
        int(board[rr][cc]) != int(base[rr][cc])
        for rr in range(h) for cc in range(w)
    )
    nonbg_total = sum(int(v) != bg for r in board for v in r)
    colors = {int(c["color"]) for c in comps}
    return {
        "moved_count": len(comps),
        "moved_area_sum": sum(int(c["area"]) for c in comps),
        "moved_area_max": max(int(c["area"]) for c in comps),
        "moved_color_count": len(colors),
        "all_component_count": len(all_comps),
        "dest_collision_count": collision,
        "dest_source_overlap_count": overlap,
        "source_ring_nonbg": source_ring,
        "dest_ring_nonbg": dest_ring,
        "ring_delta": dest_ring - source_ring,
        "min_edge_distance": int(min_edge),
        "transport_delta_cells": transport_delta,
        "nonbg_total": nonbg_total,
    }


def collect_predictions(rows, exact, model, rules, mode, pad):
    out = []
    for row in rows:
        if row["exact_key"] in exact:
            continue
        pred = r266.apply(row, model, rules, mode, pad)
        if pred is None:
            continue
        fv = feature_vector(row, model)
        if fv is None:
            continue
        out.append({
            "trace": row["trace"],
            "transition_id": row["transition_id"],
            "action": row["action"],
            "correct": pred == row["after"],
            "features": fv,
        })
    return out


def pure_summary(rows):
    """Find label-pure correct buckets/stumps; diagnostic only."""
    result = {"single_value": [], "pair_value": [], "threshold": []}
    for f in FEATURES:
        buckets = defaultdict(list)
        for x in rows:
            buckets[x["features"][f]].append(x)
        for value, xs in buckets.items():
            c = sum(x["correct"] for x in xs)
            w = len(xs) - c
            traces = len({x["trace"] for x in xs})
            if c >= 2 and w == 0 and traces >= 2:
                result["single_value"].append({"feature": f, "value": value, "correct": c, "wrong": 0, "traces": traces})

        vals = sorted({x["features"][f] for x in rows})
        for t in vals:
            for op in ("le", "ge"):
                xs = [x for x in rows if (x["features"][f] <= t if op == "le" else x["features"][f] >= t)]
                c = sum(x["correct"] for x in xs)
                w = len(xs) - c
                traces = len({x["trace"] for x in xs})
                if c >= 2 and w == 0 and traces >= 2:
                    result["threshold"].append({"feature": f, "op": op, "threshold": t, "correct": c, "wrong": 0, "traces": traces})

    for f1, f2 in itertools.combinations(FEATURES, 2):
        buckets = defaultdict(list)
        for x in rows:
            buckets[(x["features"][f1], x["features"][f2])].append(x)
        for value, xs in buckets.items():
            c = sum(x["correct"] for x in xs)
            w = len(xs) - c
            traces = len({x["trace"] for x in xs})
            if c >= 2 and w == 0 and traces >= 2:
                result["pair_value"].append({"features": [f1, f2], "value": list(value), "correct": c, "wrong": 0, "traces": traces})

    for k in result:
        result[k].sort(key=lambda z: (-z["correct"], -z["traces"], json.dumps(z, sort_keys=True)))
        result[k] = result[k][:30]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    ps = sorted(a.input, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise ValueError(f"exact p0..p9 required, got {nums}")
    parts = [prep(p) for p in ps]
    tr = [r for part in parts[:5] for r in part]
    va = [r for part in parts[5:] for r in part]
    tr_by, va_by = defaultdict(list), defaultdict(list)
    for r in tr:
        tr_by[r["action"]].append(r)
    for r in va:
        va_by[r["action"]].append(r)
    exact = r251.fit_exact(tr)

    actions = {}
    for action in sorted(set(tr_by) | set(va_by)):
        model = r266.fit_base(tr_by[action])
        variants = []
        for mode, pad, edit_radius, support in r266.VARIANTS:
            rules = r266.fit_rules(tr_by[action], model, mode, pad, edit_radius, support)
            preds = collect_predictions(va_by[action], exact, model, rules, mode, pad)
            correct = sum(x["correct"] for x in preds)
            wrong = len(preds) - correct
            variants.append({
                "key": f"{mode}_p{pad}_e{edit_radius}_s{support}",
                "mode": mode, "pad": pad, "edit_radius": edit_radius, "support": support,
                "rule_count": len(rules), "predictions": len(preds), "correct": correct, "wrong": wrong,
            })
        exploratory = [v for v in variants if v["correct"] > 0 and v["wrong"] > 0]
        exploratory.sort(key=lambda v: (-v["correct"], v["wrong"], -v["predictions"], v["key"]))
        if not exploratory:
            actions[action] = {"best_mixed_variant": None, "variants_with_correct_and_wrong": 0, "separator": None}
            continue
        best = exploratory[0]
        rules = r266.fit_rules(tr_by[action], model, best["mode"], best["pad"], best["edit_radius"], best["support"])
        preds = collect_predictions(va_by[action], exact, model, rules, best["mode"], best["pad"])
        sep = pure_summary(preds)
        best_signal = max(
            [x["correct"] for family in sep.values() for x in family] or [0]
        )
        actions[action] = {
            "best_mixed_variant": best,
            "variants_with_correct_and_wrong": len(exploratory),
            "validation_examples": preds[:80],
            "separator": sep,
            "max_pure_correct_support": best_signal,
        }

    signal_actions = [a for a, x in actions.items() if int(x.get("max_pure_correct_support", 0) or 0) >= 2]
    out = {
        "schema": "deus/arc3-r267-interaction-separator-diagnostic/1",
        "rung": RUNG,
        "lineage": {
            "r266": "run35801138316/artifact10725224736",
            "repair": "replace exact context lookup retry with compact relational/topological separator falsifier",
        },
        "protocol": {
            "fit": "p0-p4",
            "diagnostic_eval": "p5-p9",
            "p10_p19_read": False,
            "outcome_labels_used_for_diagnostic_only": True,
            "promotion": False,
        },
        "actions": actions,
        "signal_actions": signal_actions,
        "diagnostic_signal": bool(signal_actions),
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "p10_p19_read": False,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    compact = {
        k: {
            "best": v.get("best_mixed_variant"),
            "max_pure_correct_support": v.get("max_pure_correct_support", 0),
        }
        for k, v in actions.items()
    }
    print(json.dumps({"diagnostic_signal": bool(signal_actions), "signal_actions": signal_actions, "actions": compact}, sort_keys=True))


if __name__ == "__main__":
    main()
