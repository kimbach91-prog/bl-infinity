#!/usr/bin/env python3
"""Target-blind ARC3 A/B using a compact object segmentation view.

This repair rung is source-grounded by the public Tufa harness design, which
uses object segmentation as the primary board view and raw ASCII only for local
inspection. This implementation is clean-room and uses only the pre-action
public board/action. It is public-development evidence, not independent
competition generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import deque
from pathlib import Path
from typing import Any

import temporal_state_target_blind_ab as base

ARMS = ("raw_board_action", "segmentation_action")


def components(board: list[list[int]]) -> tuple[list[dict[str, Any]], list[list[int]]]:
    h, w = len(board), len(board[0])
    seen: set[tuple[int, int]] = set()
    owner = [[-1] * w for _ in range(h)]
    nodes: list[dict[str, Any]] = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen:
                continue
            color = int(board[r][c])
            q = deque([(r, c)])
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while q:
                rr, cc = q.popleft()
                if int(board[rr][cc]) != color:
                    continue
                cells.append((rr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and int(board[nr][nc]) == color:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            node_id = len(nodes)
            for rr, cc in cells:
                owner[rr][cc] = node_id
            r0 = min(rr for rr, _ in cells)
            r1 = max(rr for rr, _ in cells)
            c0 = min(cc for _, cc in cells)
            c1 = max(cc for _, cc in cells)
            norm = sorted((rr - r0, cc - c0) for rr, cc in cells)
            shape_hash = hashlib.sha256(base.stable([color, norm]).encode("utf-8")).hexdigest()[:12]
            nodes.append({
                "id": node_id,
                "color": color,
                "hash": shape_hash,
                "pixels": len(cells),
                "bbox": [r0, c0, r1, c1],
                "edge": [r0 == 0, c1 == w - 1, r1 == h - 1, c0 == 0],
            })
    return nodes, owner


def segmentation_representation(case: dict[str, Any]) -> dict[str, Any]:
    raw = case["representations"]["raw_board_action"]
    board = [list(map(int, row)) for row in raw["board"]]
    h, w = len(board), len(board[0])
    nodes, owner = components(board)
    adjacency: set[tuple[int, int]] = set()
    for r in range(h):
        for c in range(w):
            a = owner[r][c]
            if r + 1 < h:
                b = owner[r + 1][c]
                if a != b:
                    adjacency.add((min(a, b), max(a, b)))
            if c + 1 < w:
                b = owner[r][c + 1]
                if a != b:
                    adjacency.add((min(a, b), max(a, b)))
    return {
        "level": raw.get("level"),
        "action": raw.get("action"),
        "shape": [h, w],
        "segmentation": {
            "nodes": nodes,
            "adjacency_list": [list(x) for x in sorted(adjacency)],
        },
    }


def representation(case: dict[str, Any], arm: str) -> Any:
    if arm == "raw_board_action":
        return case["representations"]["raw_board_action"]
    if arm == "segmentation_action":
        return segmentation_representation(case)
    raise KeyError(arm)


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    rep = base.stable(representation(case, arm))
    if arm == "segmentation_action":
        guidance = (
            "Interpret the segmentation as the primary scene view: connected objects, "
            "colors, shapes, edge contact, adjacency, and the already-chosen action. "
        )
    else:
        guidance = "Interpret the full pre-action board and already-chosen action. "
    prompt = (
        f"Representation arm: {arm}\n"
        + guidance
        + "Pre-action state/action representation:\n"
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
    ap.add_argument("--receipt", type=Path, default=Path("segmentation-target-blind-ab.json"))
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
    rep_hashes: list[str] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(cases):
            expected = "ALPHA" if bool(case["outcome"]["board_changed"]) else "BETA"
            rep_hashes.append(hashlib.sha256(base.stable(segmentation_representation(case)).encode("utf-8")).hexdigest())
            arms = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, rep_chars = prompt_for(case, arm)
                res = base.call_model(prompt)
                selected, exact = base.normalize_choice(res["content"])
                call_rows.append({
                    "case": i,
                    "case_hash": case["case_hash"],
                    "trace": case["trace"],
                    "trace_index": case["trace_index"],
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
    seg = summarize(call_rows, "segmentation_action")
    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_FIXED_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or seg["failures"] or raw["calls"] != len(cases) or seg["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif seg["correct"] > raw["correct"] and seg["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_TARGET_BLIND_SEGMENTATION_BEHAVIOR_GAIN"
    elif (
        seg["correct"] == raw["correct"]
        and raw["representation_chars_total"] > 0
        and seg["representation_chars_total"] <= 0.65 * raw["representation_chars_total"]
        and seg["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_TARGET_BLIND_SEGMENTATION_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-segmentation-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": base.ENDPOINT,
        "requested_model": base.MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "trace_repo": base.tsa.TUFA_REPO,
            "trace_commit": base.tsa.TUFA_COMMIT,
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "public_design_reference": "Tufalabs/duck-harness ARC3-Inference prompts.py: segmentation primary, raw ASCII local-only",
            "implementation": "clean-room 4-connected same-color segmentation + adjacency",
        },
        "repair_hypothesis": {
            "prior_result": "verbose exact-board + object geometry lost 4/8 vs raw 5/8",
            "representation_change": "replace full board with compact connected-object segmentation and adjacency",
            "current_outcome_used_to_build_segmentation": False,
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
        "segmentation_representation_sha256": rep_hashes,
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_board_action": raw, "segmentation_action": seg},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_label_semantics": True,
            "alternating_arm_order": True,
            "no_target_matching": True,
            "behavior_gain_or_strict_nondominated_efficiency_required": True,
            "provider_failure": "INCONCLUSIVE",
        },
        "rows": call_rows,
        "truth": {
            "public_trace_only": True,
            "public_source_shaped_representation": True,
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
