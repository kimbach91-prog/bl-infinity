#!/usr/bin/env python3
"""Cross-game public-development A/B for adaptive lossless scene encoding.

Cases are selected by a hash of pre-action state + already-chosen action only.
A fixed ordered family of change-magnitude targets is declared in code before
model calls; the first target with non-degenerate labels on the already-fixed
cases is used. Target balance can choose the evaluation target but never cases,
arm, prompt content, or model outputs. This is public development evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

import adaptive_lossless_scene as als
import segmentation_target_blind_ab as seg

ARMS = ("raw_board_action", "adaptive_lossless_action")
TARGET_THRESHOLDS = (4, 16, 64, 256)
CASES_PER_GAME_DEFAULT = 6
MIN_EACH_LABEL = 3
MAX_TRANSPORT_ATTEMPTS = 4
SUCCESS_PACING_S = 0.7
_ORIGINAL_CALL = seg.base.call_model


def stable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def valid_grid(v: Any) -> bool:
    return isinstance(v, list) and len(v) == 64 and all(isinstance(r, list) and len(r) == 64 for r in v)


def changed_cells(a: list[list[int]], b: list[list[int]]) -> int:
    return sum(int(x != y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def reliable_call(prompt: str) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = []
    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        res = _ORIGINAL_CALL(prompt)
        trace.append({
            "attempt": attempt,
            "http_status": res.get("http_status"),
            "error": res.get("error"),
            "provider_execution": bool(res.get("provider_execution")),
        })
        last = res
        if res.get("provider_execution"):
            out = dict(res)
            out["transport_attempts"] = attempt
            out["transport_trace"] = trace
            time.sleep(SUCCESS_PACING_S)
            return out
        if attempt < MAX_TRANSPORT_ATTEMPTS:
            time.sleep(float(2 * attempt))
    assert last is not None
    out = dict(last)
    out["transport_attempts"] = MAX_TRANSPORT_ATTEMPTS
    out["transport_trace"] = trace
    return out


def load_game(path: Path) -> tuple[str, list[dict[str, Any]]]:
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
    if not game_id:
        raise ValueError(f"{path}: missing game_id")

    cases: list[dict[str, Any]] = []
    for i in range(1, len(actions)):
        prev, cur = actions[i - 1], actions[i]
        if not (valid_grid(prev.get("grid")) and valid_grid(cur.get("grid"))):
            continue
        if not (isinstance(prev.get("step_index"), int) and isinstance(cur.get("step_index"), int) and cur["step_index"] == prev["step_index"] + 1):
            continue
        if str(prev.get("state", "")).upper() not in {"", "NOT_FINISHED"}:
            continue
        if cur.get("level_up") is True or cur.get("level") != prev.get("level"):
            continue
        raw = {
            "level": prev.get("level"),
            "action": {"id": cur.get("action"), "x": cur.get("x"), "y": cur.get("y")},
            "board": prev["grid"],
        }
        identity = {"game_id": game_id, "pre_step": prev.get("step_index"), "raw": raw}
        cases.append({
            "game_id": game_id,
            "trace": path.name,
            "trace_index": i,
            "case_hash": hashlib.sha256(stable(identity).encode()).hexdigest(),
            "raw": raw,
            "outcome_changed_cells": changed_cells(prev["grid"], cur["grid"]),
        })
    return game_id, cases


def select_fixed(per_game: dict[str, list[dict[str, Any]]], n: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for game_id in sorted(per_game):
        ranked = sorted(per_game[game_id], key=lambda c: c["case_hash"])
        if len(ranked) < n:
            raise ValueError(f"{game_id}: only {len(ranked)} eligible cases")
        out.extend(ranked[:n])
    return out


def choose_target(selected: list[dict[str, Any]]) -> tuple[int | None, dict[str, dict[str, int]]]:
    dist: dict[str, dict[str, int]] = {}
    chosen: int | None = None
    for threshold in TARGET_THRESHOLDS:
        alpha = sum(c["outcome_changed_cells"] >= threshold for c in selected)
        beta = len(selected) - alpha
        dist[str(threshold)] = {"ALPHA_ge_threshold": alpha, "BETA_lt_threshold": beta}
        if chosen is None and min(alpha, beta) >= MIN_EACH_LABEL:
            chosen = threshold
    return chosen, dist


def representation(case: dict[str, Any], arm: str) -> Any:
    if arm == "raw_board_action":
        return case["raw"]
    if arm == "adaptive_lossless_action":
        rep = als.encode(case["raw"])
        als.validate(case["raw"], rep)
        return rep
    raise KeyError(arm)


def prompt_for(case: dict[str, Any], arm: str, threshold: int) -> tuple[str, int]:
    rep = stable(representation(case, arm))
    guidance = (
        "The state is losslessly row-RLE encoded and may include bounded object hints; reconstruct exact board semantics before reasoning. "
        if arm == "adaptive_lossless_action"
        else "The state contains the full raw 64x64 board. "
    )
    prompt = (
        f"Representation arm: {arm}\n" + guidance
        + "Pre-action public state and already-chosen action:\n" + rep
        + f"\nPredict the immediate next-board change magnitude. ALPHA = at least {threshold} cells change. "
          f"BETA = fewer than {threshold} cells change. Reply exactly one token."
    )
    return prompt, len(rep)


def summarize(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    vals = [r for r in rows if r["arm"] == arm]
    lats = [r["latency_ms"] for r in vals if r["provider_execution"]]
    return {
        "calls": len(vals),
        "executed": sum(bool(r["provider_execution"]) for r in vals),
        "failures": sum(not bool(r["provider_execution"]) for r in vals),
        "correct": sum(bool(r["correct"]) for r in vals),
        "accuracy": round(sum(bool(r["correct"]) for r in vals) / len(vals), 6) if vals else None,
        "exact_format_rate": round(sum(bool(r["exact_format"]) for r in vals) / len(vals), 6) if vals else None,
        "representation_chars_total": sum(int(r["representation_chars"]) for r in vals),
        "mean_latency_ms": round(statistics.mean(lats), 1) if lats else None,
        "median_latency_ms": round(statistics.median(lats), 1) if lats else None,
    }


def per_game(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        d = out.setdefault(r["game_id"], {"raw": 0, "adaptive": 0, "cases": 0})
        if r["arm"] == "raw_board_action":
            d["raw"] += int(bool(r["correct"])); d["cases"] += 1
        else:
            d["adaptive"] += int(bool(r["correct"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--cases-per-game", type=int, default=CASES_PER_GAME_DEFAULT)
    ap.add_argument("--receipt", type=Path, default=Path("adaptive-lossless-behavior-ab.json"))
    args = ap.parse_args()

    games: dict[str, list[dict[str, Any]]] = {}
    for path in args.input:
        gid, cases = load_game(path)
        if gid in games:
            raise ValueError(f"duplicate game_id {gid}")
        games[gid] = cases
    selected = select_fixed(games, args.cases_per_game)
    threshold, target_distributions = choose_target(selected)

    canary = reliable_call("Public S0 canary. If at least 4 cells changed, ALPHA is correct. Reply exactly ALPHA.") if threshold is not None else None
    canary_choice, _ = seg.base.normalize_choice(canary["content"]) if canary else (None, False)
    canary_ok = bool(canary and canary.get("provider_execution") and canary_choice == "ALPHA")

    rows: list[dict[str, Any]] = []
    if threshold is not None and canary_ok:
        for idx, case in enumerate(selected):
            expected = "ALPHA" if case["outcome_changed_cells"] >= threshold else "BETA"
            arms = list(ARMS) if idx % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, chars = prompt_for(case, arm, threshold)
                res = reliable_call(prompt)
                choice, exact = seg.base.normalize_choice(res["content"])
                rows.append({
                    "case": idx,
                    "game_id": case["game_id"],
                    "case_hash": case["case_hash"],
                    "trace": case["trace"],
                    "trace_index": case["trace_index"],
                    "arm": arm,
                    "threshold": threshold,
                    "changed_cells": case["outcome_changed_cells"],
                    "expected": expected,
                    "selected": choice,
                    "correct": choice == expected,
                    "exact_format": exact,
                    "representation_chars": chars,
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                    "transport_attempts": res.get("transport_attempts"),
                })

    raw = summarize(rows, "raw_board_action")
    adaptive = summarize(rows, "adaptive_lossless_action")
    pg = per_game(rows)
    wins = sum(d["adaptive"] > d["raw"] for d in pg.values())
    losses = sum(d["adaptive"] < d["raw"] for d in pg.values())
    ties = sum(d["adaptive"] == d["raw"] for d in pg.values())

    if threshold is None:
        gate = "INCONCLUSIVE_NO_PREDECLARED_NONDEGENERATE_TARGET"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or adaptive["failures"] or raw["calls"] != len(selected) or adaptive["calls"] != len(selected):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif adaptive["correct"] >= raw["correct"] + 2 and wins >= 2 and losses == 0 and adaptive["mean_latency_ms"] <= 1.5 * raw["mean_latency_ms"]:
        gate = "PROMOTE_ADAPTIVE_LOSSLESS_CROSS_GAME_BEHAVIOR_GAIN"
    elif adaptive["correct"] == raw["correct"] and losses == 0 and adaptive["representation_chars_total"] <= 0.65 * raw["representation_chars_total"] and adaptive["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]:
        gate = "PROMOTE_ADAPTIVE_LOSSLESS_CROSS_GAME_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-adaptive-lossless-cross-game-behavior-ab/1",
        "provider": "BLOCKRUN",
        "requested_model": seg.base.MODEL,
        "data_class": "BL-S0_PUBLIC_CROSS_GAME_DEVELOPMENT",
        "selection": {
            "distinct_games": sorted(games),
            "cases_per_game": args.cases_per_game,
            "fixed_cases": len(selected),
            "case_order": "game_id lexical then sha256(game_id, pre-step, pre-action raw state/action)",
            "outcome_used_for_case_selection": False,
            "outcome_used_in_model_prompt": False,
        },
        "target_design": {
            "ordered_thresholds_predeclared_in_source": list(TARGET_THRESHOLDS),
            "minimum_each_label": MIN_EACH_LABEL,
            "target_selection_rule": "first ordered threshold meeting label-balance floor on already-fixed cases; performed before any model calls",
            "target_selected_using_model_outputs": False,
            "chosen_changed_cell_threshold": threshold,
            "distributions": target_distributions,
        },
        "arms": {"raw_board_action": raw, "adaptive_lossless_action": adaptive},
        "per_game": pg,
        "cross_game_comparison": {"adaptive_wins": wins, "adaptive_losses": losses, "ties": ties},
        "promotion_gate": gate,
        "rows": rows,
        "truth": {
            "public_trace_only": True,
            "public_development_benchmark_design_used_label_balance": True,
            "source_assisted_replay": False,
            "independent_generalization_claim": False,
            "model_behavior_test": True,
            "provider_execution_is_not_kaggle_execution": True,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("selection", "target_design", "arms", "per_game", "cross_game_comparison", "promotion_gate", "truth")}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
