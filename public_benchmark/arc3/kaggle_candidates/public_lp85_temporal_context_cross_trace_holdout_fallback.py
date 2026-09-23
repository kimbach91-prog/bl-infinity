#!/usr/bin/env python3
"""Fallback: lp85 cross-trace structural-fit + causal temporal-context holdout.

This is a bounded public/offline validation of one *frozen* mechanism discovered
by the prior p0-p4 diagnostic: ACTION_REGION4 + H3 stable period/velocity.

For each p0..p4 trace, R300 structural templates are fit on the other four
traces only.  The held-out trace is then evaluated causally; residual-history
updates may use only outcomes from earlier transitions of that same held-out
trace.  No p5..p19 trace is staged or read.

Truth boundary: this tests cross-trace structural fit plus online causal
adaptation.  It is not static independent generalization and is not a Kaggle
score/submission result.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_lp85_seeded_structural_residual_gate_300 as r300
import public_lp85_temporal_residual_context_diag_302 as r302

TARGET_GAME = "lp85-305b61c3"
CTX_MODE = "ACTION_REGION4"
HISTORY_MODE = "H3_STABLE_PERIOD_VELOCITY"


def main() -> None:
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
    if nums != list(range(5)):
        raise SystemExit(f"exact p0-p4 required, got {nums}")

    traces = [r278.annotated_rows([p]) for p in ps]
    overall = Counter()
    folds = []
    for hold_i in range(5):
        train_traces = [tr for i, tr in enumerate(traces) if i != hold_i]
        train_rows = [r for tr in train_traces for r in tr]
        templates, fit = r300.fit_templates(train_rows, train_traces)
        metrics, per_trace = r302.run_mode(
            [traces[hold_i]], templates, CTX_MODE, HISTORY_MODE
        )
        overall.update(metrics)
        folds.append({
            "holdout_p": hold_i,
            "train_ps": [i for i in range(5) if i != hold_i],
            "fit_gate": fit,
            "metrics": metrics,
            "per_trace": per_trace,
        })

    predicted = int(overall.get("predicted_changes", 0))
    false = int(overall.get("false_changes", 0))
    reduction = int(overall.get("error_reduction_vs_r300_base", 0))
    if predicted > 0 and false == 0 and reduction > 0:
        verdict = "CROSS_TRACE_STRUCTURAL_FIT_CAUSAL_HOLDOUT_ZERO_FALSE"
    elif reduction > 0:
        verdict = "CROSS_TRACE_STRUCTURAL_FIT_CAUSAL_HOLDOUT_GAIN_UNSAFE"
    else:
        verdict = "CROSS_TRACE_STRUCTURAL_FIT_CAUSAL_HOLDOUT_NO_SIGNAL"

    out = {
        "schema": "deus/arc3-lp85-temporal-context-cross-trace-holdout-fallback/1",
        "game": TARGET_GAME,
        "frozen_mechanism": {
            "context": CTX_MODE,
            "history": HISTORY_MODE,
            "residual_base": "R300 structural residual templates",
            "guard": "exact base pre-values at predicted translated component",
            "selection_changed_after_holdout_read": False,
        },
        "protocol": {
            "input_scope": "p0-p4 only",
            "folds": "leave-one-trace-out structural-template fit",
            "heldout_runtime": "past-only causal residual-history adaptation within heldout trace",
            "same_trace_past_outcome_adaptation": True,
            "p5_p19_staged_or_read": False,
            "promotion_in_this_run": False,
        },
        "folds": folds,
        "overall": dict(overall),
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "cross_trace_structural_fit_holdout": True,
            "static_independent_generalization": False,
            "online_causal_adaptation": True,
            "p5_p19_read": False,
            "solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "overall": dict(overall), "folds": [
        {"holdout_p": f["holdout_p"], "metrics": f["metrics"]} for f in folds
    ]}, sort_keys=True))


if __name__ == "__main__":
    main()
