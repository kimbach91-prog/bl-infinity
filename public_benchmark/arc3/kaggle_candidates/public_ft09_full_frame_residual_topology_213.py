#!/usr/bin/env python3
"""R213: ft09 full-frame residual topology diagnostic.

R212 showed that a correct clicked-tile target color is not enough to render the
next full frame: the frozen R202+R211 composer was only 26/287 exact and the
ring2 recolor branch was 21/282 exact.  This diagnostic does not tune a new
solver on p10-p19.  It classifies the exact heldout residual topology to decide
which mechanism must be modeled next: clicked-tile shape, additional macro-tile
changes, non-macro/HUD changes, or mixtures of those.

Model fitting remains p0-p9 only. p10-p19 are read once for frozen diagnosis.
No Kaggle execution or submission occurs here.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import public_ft09_full_frame_composer_212 as c212
import public_ft09_ring2_relational_gate_211 as r211

RUNG = 213
GAME = "ft09-0d8bbf25"


def pnum(path: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", path.name)
    return int(m.group(1)) if m else -1


def six_components(board):
    """Return unique solid 6x6 same-color 4-connected component boxes."""
    h, w = len(board), len(board[0])
    seen = set()
    boxes = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen:
                continue
            v = board[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            pts = []
            while stack:
                rr, cc = stack.pop()
                pts.append((rr, cc))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and board[nr][nc] == v:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            if len(pts) != 36:
                continue
            rs = [x for x, _ in pts]
            cs = [y for _, y in pts]
            r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
            if (r1 - r0 + 1, c1 - c0 + 1) == (6, 6):
                boxes.append((r0, c0, r1, c1, v))
    return boxes


def coords_in_box(box):
    r0, c0, r1, c1 = box[:4]
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}


def changed_coords(a, b):
    return {(r, c) for r in range(len(a)) for c in range(len(a[0])) if a[r][c] != b[r][c]}


def bbox_of(coords):
    if not coords:
        return None
    rs = [r for r, _ in coords]
    cs = [c for _, c in coords]
    return [min(rs), min(cs), max(rs), max(cs)]


def build_train_nonmacro_mask(paths):
    counts = Counter()
    total = 0
    for p in paths:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            before, after = row["before"], row["after"]
            macro = set()
            for box in six_components(before):
                macro |= coords_in_box(box)
            for xy in changed_coords(before, after) - macro:
                counts[xy] += 1
                total += 1
    return counts, total


def classify(row, pred, train_nonmacro_coords):
    before, after = row["before"], row["after"]
    click = coords_in_box(row["bbox"])
    macro_boxes = six_components(before)
    macro_union = set()
    for b in macro_boxes:
        macro_union |= coords_in_box(b)

    actual_change = changed_coords(before, after)
    residual = changed_coords(pred, after)
    inside_resid = residual & click
    outside_resid = residual - click
    outside_macro = outside_resid & (macro_union - click)
    nonmacro = outside_resid - macro_union

    changed_other_components = 0
    changed_other_boxes = []
    for b in macro_boxes:
        cells = coords_in_box(b)
        if cells & click:
            continue
        if actual_change & cells:
            changed_other_components += 1
            if len(changed_other_boxes) < 12:
                changed_other_boxes.append(list(b[:4]))

    r0, c0, r1, c1, _ = row["bbox"]
    clicked_solid = all(after[r][c] == row["target"] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))
    train_seen_nonmacro = sum(1 for xy in nonmacro if xy in train_nonmacro_coords)
    train_seen_fraction = train_seen_nonmacro / len(nonmacro) if nonmacro else 1.0

    if not residual:
        category = "EXACT"
    elif inside_resid and not outside_resid:
        category = "CLICKED_SHAPE_ONLY"
    elif outside_macro and not nonmacro and not inside_resid:
        category = "EXTRA_MACRO_ONLY"
    elif nonmacro and not outside_macro and not inside_resid:
        category = "NONMACRO_HUD_ONLY"
    elif not inside_resid and (outside_macro or nonmacro):
        category = "EXTRA_MACRO_PLUS_HUD"
    else:
        category = "MIXED_WITH_CLICKED_SHAPE"

    return {
        "category": category,
        "residual_cells": len(residual),
        "inside_clicked_residual_cells": len(inside_resid),
        "outside_macro_residual_cells": len(outside_macro),
        "nonmacro_residual_cells": len(nonmacro),
        "actual_changed_cells": len(actual_change),
        "clicked_bbox_solid_target": clicked_solid,
        "changed_other_components": changed_other_components,
        "changed_other_boxes": changed_other_boxes,
        "nonmacro_train_seen_fraction": round(train_seen_fraction, 6),
        "residual_bbox": bbox_of(residual),
        "nonmacro_bbox": bbox_of(nonmacro),
    }


def run(paths):
    ps = sorted(paths, key=pnum)
    nums = [pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"exact p0..p19 required; got {nums}")

    train, held = ps[:10], ps[10:]
    ring = c212.ring2_model(train)
    nonmacro_counts, train_nonmacro_events = build_train_nonmacro_mask(train)
    train_nonmacro_coords = set(nonmacro_counts)

    stats = Counter()
    category_cells = Counter()
    examples = []
    for p in held:
        for row in c212.all_rows(p):
            if not row.get("eligible"):
                continue
            tgt = ring.get(repr((row["base"], row["ring2"])))
            if tgt is None:
                continue
            pred = c212.recolor_bbox(row["before"], row["bbox"], tgt)
            diag = classify(row, pred, train_nonmacro_coords)
            stats["predictions"] += 1
            stats["clicked_bbox_solid_target"] += int(diag["clicked_bbox_solid_target"])
            stats["has_inside_clicked_residual"] += int(diag["inside_clicked_residual_cells"] > 0)
            stats["has_outside_macro_residual"] += int(diag["outside_macro_residual_cells"] > 0)
            stats["has_nonmacro_residual"] += int(diag["nonmacro_residual_cells"] > 0)
            stats["changed_other_component_frames"] += int(diag["changed_other_components"] > 0)
            stats[f"category::{diag['category']}"] += 1
            category_cells[diag["category"]] += diag["residual_cells"]
            if diag["category"] != "EXACT" and len(examples) < 60:
                examples.append({
                    "trace": row["path"], "p": row["p"], "step0": row["step0"],
                    "current": row["current"], "target": row["target"], **diag,
                })

    n = stats["predictions"]
    categories = {
        k.split("::", 1)[1]: {"frames": v, "fraction": round(v / n, 6) if n else 0.0,
                                "residual_cells": category_cells[k.split("::", 1)[1]]}
        for k, v in stats.items() if k.startswith("category::")
    }
    dominant = max(categories, key=lambda k: categories[k]["frames"]) if categories else None

    return {
        "schema": "deus/arc3-ft09-full-frame-residual-topology/1",
        "rung": RUNG,
        "game": GAME,
        "source_falsifier": {
            "r212_full_frame_composer_run": 35729975139,
            "r212_ring2_branch": {"predictions": 282, "correct": 21, "wrong": 261, "exact_accuracy": 0.074468},
        },
        "train": {
            "scope": "p0-p9 only",
            "ring2_keys": len(ring),
            "nonmacro_change_coordinates": len(train_nonmacro_coords),
            "nonmacro_change_events": train_nonmacro_events,
        },
        "heldout": {
            "scope": "p10-p19 frozen diagnostic",
            "predictions": n,
            "clicked_bbox_solid_target_fraction": round(stats["clicked_bbox_solid_target"] / n, 6) if n else None,
            "inside_clicked_residual_frame_fraction": round(stats["has_inside_clicked_residual"] / n, 6) if n else None,
            "outside_macro_residual_frame_fraction": round(stats["has_outside_macro_residual"] / n, 6) if n else None,
            "nonmacro_residual_frame_fraction": round(stats["has_nonmacro_residual"] / n, 6) if n else None,
            "changed_other_component_frame_fraction": round(stats["changed_other_component_frames"] / n, 6) if n else None,
            "categories": categories,
            "dominant_residual_category": dominant,
            "examples": examples,
        },
        "next_mechanism": {
            "selected_by": "dominant exact residual topology only",
            "family": dominant,
            "rule": "repair only the discriminating residual mechanism; do not alter frozen R211 target-color anchor",
        },
        "promotion": {
            "solver_promotion": False,
            "kaggle_packaging": False,
            "reason": "diagnostic-only residual decomposition after R212 full-frame falsifier",
        },
        "truth": {
            "public_trace_only": True,
            "p0_p9_only_for_model_fit_and_train_mask": True,
            "p10_p19_used_only_for_frozen_diagnosis": True,
            "heldout_never_updates_models": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = run(a.input)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "heldout": {k: d["heldout"][k] for k in (
            "predictions", "clicked_bbox_solid_target_fraction",
            "inside_clicked_residual_frame_fraction", "outside_macro_residual_frame_fraction",
            "nonmacro_residual_frame_fraction", "changed_other_component_frame_fraction",
            "dominant_residual_category")},
        "categories": d["heldout"]["categories"],
        "next_mechanism": d["next_mechanism"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
