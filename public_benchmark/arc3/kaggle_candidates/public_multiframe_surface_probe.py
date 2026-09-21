#!/usr/bin/env python3
"""Targeted public multi-frame surface probe for ARC-AGI-3.

Uses the official online toolkit on public-development games only. The action
choices are declared statically and are not adapted from outcomes. The probe
records frame multiplicity/difference structure only; it is not a solver and
makes no hidden/Kaggle score claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

from public_multiframe_probe import changed_cells, frame_list, stable_hash

# Fixed before this execution. bp35 ACTION3 replaces the invalid ACTION1 only
# because the prior contract probe showed its advertised action space is
# {3,4,6,7}; no post-action outcome was used to select ACTION3.
TARGETS = (
    ("sp80", 5),
    ("bp35", 3),
    ("wa30", 1),
)


def probe(arcade: Any, game_id: str, action_id: int) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"game_id": game_id, "requested_action": action_id, "status": "ENV_CREATE_FAILED"}
    action_map = {action.value: action for action in env.action_space}
    available = sorted(action_map)
    if action_id not in action_map:
        return {
            "game_id": game_id,
            "requested_action": action_id,
            "available_actions": available,
            "status": "ACTION_UNAVAILABLE",
        }
    obs = env.step(action_map[action_id])
    frames = frame_list(obs)
    hashes = [stable_hash(f) for f in frames]
    adjacent = [changed_cells(a, b) for a, b in zip(frames, frames[1:])]
    valid = [x for x in adjacent if isinstance(x, int)]
    return {
        "game_id": game_id,
        "requested_action": action_id,
        "available_actions": available,
        "status": "EXECUTED",
        "frame_count": len(frames),
        "unique_frame_count": len(set(hashes)),
        "adjacent_changed_cells": adjacent,
        "adjacent_changed_cells_total": sum(valid),
        "first_to_final_changed_cells": changed_cells(frames[0], frames[-1]) if frames else None,
        "levels_completed": int(getattr(obs, "levels_completed", 0) or 0),
        "state": str(getattr(getattr(obs, "state", None), "value", getattr(obs, "state", ""))),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-multiframe-surface-probe.json"))
    args = ap.parse_args()
    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    rows = [probe(arcade, gid, action) for gid, action in TARGETS]
    executed = [r for r in rows if r.get("status") == "EXECUTED"]
    rich = [r for r in executed if int(r.get("unique_frame_count", 0)) > 2]
    multiframe = [r for r in executed if int(r.get("frame_count", 0)) > 1]
    receipt = {
        "schema": "deus/arc3-public-multiframe-surface-probe/1",
        "toolkit": "arc-agi==0.9.9",
        "declared_targets": [{"game_id": g, "action_id": a} for g, a in TARGETS],
        "outcome_adaptive_action_selection": False,
        "results": rows,
        "summary": {
            "targets": len(TARGETS),
            "executed": len(executed),
            "multiframe_targets": [r["game_id"] for r in multiframe],
            "rich_multiframe_targets": [r["game_id"] for r in rich],
            "max_frame_count": max((int(r.get("frame_count", 0)) for r in executed), default=0),
            "max_unique_frame_count": max((int(r.get("unique_frame_count", 0)) for r in executed), default=0),
        },
        "truth": {
            "public_development_environment_only": True,
            "official_online_toolkit_execution": True,
            "include_frame_data_true": True,
            "fixed_actions_declared_before_outcomes": True,
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
    return 0 if len(executed) == len(TARGETS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
