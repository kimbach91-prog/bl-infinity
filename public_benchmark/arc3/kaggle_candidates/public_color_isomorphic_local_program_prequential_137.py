#!/usr/bin/env python3
"""Rung 137: color-isomorphic local executable transition programs.

Representation change from rung 136
-----------------------------------
Rung 136 required an exact local before-patch match, so visually identical local
causal structure using different color IDs fragmented into different programs.
Rung 137 canonicalizes colors by equality/first-occurrence roles inside the local
transition patch. The learned program is therefore a structural rewrite over
color roles rather than literal palette IDs.

The evaluator remains prefix-only and prequential: exact visible-state/action
memory has priority; a structural program must have >=2 prior-state support and
>=3 *prior* unseen-state shadow tests with zero errors before it may affect a
candidate. The current outcome is revealed only after the current decision.
Ambiguous structural placement, whole-board patches, or output roles not grounded
in the matched before-patch all cause abstention.

This is source-assisted replay on pinned public traces only; it is not independent
generalization, model/GPU/Kaggle execution, submission, leaderboard, or award
evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base

RUNG = 137
MIN_PROGRAM_SUPPORT = 2
MIN_PRIOR_SHADOW_TESTS = 3
PATCH_PADDING = 1
Grid = list[list[int]]


def extract_patch(board: Grid, r0: int, c0: int, r1: int, c1: int) -> Grid:
    return [row[c0:c1 + 1] for row in board[r0:r1 + 1]]


def canonicalize_pair(before: Grid, after: Grid) -> tuple[Grid, Grid]:
    """Canonicalize color IDs jointly, assigning labels by first occurrence.

    Before is traversed first so every label that can be instantiated at apply
    time is stable. New colors that occur only in the outcome receive later
    labels; such programs are allowed to exist but fail closed at application.
    """
    mapping: dict[int, int] = {}
    nxt = 0

    def canon(grid: Grid) -> Grid:
        nonlocal nxt
        out: Grid = []
        for row in grid:
            rr: list[int] = []
            for value in row:
                if value not in mapping:
                    mapping[value] = nxt
                    nxt += 1
                rr.append(mapping[value])
            out.append(rr)
        return out

    return canon(before), canon(after)


def canonicalize_single(grid: Grid) -> tuple[Grid, dict[int, int]]:
    """Return structural labels and label->actual-color map for one patch."""
    actual_to_label: dict[int, int] = {}
    label_to_actual: dict[int, int] = {}
    nxt = 0
    out: Grid = []
    for row in grid:
        rr: list[int] = []
        for value in row:
            if value not in actual_to_label:
                actual_to_label[value] = nxt
                label_to_actual[nxt] = value
                nxt += 1
            rr.append(actual_to_label[value])
        out.append(rr)
    return out, label_to_actual


def infer_program(before: Grid, after: Grid) -> dict[str, Any] | None:
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
    pre = extract_patch(before, r0, c0, r1, c1)
    post = extract_patch(after, r0, c0, r1, c1)
    if len(pre) == h and len(pre[0]) == w:
        return None
    pre_norm, post_norm = canonicalize_pair(pre, post)
    return {
        "kind": "color_isomorphic_local_rewrite",
        "h": len(pre_norm),
        "w": len(pre_norm[0]),
        "before_norm": pre_norm,
        "after_norm": post_norm,
    }


def structural_matches(board: Grid, before_norm: Grid) -> list[tuple[int, int, dict[int, int]]]:
    h, w = len(board), len(board[0])
    ph, pw = len(before_norm), len(before_norm[0])
    if ph > h or pw > w:
        return []
    hits: list[tuple[int, int, dict[int, int]]] = []
    for r0 in range(h - ph + 1):
        for c0 in range(w - pw + 1):
            patch = [row[c0:c0 + pw] for row in board[r0:r0 + ph]]
            norm, label_to_actual = canonicalize_single(patch)
            if norm == before_norm:
                hits.append((r0, c0, label_to_actual))
    return hits


def apply_program(program: dict[str, Any], board: Grid) -> Grid | None:
    before_norm = base.as_grid(program["before_norm"])
    after_norm = base.as_grid(program["after_norm"])
    if not base.same_shape(before_norm, after_norm):
        return None
    hits = structural_matches(board, before_norm)
    # Structural matching is intentionally fail-closed. Multiple locations mean
    # the program lacks a role selector and cannot act safely.
    if len(hits) != 1:
        return None
    r0, c0, label_to_actual = hits[0]
    labels_needed = {v for row in after_norm for v in row}
    if not labels_needed.issubset(label_to_actual):
        return None
    out = [row[:] for row in board]
    for rr, row in enumerate(after_norm):
        for cc, label in enumerate(row):
            out[r0 + rr][c0 + cc] = label_to_actual[label]
    return out


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
                pred = apply_program(entry["program"], before)
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

        # Outcome is revealed only after the current candidate decision.
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

        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key, actual_digest)] = [row[:] for row in after]
        program = infer_program(before, after)
        if program is not None:
            pkey = base.stable(program)
            entry = program_bank[action].setdefault(pkey, {"program": program, "support": 0, "pre_states": set()})
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
        "schema": "deus/arc3-public-color-isomorphic-local-program-prequential/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY_COLOR_ISOMORPHIC_LOCAL_PROGRAM_AUDIT",
        "representation_change_from_rung136": {
            "changed": True,
            "change": "canonicalize local transition colors into structural equality roles, allowing the same executable rewrite to share support across different literal palette IDs",
            "patch_padding": PATCH_PADDING,
            "minimum_program_support": MIN_PROGRAM_SUPPORT,
            "minimum_prior_shadow_tests": MIN_PRIOR_SHADOW_TESTS,
            "allowed_prior_shadow_wrong": 0,
            "ambiguous_structural_placement": "ABSTAIN",
            "ungrounded_output_color_role": "ABSTAIN",
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
        "next_gate_signal": "STRICT_PREQUENTIAL_COLOR_ISOMORPHIC_LOCAL_PROGRAM_GAIN" if strict_gain else "NO_STRICT_PREQUENTIAL_COLOR_ISOMORPHIC_LOCAL_PROGRAM_GAIN",
        "promotion": {
            "strict_prequential_color_isomorphic_local_program_gain": strict_gain,
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
    events: list[dict[str, Any]] = []
    colors = (1, 2, 3, 4, 5, 6)
    for i, (col, color) in enumerate(zip((2, 4, 6, 8, 10, 12), colors)):
        w = 18
        before = [[0] * w for _ in range(5)]
        after = [[0] * w for _ in range(5)]
        marker_col = (i * 3) % w
        marker_color = 8 + i
        before[0][marker_col] = marker_color
        after[0][marker_col] = marker_color
        before[2][col] = color
        after[2][col + 1] = color
        events.append({"type": "initial", "board": before, "level": 1})
        events.append({"type": "action", "board": after, "level": 1, "action_display": "RIGHT"})
    return events


def self_test() -> dict[str, Any]:
    m = audit_trace(synthetic_events())
    invariants = {
        "baseline_abstains_on_unique_states": m["baseline_predictions"] == 0,
        "stable_structural_program_exists": m["stable_programs_final"] >= 1,
        "shadow_validation_occurs": m["program_shadow_tests"] >= 3,
        "shadow_validation_is_clean": m["program_shadow_wrong"] == 0,
        "qualified_program_eventually_acts": m["added_program_predictions"] >= 1,
        "qualified_program_is_correct": m["added_program_correct"] >= 1,
        "qualified_program_adds_no_error": m["added_program_wrong"] == 0,
    }
    return {
        "schema": "deus/arc3-public-color-isomorphic-local-program-prequential-selftest/1",
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
