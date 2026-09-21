#!/usr/bin/env python3
"""Rung 132: bind the retrodiction verifier to real pinned public ARC-AGI-3 traces.

This is a CPU-only, clean-room public-trace audit.  It does not call a model,
Kaggle, or a competition endpoint.  Each prediction is made from a prefix of
already-observed transitions only; the current transition outcome is revealed
only after the prediction/abstention decision has been recorded.

The purpose is narrow: test whether visible-state deterministic lookup is
observationally identifiable on real public traces, and whether explicit
already-visible context (level and/or the previous observed effect) repairs
aliasing without pretending that public replay is independent generalization.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable

RUNG = 132
TUFA_REPO = "Tufalabs/duck-harness"
TUFA_COMMIT = "7652836056c59e044f093e3c13ed7438c814169e"
Grid = list[list[int]]


def stable(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(x: Any) -> str:
    return hashlib.sha256(stable(x).encode("utf-8")).hexdigest()


def as_grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value:
        raise ValueError("board must be a non-empty list")
    out: Grid = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError("board rows must be non-empty lists")
        vals = [int(v) for v in row]
        width = len(vals) if width is None else width
        if len(vals) != width:
            raise ValueError("ragged board")
        out.append(vals)
    return out


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: object required")
        if obj.get("type") not in {"initial", "action"} or "board" not in obj:
            continue
        as_grid(obj["board"])
        events.append(obj)
    if len(events) < 2:
        raise ValueError(f"{path}: fewer than two board-bearing events")
    return events


def effect_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    b = as_grid(before["board"])
    a = as_grid(after["board"])
    return {
        "board_changed": b != a,
        "level_delta": int(after.get("level") or 0) - int(before.get("level") or 0),
        "reward_positive": float(after.get("reward") or 0.0) > 0.0,
        "level_completed": bool(after.get("level_completed")),
        "game_over": bool(after.get("game_over")),
        "run_complete": bool(after.get("run_complete")),
    }


def action_name(event: dict[str, Any]) -> str:
    return str(event.get("action_display") or event.get("action_name") or "")


def rep_raw(pre: dict[str, Any], action: str, prev_effect: dict[str, Any] | None) -> Any:
    return {"board": as_grid(pre["board"]), "action": action}


def rep_level(pre: dict[str, Any], action: str, prev_effect: dict[str, Any] | None) -> Any:
    return {"board": as_grid(pre["board"]), "level": int(pre.get("level") or 0), "action": action}


def rep_prev(pre: dict[str, Any], action: str, prev_effect: dict[str, Any] | None) -> Any:
    return {"board": as_grid(pre["board"]), "previous_effect": prev_effect, "action": action}


def rep_level_prev(pre: dict[str, Any], action: str, prev_effect: dict[str, Any] | None) -> Any:
    return {
        "board": as_grid(pre["board"]),
        "level": int(pre.get("level") or 0),
        "previous_effect": prev_effect,
        "action": action,
    }


REPRESENTATIONS: dict[str, Callable[[dict[str, Any], str, dict[str, Any] | None], Any]] = {
    "visible_board_action": rep_raw,
    "visible_board_level_action": rep_level,
    "visible_board_prev_effect_action": rep_prev,
    "visible_board_level_prev_effect_action": rep_level_prev,
}


@dataclass
class Metrics:
    transitions: int = 0
    unseen_abstentions: int = 0
    conflict_abstentions: int = 0
    predictions: int = 0
    correct: int = 0
    wrong: int = 0
    final_unique_keys: int = 0
    final_repeated_keys: int = 0
    final_conflict_keys: int = 0
    repeated_transition_support: int = 0

    def finalize(self) -> dict[str, Any]:
        d = asdict(self)
        d["prediction_accuracy"] = round(self.correct / self.predictions, 6) if self.predictions else None
        d["prediction_coverage"] = round(self.predictions / self.transitions, 6) if self.transitions else 0.0
        d["wrong_rate_over_predictions"] = round(self.wrong / self.predictions, 6) if self.predictions else None
        d["repeat_support_ratio"] = round(self.repeated_transition_support / self.transitions, 6) if self.transitions else 0.0
        d["conflict_key_ratio"] = round(self.final_conflict_keys / self.final_repeated_keys, 6) if self.final_repeated_keys else 0.0
        return d


def audit_trace(events: list[dict[str, Any]], rep_fn: Callable[[dict[str, Any], str, dict[str, Any] | None], Any]) -> dict[str, Any]:
    table: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    exemplar: dict[tuple[str, str], Grid] = {}
    metrics = Metrics()
    prev_effect: dict[str, Any] | None = None
    pre = events[0]

    for event in events[1:]:
        if event.get("type") != "action":
            pre = event
            prev_effect = None
            continue
        action = action_name(event)
        rep = rep_fn(pre, action, prev_effect)
        k = digest(rep)
        actual_board = as_grid(event["board"])
        actual_digest = digest(actual_board)
        seen = table.get(k)

        metrics.transitions += 1
        if not seen:
            metrics.unseen_abstentions += 1
        elif len(seen) > 1:
            metrics.conflict_abstentions += 1
        else:
            metrics.predictions += 1
            expected_digest = next(iter(seen))
            expected_board = exemplar[(k, expected_digest)]
            # Check both digest and full board so a hash is never treated as proof by itself.
            if expected_digest == actual_digest and expected_board == actual_board:
                metrics.correct += 1
            else:
                metrics.wrong += 1

        table.setdefault(k, set()).add(actual_digest)
        counts[k] = counts.get(k, 0) + 1
        exemplar[(k, actual_digest)] = copy.deepcopy(actual_board)
        prev_effect = effect_summary(pre, event)
        pre = event

    metrics.final_unique_keys = len(table)
    metrics.final_repeated_keys = sum(1 for k, n in counts.items() if n > 1)
    metrics.final_conflict_keys = sum(1 for outcomes in table.values() if len(outcomes) > 1)
    metrics.repeated_transition_support = sum(n for n in counts.values() if n > 1)
    return metrics.finalize()


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    summed = Metrics()
    for x in items:
        for f in (
            "transitions", "unseen_abstentions", "conflict_abstentions", "predictions",
            "correct", "wrong", "final_unique_keys", "final_repeated_keys",
            "final_conflict_keys", "repeated_transition_support",
        ):
            setattr(summed, f, getattr(summed, f) + int(x[f]))
    return summed.finalize()


def run(paths: list[Path]) -> dict[str, Any]:
    by_rep: dict[str, list[dict[str, Any]]] = {name: [] for name in REPRESENTATIONS}
    trace_meta: list[dict[str, Any]] = []
    for path in paths:
        events = load_events(path)
        trace_meta.append({"path": str(path), "board_events": len(events)})
        for name, fn in REPRESENTATIONS.items():
            by_rep[name].append(audit_trace(events, fn))

    agg = {name: aggregate(parts) for name, parts in by_rep.items()}
    raw = agg["visible_board_action"]
    contextual: dict[str, Any] = {}
    for name in ("visible_board_level_action", "visible_board_prev_effect_action", "visible_board_level_prev_effect_action"):
        m = agg[name]
        raw_acc = raw["prediction_accuracy"]
        acc = m["prediction_accuracy"]
        contextual[name] = {
            "wrong_delta_vs_raw": m["wrong"] - raw["wrong"],
            "prediction_delta_vs_raw": m["predictions"] - raw["predictions"],
            "conflict_key_delta_vs_raw": m["final_conflict_keys"] - raw["final_conflict_keys"],
            "accuracy_delta_vs_raw": None if raw_acc is None or acc is None else round(acc - raw_acc, 6),
            "non_dominated_retrodiction_signal": (
                m["wrong"] <= raw["wrong"]
                and m["correct"] >= raw["correct"]
                and m["final_conflict_keys"] <= raw["final_conflict_keys"]
                and m["predictions"] > 0
            ),
        }

    any_context_signal = any(x["non_dominated_retrodiction_signal"] for x in contextual.values())
    return {
        "schema": "deus/arc3-public-retrodiction-prefix-bind/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREFIX_ONLY",
        "source_grounding": {
            "public_trace_repo": TUFA_REPO,
            "public_trace_commit": TUFA_COMMIT,
            "trace_paths": [str(p) for p in paths],
            "clean_room_implementation": True,
            "upstream_code_imported": False,
            "upstream_code_copied": False,
        },
        "causality_contract": {
            "prediction_key_uses_current_outcome": False,
            "prediction_uses_future_transitions": False,
            "current_outcome_ingested_only_after_prediction_or_abstention": True,
            "maps_reset_between_traces": True,
        },
        "traces": trace_meta,
        "aggregate": agg,
        "context_comparison": contextual,
        "next_gate_signal": "CONTEXT_RETRODICTION_SIGNAL" if any_context_signal else "NO_CONTEXT_RETRODICTION_SIGNAL",
        "promotion": {
            "public_harness_bind_verified": True,
            "candidate_model_promotion": False,
            "kaggle_packaging": False,
            "reason": "public prefix-retrodiction evidence can select a representation for a later fixed-model A/B, but cannot establish solver or hidden-score gain",
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "award_or_settlement_claim": False,
        },
    }


def self_test() -> dict[str, Any]:
    # Same visible board/action has two hidden regimes.  Level is an explicitly
    # visible pre-action context signal and must resolve the alias without future data.
    a = [[1, 0, 0]]
    b = [[0, 1, 0]]
    c = [[0, 0, 1]]
    events: list[dict[str, Any]] = [{"type": "initial", "board": a, "level": 1}]
    # Repeat board A/RIGHT twice at each visible level, with level-specific outcome.
    for level, out in ((1, b), (1, b), (2, c), (2, c), (1, b), (2, c)):
        events.append({"type": "action", "board": out, "level": level, "action_display": "RIGHT"})
        events.append({"type": "initial", "board": a, "level": level})
    # Drop trailing reset; parser/auditor accepts interspersed initial events.
    events = events[:-1]
    raw = audit_trace(events, rep_raw)
    level = audit_trace(events, rep_level)
    invariants = {
        "raw_detects_regime_aliasing": raw["wrong"] > 0 or raw["final_conflict_keys"] > 0,
        "visible_level_reduces_conflicts": level["final_conflict_keys"] < raw["final_conflict_keys"],
        "visible_level_has_no_wrong_prefix_prediction": level["wrong"] == 0,
        "visible_level_keeps_prefix_predictions": level["predictions"] > 0,
    }
    return {
        "schema": "deus/arc3-public-retrodiction-prefix-bind-selftest/1",
        "passed": all(invariants.values()),
        "invariants": invariants,
        "raw": raw,
        "visible_level": level,
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
