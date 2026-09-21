#!/usr/bin/env python3
"""Deterministic public cross-game audit for adaptive lossless scene encoding."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

import adaptive_lossless_scene as als


def valid_grid(v: Any) -> bool:
    return isinstance(v, list) and len(v) == 64 and all(isinstance(r, list) and len(r) == 64 for r in v)


def load_preactions(path: Path) -> tuple[str, list[dict[str, Any]]]:
    game_id = ""
    actions: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if not game_id and isinstance(e.get("game_id"), str):
                game_id = e["game_id"]
            if e.get("kind") == "action_taken":
                actions.append(e)
    rows: list[dict[str, Any]] = []
    for i in range(1, len(actions)):
        prev, cur = actions[i - 1], actions[i]
        if not valid_grid(prev.get("grid")):
            continue
        if not (isinstance(prev.get("step_index"), int) and isinstance(cur.get("step_index"), int) and cur["step_index"] == prev["step_index"] + 1):
            continue
        if str(prev.get("state", "")).upper() not in {"", "NOT_FINISHED"}:
            continue
        if cur.get("level_up") is True or cur.get("level") != prev.get("level"):
            continue
        rows.append({
            "level": prev.get("level"),
            "action": {"id": cur.get("action"), "x": cur.get("x"), "y": cur.get("y")},
            "board": prev["grid"],
        })
    return game_id, rows


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    idx = min(len(xs) - 1, max(0, round((len(xs) - 1) * q)))
    return round(xs[idx], 6)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--receipt", type=Path, default=Path("adaptive-lossless-scene-audit.json"))
    args = ap.parse_args()

    total_raw = total_adaptive = 0
    total = 0
    mode_counts: dict[str, int] = {}
    ratios: list[float] = []
    games: dict[str, dict[str, Any]] = {}

    for path in args.input:
        game_id, rows = load_preactions(path)
        if not game_id:
            raise AssertionError(f"missing game id: {path}")
        game_raw = game_adaptive = 0
        game_modes: dict[str, int] = {}
        for raw in rows:
            rep = als.encode(raw)
            als.validate(raw, rep)
            raw_len = len(als.stable(raw))
            payload = dict(rep); payload.pop("mode", None)
            adaptive_len = len(als.stable(payload))
            if adaptive_len > raw_len:
                raise AssertionError("non-expansion invariant failed")
            total += 1
            total_raw += raw_len
            total_adaptive += adaptive_len
            game_raw += raw_len
            game_adaptive += adaptive_len
            ratios.append(adaptive_len / raw_len if raw_len else 1.0)
            mode_counts[rep["mode"]] = mode_counts.get(rep["mode"], 0) + 1
            game_modes[rep["mode"]] = game_modes.get(rep["mode"], 0) + 1
        games[game_id] = {
            "trace": path.name,
            "cases": len(rows),
            "raw_chars": game_raw,
            "adaptive_chars": game_adaptive,
            "reduction_pct": round(100 * (1 - game_adaptive / game_raw), 6) if game_raw else 0.0,
            "modes": game_modes,
        }

    receipt = {
        "schema": "deus/arc3-adaptive-lossless-scene-audit/1",
        "source": "schema-harness/arc-agi-3-schema-traces public trajectories",
        "distinct_games": sorted(games),
        "games": games,
        "aggregate": {
            "cases": total,
            "raw_chars": total_raw,
            "adaptive_chars": total_adaptive,
            "reduction_pct": round(100 * (1 - total_adaptive / total_raw), 6) if total_raw else 0.0,
            "mode_counts": mode_counts,
            "ratio_median": round(statistics.median(ratios), 6) if ratios else None,
            "ratio_p90": pct(ratios, 0.90),
            "ratio_max": round(max(ratios), 6) if ratios else None,
        },
        "invariants": {
            "lossless_board_roundtrip_all_cases": True,
            "level_action_preserved_all_cases": True,
            "adaptive_payload_never_exceeds_raw_chars": True,
            "future_outcome_read_for_representation": False,
        },
        "truth": {
            "public_trace_only": True,
            "deterministic_representation_audit": True,
            "model_behavior_test": False,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
