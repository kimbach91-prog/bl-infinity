#!/usr/bin/env python3
"""Cross-game public ARC3 target-blind A/B for compact segmentation.

Uses three distinct public Schema trajectories. For each game, deterministic
case selection depends only on the pre-action public state and already-chosen
action. The post-action board is withheld until scoring.

This is a public-development generalization proxy, not Kaggle execution,
hidden-score evidence, or independent private generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

import segmentation_target_blind_ab as seg

ARMS = ("raw_board_action", "segmentation_action")
EXPECTED_GAMES = 3
MAX_TRANSPORT_ATTEMPTS = 4
SUCCESS_PACING_S = 0.8
_ORIGINAL_CALL = seg.base.call_model


def stable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def reliable_call(prompt: str) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        res = _ORIGINAL_CALL(prompt)
        attempts.append({
            "attempt": attempt,
            "http_status": res.get("http_status"),
            "error": res.get("error"),
            "provider_execution": bool(res.get("provider_execution")),
        })
        last = res
        if res.get("provider_execution"):
            out = dict(res)
            out["transport_attempts"] = attempt
            out["transport_trace"] = attempts
            time.sleep(SUCCESS_PACING_S)
            return out
        if attempt < MAX_TRANSPORT_ATTEMPTS:
            time.sleep(float(attempt * 2))
    assert last is not None
    out = dict(last)
    out["transport_attempts"] = MAX_TRANSPORT_ATTEMPTS
    out["transport_trace"] = attempts
    return out


def valid_grid(v: Any) -> bool:
    return (
        isinstance(v, list)
        and len(v) == 64
        and all(isinstance(row, list) and len(row) == 64 for row in v)
    )


def load_game(path: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    game_id = ""
    actions: list[dict[str, Any]] = []
    events = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            events += 1
            e = json.loads(line)
            if not game_id and isinstance(e.get("game_id"), str):
                game_id = e["game_id"]
            if e.get("kind") == "action_taken":
                actions.append(e)
    if not game_id:
        raise ValueError(f"{path}: missing game_id")

    cases: list[dict[str, Any]] = []
    skipped = {"bad_grid": 0, "noncontiguous": 0, "terminal_prestate": 0, "level_transition": 0}
    for i in range(1, len(actions)):
        prev = actions[i - 1]
        cur = actions[i]
        if not (valid_grid(prev.get("grid")) and valid_grid(cur.get("grid"))):
            skipped["bad_grid"] += 1
            continue
        if not (isinstance(prev.get("step_index"), int) and isinstance(cur.get("step_index"), int) and cur["step_index"] == prev["step_index"] + 1):
            skipped["noncontiguous"] += 1
            continue
        if str(prev.get("state", "")).upper() not in {"", "NOT_FINISHED"}:
            skipped["terminal_prestate"] += 1
            continue
        # Keep the proxy focused on within-level transition mechanics. A level-up
        # changes both scene and task phase and would trivially bias ALPHA.
        if cur.get("level_up") is True or cur.get("level") != prev.get("level"):
            skipped["level_transition"] += 1
            continue

        action = {
            "id": cur.get("action"),
            "x": cur.get("x"),
            "y": cur.get("y"),
        }
        raw = {
            "level": prev.get("level"),
            "action": action,
            "board": prev["grid"],
        }
        identity = {
            "game_id": game_id,
            "pre_step_index": prev.get("step_index"),
            "action_step_index": cur.get("step_index"),
            "raw_board_action": raw,
        }
        cases.append({
            "game_id": game_id,
            "trace": path.name,
            "trace_index": i,
            "case_hash": hashlib.sha256(stable(identity).encode("utf-8")).hexdigest(),
            "representations": {"raw_board_action": raw},
            "outcome": {"board_changed": prev["grid"] != cur["grid"]},
        })
    return game_id, cases, {
        "path": path.name,
        "events": events,
        "action_taken": len(actions),
        "eligible_transitions": len(cases),
        "skipped": skipped,
    }


def select_cases(per_game: dict[str, list[dict[str, Any]]], per_game_n: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    # Game ordering and case ordering are target-blind.
    for game_id in sorted(per_game):
        selected.extend(sorted(per_game[game_id], key=lambda r: r["case_hash"])[:per_game_n])
    return selected


def representation(case: dict[str, Any], arm: str) -> Any:
    if arm == "raw_board_action":
        return case["representations"]["raw_board_action"]
    if arm == "segmentation_action":
        return seg.segmentation_representation(case)
    raise KeyError(arm)


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    rep = stable(representation(case, arm))
    guidance = (
        "Interpret connected objects, colors, shape hashes, edge contact and adjacency as the primary scene view. "
        if arm == "segmentation_action"
        else "Interpret the full pre-action 64x64 board. "
    )
    prompt = (
        f"Representation arm: {arm}\n"
        + guidance
        + "Pre-action public state and already-chosen action:\n"
        + rep
        + "\nPredict the immediate NEXT-board effect of this already-chosen action. "
        "ALPHA = board visibly changes. BETA = board does not visibly change. "
        "Reply exactly one token."
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


def by_game(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        g = r["game_id"]
        d = out.setdefault(g, {"raw": 0, "seg": 0, "cases": 0})
        if r["arm"] == "raw_board_action":
            d["raw"] += int(bool(r["correct"]))
            d["cases"] += 1
        elif r["arm"] == "segmentation_action":
            d["seg"] += int(bool(r["correct"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--cases-per-game", type=int, default=4)
    ap.add_argument("--receipt", type=Path, default=Path("segmentation-cross-game-target-blind-ab.json"))
    args = ap.parse_args()

    per_game: dict[str, list[dict[str, Any]]] = {}
    trace_stats: list[dict[str, Any]] = []
    for path in args.input:
        game_id, cases, stats = load_game(path)
        if game_id in per_game:
            raise ValueError(f"duplicate game_id: {game_id}")
        per_game[game_id] = cases
        trace_stats.append({"game_id": game_id, **stats})

    selected = select_cases(per_game, args.cases_per_game)
    expected_count = len(per_game) * args.cases_per_game
    selection_ok = len(per_game) >= EXPECTED_GAMES and len(selected) == expected_count
    labels = ["ALPHA" if c["outcome"]["board_changed"] else "BETA" for c in selected]
    alpha_count = sum(x == "ALPHA" for x in labels)
    beta_count = sum(x == "BETA" for x in labels)
    majority_baseline = max(alpha_count, beta_count) / len(labels) if labels else 1.0

    canary = reliable_call("Public S0 canary. A move changed the next board. ALPHA means changed. Reply exactly ALPHA.")
    canary_choice, canary_exact = seg.base.normalize_choice(canary["content"])
    canary_ok = canary["provider_execution"] and canary_choice == "ALPHA"

    call_rows: list[dict[str, Any]] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(selected):
            expected = "ALPHA" if case["outcome"]["board_changed"] else "BETA"
            arms = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, rep_chars = prompt_for(case, arm)
                res = reliable_call(prompt)
                selected_token, exact = seg.base.normalize_choice(res["content"])
                call_rows.append({
                    "case": i,
                    "game_id": case["game_id"],
                    "case_hash": case["case_hash"],
                    "trace": case["trace"],
                    "trace_index": case["trace_index"],
                    "arm": arm,
                    "expected": expected,
                    "selected": selected_token,
                    "correct": selected_token == expected,
                    "exact_format": exact,
                    "representation_chars": rep_chars,
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "response_schema_ok": res["response_schema_ok"],
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                    "transport_attempts": res.get("transport_attempts"),
                })

    raw = summarize(call_rows, "raw_board_action")
    segmentation = summarize(call_rows, "segmentation_action")
    games = by_game(call_rows)
    wins = sum(d["seg"] > d["raw"] for d in games.values())
    losses = sum(d["seg"] < d["raw"] for d in games.values())
    ties = sum(d["seg"] == d["raw"] for d in games.values())

    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_DISTINCT_GAME_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or segmentation["failures"] or raw["calls"] != len(selected) or segmentation["calls"] != len(selected):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif (
        segmentation["correct"] >= raw["correct"] + 2
        and wins >= 2
        and losses == 0
        and segmentation["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_CROSS_GAME_SEGMENTATION_BEHAVIOR_GAIN"
    elif (
        segmentation["correct"] == raw["correct"]
        and losses == 0
        and raw["representation_chars_total"] > 0
        and segmentation["representation_chars_total"] <= 0.65 * raw["representation_chars_total"]
        and segmentation["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_CROSS_GAME_SEGMENTATION_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-segmentation-cross-game-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": seg.base.ENDPOINT,
        "requested_model": seg.base.MODEL,
        "data_class": "BL-S0_PUBLIC_CROSS_GAME_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "dataset": "schema-harness/arc-agi-3-schema-traces",
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "download_hashes_external_to_receipt": "workflow artifact SHA256SUMS.txt",
            "implementation": "clean-room pairwise action_taken reconstruction; post-action grid withheld until scoring",
        },
        "selection": {
            "distinct_games": sorted(per_game),
            "distinct_game_count": len(per_game),
            "cases_per_game": args.cases_per_game,
            "fixed_cases_selected": len(selected),
            "ordering": "game_id lexical, then sha256(game_id, step indexes, pre-action raw representation); outcome excluded",
            "target_used_for_case_selection": False,
            "target_used_for_prompt": False,
            "label_counts_after_selection": {"ALPHA_changed": alpha_count, "BETA_unchanged": beta_count},
            "majority_baseline_accuracy": round(majority_baseline, 6),
            "level_transition_cases_excluded_before_selection": True,
        },
        "arms": {"raw_board_action": raw, "segmentation_action": segmentation},
        "per_game": games,
        "cross_game_comparison": {"segmentation_wins": wins, "segmentation_losses": losses, "ties": ties},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_label_semantics": True,
            "alternating_arm_order": True,
            "no_target_matching": True,
            "behavior_gain_requires_overall_plus_two_and_at_least_two_game_wins_and_zero_game_losses": True,
            "provider_failure": "INCONCLUSIVE",
            "transport_retry_only_before_provider_execution": True,
        },
        "rows": call_rows,
        "truth": {
            "public_trace_only": True,
            "cross_game_public_development_proxy": True,
            "source_assisted_replay": False,
            "target_blind_public_development_behavior": True,
            "independent_generalization_claim": False,
            "model_behavior_test": True,
            "provider_execution_is_not_kaggle_execution": True,
            "hidden_kaggle_data_read": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
            "owner_score_claim": False,
            "prize_or_award_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "selection": receipt["selection"],
        "arms": receipt["arms"],
        "per_game": receipt["per_game"],
        "cross_game_comparison": receipt["cross_game_comparison"],
        "promotion_gate": gate,
        "truth": receipt["truth"],
    }, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
