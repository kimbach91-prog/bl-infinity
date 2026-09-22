#!/usr/bin/env python3
"""Rung 167: characterize dense transition dynamics as global scroll/render maps.

R166 showed that 439/470 non-identity public transitions change >=65 cells,
while only 9/470 are sparse <=16-cell effects. This rung changes representation
again: instead of local-object edits, test whether dense effects are explained by
a direction-conditioned whole-board coordinate transport (camera/scene scroll)
plus a smaller residual renderer.

This is outcome-assisted structural research only. It does not make a pre-action
prediction. Its purpose is to decide whether the next executable rung should be
a global scroll renderer with learned boundary/overlay rules or a more general
latent renderer. Public pinned traces only; no Kaggle claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base

RUNG = 167
MAX_SHIFT = 3
Grid = list[list[int]]
MOVEMENT_ACTIONS = {"UP", "DOWN", "LEFT", "RIGHT"}


def same_shape(a: Grid, b: Grid) -> bool:
    return len(a) == len(b) and len(a[0]) == len(b[0])


def shift_score(before: Grid, after: Grid, dr: int, dc: int) -> dict[str, Any]:
    """Score after[r,c] = before[r-dr,c-dc] on coordinates with valid source."""
    h, w = len(before), len(before[0])
    valid = matches = 0
    mismatches: list[tuple[int, int]] = []
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            valid += 1
            if after[r][c] == before[sr][sc]:
                matches += 1
            else:
                mismatches.append((r, c))
    total = h * w
    return {
        "dr": dr,
        "dc": dc,
        "valid": valid,
        "matches": matches,
        "valid_match_fraction": round(matches / valid, 6) if valid else 0.0,
        "whole_board_explained_fraction": round(matches / total, 6) if total else 0.0,
        "residual_cells_within_valid": valid - matches,
        "interior_exact": bool(valid and matches == valid),
        "mismatch_bbox": _bbox(mismatches),
    }


def _bbox(points: list[tuple[int, int]]) -> list[int] | None:
    if not points:
        return None
    rs = [r for r, _ in points]
    cs = [c for _, c in points]
    return [min(rs), min(cs), max(rs), max(cs)]


def changed_cells(before: Grid, after: Grid) -> int:
    return sum(
        before[r][c] != after[r][c]
        for r in range(len(before))
        for c in range(len(before[0]))
    )


def best_nonzero_shift(before: Grid, after: Grid) -> dict[str, Any]:
    candidates = []
    for dr in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dc in range(-MAX_SHIFT, MAX_SHIFT + 1):
            if (dr, dc) == (0, 0):
                continue
            q = shift_score(before, after, dr, dc)
            # Prefer high valid-region exactness, then explained whole-board mass,
            # then smaller Manhattan displacement as deterministic tie-break.
            candidates.append(q)
    return max(
        candidates,
        key=lambda q: (
            q["valid_match_fraction"],
            q["whole_board_explained_fraction"],
            -abs(q["dr"]) - abs(q["dc"]),
            -q["dr"],
            -q["dc"],
        ),
    )


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    action_stats: dict[str, dict[str, Any]] = {}
    total = identity = nonidentity = 0
    high98 = high95 = high90 = interior_exact = 0
    shift_counts: Counter[tuple[int, int]] = Counter()
    residual_counts: Counter[int] = Counter()
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if not same_shape(before, after):
            continue
        total += 1
        changed = changed_cells(before, after)
        if changed == 0:
            identity += 1
            continue
        nonidentity += 1
        best = best_nonzero_shift(before, after)
        sh = (int(best["dr"]), int(best["dc"]))
        shift_counts[sh] += 1
        residual_counts[int(best["residual_cells_within_valid"])] += 1
        f = float(best["valid_match_fraction"])
        high98 += int(f >= 0.98)
        high95 += int(f >= 0.95)
        high90 += int(f >= 0.90)
        interior_exact += int(bool(best["interior_exact"]))

        s = action_stats.setdefault(
            action,
            {
                "nonidentity": 0,
                "high98": 0,
                "high95": 0,
                "high90": 0,
                "interior_exact": 0,
                "shift_counts": Counter(),
                "residual_counts": Counter(),
            },
        )
        s["nonidentity"] += 1
        s["high98"] += int(f >= 0.98)
        s["high95"] += int(f >= 0.95)
        s["high90"] += int(f >= 0.90)
        s["interior_exact"] += int(bool(best["interior_exact"]))
        s["shift_counts"][sh] += 1
        s["residual_counts"][int(best["residual_cells_within_valid"])] += 1

    action_out = {}
    for action, s in sorted(action_stats.items()):
        n = int(s["nonidentity"])
        dominant_shift, dominant_n = s["shift_counts"].most_common(1)[0]
        action_out[action] = {
            "nonidentity": n,
            "high98": int(s["high98"]),
            "high95": int(s["high95"]),
            "high90": int(s["high90"]),
            "interior_exact": int(s["interior_exact"]),
            "high95_fraction": round(int(s["high95"]) / n, 6) if n else None,
            "dominant_shift": list(dominant_shift),
            "dominant_shift_count": int(dominant_n),
            "dominant_shift_fraction": round(dominant_n / n, 6) if n else None,
            "shift_top10": [[list(k), int(v)] for k, v in s["shift_counts"].most_common(10)],
            "residual_top10": [[int(k), int(v)] for k, v in s["residual_counts"].most_common(10)],
        }

    return {
        "transitions": total,
        "identity": identity,
        "nonidentity": nonidentity,
        "high98": high98,
        "high95": high95,
        "high90": high90,
        "interior_exact": interior_exact,
        "high95_fraction_of_nonidentity": round(high95 / nonidentity, 6) if nonidentity else None,
        "shift_top20": [[list(k), int(v)] for k, v in shift_counts.most_common(20)],
        "residual_top20": [[int(k), int(v)] for k, v in residual_counts.most_common(20)],
        "per_action": action_out,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    total = sum(p["transitions"] for p in parts)
    identity = sum(p["identity"] for p in parts)
    nonidentity = sum(p["nonidentity"] for p in parts)
    high95 = sum(p["high95"] for p in parts)
    high98 = sum(p["high98"] for p in parts)
    interior_exact = sum(p["interior_exact"] for p in parts)

    movement_rollup: dict[str, Counter[tuple[int, int]]] = defaultdict(Counter)
    movement_counts = Counter()
    movement_high95 = Counter()
    for p in parts:
        for action, s in p["per_action"].items():
            if action not in MOVEMENT_ACTIONS:
                continue
            movement_counts[action] += int(s["nonidentity"])
            movement_high95[action] += int(s["high95"])
            for shift, n in s["shift_top10"]:
                movement_rollup[action][tuple(shift)] += int(n)

    movement = {}
    strong_actions = 0
    for action in sorted(MOVEMENT_ACTIONS):
        n = int(movement_counts[action])
        if not n:
            continue
        dom, dom_n = movement_rollup[action].most_common(1)[0]
        h95 = int(movement_high95[action])
        h95f = h95 / n
        domf = dom_n / n
        if h95f >= 0.75 and domf >= 0.60:
            strong_actions += 1
        movement[action] = {
            "nonidentity": n,
            "high95": h95,
            "high95_fraction": round(h95f, 6),
            "dominant_shift": list(dom),
            "dominant_shift_count": int(dom_n),
            "dominant_shift_fraction": round(domf, 6),
            "shift_top10": [[list(k), int(v)] for k, v in movement_rollup[action].most_common(10)],
        }

    recommendation = (
        "ACTION_CONDITIONED_GLOBAL_SCROLL_RENDERER"
        if strong_actions >= 2
        else "GENERAL_LATENT_DENSE_RENDERER"
    )
    return {
        "schema": "deus/arc3-public-dense-scroll-renderer-audit/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_OUTCOME_ASSISTED_DENSE_SCROLL_STRUCTURE_AUDIT",
        "representation_change_from_rung166": {
            "changed": True,
            "change": "test dense non-identity effects as whole-board coordinate transport plus residual renderer, replacing sparse/local object-edit assumptions",
        },
        "parameters": {"max_shift": MAX_SHIFT, "high_fit_threshold": 0.95},
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "clean_room_implementation": True,
        },
        "traces": [{"path": str(p), "audit": a} for p, a in zip(paths, parts)],
        "aggregate": {
            "transitions": total,
            "identity": identity,
            "nonidentity": nonidentity,
            "best_nonzero_shift_high95": high95,
            "best_nonzero_shift_high98": high98,
            "best_nonzero_shift_interior_exact": interior_exact,
            "high95_fraction_of_nonidentity": round(high95 / nonidentity, 6) if nonidentity else None,
            "movement_actions": movement,
            "strong_action_count": strong_actions,
            "recommendation": recommendation,
        },
        "diagnostic_gate": "DENSE_SCROLL_STRUCTURE_CHARACTERIZED",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "outcome_assisted_analysis": True,
            "preoutcome_prediction_made": False,
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
