#!/usr/bin/env python3
"""Rung 127: independent runtime replay audit of a pinned public OpenWorld ARC-AGI-3 archive.

This rung does NOT evaluate generalization. It deliberately consumes a public archive of
already-discovered action traces and asks one narrow question: do those published traces
replay to the published level depths on the current official public ARC engine?

Truth boundary:
- source-assisted replay != independent solving/generalization;
- public ARC runtime != Kaggle hidden evaluation;
- no Kaggle data, execution, submission, or owner-score claim is involved;
- no upstream implementation code is imported or copied; only the pinned public JSON
  archive is consumed as data after license/provenance checks in the workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import arc_agi
from arcengine import GameAction

PINNED_UPSTREAM = "quome-cloud/openworld@e8248685e4f682dd6587e1af6296733cf3838a59"
PINNED_ARCHIVE_PATH = "experiments/results/arc3_fullgame_sourcefree_fable.json"
EXPECTED_GAMES = {
    "ar25", "bp35", "cd82", "cn04", "dc22", "ft09", "g50t", "ka59", "lf52",
    "lp85", "ls20", "m0r0", "r11l", "re86", "s5i5", "sb26", "sc25", "sk48",
    "sp80", "su15", "tn36", "tr87", "tu93", "vc33", "wa30",
}
SIMPLE = {
    1: GameAction.ACTION1,
    2: GameAction.ACTION2,
    3: GameAction.ACTION3,
    4: GameAction.ACTION4,
    5: GameAction.ACTION5,
    7: GameAction.ACTION7,
}


def state_name(obs: Any) -> str:
    raw = getattr(obs, "state", "")
    return str(getattr(raw, "value", raw))


def levels(obs: Any) -> int:
    return int(getattr(obs, "levels_completed", 0) or 0)


def has_observation(obs: Any) -> bool:
    if obs is None:
        return False
    # ARC versions differ in frame shape/property. A non-None observation with a state and
    # levels_completed is sufficient for replay accounting; frame absence is recorded separately.
    return hasattr(obs, "levels_completed")


def execute(env: Any, action: list[Any]) -> Any:
    if not isinstance(action, list) or not action:
        raise ValueError(f"malformed action: {action!r}")
    aid = int(action[0])
    if aid == 6:
        if len(action) != 3:
            raise ValueError(f"ACTION6 requires [6,x,y], got {action!r}")
        return env.step(GameAction.ACTION6, {"x": int(action[1]), "y": int(action[2])})
    if aid not in SIMPLE or len(action) != 1:
        raise ValueError(f"unsupported action encoding: {action!r}")
    return env.step(SIMPLE[aid])


def validate_archive(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    protocol = str(data.get("protocol", ""))
    verification = str(data.get("verification", ""))
    per_game = data.get("per_game")
    solutions = data.get("solutions")
    if not protocol.lower().startswith("source-free"):
        errors.append("protocol_not_source_free")
    if "real-env replay" not in verification:
        errors.append("verification_missing_real_env_replay_claim")
    if not isinstance(per_game, dict):
        return errors + ["per_game_missing"]
    if not isinstance(solutions, dict):
        return errors + ["solutions_missing"]
    games = set(per_game)
    if games != EXPECTED_GAMES:
        errors.append(f"game_set_mismatch:{sorted(games ^ EXPECTED_GAMES)}")
    for g in sorted(EXPECTED_GAMES):
        meta = per_game.get(g)
        seq = solutions.get(g)
        if not isinstance(meta, dict):
            errors.append(f"{g}:meta_missing")
            continue
        win = int(meta.get("win", 0) or 0)
        claimed = int(meta.get("levels", 0) or 0)
        if win <= 0 or claimed < win:
            errors.append(f"{g}:not_claimed_full:{claimed}/{win}")
        if not isinstance(seq, list) or not seq:
            errors.append(f"{g}:solution_missing")
    return errors


def replay_game(arcade: Any, game: str, seq: list[list[Any]], target: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "game": game,
        "target_levels": target,
        "archive_actions": len(seq),
        "executed_actions": 0,
        "final_levels": None,
        "final_state": None,
        "replay_pass": False,
        "inconclusive": None,
        "first_error_step": None,
    }
    try:
        env = arcade.make(game, save_recording=False, include_frame_data=False)
        if env is None:
            row["inconclusive"] = "MAKE_FAILED"
            return row
        obs = env.reset()
        if not has_observation(obs):
            row["inconclusive"] = "RESET_OBSERVATION_INVALID"
            return row
        for idx, action in enumerate(seq, start=1):
            obs = execute(env, action)
            row["executed_actions"] = idx
            if not has_observation(obs):
                row["inconclusive"] = "STEP_OBSERVATION_INVALID"
                row["first_error_step"] = idx
                break
            if levels(obs) >= target:
                break
        if has_observation(obs):
            row["final_levels"] = levels(obs)
            row["final_state"] = state_name(obs)
            row["replay_pass"] = bool(levels(obs) >= target)
        return row
    except Exception as exc:
        row["inconclusive"] = f"{type(exc).__name__}:{exc}"
        row["first_error_step"] = row["executed_actions"] + 1
        return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=Path("openworld-sourcefree-replay-audit-127.json"))
    args = ap.parse_args()

    raw = args.archive.read_bytes()
    data = json.loads(raw)
    archive_errors = validate_archive(data)
    rows: list[dict[str, Any]] = []

    if not archive_errors:
        arcade = arc_agi.Arcade()
        for game in sorted(EXPECTED_GAMES):
            meta = data["per_game"][game]
            rows.append(replay_game(arcade, game, data["solutions"][game], int(meta["win"])))

    inconclusive = [r for r in rows if r.get("inconclusive")]
    failed = [r for r in rows if not r.get("inconclusive") and not r.get("replay_pass")]
    passed = [r for r in rows if r.get("replay_pass")]
    full_runtime_pass = bool(not archive_errors and len(rows) == 25 and len(passed) == 25 and not inconclusive and not failed)

    if archive_errors:
        gate = "INCONCLUSIVE_ARCHIVE_CONTRACT"
    elif inconclusive:
        gate = "INCONCLUSIVE_PUBLIC_RUNTIME"
    elif failed:
        gate = "SOURCE_TRACE_REPLAY_MISMATCH"
    elif full_runtime_pass:
        gate = "SOURCE_ASSISTED_REPLAY_25OF25_VERIFIED_NO_PROMOTION"
    else:
        gate = "INCONCLUSIVE_UNKNOWN"

    receipt = {
        "schema": "deus/arc3-openworld-sourcefree-replay-audit/1",
        "rung": 127,
        "change_kind": "PUBLIC_SOURCE_ASSISTED_RUNTIME_REPRODUCIBILITY_AUDIT",
        "source": {
            "upstream": PINNED_UPSTREAM,
            "archive_path": PINNED_ARCHIVE_PATH,
            "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "declared_license": "Apache-2.0",
            "archive_protocol": data.get("protocol"),
            "archive_verification_claim": data.get("verification"),
            "upstream_implementation_imported": False,
            "upstream_implementation_copied": False,
            "archive_data_consumed": True,
        },
        "archive_contract_errors": archive_errors,
        "summary": {
            "games_expected": 25,
            "games_attempted": len(rows),
            "replay_passed": len(passed),
            "replay_failed": len(failed),
            "inconclusive": len(inconclusive),
            "executed_actions_total": sum(int(r.get("executed_actions", 0)) for r in rows),
            "full_runtime_pass": full_runtime_pass,
        },
        "rows": rows,
        "promotion_gate": gate,
        "truth": {
            "public_development_environment_only": True,
            "source_assisted_replay": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "award_or_settlement_claim": False,
            "provider_execution_evidence_only": True,
            "promotion_allowed": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"promotion_gate": gate, "summary": receipt["summary"], "archive_errors": archive_errors}, sort_keys=True))

    # Fail closed on archive/runtime inconclusive or mismatch. A complete source-assisted replay is
    # still explicitly NO_PROMOTION, so success only means the reproducibility audit itself completed.
    return 0 if full_runtime_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
