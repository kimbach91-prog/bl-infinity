#!/usr/bin/env python3
"""Rung 136: prefix-only local transition-program world-model audit.

Representation change from rung 135
-----------------------------------
Rung 135 tested a tiny hand-written global rule bank. Rung 136 instead learns
*local executable transition programs* from observed outcomes. A program is an
exact before-patch -> after-patch rewrite, anchored only to the changed region
plus one-cell context and therefore independent of absolute board position.

For an exact-state-unseen current event, learned programs for the current action
are scanned against the visible board. A program is shadow-tested only after its
current prediction has been committed; it may affect a future candidate only
when it has support from >=2 distinct prior states and >=3 prior shadow tests
with zero error. Exact visible-state/action memory always has priority.

This is source-assisted replay on pinned public traces. It is not an independent
generalization, model/GPU/Kaggle execution, submission, leaderboard, or award
claim.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base

RUNG = 136
MIN_PROGRAM_SUPPORT = 2
MIN_PRIOR_SHADOW_TESTS = 3
PATCH_PADDING = 1
Grid = list[list[int]]


def extract_patch(board: Grid, r0: int, c0: int, r1: int, c1: int) -> Grid:
    return [row[c0 : c1 + 1] for row in board[r0 : r1 + 1]]


def infer_local_program(before: Grid, after: Grid) -> dict[str, Any] | None:
    if not base.same_shape(before, after) or before == after:
        return None
    h, w = len(before), len(before[0])
    diff = [(r, c) for r in range(h) for c in range(w) if before[r][c] != after[r][c]]
    if not diff:
        return None
    r0 = max(0, min(r for r, _ in diff) - PATCH_PADDING)
    c0 = max(0, min(c for _, c in diff) - PATCH_PADDING)
    r1 = min(h - 1, max(r for r, _ in diff) + PATCH_PADDING)
    c1 = min(w - 1, max(c for _, c in diff) + PATCH_PADDING)
    pre_patch = extract_patch(before, r0, c0, r1, c1)
    post_patch = extract_patch(after, r0, c0, r1, c1)
    # Exclude whole-board memorization. The learned lane must abstract away some
    # global state in order to count as an unseen-state transition program.
    if len(pre_patch) == h and len(pre_patch[0]) == w:
        return None
    return {
        "kind": "local_patch_rewrite",
        "h": len(pre_patch),
        "w": len(pre_patch[0]),
        "before_patch": pre_patch,
        "after_patch": post_patch,
    }


def find_patch(board: Grid, patch: Grid) -> list[tuple[int, int]]:
    h, w = len(board), len(board[0])
    ph, pw = len(patch), len(patch[0])
    if ph > h or pw > w:
        return []
    hits: list[tuple[int, int]] = []
    for r0 in range(h - ph + 1):
        for c0 in range(w - pw + 1):
            ok = True
            for rr in range(ph):
                if board[r0 + rr][c0 : c0 + pw] != patch[rr]:
                    ok = False
                    break
            if ok:
                hits.append((r0, c0))
    return hits


def apply_local_program(program: dict[str, Any], board: Grid) -> Grid | None:
    pre_patch = base.as_grid(program["before_patch"])
    post_patch = base.as_grid(program["after_patch"])
    if not base.same_shape(pre_patch, post_patch):
        return None
    hits = find_patch(board, pre_patch)
    # Ambiguous placement is fail-closed.
    if len(hits) != 1:
        return None
    r0, c0 = hits[0]
    out = [row[:] for row in board]
    for rr, row in enumerate(post_patch):
        out[r0 + rr][c0 : c0 + len(row)] = row[:]
    return out


def program_key(program: dict[str, Any]) -> str:
    return base.stable(program)


def qualified(stats: dict[str, int]) -> bool:
    return stats["tests"] >= MIN_PRIOR_SHADOW_TESTS and stats["wrong"] == 0


@dataclass
class Metrics:
    transitions: int = 0
    baseline_predictions: int = 0
    baseline_correct: int = 0
    baseline_wrong: int = 0
    candidate_predictions: int = 0
    candidate_correct: int = 0
    candidate_wrong: int = 0
    added_program_predictions: int = 0
    added_program_correct: int = 0
    added_program_wrong: int = 0
    program_shadow_tests: int = 0
    program_shadow_correct: int = 0
    program_shadow_wrong: int = 0
    no_qualified_program_abstentions: int = 0
    qualified_program_conflict_abstentions: int = 0
    qualified_program_applications: int = 0
    programs_inferred: int = 0
    stable_programs_final: int = 0
    reliability_qualified_programs_final: int = 0
    exact_unique_keys_final: int = 0

    def finalize(self) -> dict[str, Any]:
        d = asdict(self)
        d["baseline_accuracy"] = round(self.baseline_correct / self.baseline_predictions, 6) if self.baseline_predictions else None
        d["baseline_coverage"] = round(self.baseline_predictions / self.transitions, 6) if self.transitions else 0.0
        d["candidate_accuracy"] = round(self.candidate_correct / self.candidate_predictions, 6) if self.candidate_predictions else None
        d["candidate_coverage"] = round(self.candidate_predictions / self.transitions, 6) if self.transitions else 0.0
        d["added_program_accuracy"] = round(self.added_program_correct / self.added_program_predictions, 6) if self.added_program_predictions else None
        d["program_shadow_accuracy"] = round(self.program_shadow_correct / self.program_shadow_tests, 6) if self.program_shadow_tests else None
        return d


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_outcomes: dict[str, set[str]] = defaultdict(set)
    exact_exemplar: dict[tuple[str, str], Grid] = {}
    # action -> program_key -> metadata
    program_bank: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    shadow: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"tests": 0, "correct": 0, "wrong": 0})
    m = Metrics()
    pre = events[0]

    for event in events[1:]:
        if event.get("type") != "action":
            pre = event
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(event["board"])
        action = base.action_name(event)
        pre_digest = base.digest(before)
        exact_key = base.digest({"board": before, "action": action})
        actual_digest = base.digest(after)
        m.transitions += 1

        seen = exact_outcomes.get(exact_key, set())
        baseline_prediction: Grid | None = None
        if len(seen) == 1:
            exp_digest = next(iter(seen))
            baseline_prediction = exact_exemplar[(exact_key, exp_digest)]
            m.baseline_predictions += 1
            if baseline_prediction == after:
                m.baseline_correct += 1
            else:
                m.baseline_wrong += 1

        candidate_prediction = baseline_prediction
        candidate_from_program = False
        shadow_applicable: list[tuple[str, Grid]] = []

        if baseline_prediction is None:
            qualified_predictions: dict[str, Grid] = {}
            for pkey, entry in program_bank.get(action, {}).items():
                if entry["support"] < MIN_PROGRAM_SUPPORT or len(entry["pre_states"]) < MIN_PROGRAM_SUPPORT:
                    continue
                pred = apply_local_program(entry["program"], before)
                if pred is None:
                    continue
                shadow_applicable.append((pkey, pred))
                stats = shadow[(action, pkey)]
                if qualified(stats):
                    qualified_predictions[base.digest(pred)] = pred
                    m.qualified_program_applications += 1
            if not qualified_predictions:
                m.no_qualified_program_abstentions += 1
            elif len(qualified_predictions) > 1:
                m.qualified_program_conflict_abstentions += 1
            else:
                candidate_prediction = next(iter(qualified_predictions.values()))
                candidate_from_program = True

        if candidate_prediction is not None:
            m.candidate_predictions += 1
            correct = candidate_prediction == after
            if correct:
                m.candidate_correct += 1
            else:
                m.candidate_wrong += 1
            if candidate_from_program:
                m.added_program_predictions += 1
                if correct:
                    m.added_program_correct += 1
                else:
                    m.added_program_wrong += 1

        # Reveal current outcome only after current decision is fixed.
        for pkey, pred in shadow_applicable:
            stats = shadow[(action, pkey)]
            stats["tests"] += 1
            m.program_shadow_tests += 1
            if pred == after:
                stats["correct"] += 1
                m.program_shadow_correct += 1
            else:
                stats["wrong"] += 1
                m.program_shadow_wrong += 1

        # Learn from the now-observed transition only after evaluation.
        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key, actual_digest)] = [row[:] for row in after]
        program = infer_local_program(before, after)
        if program is not None:
            pkey = program_key(program)
            entry = program_bank[action].setdefault(
                pkey, {"program": program, "support": 0, "pre_states": set()}
            )
            entry["support"] += 1
            entry["pre_states"].add(pre_digest)
            m.programs_inferred += 1
        pre = event

    m.exact_unique_keys_final = len(exact_outcomes)
    m.stable_programs_final = sum(
        1 for by_program in program_bank.values() for entry in by_program.values()
        if entry["support"] >= MIN_PROGRAM_SUPPORT and len(entry["pre_states"]) >= MIN_PROGRAM_SUPPORT
    )
    m.reliability_qualified_programs_final = sum(1 for stats in shadow.values() if qualified(stats))
    return m.finalize()


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    summed = Metrics()
    fields = list(asdict(summed))
    for p in parts:
        for f in fields:
            setattr(summed, f, getattr(summed, f) + int(p[f]))
    return summed.finalize()


def run(paths: list[Path]) -> dict[str, Any]:
    per_trace: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for path in paths:
        events = base.load_events(path)
        metrics = audit_trace(events)
        per_trace.append(metrics)
        traces.append({"path": str(path), "board_events": len(events), "metrics": metrics})
    agg = aggregate(per_trace)
    strict_gain = (
        agg["added_program_predictions"] > 0
        and agg["added_program_correct"] > 0
        and agg["added_program_wrong"] == 0
        and agg["candidate_correct"] > agg["baseline_correct"]
        and agg["candidate_wrong"] <= agg["baseline_wrong"]
    )
    return {
        "schema": "deus/arc3-public-local-transition-program-prequential/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY_LOCAL_EXECUTABLE_PROGRAM_AUDIT",
        "representation_change_from_rung135": {
            "changed": True,
            "change": "replace hand-written global rule families with learned position-invariant local before-patch -> after-patch executable programs",
            "patch_padding": PATCH_PADDING,
            "minimum_program_support": MIN_PROGRAM_SUPPORT,
            "minimum_prior_shadow_tests": MIN_PRIOR_SHADOW_TESTS,
            "allowed_prior_shadow_wrong": 0,
            "ambiguous_patch_placement": "ABSTAIN",
            "whole_board_patch": "REJECT",
        },
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "architectural_reference_repo": base.TWIN_REPO,
            "architectural_reference_commit": base.TWIN_COMMIT,
            "clean_room_implementation": True,
            "upstream_twin_code_imported": False,
            "upstream_twin_code_copied": False,
        },
        "causality_contract": {
            "prediction_uses_current_outcome": False,
            "prediction_uses_future_transitions": False,
            "program_learned_only_after_observed_outcome": True,
            "candidate_qualification_uses_only_prior_shadow_outcomes": True,
            "current_outcome_added_to_shadow_only_after_current_decision": True,
            "exact_baseline_consulted_first": True,
            "maps_reset_between_trace_files": True,
        },
        "traces": traces,
        "aggregate": agg,
        "next_gate_signal": "STRICT_PREQUENTIAL_LOCAL_PROGRAM_GAIN" if strict_gain else "NO_STRICT_PREQUENTIAL_LOCAL_PROGRAM_GAIN",
        "promotion": {
            "strict_prequential_local_program_gain": strict_gain,
            "candidate_model_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "prefix_unseen_exact_state_prediction_measured": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "award_or_settlement_claim": False,
        },
    }


def synthetic_events() -> list[dict[str, Any]]:
    # Six globally different states share the same local rewrite at different
    # absolute locations. Two observations establish support, three later unseen
    # states shadow-validate it, and the sixth permits the first qualified use.
    events: list[dict[str, Any]] = []
    for i, col in enumerate((2, 4, 6, 8, 10, 12)):
        w = 18
        before = [[0] * w for _ in range(5)]
        after = [[0] * w for _ in range(5)]
        # Unique global marker keeps every exact state distinct and sits outside
        # the local rewrite patch.
        marker_col = (i * 3) % w
        before[0][marker_col] = 7
        after[0][marker_col] = 7
        before[2][col] = 1
        after[2][col + 1] = 1
        events.append({"type": "initial", "board": before, "level": 1})
        events.append({"type": "action", "board": after, "level": 1, "action_display": "RIGHT"})
    return events


def self_test() -> dict[str, Any]:
    m = audit_trace(synthetic_events())
    invariants = {
        "baseline_abstains_on_unique_states": m["baseline_predictions"] == 0,
        "stable_local_program_exists": m["stable_programs_final"] >= 1,
        "shadow_validation_occurs": m["program_shadow_tests"] >= 3,
        "shadow_validation_is_clean": m["program_shadow_wrong"] == 0,
        "qualified_program_eventually_acts": m["added_program_predictions"] >= 1,
        "qualified_program_is_correct": m["added_program_correct"] >= 1,
        "qualified_program_adds_no_error": m["added_program_wrong"] == 0,
    }
    return {
        "schema": "deus/arc3-public-local-transition-program-prequential-selftest/1",
        "rung": RUNG,
        "passed": all(invariants.values()),
        "invariants": invariants,
        "metrics": m,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        result = self_test()
        code = 0 if result["passed"] else 2
    else:
        if not args.input:
            raise SystemExit("at least one --input is required")
        result = run(args.input)
        code = 0
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
