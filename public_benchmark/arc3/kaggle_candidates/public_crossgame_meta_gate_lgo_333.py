#!/usr/bin/env python3
"""R333: cross-game leave-one-game-out reliability gate audit for R327.

This is a new public-development policy test built after R330/R331.  It does not
reuse p5-p9 outcomes to fit a gate and it never stages/reads p5-p19.  Each game
summary is computed from p0-p4 only:
  * the unchanged R327 structural method is evaluated by 5-fold trace LOTO;
  * a deployment-side complexity feature (accepted_templates) is fitted on all
    five p0-p4 traces for that game.

The aggregate then performs 25 leave-one-GAME-out folds.  For each held game a
single threshold is chosen using only the other 24 game summaries.  The
threshold-selection algorithm is frozen here before this workflow executes:
  1) candidate thresholds are -1 plus observed training gate values;
  2) activate games with accepted_templates <= threshold;
  3) require aggregate training false_changes == 0, pixel_gain >= 0, and
     exact_frame_gain >= 0;
  4) among feasible thresholds maximize, in order, exact_frame_gain,
     pixel_gain, predicted_changes, number of active games, then prefer the
     smaller threshold.

The held game's evaluation metrics are never used to choose its threshold.
This is game-level public cross-validation only, not hidden/Kaggle evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327
import public_structural25_fixed_method_loto_329 as r329

RUNG = 333
BASE_MODE = "delta"
GRID = 8
EXPECTED_GAMES = 25
IDEMPOTENCY_KEY = "R333-CROSSGAME-META-GATE-LGO-20260923-001"
R327_FREEZE = "8d54bd197ae805a306493d5630c11268fcbe1ef9"
R329_FREEZE = "b3bef4979c940f010227632c215bce5767e5315a"
R330_FREEZE = "7358fa568414a96a2acf864a450ecc078bd8c433"
METRICS = (
    "frames", "pixels", "identity_errors", "candidate_errors",
    "identity_exact_frames", "candidate_exact_frames", "predicted_changes",
    "true_changed_correct", "false_changes", "template_firings",
    "conflicting_cells", "pixel_gain", "exact_frame_gain",
)


def _paths_ok(paths: list[Path], game: str) -> list[Path]:
    ps = sorted(paths, key=r246.pnum)
    if any(r246.game_id(p) != game for p in ps):
        raise SystemExit(f"mixed game inputs for {game}")
    if [r246.pnum(p) for p in ps] != list(range(5)):
        raise SystemExit(f"exact p0-p4 required for {game}")
    return ps


def summarize_game(paths: list[Path], game: str) -> dict:
    ps = _paths_ok(paths, game)
    traces = [r302.augment_trace(p) for p in ps]
    prepared = [r321.prep(t, BASE_MODE, GRID) for t in traces]
    _, full_fit = r327.fit_templates(prepared)
    base = r329.run_game(ps)
    return {
        "schema": "deus/arc3-r333-game-summary/1",
        "idempotency_key": IDEMPOTENCY_KEY,
        "game": game,
        "gate_feature": "accepted_templates",
        "gate_value": int(full_fit.get("accepted_templates", 0)),
        "full_fit": full_fit,
        "loto": base["loto"],
        "r329_verdict": base["verdict"],
        "protocol": {
            "data": "public p0-p4 only",
            "evaluation": "5-fold leave-one-trace-out for method outcome",
            "gate_feature_fit": "all p0-p4 traces; outcome-independent complexity feature",
            "p5_p9_staged_or_read": False,
            "p10_p19_staged_or_read": False,
        },
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "kaggle_execution": False,
            "competition_submission": False,
        },
    }


def _activated_aggregate(rows: list[dict], threshold: int) -> dict:
    c = Counter()
    active = 0
    for row in rows:
        if int(row["gate_value"]) > threshold:
            continue
        active += 1
        m = row["loto"]
        for k in METRICS:
            c[k] += int(m.get(k, 0))
    c["active_games"] = active
    # Recompute gains from primitive error/exact counters when available.
    if active:
        c["pixel_gain"] = c["identity_errors"] - c["candidate_errors"]
        c["exact_frame_gain"] = c["candidate_exact_frames"] - c["identity_exact_frames"]
    return dict(c)


def choose_threshold(train_rows: list[dict]) -> tuple[int, list[dict]]:
    candidates = [-1] + sorted({int(r["gate_value"]) for r in train_rows})
    feasible = []
    for t in candidates:
        a = _activated_aggregate(train_rows, t)
        ok = (
            int(a.get("false_changes", 0)) == 0
            and int(a.get("pixel_gain", 0)) >= 0
            and int(a.get("exact_frame_gain", 0)) >= 0
        )
        rec = {"threshold": t, "feasible": ok, "train": a}
        feasible.append(rec)
    valid = [x for x in feasible if x["feasible"]]
    if not valid:
        raise AssertionError("threshold -1 must be feasible")
    best = max(
        valid,
        key=lambda x: (
            int(x["train"].get("exact_frame_gain", 0)),
            int(x["train"].get("pixel_gain", 0)),
            int(x["train"].get("predicted_changes", 0)),
            int(x["train"].get("active_games", 0)),
            -int(x["threshold"]),
        ),
    )
    return int(best["threshold"]), feasible


def selected_metrics(row: dict, gate_on: bool) -> dict:
    m = row["loto"]
    if gate_on:
        return {k: int(m.get(k, 0)) for k in METRICS}
    # Identity fallback: preserve workload/error baseline and zero intervention.
    return {
        "frames": int(m.get("frames", 0)),
        "pixels": int(m.get("pixels", 0)),
        "identity_errors": int(m.get("identity_errors", 0)),
        "candidate_errors": int(m.get("identity_errors", 0)),
        "identity_exact_frames": int(m.get("identity_exact_frames", 0)),
        "candidate_exact_frames": int(m.get("identity_exact_frames", 0)),
        "predicted_changes": 0,
        "true_changed_correct": 0,
        "false_changes": 0,
        "template_firings": 0,
        "conflicting_cells": 0,
        "pixel_gain": 0,
        "exact_frame_gain": 0,
    }


def aggregate(summary_paths: list[Path]) -> dict:
    rows = [json.loads(p.read_text()) for p in summary_paths]
    if len(rows) != EXPECTED_GAMES or len({r["game"] for r in rows}) != EXPECTED_GAMES:
        raise SystemExit(f"exactly {EXPECTED_GAMES} unique game summaries required")
    for r in rows:
        assert r["schema"] == "deus/arc3-r333-game-summary/1"
        assert r["idempotency_key"] == IDEMPOTENCY_KEY
        assert r["protocol"]["p5_p9_staged_or_read"] is False
        assert r["protocol"]["p10_p19_staged_or_read"] is False

    folds = []
    agg = Counter()
    thresholds = Counter()
    for held in sorted(rows, key=lambda x: x["game"]):
        train = [r for r in rows if r["game"] != held["game"]]
        threshold, search = choose_threshold(train)
        gate_on = int(held["gate_value"]) <= threshold
        hm = selected_metrics(held, gate_on)
        for k, v in hm.items():
            agg[k] += int(v)
        thresholds[str(threshold)] += 1
        folds.append({
            "held_game": held["game"],
            "held_gate_value": int(held["gate_value"]),
            "selected_threshold": threshold,
            "gate_on": gate_on,
            "held_selected_metrics": hm,
            "selection_used_held_outcome": False,
            "feasible_thresholds": [x["threshold"] for x in search if x["feasible"]],
        })

    agg["pixel_gain"] = agg["identity_errors"] - agg["candidate_errors"]
    agg["exact_frame_gain"] = agg["candidate_exact_frames"] - agg["identity_exact_frames"]
    agg["gate_on_games"] = sum(int(f["gate_on"]) for f in folds)
    agg["gate_off_games"] = EXPECTED_GAMES - agg["gate_on_games"]

    # Descriptive fixed-AT15 reference only; not the R333 selector.
    ref = Counter()
    for r in rows:
        hm = selected_metrics(r, int(r["gate_value"]) <= 15)
        for k, v in hm.items():
            ref[k] += int(v)
    ref["pixel_gain"] = ref["identity_errors"] - ref["candidate_errors"]
    ref["exact_frame_gain"] = ref["candidate_exact_frames"] - ref["identity_exact_frames"]
    ref["gate_on_games"] = sum(int(int(r["gate_value"]) <= 15) for r in rows)
    ref["gate_off_games"] = EXPECTED_GAMES - ref["gate_on_games"]

    if agg["false_changes"] == 0 and agg["pixel_gain"] > 0 and agg["exact_frame_gain"] > 0:
        verdict = "CROSSGAME_LGO_ZERO_FALSE_EXACTFRAME_SIGNAL"
    elif agg["false_changes"] == 0 and agg["pixel_gain"] > 0:
        verdict = "CROSSGAME_LGO_ZERO_FALSE_PIXEL_SIGNAL"
    elif agg["false_changes"] > 0:
        verdict = "CROSSGAME_LGO_FALSE_CHANGE_FALSIFIER"
    else:
        verdict = "CROSSGAME_LGO_NO_MATERIAL_SIGNAL"

    return {
        "schema": "deus/arc3-r333-crossgame-meta-gate-lgo/1",
        "rung": RUNG,
        "idempotency_key": IDEMPOTENCY_KEY,
        "lineage": {
            "r327_method_commit": R327_FREEZE,
            "r329_matrix_commit": R329_FREEZE,
            "r330_reference_commit": R330_FREEZE,
        },
        "freeze": {
            "gate_feature": "accepted_templates",
            "operator": "<=",
            "selector": "leave-one-game-out threshold fit on other 24 games only",
            "feasibility": "train false_changes==0 and pixel_gain>=0 and exact_frame_gain>=0",
            "objective_order": ["exact_frame_gain", "pixel_gain", "predicted_changes", "active_games", "smaller_threshold"],
            "per_game_method_selection": False,
            "held_game_outcome_used_for_threshold": False,
        },
        "protocol": {
            "data": "public p0-p4 only",
            "game_count": EXPECTED_GAMES,
            "outer_evaluation": "leave-one-game-out",
            "inner_method_evaluation": "per-game five-fold trace LOTO",
            "p5_p9_staged_or_read": False,
            "p10_p19_staged_or_read": False,
            "post_r330_hypothesis": True,
        },
        "aggregate": dict(agg),
        "threshold_histogram": dict(sorted(thresholds.items(), key=lambda kv: int(kv[0]))),
        "folds": folds,
        "reference_fixed_at15_p0_p4": dict(ref),
        "verdict": verdict,
        "truth": {
            "public_offline_only": True,
            "source_free_runtime_logic": True,
            "game_level_cross_validation": True,
            "independent_hidden_generalization_claim": False,
            "whole_game_solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "competition_quota_spent": 0,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--game")
    ap.add_argument("--aggregate-dir", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if bool(a.game) == bool(a.aggregate_dir):
        raise SystemExit("choose exactly one of --game or --aggregate-dir")
    if a.game:
        out = summarize_game(a.input, a.game)
        a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"game": out["game"], "gate_value": out["gate_value"], "loto": out["loto"]}, sort_keys=True))
        return
    paths = sorted(a.aggregate_dir.glob("r333-game-*.json"))
    out = aggregate(paths)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": out["verdict"], "aggregate": out["aggregate"], "threshold_histogram": out["threshold_histogram"]}, sort_keys=True))


if __name__ == "__main__":
    main()
