#!/usr/bin/env python3
"""Target-blind ARC3 A/B with an action-local temporal focus representation.

Repair rung after history2_visual_action lost target-blind outcome accuracy versus
the raw board. The new arm keeps temporal history but restores exact local grid
geometry around the object implicated by the most recent completed transition.
Focus selection uses only past/current observable state; the current action's
outcome is never used to choose the crop, cases, prompt, or representation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

import temporal_state_target_blind_ab as base

ARMS = ("raw_board_action", "history2_focus_action")
MAX_FOCUS_SIDE = 17
FOCUS_MARGIN = 3


def qbin(pos: int, size: int) -> int:
    if size <= 1:
        return 0
    return min(3, (pos * 4) // size)


def focus_representation(case: dict[str, Any]) -> dict[str, Any]:
    raw = case["representations"]["raw_board_action"]
    hist = case["representations"]["history2_visual_action"]
    board = raw["board"]
    h, w = len(board), len(board[0])
    past1 = hist.get("past1") or {}
    qset = {
        (int(x[0]), int(x[1]))
        for x in past1.get("q", [])
        if isinstance(x, list) and len(x) == 2
    }
    to_colors = {
        int(x[1])
        for x in past1.get("dc", [])
        if isinstance(x, list) and len(x) >= 2
    }

    candidates: list[tuple[int, int]] = []
    if qset and to_colors:
        for r, row in enumerate(board):
            for c, value in enumerate(row):
                if int(value) in to_colors and (qbin(r, h), qbin(c, w)) in qset:
                    candidates.append((r, c))

    if candidates:
        r0 = min(r for r, _ in candidates)
        r1 = max(r for r, _ in candidates) + 1
        c0 = min(c for _, c in candidates)
        c1 = max(c for _, c in candidates) + 1
        focus_source = "past_delta_destination_colors_in_changed_quadrants"
    elif qset:
        r0 = min(q[0] for q in qset) * h // 4
        r1 = max(1, (max(q[0] for q in qset) + 1) * h // 4)
        c0 = min(q[1] for q in qset) * w // 4
        c1 = max(1, (max(q[1] for q in qset) + 1) * w // 4)
        focus_source = "past_changed_quadrants_fallback"
    else:
        # Fail softly to a small central crop rather than re-expanding to the raw board.
        cr, cc = h // 2, w // 2
        r0, r1 = max(0, cr - 4), min(h, cr + 5)
        c0, c1 = max(0, cc - 4), min(w, cc + 5)
        focus_source = "center_fallback_no_past_spatial_signal"

    r0, r1 = max(0, r0 - FOCUS_MARGIN), min(h, r1 + FOCUS_MARGIN)
    c0, c1 = max(0, c0 - FOCUS_MARGIN), min(w, c1 + FOCUS_MARGIN)

    # Bound representation cost while keeping the inferred active region centered.
    if r1 - r0 > MAX_FOCUS_SIDE:
        mid = (r0 + r1) // 2
        r0 = max(0, min(h - MAX_FOCUS_SIDE, mid - MAX_FOCUS_SIDE // 2))
        r1 = min(h, r0 + MAX_FOCUS_SIDE)
    if c1 - c0 > MAX_FOCUS_SIDE:
        mid = (c0 + c1) // 2
        c0 = max(0, min(w - MAX_FOCUS_SIDE, mid - MAX_FOCUS_SIDE // 2))
        c1 = min(w, c0 + MAX_FOCUS_SIDE)

    crop = [list(map(int, row[c0:c1])) for row in board[r0:r1]]
    return {
        "level": hist.get("level"),
        "action": hist.get("action"),
        "visual": hist.get("visual"),
        "past1": hist.get("past1"),
        "past2": hist.get("past2"),
        "focus": {
            "source": focus_source,
            "origin_q": [qbin(r0, h), qbin(c0, w)],
            "shape": [r1 - r0, c1 - c0],
            "crop": crop,
        },
    }


def representation(case: dict[str, Any], arm: str) -> Any:
    if arm == "raw_board_action":
        return case["representations"]["raw_board_action"]
    if arm == "history2_focus_action":
        return focus_representation(case)
    raise KeyError(arm)


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    rep = base.stable(representation(case, arm))
    prompt = (
        f"Representation arm: {arm}\n"
        "Pre-action state/action representation:\n"
        + rep
        + "\nPredict the immediate NEXT-board effect of this already-chosen action. "
        "ALPHA = board visibly changes. BETA = board does not visibly change. "
        "Reply exactly one token."
    )
    return prompt, len(rep)


def summarize(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    vals = [r for r in rows if r["arm"] == arm]
    lats = [r["latency_ms"] for r in vals if r["provider_execution"]]
    return {
        "calls": len(vals),
        "executed": sum(bool(r["provider_execution"]) for r in vals),
        "failures": sum(not bool(r["provider_execution"]) for r in vals),
        "correct": sum(bool(r["correct"]) for r in vals),
        "accuracy": round(sum(bool(r["correct"]) for r in vals) / len(vals), 6) if vals else None,
        "exact_format_rate": round(sum(bool(r["exact_format"]) for r in vals) / len(vals), 6) if vals else None,
        "prompt_chars_total": sum(int(r["prompt_chars"]) for r in vals),
        "representation_chars_total": sum(int(r["representation_chars"]) for r in vals),
        "mean_latency_ms": round(statistics.mean(lats), 1) if lats else None,
        "median_latency_ms": round(statistics.median(lats), 1) if lats else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--receipt", type=Path, default=Path("temporal-focus-target-blind-ab.json"))
    ap.add_argument("--max-cases", type=int, default=8)
    args = ap.parse_args()

    rows, trace_stats = base.load_rows(args.input)
    cases = base.select_cases(rows, args.max_cases)
    selection_ok = len(cases) >= 6
    labels = ["ALPHA" if bool(c["outcome"]["board_changed"]) else "BETA" for c in cases]
    alpha_count = sum(x == "ALPHA" for x in labels)
    beta_count = sum(x == "BETA" for x in labels)
    majority_baseline = max(alpha_count, beta_count) / len(labels) if labels else 1.0

    canary = base.call_model(
        "Public S0 canary. A move changed the next board. ALPHA means changed. Reply exactly ALPHA."
    )
    canary_choice, canary_exact = base.normalize_choice(canary["content"])
    canary_ok = canary["provider_execution"] and canary_choice == "ALPHA"

    call_rows: list[dict[str, Any]] = []
    focus_hashes: list[str] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(cases):
            expected = "ALPHA" if bool(case["outcome"]["board_changed"]) else "BETA"
            focus_hashes.append(hashlib.sha256(base.stable(focus_representation(case)).encode("utf-8")).hexdigest())
            arms = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, rep_chars = prompt_for(case, arm)
                res = base.call_model(prompt)
                selected, exact = base.normalize_choice(res["content"])
                call_rows.append({
                    "case": i,
                    "case_hash": case["case_hash"],
                    "arm": arm,
                    "expected": expected,
                    "selected": selected,
                    "correct": selected == expected,
                    "exact_format": exact,
                    "prompt_chars": len(prompt),
                    "representation_chars": rep_chars,
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "response_schema_ok": res["response_schema_ok"],
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                    "raw_response_excerpt": res["content"][:160],
                })

    raw = summarize(call_rows, "raw_board_action")
    focus = summarize(call_rows, "history2_focus_action")
    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_FIXED_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or focus["failures"] or raw["calls"] != len(cases) or focus["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif focus["correct"] > raw["correct"] and focus["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_TARGET_BLIND_FOCUS_BEHAVIOR_GAIN"
    elif (
        focus["correct"] == raw["correct"]
        and raw["representation_chars_total"] > 0
        and focus["representation_chars_total"] <= 0.50 * raw["representation_chars_total"]
        and focus["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_TARGET_BLIND_FOCUS_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-temporal-focus-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": base.ENDPOINT,
        "requested_model": base.MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "trace_repo": base.tsa.TUFA_REPO,
            "trace_commit": base.tsa.TUFA_COMMIT,
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "implementation": "clean-room action-local focus repair; no outcome-derived focus",
        },
        "repair_hypothesis": {
            "prior_result": "history2_visual_action lost 4/8 vs raw 5/8 on target-blind board-change prediction",
            "representation_change": "restore bounded exact local geometry around object implicated by completed past transition",
            "max_focus_side": MAX_FOCUS_SIDE,
            "focus_margin": FOCUS_MARGIN,
            "current_outcome_used_to_build_focus": False,
        },
        "selection": {
            "available_rows": len(rows),
            "fixed_cases_selected": len(cases),
            "label_counts": {"ALPHA_changed": alpha_count, "BETA_unchanged": beta_count},
            "majority_baseline_accuracy": round(majority_baseline, 6),
            "target_used_for_case_selection": False,
            "target_used_for_prompt": False,
            "case_order_reused_from_prior_target_blind_rung": True,
        },
        "focus_representation_sha256": focus_hashes,
        "arms": {"raw_board_action": raw, "history2_focus_action": focus},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_label_semantics": True,
            "alternating_arm_order": True,
            "no_target_matching": True,
            "focus_accuracy_gain_promotes_only_if_mean_latency_lte_150pct_raw": True,
            "equal_accuracy_efficiency_gate": "focus chars <=50% raw and mean latency <=135% raw",
            "provider_failure": "INCONCLUSIVE",
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": False,
            "target_blind_public_development_behavior": True,
            "independent_generalization_claim": False,
            "model_behavior_test": True,
            "provider_execution_is_not_kaggle_execution": True,
            "hidden_kaggle_data_read": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
            "owner_score_claim": False,
            "prize_or_award_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
