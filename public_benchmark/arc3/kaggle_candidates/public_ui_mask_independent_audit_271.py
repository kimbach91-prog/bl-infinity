#!/usr/bin/env python3
"""R271 independent audit of R270 frozen UI-mask representation gate.

This auditor intentionally imports no R246/R251/R268/R270 modules. It
reimplements only the minimal event parser, canonical JSON digest, static
UI-mask transform, deterministic (state,action)->next-state table, and frozen
p0-p4 -> p10-p19 evaluator using Python stdlib.

The 14-game candidate set and expected aggregate are frozen from completed R270
before this file is executed. p5-p9 are neither staged nor read here.

Truth boundary: public trace audit only; source-assisted representation idea;
not independent hidden-set generalization, not a full solver, not Kaggle score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

RUNG = 271
SENTINEL = 16
R270_RUN = 35804180491
R270_ARTIFACT_ID = 10727555733
R270_HEAD = "cca32fc25ea33fa1a9378dd9a409c281d9ac1f9a"
R270_ARTIFACT_ZIP_SHA256 = "6d98e35ad9dda2b010e6bdd5ec2e0a8f3c7343b11012aa3e062d78e4bae27c84"
FROZEN_GAMES = (
    "ar25-0c556536",
    "ft09-0d8bbf25",
    "ka59-38d34dbb",
    "lf52-271a04aa",
    "lp85-305b61c3",
    "r11l-495a7899",
    "re86-8af5384d",
    "s5i5-18d95033",
    "su15-1944f8ab",
    "tn36-ef4dde99",
    "tr87-cd924810",
    "tu93-0768757b",
    "vc33-5430563c",
    "wa30-ee6fef47",
)
EXPECTED_PNUMS = tuple(range(5)) + tuple(range(10, 20))
EXPECTED_R270_AGGREGATE = {
    "raw_transitions": 17185,
    "raw_predictions": 1943,
    "raw_correct": 1867,
    "raw_wrong": 76,
    "raw_abstain": 15242,
    "ui_mask_transitions": 17185,
    "ui_mask_predictions": 5066,
    "ui_mask_correct": 5066,
    "ui_mask_wrong": 0,
    "ui_mask_abstain": 12119,
    "correct_delta": 3199,
    "wrong_delta": -76,
}


def pnum(path: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", path.name)
    return int(m.group(1)) if m else -1


def game_id(path: Path) -> str:
    m = re.match(r"(.+)_p\d+_events\.jsonl$", path.name)
    return m.group(1) if m else path.stem


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_events(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get("type") in {"initial", "action"} and isinstance(obj.get("board"), list):
            out.append(obj)
    if len(out) < 2:
        raise ValueError(f"{path}: insufficient events")
    return out


def action_name(event: dict[str, Any]) -> str:
    return str(event.get("action_display") or event.get("action_name") or "")


def transition_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        events = load_events(path)
        pre = events[0]
        for event in events[1:]:
            if event.get("type") != "action":
                pre = event
                continue
            before = [[int(v) for v in row] for row in pre["board"]]
            after = [[int(v) for v in row] for row in event["board"]]
            if before and after and len(before) == len(after) and len(before[0]) == len(after[0]):
                rows.append({
                    "before": before,
                    "after": after,
                    "action": action_name(event),
                    "trace": path.name,
                })
            pre = event
    return rows


def static_ui_mask(board: list[list[int]]) -> list[list[int]]:
    x = [list(map(int, row)) for row in board]
    if not x or not x[0]:
        return x
    h, w = len(x), len(x[0])
    for r in range(h):
        x[r][0] = SENTINEL
        if w > 1:
            x[r][w - 1] = SENTINEL
    for r in {0, 1, h - 1}:
        if 0 <= r < h:
            for c in range(w):
                x[r][c] = SENTINEL
    return x


def state_key(board: list[list[int]], mode: str) -> str:
    if mode == "raw":
        return digest(board)
    if mode == "ui_mask":
        return digest(static_ui_mask(board))
    raise KeyError(mode)


def fit_table(rows: list[dict[str, Any]], mode: str) -> tuple[dict[tuple[str, str], str], dict[str, int]]:
    observations: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    before_states: set[str] = set()
    for row in rows:
        before = state_key(row["before"], mode)
        after = state_key(row["after"], mode)
        before_states.add(before)
        observations[(before, row["action"])][after] += 1
    deterministic: dict[tuple[str, str], str] = {}
    ambiguous = 0
    for key, counter in observations.items():
        if len(counter) == 1:
            deterministic[key] = next(iter(counter))
        else:
            ambiguous += 1
    return deterministic, {
        "unique_before_states": len(before_states),
        "state_action_keys": len(observations),
        "deterministic_keys": len(deterministic),
        "ambiguous_keys": ambiguous,
    }


def evaluate(rows: list[dict[str, Any]], table: dict[tuple[str, str], str], mode: str) -> dict[str, Any]:
    s: Counter[str] = Counter()
    for row in rows:
        s["transitions"] += 1
        key = (state_key(row["before"], mode), row["action"])
        prediction = table.get(key)
        if prediction is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        if prediction == state_key(row["after"], mode):
            s["correct"] += 1
        else:
            s["wrong"] += 1
    predictions = s["predictions"]
    return {
        **dict(s),
        "accuracy": round(s["correct"] / predictions, 6) if predictions else None,
        "coverage": round(s["predictions"] / s["transitions"], 6) if s["transitions"] else 0.0,
    }


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ordered = sorted(paths, key=pnum)
    nums = tuple(pnum(p) for p in ordered)
    if nums != EXPECTED_PNUMS:
        raise ValueError(f"exact p0-p4+p10-p19 required, got {nums}")
    fit_paths = [p for p in ordered if 0 <= pnum(p) <= 4]
    holdout_paths = [p for p in ordered if 10 <= pnum(p) <= 19]
    fit_rows = transition_rows(fit_paths)
    holdout_rows = transition_rows(holdout_paths)
    out: dict[str, Any] = {}
    for mode in ("raw", "ui_mask"):
        table, stats = fit_table(fit_rows, mode)
        out[mode] = {
            "fit": stats,
            "holdout": evaluate(holdout_rows, table, mode),
        }
    raw = out["raw"]["holdout"]
    masked = out["ui_mask"]["holdout"]
    out["delta"] = {
        "correct": int(masked.get("correct", 0)) - int(raw.get("correct", 0)),
        "wrong": int(masked.get("wrong", 0)) - int(raw.get("wrong", 0)),
        "predictions": int(masked.get("predictions", 0)) - int(raw.get("predictions", 0)),
    }
    out["game_gate"] = bool(
        int(masked.get("wrong", 0)) == 0
        and int(masked.get("correct", 0)) > int(raw.get("correct", 0))
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    by_game: dict[str, list[Path]] = defaultdict(list)
    for path in args.input:
        by_game[game_id(path)].append(path)
    if set(by_game) != set(FROZEN_GAMES):
        raise SystemExit(
            f"input games mismatch: missing={sorted(set(FROZEN_GAMES)-set(by_game))} "
            f"extra={sorted(set(by_game)-set(FROZEN_GAMES))}"
        )

    games = {game: evaluate_game(by_game[game]) for game in FROZEN_GAMES}
    aggregate: Counter[str] = Counter()
    for result in games.values():
        for mode in ("raw", "ui_mask"):
            metrics = result[mode]["holdout"]
            for key in ("transitions", "predictions", "correct", "wrong", "abstain"):
                aggregate[f"{mode}_{key}"] += int(metrics.get(key, 0) or 0)

    actual = dict(aggregate)
    actual["correct_delta"] = aggregate["ui_mask_correct"] - aggregate["raw_correct"]
    actual["wrong_delta"] = aggregate["ui_mask_wrong"] - aggregate["raw_wrong"]
    actual["raw_accuracy"] = round(aggregate["raw_correct"] / aggregate["raw_predictions"], 6)
    actual["ui_mask_accuracy"] = round(aggregate["ui_mask_correct"] / aggregate["ui_mask_predictions"], 6)

    aggregate_match = all(actual.get(k) == v for k, v in EXPECTED_R270_AGGREGATE.items())
    promoted_games = [game for game, result in games.items() if result["game_gate"]]
    all_game_gates = set(promoted_games) == set(FROZEN_GAMES)
    passed = bool(
        aggregate_match
        and all_game_gates
        and aggregate["ui_mask_wrong"] == 0
        and aggregate["ui_mask_correct"] > aggregate["raw_correct"]
    )

    output = {
        "schema": "deus/arc3-r271-ui-mask-independent-audit/1",
        "rung": RUNG,
        "audit_of": {
            "run": R270_RUN,
            "head": R270_HEAD,
            "artifact_id": R270_ARTIFACT_ID,
            "artifact_zip_sha256": R270_ARTIFACT_ZIP_SHA256,
        },
        "independence": {
            "imports_prior_deus_solver_modules": False,
            "minimal_semantics_reimplemented": [
                "event_parser",
                "action_name",
                "canonical_json_digest",
                "static_ui_mask",
                "deterministic_state_action_table",
                "frozen_evaluator",
            ],
            "p5_p9_staged_or_read": False,
        },
        "protocol": {
            "candidate_set": "frozen from completed R268/R270 before audit",
            "fit": "p0-p4",
            "audit_eval": "p10-p19",
            "model_update_on_p10_p19": False,
            "selector_retune_on_p10_p19": False,
            "expected_aggregate_source": "completed R270 receipt, fixed before R271 execution",
        },
        "expected_r270_aggregate": EXPECTED_R270_AGGREGATE,
        "actual_aggregate": actual,
        "aggregate_match": aggregate_match,
        "promoted_games": promoted_games,
        "all_14_game_gates_match_pass": all_game_gates,
        "games": games,
        "verdict": "AUDIT_PASS" if passed else "AUDIT_FAIL",
        "truth": {
            "public_trace_only": True,
            "source_assisted_representation_idea": True,
            "independent_implementation_audit": True,
            "independent_hidden_generalization_claim": False,
            "full_solver_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "official_leaderboard_score_claim": False,
            "submission_quota_spent_by_r271": False,
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": output["verdict"],
        "aggregate_match": aggregate_match,
        "actual_aggregate": actual,
        "promoted_game_count": len(promoted_games),
    }, sort_keys=True))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
