#!/usr/bin/env python3
"""Replay a disclosed Bách Lâm × DEUS ARC-AGI-3 public-dev route."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arc_agi
from arc_agi import OperationMode


HERE = Path(__file__).resolve().parent
ROUTE_PATH = HERE / "route.json"
SOURCE_URL = (
    "https://github.com/kimbach91-prog/bl-infinity/"
    "tree/main/public_benchmark/arc-agi-3"
)


def canonical_route_hash(actions: list[int]) -> str:
    payload = ",".join(str(action) for action in actions).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "result.json")
    args = parser.parse_args()

    route = json.loads(ROUTE_PATH.read_text(encoding="utf-8"))
    actions = route["actions"]
    actual_hash = canonical_route_hash(actions)
    if actual_hash != route["route_sha256"]:
        raise SystemExit(
            f"Route hash mismatch: expected {route['route_sha256']}, got {actual_hash}"
        )

    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    card_id = arcade.create_scorecard(
        tags=[
            "bach-lam-x-deus",
            "public-dev-game",
            "observation-state-search",
            "reproducible",
        ],
        source_url=SOURCE_URL,
        opaque={
            "system_label": route["system_label"],
            "evaluation_scope": route["evaluation_scope"],
            "environment": route["environment"],
            "route_sha256": actual_hash,
            "claim_boundary": "partial public-dev result; not hidden generalization or AGI proof",
        },
    )

    stable_game_id = route["environment"].split("-", 1)[0]
    environment = arcade.make(
        stable_game_id,
        scorecard_id=card_id,
        save_recording=True,
        include_frame_data=True,
    )
    if environment is None:
        raise SystemExit("ARC environment could not be created")

    action_map = {action.value: action for action in environment.action_space}
    observation = None
    for index, action_id in enumerate(actions, start=1):
        if action_id not in action_map:
            raise SystemExit(f"Action {action_id} unavailable at step {index}")
        observation = environment.step(action_map[action_id])

    final_card = arcade.close_scorecard(scorecard_id=card_id)
    if final_card is None:
        raise SystemExit("ARC server did not return a finalized scorecard")

    receipt = final_card.model_dump(mode="json")
    receipt["reproduction"] = {
        "system_label": route["system_label"],
        "source_url": SOURCE_URL,
        "route_sha256": actual_hash,
        "observed_levels_completed_after_replay": (
            observation.levels_completed if observation is not None else 0
        ),
        "observed_state_after_replay": (
            observation.state.value if observation is not None else "NOT_PLAYED"
        ),
    }
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

