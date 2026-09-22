#!/usr/bin/env python3
"""Rung 169: prequential inverse-action temporal full-frame renderer.

R168 showed global scroll structure but prefix-atlas completion produced only five
raw opportunities and all five were wrong. This rung changes representation
again: exploit reversible navigation history rather than trying to synthesize
unknown border cells.

On an exact-state Markov-cache miss, if the current action is the inverse of the
immediately previous movement action, the board visible immediately before that
previous action is a source-shaped candidate for the current next board. This is
pre-action/prefix-only. The raw candidate is shadow-tested per ordered inverse
pair; it may emit only after >=2 prior exact shadow successes and zero failures.
Current outcome is ingested only after prediction/scoring.

Public pinned trace replay only. Any gain is source-assisted temporal replay, not
independent generalization and not a Kaggle score.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160

RUNG = 169
MIN_PRIOR_SHADOW_OK = 2
INVERSE = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
Grid = list[list[int]]


def unique_program(bank: Counter[str], support: int = 1) -> str | None:
    if len(bank) != 1:
        return None
    p, n = next(iter(bank.items()))
    return p if n >= support else None


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_bank: dict[str, Counter[str]] = defaultdict(Counter)
    shadow_ok = Counter()
    shadow_wrong = Counter()
    baseline = {"predictions": 0, "correct": 0, "wrong": 0}
    candidate = {
        "predictions": 0,
        "correct": 0,
        "wrong": 0,
        "added_predictions_vs_exact": 0,
        "added_correct_vs_exact": 0,
        "added_wrong_vs_exact": 0,
        "raw_inverse_opportunities": 0,
        "raw_shadow_correct": 0,
        "raw_shadow_wrong": 0,
        "qualified_opportunities": 0,
    }

    # History at action boundaries. prev_before is the board before prev_action;
    # prev_after is current visible board before this action.
    prev_action: str | None = None
    prev_before: Grid | None = None
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
            prev_action = action
            prev_before = [row[:] for row in before]
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

        raw = None
        pair = None
        if (
            pred_exact is None
            and prev_action in INVERSE
            and INVERSE[prev_action] == action
            and prev_before is not None
            and len(prev_before) == len(before)
            and len(prev_before[0]) == len(before[0])
        ):
            raw = [row[:] for row in prev_before]
            pair = f"{prev_action}->{action}"

        if raw is not None and pair is not None:
            candidate["raw_inverse_opportunities"] += 1
            qualified = shadow_ok[pair] >= MIN_PRIOR_SHADOW_OK and shadow_wrong[pair] == 0
            if qualified:
                candidate["qualified_opportunities"] += 1
                candidate["predictions"] += 1
                candidate["added_predictions_vs_exact"] += 1
                if raw == after:
                    candidate["correct"] += 1
                    candidate["added_correct_vs_exact"] += 1
                else:
                    candidate["wrong"] += 1
                    candidate["added_wrong_vs_exact"] += 1
            # Update reliability only after prediction/scoring decision is fixed.
            if raw == after:
                candidate["raw_shadow_correct"] += 1
                shadow_ok[pair] += 1
            else:
                candidate["raw_shadow_wrong"] += 1
                shadow_wrong[pair] += 1

        # Post-outcome exact cache learning.
        exact_bank[exact_key][r160.program(before, after)] += 1
        prev_action = action
        prev_before = [row[:] for row in before]

    baseline["accuracy"] = round(baseline["correct"] / baseline["predictions"], 6) if baseline["predictions"] else None
    candidate["accuracy"] = round(candidate["correct"] / candidate["predictions"], 6) if candidate["predictions"] else None
    candidate["strict_zero_error"] = bool(candidate["predictions"] and candidate["wrong"] == 0)
    return {
        "baseline_exact_markov": baseline,
        "inverse_temporal_candidate": candidate,
        "shadow_ok_by_pair": dict(shadow_ok),
        "shadow_wrong_by_pair": dict(shadow_wrong),
    }


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    bpred = sum(p["baseline_exact_markov"]["predictions"] for p in parts)
    bcor = sum(p["baseline_exact_markov"]["correct"] for p in parts)
    bwrong = sum(p["baseline_exact_markov"]["wrong"] for p in parts)
    fields = [
        "predictions", "correct", "wrong", "added_predictions_vs_exact",
        "added_correct_vs_exact", "added_wrong_vs_exact", "raw_inverse_opportunities",
        "raw_shadow_correct", "raw_shadow_wrong", "qualified_opportunities",
    ]
    c = {k: sum(p["inverse_temporal_candidate"][k] for p in parts) for k in fields}
    c["accuracy"] = round(c["correct"] / c["predictions"], 6) if c["predictions"] else None
    c["strict_zero_error"] = bool(c["predictions"] and c["wrong"] == 0)
    addc = [p["inverse_temporal_candidate"]["added_correct_vs_exact"] for p in parts]
    addw = [p["inverse_temporal_candidate"]["added_wrong_vs_exact"] for p in parts]
    c["per_trace_added_correct"] = addc
    c["per_trace_added_wrong"] = addw
    c["zero_error_nonzero_p0_p10"] = bool(
        len(parts) >= 2 and addc[0] > 0 and addc[1] > 0 and
        addw[0] == 0 and addw[1] == 0 and c["wrong"] == 0
    )
    return {
        "baseline_exact_markov": {
            "predictions": bpred,
            "correct": bcor,
            "wrong": bwrong,
            "accuracy": round(bcor / bpred, 6) if bpred else None,
            "per_trace_predictions": [p["baseline_exact_markov"]["predictions"] for p in parts],
            "per_trace_correct": [p["baseline_exact_markov"]["correct"] for p in parts],
            "per_trace_wrong": [p["baseline_exact_markov"]["wrong"] for p in parts],
        },
        "inverse_temporal_candidate": c,
        "per_trace": parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    agg = aggregate(parts)
    c = agg["inverse_temporal_candidate"]
    gate = (
        "ZERO_ERROR_P0_P10_PREQUENTIAL_INVERSE_TEMPORAL_GAIN"
        if c["zero_error_nonzero_p0_p10"]
        else "NO_STRICT_PREQUENTIAL_INVERSE_TEMPORAL_GAIN"
    )
    return {
        "schema": "deus/arc3-public-inverse-action-temporal-renderer/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_TEMPORAL_REVERSIBILITY_FULLFRAME_DIAGNOSTIC",
        "representation_change_from_rung168": {
            "changed": True,
            "change": "replace prefix-atlas completion with reversible temporal-history candidate: an immediate inverse movement predicts the board visible before the prior move, guarded by pair-specific shadow reliability",
        },
        "parameters": {"min_prior_shadow_ok": MIN_PRIOR_SHADOW_OK},
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "clean_room_implementation": True,
        },
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
