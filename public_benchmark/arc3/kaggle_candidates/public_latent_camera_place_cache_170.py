#!/usr/bin/env python3
"""Rung 170: prequential latent-camera place cache.

R167 showed strong vertical whole-board transport while r168 prefix-atlas and
r169 immediate inverse-history completion failed. This rung changes state
representation from visible-board history to a latent camera coordinate.

For each trace, camera position starts at (0,0). From prior outcomes only, the
agent learns reliable action->screen-shift deltas. For UP/DOWN, once an action
has >=3 >=95%-fit shift observations with >=90% dominant agreement, a current
action predicts the next latent camera position before seeing its outcome. If a
single exact full board has previously been observed at that latent place, that
board is a raw candidate on exact-state-cache misses. Raw place-cache candidates
are shadow-tested and can emit only after >=2 prior successes and zero failures.

After scoring, the current outcome is used to update the actual latent camera
position: identity/non-scroll transitions keep position; >=95%-fit vertical
scrolls update it by the observed shift. This is public source-assisted replay,
not independent generalization or a Kaggle score.
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

RUNG = 170
MIN_SHIFT_SUPPORT = 3
MIN_SHIFT_DOMINANT_FRACTION = 0.90
MIN_TRANSITION_FIT = 0.95
MIN_PRIOR_SHADOW_OK = 2
CAMERA_ACTIONS = {"UP", "DOWN"}
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


def unique_board_at_place(bank: Counter[str]) -> str | None:
    return unique_program(bank, 1)


def decode_board(s: str) -> Grid:
    return json.loads(s)


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_bank: dict[str, Counter[str]] = defaultdict(Counter)
    shift_votes: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    place_boards: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)
    shadow_ok = Counter()
    shadow_wrong = Counter()
    camera = (0, 0)

    baseline = {"predictions": 0, "correct": 0, "wrong": 0}
    cand = {
        "predictions": 0,
        "correct": 0,
        "wrong": 0,
        "added_predictions_vs_exact": 0,
        "added_correct_vs_exact": 0,
        "added_wrong_vs_exact": 0,
        "raw_place_opportunities": 0,
        "raw_shadow_correct": 0,
        "raw_shadow_wrong": 0,
        "qualified_opportunities": 0,
        "predicted_place_cache_hit": 0,
        "stable_shift_available": 0,
    }

    pre = events[0]
    first = base.as_grid(pre["board"])
    place_boards[camera][base.stable(first)] += 1

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
        pair = action
        predicted_camera = None
        sh = stable_shift(shift_votes[action]) if action in CAMERA_ACTIONS else None
        if sh is not None:
            cand["stable_shift_available"] += 1
            # Camera/world-origin delta has opposite sign to visible screen shift.
            predicted_camera = (camera[0] - sh[0], camera[1] - sh[1])
            if pred_exact is None and predicted_camera in place_boards:
                s = unique_board_at_place(place_boards[predicted_camera])
                if s is not None:
                    pred = decode_board(s)
                    cand["predicted_place_cache_hit"] += 1

        if pred is not None:
            cand["raw_place_opportunities"] += 1
            qualified = shadow_ok[pair] >= MIN_PRIOR_SHADOW_OK and shadow_wrong[pair] == 0
            if qualified:
                cand["qualified_opportunities"] += 1
                cand["predictions"] += 1
                cand["added_predictions_vs_exact"] += 1
                if pred == after:
                    cand["correct"] += 1
                    cand["added_correct_vs_exact"] += 1
                else:
                    cand["wrong"] += 1
                    cand["added_wrong_vs_exact"] += 1
            if pred == after:
                cand["raw_shadow_correct"] += 1
                shadow_ok[pair] += 1
            else:
                cand["raw_shadow_wrong"] += 1
                shadow_wrong[pair] += 1

        # Post-outcome learning only.
        exact_bank[exact_key][r160.program(before, after)] += 1
        actual_camera = camera
        changed = sum(
            before[r][c] != after[r][c]
            for r in range(len(before))
            for c in range(len(before[0]))
        )
        if changed and action in CAMERA_ACTIONS:
            best = r167.best_nonzero_shift(before, after)
            if float(best["valid_match_fraction"]) >= MIN_TRANSITION_FIT:
                obs = (int(best["dr"]), int(best["dc"]))
                shift_votes[action][obs] += 1
                actual_camera = (camera[0] - obs[0], camera[1] - obs[1])
        camera = actual_camera
        place_boards[camera][base.stable(after)] += 1

    baseline["accuracy"] = round(baseline["correct"] / baseline["predictions"], 6) if baseline["predictions"] else None
    cand["accuracy"] = round(cand["correct"] / cand["predictions"], 6) if cand["predictions"] else None
    cand["strict_zero_error"] = bool(cand["predictions"] and cand["wrong"] == 0)
    return {
        "baseline_exact_markov": baseline,
        "latent_camera_place_candidate": cand,
        "shadow_ok_by_action": dict(shadow_ok),
        "shadow_wrong_by_action": dict(shadow_wrong),
        "final_shift_votes": {a: [[list(k), int(v)] for k, v in c.most_common()] for a, c in shift_votes.items()},
        "unique_latent_places": len(place_boards),
        "ambiguous_places": sum(1 for c in place_boards.values() if len(c) != 1),
    }


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    bp = sum(p["baseline_exact_markov"]["predictions"] for p in parts)
    bc = sum(p["baseline_exact_markov"]["correct"] for p in parts)
    bw = sum(p["baseline_exact_markov"]["wrong"] for p in parts)
    fields = [
        "predictions", "correct", "wrong", "added_predictions_vs_exact",
        "added_correct_vs_exact", "added_wrong_vs_exact", "raw_place_opportunities",
        "raw_shadow_correct", "raw_shadow_wrong", "qualified_opportunities",
        "predicted_place_cache_hit", "stable_shift_available",
    ]
    c = {k: sum(p["latent_camera_place_candidate"][k] for p in parts) for k in fields}
    c["accuracy"] = round(c["correct"] / c["predictions"], 6) if c["predictions"] else None
    c["strict_zero_error"] = bool(c["predictions"] and c["wrong"] == 0)
    addc = [p["latent_camera_place_candidate"]["added_correct_vs_exact"] for p in parts]
    addw = [p["latent_camera_place_candidate"]["added_wrong_vs_exact"] for p in parts]
    c["per_trace_added_correct"] = addc
    c["per_trace_added_wrong"] = addw
    c["zero_error_nonzero_p0_p10"] = bool(
        len(parts) >= 2 and addc[0] > 0 and addc[1] > 0 and addw[0] == 0 and addw[1] == 0 and c["wrong"] == 0
    )
    return {
        "baseline_exact_markov": {
            "predictions": bp, "correct": bc, "wrong": bw,
            "accuracy": round(bc / bp, 6) if bp else None,
            "per_trace_predictions": [p["baseline_exact_markov"]["predictions"] for p in parts],
            "per_trace_correct": [p["baseline_exact_markov"]["correct"] for p in parts],
            "per_trace_wrong": [p["baseline_exact_markov"]["wrong"] for p in parts],
        },
        "latent_camera_place_candidate": c,
        "per_trace": parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    agg = aggregate(parts)
    c = agg["latent_camera_place_candidate"]
    gate = (
        "ZERO_ERROR_P0_P10_PREQUENTIAL_LATENT_CAMERA_PLACE_GAIN"
        if c["zero_error_nonzero_p0_p10"]
        else "NO_STRICT_PREQUENTIAL_LATENT_CAMERA_PLACE_GAIN"
    )
    return {
        "schema": "deus/arc3-public-latent-camera-place-cache/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_LATENT_CAMERA_PLACE_FULLFRAME_DIAGNOSTIC",
        "representation_change_from_rung169": {
            "changed": True,
            "change": "replace immediate inverse-board replay with a learned latent camera coordinate and prior exact-board cache at previously visited places, using only reliable prior vertical scroll deltas",
        },
        "parameters": {
            "min_shift_support": MIN_SHIFT_SUPPORT,
            "min_shift_dominant_fraction": MIN_SHIFT_DOMINANT_FRACTION,
            "min_transition_fit": MIN_TRANSITION_FIT,
            "min_prior_shadow_ok": MIN_PRIOR_SHADOW_OK,
        },
        "source_grounding": {"public_trace_repo": base.TUFA_REPO, "public_trace_commit": base.TUFA_COMMIT, "clean_room_implementation": True},
        "aggregate": agg,
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
