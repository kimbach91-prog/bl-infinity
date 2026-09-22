#!/usr/bin/env python3
"""Rung 173: characterize R172 pre-action renderer error topology.

This does not change the prediction rule or claim a solver gain. It replays the
same prior-only R172 renderer on exact-state misses, then AFTER each prediction
uses the current outcome to classify wrong cells. The goal is to select the next
representation from evidence rather than blind-retrying mask thresholds.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172

RUNG = 173


def unique_program(bank: Counter[str], support: int = 1) -> str | None:
    if len(bank) != 1:
        return None
    p, n = next(iter(bank.items()))
    return p if n >= support else None


def q90(xs: list[int]) -> int | None:
    if not xs:
        return None
    ys = sorted(xs)
    return ys[min(len(ys) - 1, int(0.9 * (len(ys) - 1)))]


def analyze_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_bank: dict[str, Counter[str]] = defaultdict(Counter)
    shift_votes: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    mask_votes: dict[str, dict[tuple[int, int], Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    counts = Counter()
    action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    error_sizes: list[int] = []
    action_error_sizes: dict[str, list[int]] = defaultdict(list)
    confusion = Counter()
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if len(before) != len(after) or len(before[0]) != len(after[0]):
            continue

        exact_key = r160.context_exact(before, action)
        prog = unique_program(exact_bank[exact_key], 1) if exact_key in exact_bank else None
        pred_exact = r160.apply_program(before, prog) if prog is not None else None
        sh = r172.stable_shift(shift_votes[action]) if action in r172.CAMERA_ACTIONS else None
        pred = None
        if pred_exact is None and sh is not None:
            pred = r172.render(before, sh, mask_votes[action])

        if pred is not None:
            counts["raw_candidates"] += 1
            action_counts[action]["raw_candidates"] += 1
            h, w = len(before), len(before[0])
            dr, dc = sh
            nerr = 0
            for r in range(h):
                for c in range(w):
                    if pred[r][c] == after[r][c]:
                        continue
                    nerr += 1
                    sr, sc = r - dr, c - dc
                    inb = 0 <= sr < h and 0 <= sc < w
                    if not inb:
                        predicted_mode = "boundary_preserve"
                    elif r172.is_fixed(mask_votes[action][(r, c)]):
                        predicted_mode = "fixed"
                    else:
                        predicted_mode = "world"

                    actual = after[r][c]
                    fixed = before[r][c]
                    world = before[sr][sc] if inb else None
                    if actual == fixed and (not inb or actual != world):
                        actual_mode = "fixed_like" if inb else "boundary_preserve_like"
                    elif inb and actual == world and actual != fixed:
                        actual_mode = "world_like"
                    elif inb and actual == fixed and actual == world:
                        actual_mode = "ambiguous_equal"
                    else:
                        actual_mode = "dynamic_other"
                    counts[f"error_{actual_mode}"] += 1
                    action_counts[action][f"error_{actual_mode}"] += 1
                    confusion[f"{predicted_mode}->{actual_mode}"] += 1
            if nerr == 0:
                counts["exact_frames"] += 1
                action_counts[action]["exact_frames"] += 1
            else:
                counts["wrong_frames"] += 1
                action_counts[action]["wrong_frames"] += 1
                error_sizes.append(nerr)
                action_error_sizes[action].append(nerr)
                if nerr <= 4:
                    counts["wrong_frames_le4_cells"] += 1
                if nerr <= 16:
                    counts["wrong_frames_le16_cells"] += 1

        # Post-outcome learning, identical in order to R172.
        exact_bank[exact_key][r160.program(before, after)] += 1
        if action in r172.CAMERA_ACTIONS:
            changed = sum(before[r][c] != after[r][c] for r in range(len(before)) for c in range(len(before[0])))
            if changed:
                best = r167.best_nonzero_shift(before, after)
                if float(best["valid_match_fraction"]) >= r172.MIN_TRANSITION_FIT:
                    obs = (int(best["dr"]), int(best["dc"]))
                    shift_votes[action][obs] += 1
                    r172.update_mask(before, after, obs, mask_votes[action])

    err_total = sum(v for k, v in counts.items() if k.startswith("error_"))
    modes = {k.removeprefix("error_"): int(v) for k, v in counts.items() if k.startswith("error_")}
    mode_fractions = {k: round(v / err_total, 6) for k, v in modes.items()} if err_total else {}
    return {
        "counts": dict(counts),
        "error_cells_total": err_total,
        "error_mode_counts": modes,
        "error_mode_fractions": mode_fractions,
        "error_size": {
            "median": int(median(error_sizes)) if error_sizes else None,
            "p90": q90(error_sizes),
            "max": max(error_sizes) if error_sizes else None,
        },
        "per_action": {
            a: {
                "counts": dict(c),
                "error_size_median": int(median(action_error_sizes[a])) if action_error_sizes[a] else None,
                "error_size_p90": q90(action_error_sizes[a]),
            }
            for a, c in action_counts.items()
        },
        "prediction_actual_confusion": dict(confusion),
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [analyze_trace(base.load_events(p)) for p in paths]
    totals = Counter()
    conf = Counter()
    sizes = []
    for p in parts:
        totals.update(p["counts"])
        conf.update(p["prediction_actual_confusion"])
        # Per-trace summaries are enough for topology; use weighted cell fractions below.
    error_modes = {k.removeprefix("error_"): int(v) for k, v in totals.items() if k.startswith("error_")}
    err_total = sum(error_modes.values())
    fractions = {k: round(v / err_total, 6) for k, v in error_modes.items()} if err_total else {}
    dominant = max(error_modes, key=error_modes.get) if error_modes else "none"
    if dominant in {"fixed_like", "boundary_preserve_like"}:
        recommendation = "LEARN_STRUCTURAL_SCREEN_FIXED_AND_BOUNDARY_SELECTOR_NOT_ABSOLUTE_COORDINATE_MASK"
    elif dominant == "dynamic_other":
        recommendation = "MODEL_DYNAMIC_AGENT_OR_PATH_DEPENDENT_OVERLAY_STATE"
    elif dominant == "world_like":
        recommendation = "REDUCE_FALSE_FIXED_MASK_WITH_OBJECT_OR_REGION_CONSISTENCY"
    else:
        recommendation = "MIXED_RESIDUAL_REQUIRES_REGION_OR_OBJECT_DECOMPOSITION"
    return {
        "schema": "deus/arc3-public-world-overlay-error-topology/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_POSTSCORE_ERROR_TOPOLOGY_DIAGNOSTIC",
        "representation_change_from_rung172": {
            "changed": True,
            "change": "do not retry renderer thresholds; classify its post-prediction wrong cells into fixed/boundary/world/dynamic modes to choose the next causal representation",
        },
        "source_grounding": {"public_trace_repo": base.TUFA_REPO, "public_trace_commit": base.TUFA_COMMIT, "clean_room_implementation": True},
        "aggregate": {
            "raw_candidates": int(totals["raw_candidates"]),
            "exact_frames": int(totals["exact_frames"]),
            "wrong_frames": int(totals["wrong_frames"]),
            "wrong_frames_le4_cells": int(totals["wrong_frames_le4_cells"]),
            "wrong_frames_le16_cells": int(totals["wrong_frames_le16_cells"]),
            "error_cells_total": err_total,
            "error_mode_counts": error_modes,
            "error_mode_fractions": fractions,
            "dominant_error_mode": dominant,
            "prediction_actual_confusion": dict(conf),
            "per_trace": parts,
        },
        "diagnostic_gate": "PREQUENTIAL_RENDERER_ERROR_TOPOLOGY_CHARACTERIZED",
        "recommendation": recommendation,
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "r172_predictions_are_preaction_prior_only": True,
            "current_outcome_used_only_after_prediction_for_error_classification": True,
            "outcome_assisted_analysis": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if not args.input:
        raise SystemExit("at least one --input is required")
    d = run(args.input)
    text = json.dumps(d, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
