#!/usr/bin/env python3
"""R279: frozen public-development gate for the exact R278 lp85 signal.

R278 used only p0-p4 fit and p5-p9 diagnostic and selected:
  game: lp85-305b61c3
  mode: canon_regions_ui

R279 freezes that game+mode before reading p10-p19, refits deterministic
representation transitions on p0-p9, then evaluates reused public-development
p10-p19. UI-mask and canon_nodes_ui are read only as frozen comparison controls.
No heldout row may change selector, representation, or model.

PUBLIC_OFFLINE only; this is not independent hidden generalization, exact-frame
solver closure, Kaggle execution, or competition score evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278

RUNG = 279
FROZEN_GAME = "lp85-305b61c3"
FROZEN_MODE = "canon_regions_ui"
CONTROL_MODES = ("ui_mask", "canon_nodes_ui")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by) != {FROZEN_GAME}:
        raise SystemExit(f"exact frozen game required: {FROZEN_GAME}; got {sorted(by)}")

    ps = sorted(by[FROZEN_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise SystemExit(f"{FROZEN_GAME}: exact p0-p19 required, got {nums}")

    train = r278.annotated_rows(ps[:10])
    hold = r278.annotated_rows(ps[10:])

    cand_tab, cand_fit = r278.fit(train, FROZEN_MODE)
    cand_eval = r278.evaluate(hold, cand_tab, FROZEN_MODE)

    controls = {}
    for mode in CONTROL_MODES:
        tab, fs = r278.fit(train, mode)
        controls[mode] = {"fit": fs, "heldout": r278.evaluate(hold, tab, mode)}

    transitions = int(cand_eval.get("transitions", 0))
    min_predictions = max(10, math.ceil(0.05 * transitions))
    best_control_correct = max(int(controls[m]["heldout"].get("correct", 0)) for m in CONTROL_MODES)

    gate_pass = bool(
        int(cand_eval.get("predictions", 0)) >= min_predictions
        and int(cand_eval.get("wrong", 0)) == 0
        and float(cand_eval.get("accuracy") or 0.0) >= 0.99
        and int(cand_eval.get("correct", 0)) > best_control_correct
    )
    verdict = "PROMOTE_FROZEN_REPRESENTATION" if gate_pass else "NO_PROMOTION"

    out = {
        "schema": "deus/arc3-r279-lp85-region-frozen-gate/1",
        "rung": RUNG,
        "lineage": {
            "r278_run": 35817707053,
            "r278_head": "d5c082770462b62fa20909859f3e97ab6177ef7f",
            "r278_artifact": 10732062814,
            "r278_selector_frozen_before_p10_p19": True,
            "r278_p5_p9_signal": {
                "game": FROZEN_GAME,
                "mode": FROZEN_MODE,
                "predictions": 187,
                "correct": 187,
                "wrong": 0,
            },
        },
        "frozen_selector": {"game": FROZEN_GAME, "mode": FROZEN_MODE},
        "protocol": {
            "mechanism_selection": "R278 p0-p4 fit -> p5-p9 diagnostic",
            "model_fit": "p0-p9 only after exact selector freeze",
            "evaluation": "p10-p19 reused public-development heldout",
            "p10_p19_updates_selector": False,
            "p10_p19_updates_representation": False,
            "p10_p19_updates_model": False,
            "gate_rule_frozen_before_eval": "predictions>=max(10,ceil(5% transitions)); wrong=0; accuracy>=0.99; correct>best frozen control correct",
        },
        "candidate": {
            "fit": cand_fit,
            "heldout": cand_eval,
            "min_predictions": min_predictions,
            "best_control_correct": best_control_correct,
            "gate_pass": gate_pass,
        },
        "controls": controls,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "reused_public_development_holdout": True,
            "selector_frozen_before_holdout_read": True,
            "independent_hidden_generalization_claim": False,
            "exact_frame_solver_claim": False,
            "full_game_policy_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent_by_r279": False,
        },
    }

    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "candidate": cand_eval,
        "controls": {m: controls[m]["heldout"] for m in CONTROL_MODES},
        "min_predictions": min_predictions,
        "best_control_correct": best_control_correct,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
