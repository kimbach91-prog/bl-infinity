#!/usr/bin/env python3
"""Rung 168: prequential global-scroll + prefix-atlas full-frame renderer.

R167 found that 359/470 non-identity transitions have a >=95% fitting nonzero
whole-board shift, with UP overwhelmingly (-3,0) and DOWN overwhelmingly (3,0).
This rung turns that structure into an executable prior-only predictor.

For each action, only prior observed transitions are used to infer a dominant
whole-board shift and a per-output-cell transport field: each cell is COPY_SHIFT,
COPY_SAME, CONST, or UNKNOWN. UNKNOWN cells are not guessed. Instead, the partial
render is matched against the prefix atlas of previously observed full boards;
only a unique matching board may complete the frame. The exact-state one-shot
Markov cache from r161 is retained as baseline. On exact-cache misses, raw atlas
predictions are first shadow-tested; an action may emit only after >=2 prior
shadow successes and zero prior shadow failures. Current outcome is ingested only
after prediction/scoring.

This remains public source-assisted sequence replay, not independent
generalization and not a Kaggle score.
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

RUNG = 168
MIN_SHIFT_SAMPLES = 3
MIN_DOMINANT_FRACTION = 0.75
MIN_TRANSITION_SHIFT_FIT = 0.90
MIN_PRIOR_SHADOW_OK = 2
Grid = list[list[int]]


def board_key(board: Grid) -> str:
    return base.stable(board)


def unique_program(bank: Counter[str], support: int = 1) -> str | None:
    if len(bank) != 1:
        return None
    p, n = next(iter(bank.items()))
    return p if n >= support else None


def infer_renderer(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [
        s for s in samples
        if s["changed"] > 0 and float(s["fit"]) >= MIN_TRANSITION_SHIFT_FIT
    ]
    if len(eligible) < MIN_SHIFT_SAMPLES:
        return None
    votes = Counter(tuple(s["shift"]) for s in eligible)
    shift, count = votes.most_common(1)[0]
    if count < MIN_SHIFT_SAMPLES or count / len(eligible) < MIN_DOMINANT_FRACTION:
        return None
    chosen = [s for s in eligible if tuple(s["shift"]) == shift]
    before0: Grid = chosen[0]["before"]
    h, w = len(before0), len(before0[0])
    if any(len(s["before"]) != h or len(s["before"][0]) != w for s in chosen):
        return None
    dr, dc = shift
    modes: list[list[list[Any]]] = []
    unknown = 0
    counts = Counter()
    for r in range(h):
        row = []
        for c in range(w):
            sr, sc = r - dr, c - dc
            shift_ok = (
                0 <= sr < h and 0 <= sc < w and
                all(s["after"][r][c] == s["before"][sr][sc] for s in chosen)
            )
            same_ok = all(s["after"][r][c] == s["before"][r][c] for s in chosen)
            vals = {int(s["after"][r][c]) for s in chosen}
            if shift_ok:
                mode = ["SHIFT", int(sr), int(sc)]
                counts["SHIFT"] += 1
            elif same_ok:
                mode = ["SAME", int(r), int(c)]
                counts["SAME"] += 1
            elif len(vals) == 1:
                mode = ["CONST", int(next(iter(vals)))]
                counts["CONST"] += 1
            else:
                mode = ["UNKNOWN"]
                counts["UNKNOWN"] += 1
                unknown += 1
            row.append(mode)
        modes.append(row)
    return {
        "shift": [int(dr), int(dc)],
        "eligible_samples": len(eligible),
        "dominant_samples": len(chosen),
        "dominant_fraction": round(len(chosen) / len(eligible), 6),
        "modes": modes,
        "mode_counts": dict(counts),
        "unknown_cells": unknown,
        "known_fraction": round((h * w - unknown) / (h * w), 6),
    }


def partial_render(board: Grid, renderer: dict[str, Any]) -> list[list[int | None]]:
    h, w = len(board), len(board[0])
    out: list[list[int | None]] = [[None for _ in range(w)] for _ in range(h)]
    modes = renderer["modes"]
    for r in range(h):
        for c in range(w):
            m = modes[r][c]
            if m[0] == "SHIFT" or m[0] == "SAME":
                out[r][c] = int(board[int(m[1])][int(m[2])])
            elif m[0] == "CONST":
                out[r][c] = int(m[1])
    return out


def unique_atlas_completion(partial: list[list[int | None]], atlas: dict[str, Grid]) -> Grid | None:
    matches: list[Grid] = []
    h, w = len(partial), len(partial[0])
    for b in atlas.values():
        if len(b) != h or len(b[0]) != w:
            continue
        ok = True
        for r in range(h):
            for c in range(w):
                v = partial[r][c]
                if v is not None and int(b[r][c]) != int(v):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            matches.append(b)
            if len(matches) > 1:
                return None
    return [row[:] for row in matches[0]] if len(matches) == 1 else None


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_bank: dict[str, Counter[str]] = defaultdict(Counter)
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    atlas: dict[str, Grid] = {}
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
        "raw_scroll_atlas_opportunities": 0,
        "raw_shadow_correct": 0,
        "raw_shadow_wrong": 0,
        "qualified_opportunities": 0,
    }
    renderer_snapshots: dict[str, dict[str, Any]] = {}

    pre = events[0]
    first_board = base.as_grid(pre["board"])
    atlas[board_key(first_board)] = [row[:] for row in first_board]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            try:
                b = base.as_grid(e["board"])
                atlas[board_key(b)] = [row[:] for row in b]
            except Exception:
                pass
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if len(before) != len(after) or len(before[0]) != len(after[0]):
            continue

        exact_key = r160.context_exact(before, action)
        p = unique_program(exact_bank[exact_key], 1) if exact_key in exact_bank else None
        pred_exact = r160.apply_program(before, p) if p is not None else None
        if pred_exact is not None:
            baseline["predictions"] += 1
            if pred_exact == after:
                baseline["correct"] += 1
            else:
                baseline["wrong"] += 1

        pred_raw = None
        renderer = infer_renderer(samples[action])
        if renderer is not None:
            renderer_snapshots[action] = {
                k: v for k, v in renderer.items() if k != "modes"
            }
            partial = partial_render(before, renderer)
            pred_raw = unique_atlas_completion(partial, atlas)

        qualified_before_current = (
            shadow_ok[action] >= MIN_PRIOR_SHADOW_OK and shadow_wrong[action] == 0
        )
        if pred_exact is None and pred_raw is not None:
            candidate["raw_scroll_atlas_opportunities"] += 1
            if pred_raw == after:
                candidate["raw_shadow_correct"] += 1
            else:
                candidate["raw_shadow_wrong"] += 1
            if qualified_before_current:
                candidate["qualified_opportunities"] += 1
                candidate["predictions"] += 1
                candidate["added_predictions_vs_exact"] += 1
                if pred_raw == after:
                    candidate["correct"] += 1
                    candidate["added_correct_vs_exact"] += 1
                else:
                    candidate["wrong"] += 1
                    candidate["added_wrong_vs_exact"] += 1
            # Reliability is updated only after current prediction/scoring.
            if pred_raw == after:
                shadow_ok[action] += 1
            else:
                shadow_wrong[action] += 1

        # Post-outcome learning only.
        target = r160.program(before, after)
        exact_bank[exact_key][target] += 1
        changed = sum(
            before[r][c] != after[r][c]
            for r in range(len(before))
            for c in range(len(before[0]))
        )
        if changed:
            best = r167.best_nonzero_shift(before, after)
            samples[action].append({
                "before": [row[:] for row in before],
                "after": [row[:] for row in after],
                "changed": int(changed),
                "shift": [int(best["dr"]), int(best["dc"])],
                "fit": float(best["valid_match_fraction"]),
            })
        atlas[board_key(before)] = [row[:] for row in before]
        atlas[board_key(after)] = [row[:] for row in after]

    baseline["accuracy"] = round(baseline["correct"] / baseline["predictions"], 6) if baseline["predictions"] else None
    candidate["accuracy"] = round(candidate["correct"] / candidate["predictions"], 6) if candidate["predictions"] else None
    candidate["strict_zero_error"] = bool(candidate["predictions"] and candidate["wrong"] == 0)
    return {
        "baseline_exact_markov": baseline,
        "scroll_atlas_candidate": candidate,
        "shadow_ok_by_action": dict(shadow_ok),
        "shadow_wrong_by_action": dict(shadow_wrong),
        "renderer_snapshots": renderer_snapshots,
        "atlas_unique_boards_final": len(atlas),
    }


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    bp = sum(p["baseline_exact_markov"]["predictions"] for p in parts)
    bc = sum(p["baseline_exact_markov"]["correct"] for p in parts)
    bw = sum(p["baseline_exact_markov"]["wrong"] for p in parts)
    fields = [
        "predictions", "correct", "wrong", "added_predictions_vs_exact",
        "added_correct_vs_exact", "added_wrong_vs_exact",
        "raw_scroll_atlas_opportunities", "raw_shadow_correct", "raw_shadow_wrong",
        "qualified_opportunities",
    ]
    cand = {k: sum(p["scroll_atlas_candidate"][k] for p in parts) for k in fields}
    cand["accuracy"] = round(cand["correct"] / cand["predictions"], 6) if cand["predictions"] else None
    cand["strict_zero_error"] = bool(cand["predictions"] and cand["wrong"] == 0)
    per_add_c = [p["scroll_atlas_candidate"]["added_correct_vs_exact"] for p in parts]
    per_add_w = [p["scroll_atlas_candidate"]["added_wrong_vs_exact"] for p in parts]
    cand["per_trace_added_correct"] = per_add_c
    cand["per_trace_added_wrong"] = per_add_w
    cand["zero_error_nonzero_p0_p10"] = bool(
        len(parts) >= 2 and per_add_c[0] > 0 and per_add_c[1] > 0 and
        per_add_w[0] == 0 and per_add_w[1] == 0 and cand["wrong"] == 0
    )
    return {
        "baseline_exact_markov": {
            "predictions": bp,
            "correct": bc,
            "wrong": bw,
            "accuracy": round(bc / bp, 6) if bp else None,
            "per_trace_predictions": [p["baseline_exact_markov"]["predictions"] for p in parts],
            "per_trace_correct": [p["baseline_exact_markov"]["correct"] for p in parts],
            "per_trace_wrong": [p["baseline_exact_markov"]["wrong"] for p in parts],
        },
        "scroll_atlas_candidate": cand,
        "per_trace": parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    agg = aggregate(parts)
    inc = agg["scroll_atlas_candidate"]
    gate = (
        "ZERO_ERROR_P0_P10_PREQUENTIAL_SCROLL_ATLAS_GAIN"
        if inc["zero_error_nonzero_p0_p10"]
        else "NO_STRICT_PREQUENTIAL_SCROLL_ATLAS_GAIN"
    )
    return {
        "schema": "deus/arc3-public-prequential-scroll-atlas-renderer/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_SCROLL_ATLAS_FULLFRAME_DIAGNOSTIC",
        "representation_change_from_rung167": {
            "changed": True,
            "change": "turn outcome-assisted dense-scroll structure into a prior-only whole-board transport field with prefix-atlas completion and fail-closed shadow qualification",
        },
        "parameters": {
            "min_shift_samples": MIN_SHIFT_SAMPLES,
            "min_dominant_fraction": MIN_DOMINANT_FRACTION,
            "min_transition_shift_fit": MIN_TRANSITION_SHIFT_FIT,
            "min_prior_shadow_ok": MIN_PRIOR_SHADOW_OK,
        },
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
            "current_prediction_uses_preaction_and_prior_outcomes_only": True,
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
