#!/usr/bin/env python3
"""R330: frozen global complexity gate for R327 structural residual replay.

R329 swept the exact same R327 structural method over all 25 public games with
p0-p4 five-fold LOTO and falsified unconditional global activation: broad pixel
signal remained, but false changes and exact-frame regressions were non-zero.

Before reading any R330 p5-p9 replay result, one global training-side reliability
gate is frozen from the completed R329 p0-p4 development matrix:
    accepted_templates <= 15
There is no per-game threshold/method selection. For each game, R330 fits the
unchanged R327 template family on p0-p4. If the global gate is on, those frozen
fit templates are evaluated on p5-p9; otherwise the candidate is identity.

p5-p9 are source-assisted public-development stability evidence only. p10-p19
must never be staged/read by this rung. This is not hidden/Kaggle evidence and
cannot authorize a competition submission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327

RUNG = 330
BASE_MODE = "delta"
GRID = 8
GATE_FEATURE = "accepted_templates"
GATE_MAX = 15
R327_FREEZE = "8d54bd197ae805a306493d5630c11268fcbe1ef9"
R329_FREEZE = "b3bef4979c940f010227632c215bce5767e5315a"
IDEMPOTENCY_KEY = "R330-GLOBAL-AT15-P5P9-20260923-001"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--game", required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    ps = sorted(a.input, key=r246.pnum)
    if not ps or any(r246.game_id(p) != a.game for p in ps):
        raise SystemExit(f"exact game required: {a.game}")
    if [r246.pnum(p) for p in ps] != list(range(10)):
        raise SystemExit("exact p0-p9 required")

    train = [r302.augment_trace(p) for p in ps[:5]]
    replay = [r302.augment_trace(p) for p in ps[5:]]
    prepared_train = [r321.prep(t, BASE_MODE, GRID) for t in train]
    prepared_replay = [row for t in replay for row in r321.prep(t, BASE_MODE, GRID)]

    templates, fit = r327.fit_templates(prepared_train)
    gate_value = int(fit.get(GATE_FEATURE, 0))
    gate_on = gate_value <= GATE_MAX
    active_templates = templates if gate_on else {}
    val = r327.evaluate(prepared_replay, active_templates)

    predicted = int(val.get("predicted_changes", 0))
    false = int(val.get("false_changes", 0))
    pixel_gain = int(val.get("pixel_gain", 0))
    exact_gain = int(val.get("exact_frame_gain", 0))

    if not gate_on:
        verdict = "GLOBAL_AT15_GATE_OFF_IDENTITY"
    elif predicted > 0 and false == 0 and pixel_gain > 0 and exact_gain > 0:
        verdict = "GLOBAL_AT15_GATE_ON_ZERO_FALSE_EXACTFRAME_PASS"
    elif predicted > 0 and false == 0 and pixel_gain > 0:
        verdict = "GLOBAL_AT15_GATE_ON_ZERO_FALSE_PIXEL_ONLY"
    elif false > 0:
        verdict = "GLOBAL_AT15_GATE_ON_FALSE_CHANGE_FALSIFIER"
    else:
        verdict = "GLOBAL_AT15_GATE_ON_NO_MATERIAL_GAIN"

    out = {
        "schema": "deus/arc3-r330-global-at15-frozen-p5p9/1",
        "rung": RUNG,
        "game": a.game,
        "idempotency_key": IDEMPOTENCY_KEY,
        "freeze": {
            "r327_method_commit": R327_FREEZE,
            "r329_cross_game_commit": R329_FREEZE,
            "gate_feature": GATE_FEATURE,
            "gate_operator": "<=",
            "gate_threshold": GATE_MAX,
            "gate_selected_from": "completed R329 public p0-p4 LOTO development matrix only",
            "per_game_threshold_selection": False,
            "representation_changed_after_gate_freeze": False,
        },
        "protocol": {
            "fit": "p0-p4 only",
            "source_assisted_replay": "p5-p9 only",
            "p10_p19_staged_or_read": False,
            "p5_p9_updates_gate": False,
            "p5_p9_updates_model_family": False,
            "cross_game_hyperparameter_retune_after_replay": False,
        },
        "gate": {
            "feature": GATE_FEATURE,
            "value": gate_value,
            "threshold": GATE_MAX,
            "on": gate_on,
        },
        "fit": fit,
        "source_assisted_p5_p9": val,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p5_p9_replay_is_source_assisted": True,
            "p10_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "whole_game_solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "competition_quota_spent_by_r330": 0,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "game": a.game,
        "gate": out["gate"],
        "replay": val,
        "verdict": verdict,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
