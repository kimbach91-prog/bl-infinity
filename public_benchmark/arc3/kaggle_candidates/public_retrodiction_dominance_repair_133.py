#!/usr/bin/env python3
"""Rung 133: repair the rung-132 context dominance classifier.

Rung 132 correctly executed prefix-only public retrodiction, but its label
`non_dominated_retrodiction_signal` treated an exactly-equal context encoding as
positive evidence.  This rung leaves all trace/prefix mechanics unchanged and
repairs only the promotion semantics: a context representation must be no worse
on correctness, conflict count, and prediction coverage, AND strictly improve
at least one of those dimensions before it can emit a context-gain signal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import public_retrodiction_prefix_bind_132 as base

RUNG = 133


def dominates_strictly(raw: dict, cand: dict) -> bool:
    no_worse = (
        cand["wrong"] <= raw["wrong"]
        and cand["correct"] >= raw["correct"]
        and cand["final_conflict_keys"] <= raw["final_conflict_keys"]
        and cand["predictions"] >= raw["predictions"]
    )
    strict = (
        cand["wrong"] < raw["wrong"]
        or cand["correct"] > raw["correct"]
        or cand["final_conflict_keys"] < raw["final_conflict_keys"]
        or cand["predictions"] > raw["predictions"]
    )
    return bool(no_worse and strict and cand["predictions"] > 0)


def repaired(paths: list[Path]) -> dict:
    d = base.run(paths)
    raw = d["aggregate"]["visible_board_action"]
    comparison = {}
    for name in (
        "visible_board_level_action",
        "visible_board_prev_effect_action",
        "visible_board_level_prev_effect_action",
    ):
        m = d["aggregate"][name]
        raw_acc = raw["prediction_accuracy"]
        acc = m["prediction_accuracy"]
        strict = dominates_strictly(raw, m)
        comparison[name] = {
            "wrong_delta_vs_raw": m["wrong"] - raw["wrong"],
            "correct_delta_vs_raw": m["correct"] - raw["correct"],
            "prediction_delta_vs_raw": m["predictions"] - raw["predictions"],
            "conflict_key_delta_vs_raw": m["final_conflict_keys"] - raw["final_conflict_keys"],
            "accuracy_delta_vs_raw": None if raw_acc is None or acc is None else round(acc - raw_acc, 6),
            "strict_context_improvement": strict,
        }
    any_gain = any(x["strict_context_improvement"] for x in comparison.values())
    d["schema"] = "deus/arc3-public-retrodiction-prefix-bind/2"
    d["rung"] = RUNG
    d["repair"] = {
        "repaired_from_rung": 132,
        "representation_changed": False,
        "trace_execution_changed": False,
        "classification_changed": True,
        "reason": "exact equality is neutral evidence, not a positive context-gain signal",
    }
    d["context_comparison"] = comparison
    d["next_gate_signal"] = "STRICT_CONTEXT_RETRODICTION_GAIN" if any_gain else "NO_STRICT_CONTEXT_RETRODICTION_GAIN"
    d["promotion"]["candidate_model_promotion"] = False
    d["promotion"]["kaggle_packaging"] = False
    d["promotion"]["reason"] = (
        "public prefix-only retrodiction selects no extra context layer unless it strictly dominates raw visible-board/action; "
        "this is harness evidence only, not solver or Kaggle gain"
    )
    return d


def self_test() -> dict:
    raw = {"wrong": 0, "correct": 10, "final_conflict_keys": 0, "predictions": 10}
    equal = dict(raw)
    better = {"wrong": 0, "correct": 11, "final_conflict_keys": 0, "predictions": 11}
    less_coverage = {"wrong": 0, "correct": 9, "final_conflict_keys": 0, "predictions": 9}
    invariants = {
        "equality_is_not_gain": dominates_strictly(raw, equal) is False,
        "strict_more_correct_coverage_is_gain": dominates_strictly(raw, better) is True,
        "lower_coverage_is_not_gain": dominates_strictly(raw, less_coverage) is False,
    }
    return {"schema": "deus/arc3-retrodiction-dominance-repair-selftest/1", "passed": all(invariants.values()), "invariants": invariants}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        d = self_test()
        code = 0 if d["passed"] else 2
    else:
        if not args.input:
            raise SystemExit("at least one --input is required")
        d = repaired(args.input)
        code = 0
    text = json.dumps(d, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
