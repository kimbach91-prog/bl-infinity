#!/usr/bin/env python3
"""Target-blind ARC3 A/B with exact-board + global object geometry.

This is the repair rung after temporal history/focus lost to raw-board on a fixed
outcome-blind public-development set. The candidate keeps the complete current
board and action, then adds deterministic object/global geometry derived only
from the pre-action board. No current outcome is used for selection, prompt, or
representation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, deque
from pathlib import Path
from typing import Any

import temporal_state_target_blind_ab as base

ARMS = ("raw_board_action", "global_object_geometry_action")


def qbin(pos: int, size: int) -> int:
    if size <= 1:
        return 0
    return min(3, (pos * 4) // size)


def connected_components(board: list[list[int]], background: int) -> list[dict[str, Any]]:
    h, w = len(board), len(board[0])
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, Any]] = []
    for r in range(h):
        for c in range(w):
            color = int(board[r][c])
            if color == background or (r, c) in seen:
                continue
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
            if not cells:
                continue
            r0 = min(x for x, _ in cells)
            r1 = max(x for x, _ in cells)
            c0 = min(y for _, y in cells)
            c1 = max(y for _, y in cells)
            anchor_r, anchor_c = r0, c0
            normalized = sorted((rr - anchor_r, cc - anchor_c) for rr, cc in cells)
            shape_sig = hashlib.sha256(base.stable(normalized).encode("utf-8")).hexdigest()[:12]
            out.append({
                "color": color,
                "area": len(cells),
                "bbox": [r0, c0, r1, c1],
                "size": [r1 - r0 + 1, c1 - c0 + 1],
                "centroid_q4": [qbin(sum(rr for rr, _ in cells) // len(cells), h), qbin(sum(cc for _, cc in cells) // len(cells), w)],
                "touches_edge": [r0 == 0, c1 == w - 1, r1 == h - 1, c0 == 0],
                "shape": shape_sig,
            })
    return sorted(out, key=lambda x: (x["color"], x["bbox"], x["area"], x["shape"]))


def symmetry_flags(board: list[list[int]]) -> dict[str, bool]:
    h = len(board)
    w = len(board[0])
    horizontal = all(board[r] == board[h - 1 - r] for r in range(h))
    vertical = all(all(board[r][c] == board[r][w - 1 - c] for c in range(w)) for r in range(h))
    rot180 = all(all(board[r][c] == board[h - 1 - r][w - 1 - c] for c in range(w)) for r in range(h))
    return {"horizontal": horizontal, "vertical": vertical, "rot180": rot180}


def object_geometry_representation(case: dict[str, Any]) -> dict[str, Any]:
    raw = case["representations"]["raw_board_action"]
    board = [list(map(int, row)) for row in raw["board"]]
    flat = [v for row in board for v in row]
    counts = Counter(flat)
    background = min(((-n, color) for color, n in counts.items()))[1]
    components = connected_components(board, background)
    return {
        "level": raw.get("level"),
        "action": raw.get("action"),
        "board": board,
        "geometry": {
            "shape": [len(board), len(board[0])],
            "background_by_frequency": background,
            "color_counts": sorted([[int(color), int(n)] for color, n in counts.items()]),
            "component_count": len(components),
            "components": components,
            "symmetry": symmetry_flags(board),
        },
    }


def representation(case: dict[str, Any], arm: str) -> Any:
    if arm == "raw_board_action":
        return case["representations"]["raw_board_action"]
    if arm == "global_object_geometry_action":
        return object_geometry_representation(case)
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
    ap.add_argument("--receipt", type=Path, default=Path("global-object-geometry-target-blind-ab.json"))
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
    geometry_hashes: list[str] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(cases):
            expected = "ALPHA" if bool(case["outcome"]["board_changed"]) else "BETA"
            geometry_hashes.append(hashlib.sha256(base.stable(object_geometry_representation(case)).encode("utf-8")).hexdigest())
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
    geom = summarize(call_rows, "global_object_geometry_action")
    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_FIXED_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or geom["failures"] or raw["calls"] != len(cases) or geom["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif geom["correct"] > raw["correct"] and geom["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_TARGET_BLIND_GLOBAL_OBJECT_GEOMETRY_BEHAVIOR_GAIN"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-global-object-geometry-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": base.ENDPOINT,
        "requested_model": base.MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "trace_repo": base.tsa.TUFA_REPO,
            "trace_commit": base.tsa.TUFA_COMMIT,
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "implementation": "clean-room exact-board + deterministic connected-component/global geometry",
        },
        "repair_hypothesis": {
            "prior_result": "temporal history and temporal focus both lost 4/8 vs raw 5/8 on fixed target-blind cases",
            "representation_change": "retain exact full board while adding explicit global object geometry",
            "current_outcome_used_to_build_geometry": False,
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
        "geometry_representation_sha256": geometry_hashes,
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_board_action": raw, "global_object_geometry_action": geom},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_label_semantics": True,
            "alternating_arm_order": True,
            "no_target_matching": True,
            "behavior_gain_required": True,
            "geometry_accuracy_gain_promotes_only_if_mean_latency_lte_150pct_raw": True,
            "provider_failure": "INCONCLUSIVE",
        },
        "rows": call_rows,
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
