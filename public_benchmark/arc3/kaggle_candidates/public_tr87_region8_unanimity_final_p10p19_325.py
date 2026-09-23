#!/usr/bin/env python3
"""R325: final reused-public audit for frozen TR87 region8+unanimity candidate.

Candidate identity was fixed before p5-p9 by R323/R324. R325 keeps the exact
same representation and reliability rule, refits only the deterministic table
on public p0-p9, and evaluates once on p10-p19. No representation selection,
threshold search, or retry is allowed after p10-p19 is read.

This is PUBLIC_OFFLINE/reused-public evidence, not independent hidden
generalization, whole-game solution, Kaggle execution, competition submission,
or official leaderboard score.
"""
from __future__ import annotations

import argparse, json
from collections import Counter
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_region8_cross_trace_unanimity_323 as r323

RUNG = 325
GAME = r323.GAME
BASE_MODE = r323.BASE_MODE
GRID = r323.GRID


def _exact(paths, nums, label):
    ps = sorted(paths, key=r246.pnum)
    want = list(nums)
    got = [r246.pnum(p) for p in ps]
    if got != want:
        raise SystemExit(f"{label}: exact pnums required, got {got}, want {want}")
    if any(r246.game_id(p) != GAME for p in ps):
        raise SystemExit(f"{label}: exact game required")
    return ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, action="append", default=[])
    ap.add_argument("--eval", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    train_ps = _exact(a.train, range(10), "train")
    eval_ps = _exact(a.eval, range(10, 20), "eval")
    train_traces = [r302.augment_trace(p) for p in train_ps]
    eval_traces = [r302.augment_trace(p) for p in eval_ps]
    prepared_train = [r321.prep(t, BASE_MODE, GRID) for t in train_traces]
    prepared_eval = [r321.prep(t, BASE_MODE, GRID) for t in eval_traces]

    rules, fit = r323.fit_unanimous(prepared_train)
    total = Counter(); per_trace = []
    for i, prepared in enumerate(prepared_eval, start=10):
        ev = r314._evaluate(prepared, rules)
        per_trace.append({"trace": i, "eval": ev})
        for k, v in ev.items():
            if isinstance(v, int):
                total[k] += v
    total["pixel_gain"] = total["identity_errors"] - total["candidate_errors"]
    total["exact_frame_gain"] = total["candidate_exact_frames"] - total["identity_exact_frames"]
    total = dict(total)

    if total.get("predicted_changes", 0) > 0 and total.get("false_changes", 0) == 0 and total.get("pixel_gain", 0) > 0 and total.get("exact_frame_gain", 0) >= 0:
        verdict = "FINAL_PUBLIC_ZERO_FALSE_PASS"
    elif total.get("pixel_gain", 0) > 0:
        verdict = "FINAL_PUBLIC_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict = "FINAL_PUBLIC_NO_SIGNAL"

    out = {
        "schema": "deus/arc3-r325-tr87-region8-unanimity-final-p10p19/1",
        "rung": RUNG,
        "game": GAME,
        "candidate": {
            "representation": "R321 delta+region8",
            "reliability": "R323 deterministic rule supported in every training trace",
            "selection_source": "R323 p0-p4 LOTO; R324 p5-p9 validation",
            "representation_changed_after_r324": False,
            "reliability_changed_after_r324": False,
        },
        "protocol": {
            "fit": "exact public p0-p9 with frozen candidate family",
            "evaluation": "exact public p10-p19 one-shot final audit",
            "retune_on_p10_p19": False,
            "candidate_selection_on_p10_p19": False,
        },
        "fit": fit,
        "eval_by_trace": per_trace,
        "eval_total": total,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "reused_public_development_final_audit": True,
            "source_free_runtime_logic": True,
            "p0_p9_fit_read": True,
            "p10_p19_final_audit_read": True,
            "independent_hidden_generalization_claim": False,
            "whole_game_solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "official_leaderboard_score": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "eval_total": total, "fit": fit}, sort_keys=True))


if __name__ == "__main__":
    main()
