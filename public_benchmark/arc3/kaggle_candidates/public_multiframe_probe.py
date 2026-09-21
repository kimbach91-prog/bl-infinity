#!/usr/bin/env python3
"""Public ARC-AGI-3 multi-frame observation probe.

Replays the already-disclosed ls20 public-development route with official
`include_frame_data=True` and records only observation-frame structure and
pixel-difference statistics. It reads no game source, hidden state, Kaggle data,
or private competition output. This is observation-contract/runtime evidence,
not a solver score or Kaggle score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

HERE = Path(__file__).resolve().parents[2] / "arc-agi-3"
ROUTE_PATH = HERE / "route.json"


def stable_hash(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, separators=(",", ":"), sort_keys=False).encode("utf-8")).hexdigest()


def is_grid(v: Any) -> bool:
    return isinstance(v, list) and bool(v) and all(isinstance(r, list) for r in v)


def changed_cells(a: Any, b: Any) -> int | None:
    if not (is_grid(a) and is_grid(b)) or len(a) != len(b):
        return None
    total = 0
    for ra, rb in zip(a, b):
        if not (isinstance(ra, list) and isinstance(rb, list) and len(ra) == len(rb)):
            return None
        total += sum(int(x != y) for x, y in zip(ra, rb))
    return total


def frame_list(observation: Any) -> list[Any]:
    frames = getattr(observation, "frame", None)
    if frames is None:
        return []
    # Official FrameData.frame is a list of 2-D frame arrays. Be defensive
    # around alternate pydantic/list wrappers while preserving exact ordering.
    if isinstance(frames, list):
        return frames
    try:
        return list(frames)
    except TypeError:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-multiframe-probe.json"))
    args = ap.parse_args()

    route = json.loads(ROUTE_PATH.read_text(encoding="utf-8"))
    actions = route["actions"]
    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    stable_game_id = route["environment"].split("-", 1)[0]
    env = arcade.make(stable_game_id, save_recording=False, include_frame_data=True)
    if env is None:
        raise SystemExit("public ARC environment could not be created")

    action_map = {action.value: action for action in env.action_space}
    steps: list[dict[str, Any]] = []
    for index, action_id in enumerate(actions, start=1):
        if action_id not in action_map:
            raise SystemExit(f"action {action_id} unavailable at step {index}")
        obs = env.step(action_map[action_id])
        frames = frame_list(obs)
        hashes = [stable_hash(f) for f in frames]
        adjacent_diffs = [changed_cells(a, b) for a, b in zip(frames, frames[1:])]
        valid_diffs = [d for d in adjacent_diffs if isinstance(d, int)]
        steps.append({
            "step": index,
            "action_id": action_id,
            "frame_count": len(frames),
            "unique_frame_count": len(set(hashes)),
            "frame_hashes": hashes,
            "adjacent_changed_cells": adjacent_diffs,
            "adjacent_changed_cells_total": sum(valid_diffs),
            "first_to_final_changed_cells": changed_cells(frames[0], frames[-1]) if frames else None,
            "levels_completed": int(getattr(obs, "levels_completed", 0) or 0),
            "state": str(getattr(getattr(obs, "state", None), "value", getattr(obs, "state", ""))),
        })

    multiframe = [s for s in steps if s["frame_count"] > 1]
    animated = [s for s in steps if s["unique_frame_count"] > 1]
    max_frames = max((s["frame_count"] for s in steps), default=0)
    receipt = {
        "schema": "deus/arc3-public-multiframe-probe/1",
        "toolkit": "arc-agi==0.9.9",
        "environment": route["environment"],
        "route_sha256": route["route_sha256"],
        "actions_replayed": len(steps),
        "summary": {
            "steps_with_multiple_frames": len(multiframe),
            "steps_with_multiple_unique_frames": len(animated),
            "max_frames_in_one_step": max_frames,
            "total_frames": sum(s["frame_count"] for s in steps),
            "total_unique_frames_per_step_sum": sum(s["unique_frame_count"] for s in steps),
            "multiframe_step_indexes": [s["step"] for s in multiframe],
            "animated_step_indexes": [s["step"] for s in animated],
        },
        "steps": steps,
        "truth": {
            "public_development_environment_only": True,
            "official_online_toolkit_execution": True,
            "include_frame_data_true": True,
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
    print(json.dumps({"summary": receipt["summary"], "truth": receipt["truth"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
