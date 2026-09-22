#!/usr/bin/env python3
"""R214: ft09 deterministic HUD/nonmacro overlay, CV-selected on p0-p9.

R213 falsified the naive full-frame composer and localized 251/282 ring2 frames
(89.0%) to NONMACRO_HUD_ONLY residuals.  Preserve the frozen R211 clicked-tile
target-color mechanism and repair only that residual family.

This rung learns sparse nonmacro screen-coordinate dynamics from p0-p9 only.
A leave-one-trace-out CV on p0-p9 selects one of a few mechanistically distinct
pre-action keys.  The selected overlay is then frozen and composed with R211 on
p10-p19.  p10-p19 never select or update policy/model parameters.

Lineage was informed by earlier public-heldout diagnostics, so this remains
iterative public research, not independent generalization or Kaggle evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as c212
import public_ft09_full_frame_residual_topology_213 as r213
import public_ft09_ring2_relational_gate_211 as r211

RUNG = 214
GAME = "ft09-0d8bbf25"
FAMILIES = ("coord_value", "coord_patch3", "coord_patch5")


def pnum(path: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", path.name)
    return int(m.group(1)) if m else -1


def patch(board, r, c, radius):
    h, w = len(board), len(board[0])
    out = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            rr, cc = r + dr, c + dc
            out.append(board[rr][cc] if 0 <= rr < h and 0 <= cc < w else -1)
    return tuple(out)


def key_for(family, board, r, c):
    if family == "coord_value":
        return (r, c, board[r][c])
    if family == "coord_patch3":
        return (r, c, patch(board, r, c, 1))
    if family == "coord_patch5":
        return (r, c, patch(board, r, c, 2))
    raise ValueError(family)


def macro_union(board):
    out = set()
    for b in r213.six_components(board):
        out |= r213.coords_in_box(b)
    return out


def candidate_coords(paths):
    coords = set()
    for p in paths:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            mac = macro_union(row["before"])
            coords |= r213.changed_coords(row["before"], row["after"]) - mac
    return coords


def fit_overlay(paths, family):
    coords = candidate_coords(paths)
    obs = defaultdict(Counter)
    for p in paths:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            before, after = row["before"], row["after"]
            h, w = len(before), len(before[0])
            mac = macro_union(before)
            for r, c in coords:
                if not (0 <= r < h and 0 <= c < w) or (r, c) in mac:
                    continue
                obs[repr(key_for(family, before, r, c))][after[r][c]] += 1
    tab = {k: next(iter(v)) for k, v in obs.items() if len(v) == 1}
    return coords, tab, obs


def apply_overlay(board, coords, table, family):
    out = [row[:] for row in board]
    h, w = len(board), len(board[0])
    mac = macro_union(board)
    predicted_changes = 0
    for r, c in coords:
        if not (0 <= r < h and 0 <= c < w) or (r, c) in mac:
            continue
        pred = table.get(repr(key_for(family, board, r, c)))
        if pred is None or pred == board[r][c]:
            continue
        out[r][c] = int(pred)
        predicted_changes += 1
    return out, predicted_changes


def hud_eval(paths, coords, table, family):
    s = Counter()
    examples = []
    for p in paths:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            s["eligible"] += 1
            pred, nchange = apply_overlay(row["before"], coords, table, family)
            mac = macro_union(row["before"])
            actual = r213.changed_coords(row["before"], row["after"]) - mac
            residual = {(r, c) for r in range(len(pred)) for c in range(len(pred[0]))
                        if (r, c) not in mac and pred[r][c] != row["after"][r][c]}
            predicted = {(r, c) for r, c in coords
                         if 0 <= r < len(pred) and 0 <= c < len(pred[0]) and (r, c) not in mac
                         and pred[r][c] != row["before"][r][c]}
            s["actual_changed_cells"] += len(actual)
            s["predicted_changed_cells"] += len(predicted)
            s["residual_cells"] += len(residual)
            s["false_positive_cells"] += len(predicted - actual)
            s["missed_changed_cells"] += len(actual - predicted)
            if not residual:
                s["exact_frames"] += 1
            elif len(examples) < 20:
                examples.append({"trace": row["path"], "p": row["p"], "step0": row["step0"],
                                 "actual_changes": len(actual), "predicted_changes": nchange,
                                 "residual_cells": len(residual),
                                 "false_positive_cells": len(predicted - actual),
                                 "missed_changed_cells": len(actual - predicted)})
    e = s["eligible"]
    return {**dict(s), "exact_frame_fraction": round(s["exact_frames"] / e, 6) if e else None,
            "examples": examples}


def cv_family(train_paths, family):
    total = Counter()
    folds = []
    for hold in range(10):
        fit_paths = [p for i, p in enumerate(train_paths) if i != hold]
        test_paths = [train_paths[hold]]
        coords, tab, _ = fit_overlay(fit_paths, family)
        m = hud_eval(test_paths, coords, tab, family)
        for k in ("eligible", "exact_frames", "actual_changed_cells", "predicted_changed_cells",
                  "residual_cells", "false_positive_cells", "missed_changed_cells"):
            total[k] += m.get(k, 0)
        folds.append({"hold": hold, **{k: m.get(k, 0) for k in (
            "eligible", "exact_frames", "residual_cells", "false_positive_cells", "missed_changed_cells")}})
    e = total["eligible"]
    return {**dict(total), "exact_frame_fraction": round(total["exact_frames"] / e, 6) if e else None,
            "folds": folds}


def selection_key(item):
    family, m = item
    return (m.get("false_positive_cells", 0), m.get("residual_cells", 0),
            -m.get("exact_frames", 0), m.get("missed_changed_cells", 0), family)


def full_compose_eval(paths, ring_table, coords, overlay_table, family):
    s = Counter()
    branches = Counter()
    wrong = []
    for p in paths:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            s["eligible"] += 1
            target = ring_table.get(repr((row["base"], row["ring2"])))
            if target is None:
                s["abstain"] += 1
                continue
            clicked = c212.recolor_bbox(row["before"], row["bbox"], target)
            pred, hud_changes = apply_overlay(clicked, coords, overlay_table, family)
            s["predictions"] += 1
            s["hud_predicted_changes"] += hud_changes
            if pred == row["after"]:
                s["correct"] += 1
            else:
                s["wrong"] += 1
                mac = macro_union(row["before"])
                resid = r213.changed_coords(pred, row["after"])
                inside = resid & r213.coords_in_box(row["bbox"])
                nonmacro = resid - mac
                extra_macro = resid & (mac - r213.coords_in_box(row["bbox"]))
                if inside:
                    branches["clicked_shape"] += 1
                if nonmacro:
                    branches["nonmacro"] += 1
                if extra_macro:
                    branches["extra_macro"] += 1
                if len(wrong) < 30:
                    wrong.append({"trace": row["path"], "p": row["p"], "step0": row["step0"],
                                  "residual_cells": len(resid), "inside_clicked": len(inside),
                                  "nonmacro": len(nonmacro), "extra_macro": len(extra_macro)})
    p = s["predictions"]
    e = s["eligible"]
    return {**dict(s), "exact_accuracy": round(s["correct"] / p, 6) if p else None,
            "coverage": round(p / e, 6) if e else 0.0,
            "residual_frame_classes": dict(branches), "wrong_examples": wrong}


def run(paths):
    ps = sorted(paths, key=pnum)
    if [pnum(p) for p in ps] != list(range(20)):
        raise ValueError("exact p0..p19 required")
    train, held = ps[:10], ps[10:]

    cv = {fam: cv_family(train, fam) for fam in FAMILIES}
    selected = min(cv.items(), key=selection_key)[0]
    coords, overlay, obs = fit_overlay(train, selected)
    ring = c212.ring2_model(train)
    heldout = full_compose_eval(held, ring, coords, overlay, selected)

    r212_correct = 21
    strict_gain = heldout.get("correct", 0) - r212_correct
    gate = bool(heldout.get("predictions", 0) >= 100 and heldout.get("wrong", 0) == 0
                and (heldout.get("exact_accuracy") or 0) >= 0.99)
    useful = bool(strict_gain > 0 and (heldout.get("exact_accuracy") or 0) > 0.074468)

    return {
        "schema": "deus/arc3-ft09-hud-overlay-cv/1", "rung": RUNG, "game": GAME,
        "derivation": "R213 dominant residual = NONMACRO_HUD_ONLY (251/282 frames)",
        "protocol": {"selection": "leave-one-trace-out CV on p0-p9 only",
                     "fit": "selected deterministic sparse coordinate dynamics on all p0-p9",
                     "heldout": "single frozen p10-p19 full-frame compose with R211; no updates"},
        "cv": cv, "selected_family": selected,
        "train": {"candidate_nonmacro_coordinates": len(coords), "deterministic_keys": len(overlay),
                  "observed_keys": len(obs), "ring2_keys": len(ring)},
        "heldout": heldout,
        "reference": {"r212_ring2_full_frame": {"predictions": 282, "correct": 21, "wrong": 261,
                                                   "exact_accuracy": 0.074468},
                      "strict_exact_gain_vs_r212": strict_gain},
        "mechanism_gain": useful,
        "full_frame_gate_pass": gate,
        "promotion": {"solver_promotion": False, "kaggle_packaging": False,
                      "next_gate": "if gain, diagnose only remaining full-frame residual classes; if no gain, close coordinate-HUD family"},
        "truth": {"public_trace_only": True,
                  "policy_parameters_selected_from_p0_p9_cv_only": True,
                  "p10_p19_never_select_policy": True,
                  "heldout_never_updates_models": True,
                  "lineage_previously_informed_by_public_heldout": True,
                  "independent_generalization_claim": False,
                  "kaggle_execution": False,
                  "submission_quota_spent": False,
                  "owner_score_claim": False},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = run(a.input)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"selected_family": d["selected_family"],
                      "cv": {k: {x: v.get(x) for x in ("exact_frames", "eligible", "residual_cells", "false_positive_cells", "missed_changed_cells", "exact_frame_fraction")} for k, v in d["cv"].items()},
                      "heldout": {k: d["heldout"].get(k) for k in ("predictions", "correct", "wrong", "exact_accuracy", "coverage", "hud_predicted_changes")},
                      "gain": d["reference"]["strict_exact_gain_vs_r212"],
                      "mechanism_gain": d["mechanism_gain"],
                      "gate": d["full_frame_gate_pass"]}, sort_keys=True))


if __name__ == "__main__":
    main()
