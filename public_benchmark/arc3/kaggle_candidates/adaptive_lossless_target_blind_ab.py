#!/usr/bin/env python3
"""Cross-game target-blind public-development A/B for adaptive lossless encoding.

Fixed target: ALPHA iff the immediate next board changes by >=1 cell. Cases are
selected solely from pre-action public state + already-chosen action hashes.
Post-action outcomes are withheld until scoring. Provider model identity must
match the identity-grounded Llama route on every executed call.

This is a public-development transition-model proxy, not Kaggle execution,
hidden-score evidence, or independent private generalization.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

import adaptive_lossless_scene as als
import adaptive_lossless_behavior_ab_v3_identity as ident
import segmentation_cross_game_target_blind_ab as base

ARMS = ("raw_board_action", "adaptive_lossless_action")
FIXED_THRESHOLD = 1


def stable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def representation(case: dict[str, Any], arm: str) -> Any:
    raw = case["representations"]["raw_board_action"]
    if arm == "raw_board_action":
        return raw
    if arm == "adaptive_lossless_action":
        rep = als.encode(raw)
        als.validate(raw, rep)
        return rep
    raise KeyError(arm)


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    rep = stable(representation(case, arm))
    guidance = (
        "The state is a reversible lossless compact encoding; reconstruct exact board semantics before reasoning. "
        if arm == "adaptive_lossless_action"
        else "The state contains the full raw 64x64 board. "
    )
    prompt = (
        f"Representation arm: {arm}\n"
        + guidance
        + "Pre-action public state and already-chosen action:\n"
        + rep
        + "\nPredict the immediate NEXT-board visible change. "
        + "ALPHA = at least 1 board cell changes. BETA = 0 board cells change. "
        + "Reply exactly one token."
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
        d = out.setdefault(r["game_id"], {"raw": 0, "adaptive": 0, "cases": 0})
        if r["arm"] == "raw_board_action":
            d["raw"] += int(bool(r["correct"])); d["cases"] += 1
        else:
            d["adaptive"] += int(bool(r["correct"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--cases-per-game", type=int, default=4)
    ap.add_argument("--receipt", type=Path, default=Path("adaptive-lossless-target-blind-ab.json"))
    args = ap.parse_args()

    ident.IDENTITY_AUDIT.clear()
    per_game_cases: dict[str, list[dict[str, Any]]] = {}
    trace_stats: list[dict[str, Any]] = []
    for path in args.input:
        gid, cases, stats = base.load_game(path)
        if gid in per_game_cases:
            raise ValueError(f"duplicate game_id: {gid}")
        per_game_cases[gid] = cases
        trace_stats.append({"game_id": gid, **stats})

    selected = base.select_cases(per_game_cases, args.cases_per_game)
    expected_count = len(per_game_cases) * args.cases_per_game
    selection_ok = len(per_game_cases) >= base.EXPECTED_GAMES and len(selected) == expected_count
    labels = ["ALPHA" if c["outcome"]["board_changed"] else "BETA" for c in selected]
    alpha_count = sum(x == "ALPHA" for x in labels)
    beta_count = sum(x == "BETA" for x in labels)
    majority = max(alpha_count, beta_count) / len(labels) if labels else 1.0

    canary = ident.strict_identity_call(
        "Calibration case only: the immediate next board differs from the pre-action board in exactly 1 cell. "
        "ALPHA is the correct label. Reply exactly ALPHA."
    ) if selection_ok else None
    canary_choice, _ = base.seg.base.normalize_choice(canary["content"]) if canary else (None, False)
    canary_ok = bool(canary and canary.get("provider_execution") and canary_choice == "ALPHA")

    rows: list[dict[str, Any]] = []
    if selection_ok and canary_ok:
        for idx, case in enumerate(selected):
            expected = "ALPHA" if case["outcome"]["board_changed"] else "BETA"
            arms = list(ARMS) if idx % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, chars = prompt_for(case, arm)
                res = ident.strict_identity_call(prompt)
                choice, exact = base.seg.base.normalize_choice(res["content"])
                rows.append({
                    "case": idx,
                    "game_id": case["game_id"],
                    "case_hash": case["case_hash"],
                    "trace": case["trace"],
                    "trace_index": case["trace_index"],
                    "arm": arm,
                    "expected": expected,
                    "selected": choice,
                    "correct": choice == expected,
                    "exact_format": exact,
                    "representation_chars": chars,
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "served_model": res.get("served_model"),
                    "identity_ok": res.get("identity_ok"),
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                })

    raw = summarize(rows, "raw_board_action")
    adaptive = summarize(rows, "adaptive_lossless_action")
    games = by_game(rows)
    wins = sum(d["adaptive"] > d["raw"] for d in games.values())
    losses = sum(d["adaptive"] < d["raw"] for d in games.values())
    ties = sum(d["adaptive"] == d["raw"] for d in games.values())
    all_identity = bool(ident.IDENTITY_AUDIT) and all(bool(x.get("identity_ok")) for x in ident.IDENTITY_AUDIT)

    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_DISTINCT_GAME_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif not all_identity:
        gate = "INCONCLUSIVE_PROVIDER_IDENTITY_MISMATCH"
    elif raw["failures"] or adaptive["failures"] or raw["calls"] != len(selected) or adaptive["calls"] != len(selected):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif adaptive["correct"] >= raw["correct"] + 2 and wins >= 2 and losses == 0 and adaptive["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_ADAPTIVE_LOSSLESS_TARGET_BLIND_BEHAVIOR_GAIN"
    elif adaptive["correct"] == raw["correct"] and losses == 0 and raw["representation_chars_total"] > 0 and adaptive["representation_chars_total"] <= 0.65 * raw["representation_chars_total"] and adaptive["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]:
        gate = "PROMOTE_ADAPTIVE_LOSSLESS_TARGET_BLIND_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-adaptive-lossless-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "requested_model": ident.MODEL,
        "data_class": "BL-S0_PUBLIC_CROSS_GAME_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "dataset": "schema-harness/arc-agi-3-schema-traces",
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "implementation": "clean-room fixed-target transition reconstruction; post-action board withheld until scoring",
        },
        "selection": {
            "distinct_games": sorted(per_game_cases),
            "distinct_game_count": len(per_game_cases),
            "cases_per_game": args.cases_per_game,
            "fixed_cases_selected": len(selected),
            "ordering": "game_id lexical then sha256(pre-action public state/action); outcome excluded",
            "outcome_used_for_case_selection": False,
            "outcome_used_for_prompt": False,
            "fixed_target_before_selection": "changed_cells>=1",
            "label_counts_after_selection": {"ALPHA_changed": alpha_count, "BETA_unchanged": beta_count},
            "majority_baseline_accuracy": round(majority, 6),
        },
        "identity": {
            "call_count": len(ident.IDENTITY_AUDIT),
            "all_calls_exact_identity": all_identity,
            "served_models": sorted({str(x.get("served_model")) for x in ident.IDENTITY_AUDIT}),
        },
        "arms": {"raw_board_action": raw, "adaptive_lossless_action": adaptive},
        "per_game": games,
        "cross_game_comparison": {"adaptive_wins": wins, "adaptive_losses": losses, "ties": ties},
        "promotion_gate": gate,
        "rows": rows,
        "truth": {
            "public_trace_only": True,
            "cross_game_public_development_proxy": True,
            "fixed_target_declared_before_case_selection": True,
            "target_blind_public_development_behavior": True,
            "source_assisted_replay": False,
            "independent_generalization_claim": False,
            "transition_model_proxy_not_full_solver": True,
            "provider_model_identity_verified": all_identity,
            "provider_execution_is_not_kaggle_execution": True,
            "hidden_kaggle_data_read": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
            "owner_score_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("selection", "identity", "arms", "per_game", "cross_game_comparison", "promotion_gate", "truth")}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
