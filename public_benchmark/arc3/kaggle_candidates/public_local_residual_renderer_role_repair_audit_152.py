#!/usr/bin/env python3
"""Rung 152: repair rung151 local renderer by replacing hard mobility exclusion with a role feature.

Rung151 conservatively removed every site lying in the pre-outcome mobility source/destination
envelope. Runtime evidence showed that this representation was over-exclusive: the fixed rung149
semantic primitive stayed 190/190, but every renderer abstained on all 190 covered cases and many
true residual sites overlapped that broad *possible* mobility envelope. This rung changes the
representation rather than retrying: every board site remains eligible, while mobility membership
(source/destination/both/neither) is encoded as a local feature for the mobility-aware arm.

Labels are learned prequentially only after the current prediction is locked. Current outcome is
still used retrospectively to isolate eligible residual targets and score them, so this remains a
public source-assisted diagnostic, not an independent/full-frame/model/GPU/Kaggle result.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_local_residual_renderer_audit_151 as r151
import public_residual_placement_reconstruction_audit_150 as place150

RUNG = 152
NOOP = r151.NOOP
REPS = {
    "raw_r1_all_sites": (1, False, False),
    "canon_r1_all_sites": (1, True, False),
    "canon_mobility_r1_all_sites": (1, True, True),
}


def unique(counter: Counter[Any]) -> Any | None:
    return next(iter(counter)) if len(counter) == 1 else None


def predict_edits(
    board: list[list[int]],
    action: str,
    semantic: str,
    rep: str,
    bank: dict[str, Counter[Any]],
) -> tuple[list[tuple[int, int, int, int]] | None, str, int]:
    radius, canonical, with_mobility = REPS[rep]
    src, dst = r151.mobility_envelope(board, action)
    expected = r151.semantic_counts(semantic)
    candidates: dict[tuple[int, int], list[tuple[int, int, int, int]]] = defaultdict(list)
    ambiguous = 0
    for r, row in enumerate(board):
        for c, old in enumerate(row):
            key = r151.site_signature(board, r, c, action, radius, canonical, with_mobility, src, dst)
            if key not in bank:
                continue
            label = unique(bank[key])
            if label is None:
                ambiguous += 1
                continue
            if label == NOOP:
                continue
            pair = (int(label[0]), int(label[1]))
            if pair not in expected or pair[0] != old:
                continue
            candidates[pair].append((r, c, pair[0], pair[1]))
    for pair, count in expected.items():
        if len(candidates.get(pair, [])) != count:
            return None, "count_mismatch", ambiguous
    pred = sorted(edit for pair in expected for edit in candidates[pair])
    if not pred:
        return None, "empty_prediction", ambiguous
    return pred, "predicted", ambiguous


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_bank: dict[str, Counter[str]] = defaultdict(Counter)
    renderer_banks: dict[str, dict[str, Counter[Any]]] = {rep: defaultdict(Counter) for rep in REPS}
    stats = {
        rep: {
            "semantic_predictions": 0,
            "semantic_correct": 0,
            "semantic_wrong": 0,
            "placement_predictions": 0,
            "placement_correct": 0,
            "placement_wrong": 0,
            "placement_abstain_count_mismatch": 0,
            "placement_abstain_empty": 0,
            "ambiguous_site_context_hits": 0,
            "true_residual_sites_in_possible_mobility_envelope": 0,
        }
        for rep in REPS
    }
    eligible = 0
    reasons = Counter()
    prev1: str | None = None
    prev2: str | None = None
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        detail = place150.residual_edits(before, after, action)
        if detail is None:
            reasons["residual_detail_missing"] += 1
            continue
        edits, target_sem = detail
        ctx = r151.semantic_context(before, action, prev2, prev1)
        if ctx is None:
            reasons["semantic_context_warmup_or_missing"] += 1
            prev2, prev1 = prev1, target_sem
            continue

        eligible += 1
        sem_pred = unique(semantic_bank[ctx]) if ctx in semantic_bank else None
        true_edits = sorted(edits)
        src, dst = r151.mobility_envelope(before, action)
        broad_env = src | dst
        overlap = sum((r, c) in broad_env for r, c, _old, _new in true_edits)

        for rep in REPS:
            s = stats[rep]
            s["true_residual_sites_in_possible_mobility_envelope"] += overlap
            if sem_pred is None:
                continue
            s["semantic_predictions"] += 1
            if sem_pred == target_sem:
                s["semantic_correct"] += 1
            else:
                s["semantic_wrong"] += 1
            pred, why, ambiguous = predict_edits(before, action, sem_pred, rep, renderer_banks[rep])
            s["ambiguous_site_context_hits"] += ambiguous
            if pred is None:
                if why == "count_mismatch":
                    s["placement_abstain_count_mismatch"] += 1
                else:
                    s["placement_abstain_empty"] += 1
            else:
                s["placement_predictions"] += 1
                if pred == true_edits:
                    s["placement_correct"] += 1
                else:
                    s["placement_wrong"] += 1

        semantic_bank[ctx][target_sem] += 1
        residual_map = {(r, c): (old, new) for r, c, old, new in true_edits}
        for rep, bank in renderer_banks.items():
            radius, canonical, with_mobility = REPS[rep]
            for r, row in enumerate(before):
                for c, _old in enumerate(row):
                    key = r151.site_signature(before, r, c, action, radius, canonical, with_mobility, src, dst)
                    bank[key][residual_map.get((r, c), NOOP)] += 1

        prev2, prev1 = prev1, target_sem

    for rep, s in stats.items():
        s["semantic_accuracy"] = round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None
        s["placement_accuracy"] = round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None
        s["placement_coverage_of_eligible"] = round(s["placement_predictions"] / eligible, 6) if eligible else 0.0
        s["strict_zero_error_placement"] = bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0)
        s["renderer_contexts_final"] = len(renderer_banks[rep])
        s["renderer_conflicted_contexts_final"] = sum(len(counter) > 1 for counter in renderer_banks[rep].values())
    return {"eligible_transitions": eligible, "ineligible_reasons": dict(sorted(reasons.items())), "renderers": stats}


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = sum(p["eligible_transitions"] for p in parts)
    out: dict[str, Any] = {}
    hard: list[tuple[int, str]] = []
    for rep in REPS:
        keys = (
            "semantic_predictions", "semantic_correct", "semantic_wrong",
            "placement_predictions", "placement_correct", "placement_wrong",
            "placement_abstain_count_mismatch", "placement_abstain_empty",
            "ambiguous_site_context_hits", "true_residual_sites_in_possible_mobility_envelope",
        )
        s = {k: sum(p["renderers"][rep][k] for p in parts) for k in keys}
        pp = [p["renderers"][rep]["placement_predictions"] for p in parts]
        pc = [p["renderers"][rep]["placement_correct"] for p in parts]
        pw = [p["renderers"][rep]["placement_wrong"] for p in parts]
        sw = [p["renderers"][rep]["semantic_wrong"] for p in parts]
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
    return {"trace_count": len(parts), "eligible_transitions": eligible, "renderers": out, "best_zero_error_p0_p10_renderer": max(hard)[1] if hard else None, "per_trace": parts}


def run(paths: list[Path]) -> dict[str, Any]:
    parts = []
    traces = []
    for p in paths:
        a = audit_trace(base.load_events(p))
        parts.append(a)
        traces.append({"path": str(p), "audit": a})
    return {
        "schema": "deus/arc3-public-local-residual-renderer-role-repair-audit/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_LOCAL_RESIDUAL_RENDERER_ROLE_REPAIR_DIAGNOSTIC",
        "representation_change_from_rung151": {
            "changed": True,
            "change": "remove the hard possible-mobility source/destination exclusion that caused universal abstention; preserve every site and encode mobility membership as an optional local role feature",
        },
        "source_grounding": {"public_trace_repo": base.TUFA_REPO, "public_trace_commit": base.TUFA_COMMIT, "clean_room_implementation": True},
        "traces": traces,
        "aggregate": aggregate(parts),
        "diagnostic_gate": "LOCAL_RESIDUAL_RENDERER_ROLE_REPAIR_CHARACTERIZED",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "diagnostic_only": True,
            "renderer_inputs_available_pre_outcome": True,
            "semantic_prediction_prior_only": True,
            "renderer_prediction_prior_only": True,
            "current_targets_ingested_after_prediction": True,
            "current_outcome_used_for_eligibility_residual_isolation_and_scoring": True,
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
