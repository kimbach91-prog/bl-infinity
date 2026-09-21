#!/usr/bin/env python3
"""Rung 135: prequential reliability gate for rung-134 executable rules.

Representation change from rung 134: fitting a rule twice is not enough to let it
act. Every stable rule is first shadow-tested on exact-state-unseen prefix events.
A rule may contribute a candidate prediction only after at least three *prior*
shadow tests with zero errors. Current outcome is revealed only after the current
candidate decision, then becomes one additional shadow-validation datum.

This remains source-assisted public-trace replay, not independent generalization,
model gain, GPU execution, Kaggle execution, submission, or leaderboard evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base

RUNG = 135
MIN_RULE_SUPPORT = 2
MIN_PRIOR_SHADOW_TESTS = 3
Grid = list[list[int]]


@dataclass
class Metrics:
    transitions: int = 0
    baseline_predictions: int = 0
    baseline_correct: int = 0
    baseline_wrong: int = 0
    candidate_predictions: int = 0
    candidate_correct: int = 0
    candidate_wrong: int = 0
    added_promoted_rule_predictions: int = 0
    added_promoted_rule_correct: int = 0
    added_promoted_rule_wrong: int = 0
    shadow_rule_tests: int = 0
    shadow_rule_correct: int = 0
    shadow_rule_wrong: int = 0
    no_reliable_rule_abstentions: int = 0
    reliable_rule_conflict_abstentions: int = 0
    reliable_rule_applications: int = 0
    exact_unique_keys_final: int = 0
    stable_rules_final: int = 0
    reliability_qualified_rules_final: int = 0

    def finalize(self) -> dict[str, Any]:
        d = asdict(self)
        d["baseline_accuracy"] = round(self.baseline_correct / self.baseline_predictions, 6) if self.baseline_predictions else None
        d["baseline_coverage"] = round(self.baseline_predictions / self.transitions, 6) if self.transitions else 0.0
        d["candidate_accuracy"] = round(self.candidate_correct / self.candidate_predictions, 6) if self.candidate_predictions else None
        d["candidate_coverage"] = round(self.candidate_predictions / self.transitions, 6) if self.transitions else 0.0
        d["added_promoted_rule_accuracy"] = round(self.added_promoted_rule_correct / self.added_promoted_rule_predictions, 6) if self.added_promoted_rule_predictions else None
        d["shadow_rule_accuracy"] = round(self.shadow_rule_correct / self.shadow_rule_tests, 6) if self.shadow_rule_tests else None
        return d


def qualified(stats: dict[str, int]) -> bool:
    return stats["tests"] >= MIN_PRIOR_SHADOW_TESTS and stats["wrong"] == 0


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact_outcomes: dict[str, set[str]] = defaultdict(set)
    exact_exemplar: dict[tuple[str, str], Grid] = {}
    rule_bank: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
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
        candidate_from_rule = False
        shadow_applicable: list[tuple[str, Grid]] = []

        # Only exact-unseen events exercise off-state executable rules.
        if baseline_prediction is None:
            reliable_predictions: dict[str, Grid] = {}
            for rule_key, entry in rule_bank.get(action, {}).items():
                if entry["support"] < MIN_RULE_SUPPORT or len(entry["pre_states"]) < MIN_RULE_SUPPORT:
                    continue
                pred = base.apply_rule(entry["rule"], before)
                if pred is None:
                    continue
                shadow_applicable.append((rule_key, pred))
                stats = shadow[(action, rule_key)]
                if qualified(stats):
                    reliable_predictions[base.digest(pred)] = pred
                    m.reliable_rule_applications += 1
            if not reliable_predictions:
                m.no_reliable_rule_abstentions += 1
            elif len(reliable_predictions) > 1:
                m.reliable_rule_conflict_abstentions += 1
            else:
                candidate_prediction = next(iter(reliable_predictions.values()))
                candidate_from_rule = True

        if candidate_prediction is not None:
            m.candidate_predictions += 1
            correct = candidate_prediction == after
            if correct:
                m.candidate_correct += 1
            else:
                m.candidate_wrong += 1
            if candidate_from_rule:
                m.added_promoted_rule_predictions += 1
                if correct:
                    m.added_promoted_rule_correct += 1
                else:
                    m.added_promoted_rule_wrong += 1

        # Current outcome is now revealed for shadow validation; this cannot affect
        # the already-made current candidate decision.
        for rule_key, pred in shadow_applicable:
            stats = shadow[(action, rule_key)]
            stats["tests"] += 1
            m.shadow_rule_tests += 1
            if pred == after:
                stats["correct"] += 1
                m.shadow_rule_correct += 1
            else:
                stats["wrong"] += 1
                m.shadow_rule_wrong += 1

        # Ingest exact outcome and infer new rules only after evaluation.
        exact_outcomes[exact_key].add(actual_digest)
        exact_exemplar[(exact_key, actual_digest)] = [row[:] for row in after]
        for rule in base.infer_rules(before, after):
            rule_key = base.stable(rule)
            entry = rule_bank[action].setdefault(rule_key, {"rule": rule, "support": 0, "pre_states": set()})
            entry["support"] += 1
            entry["pre_states"].add(pre_digest)
        pre = event

    m.exact_unique_keys_final = len(exact_outcomes)
    m.stable_rules_final = sum(
        1 for by_rule in rule_bank.values() for entry in by_rule.values()
        if entry["support"] >= MIN_RULE_SUPPORT and len(entry["pre_states"]) >= MIN_RULE_SUPPORT
    )
    m.reliability_qualified_rules_final = sum(1 for stats in shadow.values() if qualified(stats))
    return m.finalize()


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    summed = Metrics()
    fields = list(asdict(summed))
    for p in parts:
        for f in fields:
            setattr(summed, f, getattr(summed, f) + int(p[f]))
    return summed.finalize()


def run(paths: list[Path]) -> dict[str, Any]:
    per_trace = []
    traces = []
    for path in paths:
        events = base.load_events(path)
        metrics = audit_trace(events)
        per_trace.append(metrics)
        traces.append({"path": str(path), "board_events": len(events), "metrics": metrics})
    agg = aggregate(per_trace)
    strict_gain = (
        agg["added_promoted_rule_predictions"] > 0
        and agg["added_promoted_rule_correct"] > 0
        and agg["added_promoted_rule_wrong"] == 0
        and agg["candidate_correct"] > agg["baseline_correct"]
        and agg["candidate_wrong"] <= agg["baseline_wrong"]
    )
    return {
        "schema": "deus/arc3-public-executable-world-model-prequential/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY_PREQUENTIAL_RELIABILITY_GATE",
        "representation_change_from_rung134": {
            "changed": True,
            "change": "stable executable rules must pass prior out-of-state shadow validation before candidate use",
            "minimum_prior_shadow_tests": MIN_PRIOR_SHADOW_TESTS,
            "allowed_prior_shadow_wrong": 0,
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
            "candidate_qualification_uses_only_prior_shadow_outcomes": True,
            "current_outcome_added_to_shadow_only_after_current_decision": True,
            "rule_is_learned_only_after_observed_outcome": True,
            "exact_baseline_consulted_first": True,
            "maps_reset_between_trace_files": True,
        },
        "traces": traces,
        "aggregate": agg,
        "next_gate_signal": "STRICT_PREQUENTIAL_EXECUTABLE_RULE_GAIN" if strict_gain else "NO_STRICT_PREQUENTIAL_EXECUTABLE_RULE_GAIN",
        "promotion": {
            "strict_prequential_rule_gain": strict_gain,
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
    # Six unique one-cell states, each shifts right. First two create the stable
    # rule, next three are shadow validations, sixth is the first qualified use.
    events: list[dict[str, Any]] = []
    for width, pos in [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5)]:
        before = [[0] * width]
        after = [[0] * width]
        before[0][pos] = 1
        after[0][pos + 1] = 1
        events.append({"type": "initial", "board": before, "level": 1})
        events.append({"type": "action", "board": after, "level": 1, "action_display": "RIGHT"})
    return events


def self_test() -> dict[str, Any]:
    m = audit_trace(synthetic_events())
    invariants = {
        "baseline_abstains_on_unique_states": m["baseline_predictions"] == 0,
        "shadow_validation_occurs": m["shadow_rule_tests"] >= 3,
        "shadow_validation_is_clean": m["shadow_rule_wrong"] == 0,
        "qualified_rule_eventually_acts": m["added_promoted_rule_predictions"] >= 1,
        "qualified_rule_is_correct": m["added_promoted_rule_correct"] >= 1,
        "qualified_rule_adds_no_error": m["added_promoted_rule_wrong"] == 0,
    }
    return {"schema": "deus/arc3-public-executable-world-model-prequential-selftest/1", "rung": RUNG, "passed": all(invariants.values()), "invariants": invariants, "metrics": m}


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
