#!/usr/bin/env python3
"""Public runtime footprint benchmark for compact animation metadata.

Fixed public games/actions only. The exact final frame remains the current-board
representation; this benchmark compares the cost of retaining every transient
pre-final frame with a compact additive animation signature. No solver-quality
or Kaggle-score claim is made.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

from animation_delta_signature import compact_json, encode_animation, plain
from public_multiframe_probe import frame_list

BENCHMARK_REV = "112"
TARGETS = (("sp80", 5), ("bp35", 3), ("wa30", 1))


def run_one(arcade: Any, game_id: str, action_id: int) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"game_id": game_id, "action_id": action_id, "status": "ENV_CREATE_FAILED"}
    action_map = {a.value: a for a in env.action_space}
    if action_id not in action_map:
        return {"game_id": game_id, "action_id": action_id, "status": "ACTION_UNAVAILABLE", "available": sorted(action_map)}
    obs = env.step(action_map[action_id])
    frames = frame_list(obs)
    sig = encode_animation(frames)
    full_extra = compact_json([plain(f) for f in frames[:-1]]) if len(frames) > 1 else ""
    sig_text = compact_json(sig) if sig is not None else ""
    return {
        "game_id": game_id,
        "action_id": action_id,
        "status": "EXECUTED",
        "frame_count": len(frames),
        "full_transient_chars": len(full_extra),
        "signature_chars": len(sig_text),
        "signature_to_full_ratio": round(len(sig_text) / len(full_extra), 6) if full_extra else 0.0,
        "signature": sig,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-animation-signature-benchmark.json"))
    args = ap.parse_args()
    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    rows = [run_one(arcade, g, a) for g, a in TARGETS]
    executed = [r for r in rows if r.get("status") == "EXECUTED"]
    rich = [r for r in executed if int(r.get("frame_count", 0)) > 1]
    total_full = sum(int(r["full_transient_chars"]) for r in rich)
    total_sig = sum(int(r["signature_chars"]) for r in rich)
    receipt = {
        "schema": "deus/arc3-public-animation-signature-benchmark/1",
        "benchmark_rev": BENCHMARK_REV,
        "toolkit": "arc-agi==0.9.9",
        "targets": [{"game_id": g, "action_id": a} for g, a in TARGETS],
        "results": rows,
        "summary": {
            "executed": len(executed),
            "multiframe_cases": len(rich),
            "full_transient_chars_total": total_full,
            "signature_chars_total": total_sig,
            "signature_to_full_ratio": round(total_sig / total_full, 6) if total_full else 0.0,
            "reduction_fraction": round(1.0 - (total_sig / total_full), 6) if total_full else 0.0,
        },
        "truth": {
            "public_development_environment_only": True,
            "fixed_actions_declared_before_outcomes": True,
            "final_frame_remains_exact_current_board": True,
            "animation_signature_is_additive_lossy_metadata": True,
            "game_source_read": False,
            "hidden_state_read": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
            "solver_behavior_gain_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": receipt["summary"], "results": rows, "truth": receipt["truth"]}, indent=2, sort_keys=True))
    if len(executed) != len(TARGETS):
        return 2
    if rich and any(int(r["signature_chars"]) >= int(r["full_transient_chars"]) for r in rich):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
