#!/usr/bin/env python3
"""Rung 153: full-history residual placement state-machine diagnostic.

Rungs150-152 established a clean boundary: the rung149 semantic primitive predicts
*what* residual value-pair multiset will occur on 190 covered public transitions with
zero observed errors, while direct placement lookup and local per-site renderers do
not predict *where*. This rung changes representation again. It treats residual
placement as a temporal global state and learns prequential transitions from prior
observed residual placements.

For each eligible transition, prediction is locked before the current outcome is
revealed. The predictor may use the current pre-action mobility/semantic context and
one or two *past* residual placements/semantics. It predicts a transformation from
the previous residual top-left to the current exact residual edit set. Only after
scoring is the current target ingested.

Current outcome is still used retrospectively to isolate the conservative residual
and score the target, therefore this remains a public source-assisted diagnostic,
not an independent/full-frame/model/GPU/Kaggle result.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_residual_action_mobility_selector_audit_149 as sel149
import public_residual_placement_reconstruction_audit_150 as r150

RUNG = 153
WIN_KEYS = sel149.FEATURE_KEYS["mobility_clearance_bundle"]


def unique(counter: Counter[str]) -> str | None:
    return next(iter(counter)) if len(counter) == 1 else None


def top_left(edits: list[tuple[int, int, int, int]]) -> tuple[int, int]:
    return min(r for r, _c, _b, _a in edits), min(c for _r, c, _b, _a in edits)


def normalized(edits: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    r0, c0 = top_left(edits)
    return sorted((r - r0, c - c0, b, a) for r, c, b, a in edits)


def transform_from_prev(
    prev_edits: list[tuple[int, int, int, int]],
    cur_edits: list[tuple[int, int, int, int]],
) -> str:
    pr, pc = top_left(prev_edits)
    cr, cc = top_left(cur_edits)
    return base.stable({"d": [cr - pr, cc - pc], "norm": normalized(cur_edits)})


def apply_transform(
    before: list[list[int]],
    prev_edits: list[tuple[int, int, int, int]],
    transform: str,
) -> list[tuple[int, int, int, int]] | None:
    raw = json.loads(transform)
    pr, pc = top_left(prev_edits)
    dr, dc = int(raw["d"][0]), int(raw["d"][1])
    ar, ac = pr + dr, pc + dc
    h, w = len(before), len(before[0])
    out: list[tuple[int, int, int, int]] = []
    for rr, cc, old, new in raw["norm"]:
        r, c = ar + int(rr), ac + int(cc)
        if not (0 <= r < h and 0 <= c < w):
            return None
        old = int(old); new = int(new)
        if before[r][c] != old:
            return None
        out.append((r, c, old, new))
    return sorted(out)


def semantic_context(
    before: list[list[int]], action: str, prev2_sem: str | None, prev1_sem: str | None
) -> str | None:
    if prev2_sem is None or prev1_sem is None:
        return None
    feat = sel149.mobility_features(before, action)
    if feat is None:
        return None
    return base.stable({"f": sel149.project(feat, WIN_KEYS), "p2": prev2_sem, "p1": prev1_sem, "a": action})


def prev_motion(prev2: list[tuple[int, int, int, int]] | None, prev1: list[tuple[int, int, int, int]] | None) -> list[int] | None:
    if prev2 is None or prev1 is None:
        return None
    a = top_left(prev2); b = top_left(prev1)
    return [b[0] - a[0], b[1] - a[1]]


def keys_for(
    before: list[list[int]],
    action: str,
    ctx: str,
    sem_pred: str,
    prev2_sem: str,
    prev1_sem: str,
    prev2_edits: list[tuple[int, int, int, int]],
    prev1_edits: list[tuple[int, int, int, int]],
) -> dict[str, str]:
    p1_norm = normalized(prev1_edits)
    p2_norm = normalized(prev2_edits)
    motion = prev_motion(prev2_edits, prev1_edits)
    return {
        "semantic_phase_prev1_shape": base.stable({
            "a": action, "sem": sem_pred, "p1_sem": prev1_sem, "p1_shape": p1_norm
        }),
        "semantic_phase_prev2_shapes": base.stable({
            "a": action, "sem": sem_pred, "p2_sem": prev2_sem, "p1_sem": prev1_sem,
            "p2_shape": p2_norm, "p1_shape": p1_norm
        }),
        "placement_velocity_state": base.stable({
            "a": action, "sem": sem_pred, "p1_sem": prev1_sem, "prev_motion": motion,
            "p1_shape": p1_norm
        }),
        "r149_context_plus_prev_placement": base.stable({
            "ctx": ctx, "sem": sem_pred, "p1_shape": p1_norm, "prev_motion": motion
        }),
    }


REPS = (
    "semantic_phase_prev1_shape",
    "semantic_phase_prev2_shapes",
    "placement_velocity_state",
    "r149_context_plus_prev_placement",
)


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_bank: dict[str, Counter[str]] = defaultdict(Counter)
    transform_banks: dict[str, dict[str, Counter[str]]] = {r: defaultdict(Counter) for r in REPS}
    stats = {r: {
        "semantic_predictions": 0, "semantic_correct": 0, "semantic_wrong": 0,
        "placement_predictions": 0, "placement_correct": 0, "placement_wrong": 0,
        "placement_unseen": 0, "placement_conflict": 0, "placement_invalid_apply": 0,
    } for r in REPS}
    eligible = 0
    reasons = Counter()
    prev2_sem: str | None = None
    prev1_sem: str | None = None
    prev2_edits: list[tuple[int, int, int, int]] | None = None
    prev1_edits: list[tuple[int, int, int, int]] | None = None
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        detail = r150.residual_edits(before, after, action)
        if detail is None:
            reasons["residual_detail_missing"] += 1
            continue
        edits, target_sem = detail
        eligible += 1
        ctx = semantic_context(before, action, prev2_sem, prev1_sem)
        sem_pred = unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None

        can_history = (
            ctx is not None and sem_pred is not None and
            prev2_sem is not None and prev1_sem is not None and
            prev2_edits is not None and prev1_edits is not None
        )
        current_keys: dict[str, str] = {}
        if can_history:
            current_keys = keys_for(before, action, ctx, sem_pred, prev2_sem, prev1_sem, prev2_edits, prev1_edits)
            for rep in REPS:
                s = stats[rep]
                s["semantic_predictions"] += 1
                if sem_pred == target_sem:
                    s["semantic_correct"] += 1
                else:
                    s["semantic_wrong"] += 1
                key = current_keys[rep]
                if key not in transform_banks[rep]:
                    s["placement_unseen"] += 1
                    continue
                pred_transform = unique(transform_banks[rep][key])
                if pred_transform is None:
                    s["placement_conflict"] += 1
                    continue
                pred = apply_transform(before, prev1_edits, pred_transform)
                if pred is None:
                    s["placement_invalid_apply"] += 1
                    continue
                s["placement_predictions"] += 1
                if pred == sorted(edits):
                    s["placement_correct"] += 1
                else:
                    s["placement_wrong"] += 1

        # Ingest current target only after prediction is locked.
        if ctx is not None:
            semantic_bank[ctx][target_sem] += 1
        if (
            ctx is not None and prev2_sem is not None and prev1_sem is not None and
            prev2_edits is not None and prev1_edits is not None
        ):
            true_keys = keys_for(before, action, ctx, target_sem, prev2_sem, prev1_sem, prev2_edits, prev1_edits)
            true_transform = transform_from_prev(prev1_edits, edits)
            for rep in REPS:
                transform_banks[rep][true_keys[rep]][true_transform] += 1

        prev2_sem, prev1_sem = prev1_sem, target_sem
        prev2_edits, prev1_edits = prev1_edits, edits

    for rep, s in stats.items():
        s["semantic_accuracy"] = round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None
        s["placement_accuracy"] = round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None
        s["placement_coverage_of_eligible"] = round(s["placement_predictions"] / eligible, 6) if eligible else 0.0
        s["strict_zero_error_placement"] = bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0)
        s["transform_contexts_final"] = len(transform_banks[rep])
        s["transform_conflicted_contexts_final"] = sum(len(c) > 1 for c in transform_banks[rep].values())
    return {"eligible_transitions": eligible, "ineligible_reasons": dict(sorted(reasons.items())), "representations": stats}


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = sum(p["eligible_transitions"] for p in parts)
    out: dict[str, Any] = {}
    hard: list[tuple[int, str]] = []
    for rep in REPS:
        keys = (
            "semantic_predictions", "semantic_correct", "semantic_wrong",
            "placement_predictions", "placement_correct", "placement_wrong",
            "placement_unseen", "placement_conflict", "placement_invalid_apply",
        )
        s = {k: sum(p["representations"][rep][k] for p in parts) for k in keys}
        pp = [p["representations"][rep]["placement_predictions"] for p in parts]
        pc = [p["representations"][rep]["placement_correct"] for p in parts]
        pw = [p["representations"][rep]["placement_wrong"] for p in parts]
        sw = [p["representations"][rep]["semantic_wrong"] for p in parts]
        s.update({
            "semantic_accuracy": round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None,
            "placement_accuracy": round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None,
            "placement_coverage_of_eligible": round(s["placement_predictions"] / eligible, 6) if eligible else 0.0,
            "strict_zero_error_placement": bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0),
            "per_trace_placement_predictions": pp,
            "per_trace_placement_correct": pc,
            "per_trace_placement_wrong": pw,
            "per_trace_semantic_wrong": sw,
        })
        out[rep] = s
        if len(pp) >= 2 and pp[0] > 0 and pp[1] > 0 and pw[0] == 0 and pw[1] == 0 and sw[0] == 0 and sw[1] == 0:
            hard.append((pp[0] + pp[1], rep))
    return {
        "trace_count": len(parts), "eligible_transitions": eligible,
        "representations": out,
        "best_zero_error_p0_p10_history_state_machine": max(hard)[1] if hard else None,
        "per_trace": parts,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    parts = []
    traces = []
    for p in paths:
        a = audit_trace(base.load_events(p)); parts.append(a); traces.append({"path": str(p), "audit": a})
    return {
        "schema": "deus/arc3-public-residual-history-state-machine-audit/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_GLOBAL_HISTORY_RESIDUAL_STATE_MACHINE_DIAGNOSTIC",
        "representation_change_from_rung152": {
            "changed": True,
            "change": "replace local per-site patch recurrence with a global temporal state-machine over prior residual placements; learn exact residual-placement transforms from one/two past observed placements and current pre-action semantic context",
        },
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "clean_room_implementation": True,
            "architectural_principle": "precommit expectation before action/outcome, verify mismatch, then ingest counterexample",
        },
        "traces": traces,
        "aggregate": aggregate(parts),
        "diagnostic_gate": "GLOBAL_HISTORY_RESIDUAL_STATE_MACHINE_CHARACTERIZED",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "diagnostic_only": True,
            "current_preaction_and_past_history_only_for_prediction": True,
            "semantic_prediction_prior_only": True,
            "placement_prediction_prior_only": True,
            "current_targets_ingested_after_prediction": True,
            "current_outcome_used_for_residual_isolation_and_scoring": True,
            "hard_trace_gate_requires_p0_and_p10_nonzero_zero_error_coverage": True,
            "full_frame_prediction_claim": False,
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
    ap = argparse.ArgumentParser(); ap.add_argument("--input", type=Path, action="append", default=[]); ap.add_argument("--output", type=Path); args = ap.parse_args()
    if not args.input: raise SystemExit("at least one --input is required")
    d = run(args.input); text = json.dumps(d, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.write_text(text, encoding="utf-8")
    print(text, end=""); return 0


if __name__ == "__main__":
    raise SystemExit(main())
