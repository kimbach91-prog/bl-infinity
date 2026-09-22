#!/usr/bin/env python3
"""Rung 172: prequential world-transport + screen-overlay renderer.

R171 found that reliable vertical transitions are ~96.9% shifted world, while
~99.2% of the residual is screen-fixed and ~99.4% of incoming boundary cells
preserve the previous screen value. R172 turns that structural result into an
executable pre-action full-frame hypothesis.

For each trace, learn only from PRIOR outcomes:
  * a stable UP/DOWN whole-screen shift;
  * per-action screen coordinates that consistently behave as screen-fixed
    rather than shifted-world.

At an exact-state cache miss, construct the next frame before seeing the current
outcome: preserve the current frame by default (including incoming boundary),
transport in-bounds world cells by the learned shift, and keep coordinates whose
prior evidence strongly identifies them as screen-fixed. Raw candidates are
shadow-tested and can emit only after two prior exact successes and zero prior
failures for that action.

This remains source-assisted public replay, not independent generalization and
not a Kaggle score. The current outcome is used only for scoring and post-action
learning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167

RUNG = 172
CAMERA_ACTIONS = {"UP", "DOWN"}
MIN_SHIFT_SUPPORT = 3
MIN_SHIFT_DOMINANT_FRACTION = 0.90
MIN_TRANSITION_FIT = 0.95
MIN_MASK_SUPPORT = 3
MIN_FIXED_FRACTION = 0.95
MIN_PRIOR_SHADOW_OK = 2
Grid = list[list[int]]


def unique_program(bank: Counter[str], support: int = 1) -> str | None:
    if len(bank) != 1:
        return None
    p, n = next(iter(bank.items()))
    return p if n >= support else None


def stable_shift(votes: Counter[tuple[int, int]]) -> tuple[int, int] | None:
    total = sum(votes.values())
    if total < MIN_SHIFT_SUPPORT:
        return None
    sh, n = votes.most_common(1)[0]
    if n < MIN_SHIFT_SUPPORT or n / total < MIN_SHIFT_DOMINANT_FRACTION:
        return None
    return sh


def is_fixed(mask_votes: Counter[str]) -> bool:
    fixed = int(mask_votes["fixed"])
    world = int(mask_votes["world"])
    n = fixed + world
    return n >= MIN_MASK_SUPPORT and fixed / n >= MIN_FIXED_FRACTION


def render(before: Grid, shift: tuple[int, int], mask: dict[tuple[int, int], Counter[str]]) -> Grid:
    dr, dc = shift
    h, w = len(before), len(before[0])
    # R171: incoming boundary overwhelmingly preserves screen value, so copy
    # current frame first and overwrite only transported in-bounds world cells.
    out = [row[:] for row in before]
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            if is_fixed(mask[(r, c)]):
                continue
            out[r][c] = before[sr][sc]
    return out


def update_mask(before: Grid, after: Grid, shift: tuple[int, int], mask: dict[tuple[int, int], Counter[str]]) -> None:
    dr, dc = shift
    h, w = len(before), len(before[0])
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            a = after[r][c]
            fixed = before[r][c]
            world = before[sr][sc]
            # Ignore ambiguous pixels where both hypotheses predict same value.
            if a == fixed and a != world:
                mask[(r, c)]["fixed"] += 1
            elif a == world and a != fixed:
                mask[(r, c)]["world"] += 1


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_bank: dict[str, Counter[str]] = defaultdict(Counter)
    shift_votes: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    mask_votes: dict[str, dict[tuple[int, int], Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    shadow_ok = Counter()
    shadow_wrong = Counter()

    baseline = {"predictions": 0, "correct": 0, "wrong": 0}
    cand = Counter()
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
        if pred_exact is not None:
            baseline["predictions"] += 1
            if pred_exact == after:
                baseline["correct"] += 1
            else:
                baseline["wrong"] += 1

        pred = None
        sh = stable_shift(shift_votes[action]) if action in CAMERA_ACTIONS else None
        if pred_exact is None and sh is not None:
            cand["stable_shift_opportunities"] += 1
            pred = render(before, sh, mask_votes[action])

        if pred is not None:
            cand["raw_candidates"] += 1
            if pred == after:
                cand["raw_correct"] += 1
            else:
                cand["raw_wrong"] += 1
            qualified = shadow_ok[action] >= MIN_PRIOR_SHADOW_OK and shadow_wrong[action] == 0
            if qualified:
                cand["qualified_predictions"] += 1
                if pred == after:
                    cand["qualified_correct"] += 1
                else:
                    cand["qualified_wrong"] += 1
            # Shadow result is learned only after the pre-action prediction.
            if pred == after:
                shadow_ok[action] += 1
            else:
                shadow_wrong[action] += 1

        # Post-outcome learning only.
        exact_bank[exact_key][r160.program(before, after)] += 1
        if action in CAMERA_ACTIONS:
            changed = sum(
                before[r][c] != after[r][c]
                for r in range(len(before))
                for c in range(len(before[0]))
            )
            if changed:
                best = r167.best_nonzero_shift(before, after)
                if float(best["valid_match_fraction"]) >= MIN_TRANSITION_FIT:
                    obs = (int(best["dr"]), int(best["dc"]))
                    shift_votes[action][obs] += 1
                    update_mask(before, after, obs, mask_votes[action])

    baseline["accuracy"] = round(baseline["correct"] / baseline["predictions"], 6) if baseline["predictions"] else None
    out = dict(cand)
    for k in ["stable_shift_opportunities", "raw_candidates", "raw_correct", "raw_wrong", "qualified_predictions", "qualified_correct", "qualified_wrong"]:
        out.setdefault(k, 0)
    out["raw_accuracy"] = round(out["raw_correct"] / out["raw_candidates"], 6) if out["raw_candidates"] else None
    out["qualified_accuracy"] = round(out["qualified_correct"] / out["qualified_predictions"], 6) if out["qualified_predictions"] else None
    out["qualified_strict_zero_error"] = bool(out["qualified_predictions"] and out["qualified_wrong"] == 0)
    out["learned_fixed_coordinates"] = {
        a: sum(1 for v in coords.values() if is_fixed(v)) for a, coords in mask_votes.items()
    }
    return {
        "baseline_exact_markov": baseline,
        "world_overlay_renderer": out,
        "shadow_ok_by_action": dict(shadow_ok),
        "shadow_wrong_by_action": dict(shadow_wrong),
        "final_shift_votes": {a: [[list(k), int(v)] for k, v in c.most_common()] for a, c in shift_votes.items()},
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    bp = sum(p["baseline_exact_markov"]["predictions"] for p in parts)
    bc = sum(p["baseline_exact_markov"]["correct"] for p in parts)
    bw = sum(p["baseline_exact_markov"]["wrong"] for p in parts)
    fields = ["stable_shift_opportunities", "raw_candidates", "raw_correct", "raw_wrong", "qualified_predictions", "qualified_correct", "qualified_wrong"]
    c = {k: sum(int(p["world_overlay_renderer"].get(k, 0)) for p in parts) for k in fields}
    c["raw_accuracy"] = round(c["raw_correct"] / c["raw_candidates"], 6) if c["raw_candidates"] else None
    c["qualified_accuracy"] = round(c["qualified_correct"] / c["qualified_predictions"], 6) if c["qualified_predictions"] else None
    c["qualified_strict_zero_error"] = bool(c["qualified_predictions"] and c["qualified_wrong"] == 0)
    c["per_trace_qualified_correct"] = [int(p["world_overlay_renderer"].get("qualified_correct", 0)) for p in parts]
    c["per_trace_qualified_wrong"] = [int(p["world_overlay_renderer"].get("qualified_wrong", 0)) for p in parts]
    c["per_trace_raw_correct"] = [int(p["world_overlay_renderer"].get("raw_correct", 0)) for p in parts]
    c["per_trace_raw_wrong"] = [int(p["world_overlay_renderer"].get("raw_wrong", 0)) for p in parts]
    c["zero_error_nonzero_p0_p10"] = bool(
        len(parts) >= 2
        and c["per_trace_qualified_correct"][0] > 0
        and c["per_trace_qualified_correct"][1] > 0
        and c["per_trace_qualified_wrong"][0] == 0
        and c["per_trace_qualified_wrong"][1] == 0
        and c["qualified_wrong"] == 0
    )
    gate = "ZERO_ERROR_P0_P10_PREQUENTIAL_WORLD_OVERLAY_GAIN" if c["zero_error_nonzero_p0_p10"] else "NO_STRICT_PREQUENTIAL_WORLD_OVERLAY_GAIN"
    return {
        "schema": "deus/arc3-public-world-overlay-renderer/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_WORLD_TRANSPORT_OVERLAY_FULLFRAME_DIAGNOSTIC",
        "representation_change_from_rung171": {
            "changed": True,
            "change": "turn the r171 decomposition into an executable prior-only renderer: learned vertical transport + learned screen-fixed coordinate mask + prior-screen-preserved incoming boundary",
        },
        "parameters": {
            "min_shift_support": MIN_SHIFT_SUPPORT,
            "min_shift_dominant_fraction": MIN_SHIFT_DOMINANT_FRACTION,
            "min_transition_fit": MIN_TRANSITION_FIT,
            "min_mask_support": MIN_MASK_SUPPORT,
            "min_fixed_fraction": MIN_FIXED_FRACTION,
            "min_prior_shadow_ok": MIN_PRIOR_SHADOW_OK,
        },
        "source_grounding": {"public_trace_repo": base.TUFA_REPO, "public_trace_commit": base.TUFA_COMMIT, "clean_room_implementation": True},
        "aggregate": {
            "baseline_exact_markov": {
                "predictions": bp, "correct": bc, "wrong": bw,
                "accuracy": round(bc / bp, 6) if bp else None,
                "per_trace_predictions": [p["baseline_exact_markov"]["predictions"] for p in parts],
                "per_trace_correct": [p["baseline_exact_markov"]["correct"] for p in parts],
                "per_trace_wrong": [p["baseline_exact_markov"]["wrong"] for p in parts],
            },
            "world_overlay_renderer": c,
            "per_trace": parts,
        },
        "diagnostic_gate": gate,
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_sequence_replay": True,
            "current_prediction_uses_preaction_and_prior_history_only": True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning": True,
            "full_frame_prediction_claim": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
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
