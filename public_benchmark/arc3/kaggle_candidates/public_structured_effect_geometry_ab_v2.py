#!/usr/bin/env python3
"""Rung 122: target-blind structured effect geometry with visible-frame carry semantics.

This repairs rung 121 by changing the observation representation, not by retrying failed
provider calls. ARC observations that contain no new frame are represented explicitly as
`new_frame_observed=false`; the last actually visible final frame is carried forward as the
current visual state. Both arms receive that same freshness flag and same carried frame.
The fixed policy budget is reduced to 3 actions/arm to keep the A/B inside the observed
provider rate envelope; there are no retries of failed model calls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

from animation_delta_signature import compact_json, plain
from public_animation_action_ab import provider_action_call
from public_multiframe_probe import frame_list
import public_effect_memory_rollout_ab as em
import public_structured_effect_geometry_ab as geom

TARGETS = em.TARGETS
ARMS = ("effect_memory", "effect_memory_plus_geometry")
STEP_BUDGET = 3
MEMORY_LIMIT = em.MEMORY_LIMIT
SOURCE_REF = geom.SOURCE_REF


def observed_frame(obs: Any) -> Any | None:
    fs = frame_list(obs)
    return plain(fs[-1]) if fs else None


def make_entry(action_id: int, before: Any, obs: Any, after: Any | None, with_geometry: bool) -> dict[str, Any]:
    fresh = after is not None
    delta = em.settled_delta(before, after) if fresh else {"changed": None, "bbox": None, "pairs": []}
    row: dict[str, Any] = {
        "action": int(action_id),
        "frames": len(frame_list(obs)),
        "new_frame_observed": fresh,
        "settled_delta": delta,
        "levels_completed": em.obs_levels(obs),
        "state": em.obs_state(obs),
    }
    if with_geometry:
        row["effect_geometry"] = (
            geom.effect_geometry(before, after)
            if fresh
            else {"valid": False, "reason": "NO_NEW_VISIBLE_FRAME"}
        )
    return row


def prompt_for(game_id: str, env: Any, obs: Any, current_frame: Any, current_fresh: bool,
               arm: str, memory: list[dict[str, Any]]) -> str:
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": em.obs_levels(obs),
        "state": em.obs_state(obs),
        "legal_actions": em.action_descriptors(env),
        "exact_current_final_frame": current_frame,
        "current_frame_is_new_in_latest_observation": current_fresh,
        "recent_settled_action_effects": memory[-MEMORY_LIMIT:],
        "memory_note": (
            "Rows are same-run visible observations. If new_frame_observed=false, no new visible "
            "frame was returned and settled_delta is unknown; the last actually visible frame is "
            "carried forward. Treat history as evidence, not a rule guarantee."
        ),
    }
    if arm == "effect_memory_plus_geometry":
        payload["geometry_note"] = (
            "effect_geometry is target-blind descriptive pixel geometry from visible before/after "
            "frames only: connected changed regions and same-color centroid shifts."
        )
    return compact_json(payload)


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        return {"inconclusive": f"PROBE_UNAVAILABLE:{game_id}:{probe_action}", "rows": []}

    obs = env.step(amap[probe_action])
    current_frame = observed_frame(obs)
    if current_frame is None:
        return {"inconclusive": f"NO_INITIAL_FRAME_AFTER_PROBE:{game_id}", "rows": []}
    current_fresh = True
    start_levels = em.obs_levels(obs)
    with_geometry = arm == "effect_memory_plus_geometry"
    memory: list[dict[str, Any]] = [{
        "action": int(probe_action),
        "frames": len(frame_list(obs)),
        "new_frame_observed": True,
        "settled_delta": {"changed": None, "bbox": None, "pairs": []},
        "levels_completed": start_levels,
        "state": em.obs_state(obs),
    }]
    if with_geometry:
        memory[0]["effect_geometry"] = {"valid": False, "reason": "NO_PRE_ACTION_FRAME"}

    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0
    no_new_frame_count = 0

    for step in range(1, STEP_BUDGET + 1):
        legal_ids = [int(a["id"]) for a in em.action_descriptors(env)]
        prompt = prompt_for(game_id, env, obs, current_frame, current_fresh, arm, memory)
        call = provider_action_call(prompt, legal_ids)
        row: dict[str, Any] = {"step": step, "arm": arm, "prompt_chars": len(prompt), **call}
        if not call["provider_execution"] or not call["legal_action"]:
            row["execution"] = None
            rows.append(row)
            return {"inconclusive": f"CALL_OR_ACTION_INVALID:{game_id}:{arm}:step{step}", "rows": rows, "start_levels": start_levels}

        chosen = int(call["chosen_action"])
        amap = {int(a.value): a for a in env.action_space}
        if chosen not in amap:
            row["execution"] = None
            rows.append(row)
            return {"inconclusive": f"ACTION_DISAPPEARED:{game_id}:{arm}:step{step}:{chosen}", "rows": rows, "start_levels": start_levels}

        before = current_frame
        next_obs = env.step(amap[chosen])
        fresh_frame = observed_frame(next_obs)
        current_fresh = fresh_frame is not None
        if fresh_frame is not None:
            current_frame = fresh_frame
        else:
            no_new_frame_count += 1
        entry = make_entry(chosen, before, next_obs, fresh_frame, with_geometry)
        memory.append(entry)

        levels_now = em.obs_levels(next_obs)
        state_now = em.obs_state(next_obs)
        gain = levels_now - start_levels
        terminal = state_now.upper() in {"GAME_OVER", "LOST", "FAILED"}
        row["execution"] = {
            "levels_completed": levels_now,
            "level_gain_from_probe": gain,
            "state": state_now,
            "terminal_failure": terminal,
            "frame_count": len(frame_list(next_obs)),
            "new_frame_observed": current_fresh,
            "settled_delta": entry["settled_delta"],
            "effect_geometry_present": "effect_geometry" in entry,
        }
        rows.append(row)
        obs = next_obs
        if gain > 0 or terminal:
            break

    return {
        "inconclusive": None,
        "rows": rows,
        "start_levels": start_levels,
        "final_levels": em.obs_levels(obs),
        "level_gain": gain,
        "terminal_failure": terminal,
        "policy_actions": len(rows),
        "no_new_frame_count": no_new_frame_count,
        "final_memory": memory[-MEMORY_LIMIT:],
    }


def summarize(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rr = [r for r in results if r["arm"] == arm]
    valid = [r for r in rr if not r["result"].get("inconclusive")]
    calls = [x for r in rr for x in r["result"].get("rows", [])]
    return {
        "games": len(rr),
        "valid_games": len(valid),
        "games_with_level_gain": sum(int(r["result"].get("level_gain", 0)) > 0 for r in valid),
        "level_gain_total": sum(int(r["result"].get("level_gain", 0)) for r in valid),
        "terminal_failures": sum(bool(r["result"].get("terminal_failure")) for r in valid),
        "policy_actions_total": sum(int(r["result"].get("policy_actions", 0)) for r in valid),
        "no_new_frame_total": sum(int(r["result"].get("no_new_frame_count", 0)) for r in valid),
        "provider_calls": len(calls),
        "provider_http_429": sum(int(x.get("http_status", 0) or 0) == 429 for x in calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-structured-effect-geometry-ab-v2.json"))
    args = ap.parse_args()
    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    results: list[dict[str, Any]] = []
    for game_id, probe_action in TARGETS:
        for arm in ARMS:
            results.append({"game_id": game_id, "probe_action": probe_action, "arm": arm, "result": run_arm(arcade, game_id, probe_action, arm)})

    inconclusive = [
        {"game_id": r["game_id"], "arm": r["arm"], "reason": r["result"].get("inconclusive")}
        for r in results if r["result"].get("inconclusive")
    ]
    base = summarize(results, "effect_memory")
    aug = summarize(results, "effect_memory_plus_geometry")
    if inconclusive:
        gate = "INCONCLUSIVE_RUNTIME_OR_PROVIDER"
    elif aug["terminal_failures"] > base["terminal_failures"]:
        gate = "VALID_NO_PROMOTION_MORE_TERMINAL_FAILURES"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"]:
        gate = "PROMOTE_STRUCTURED_EFFECT_GEOMETRY_MORE_GAINS"
    elif (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["policy_actions_total"] < base["policy_actions_total"]
        and aug["prompt_chars_total"] <= base["prompt_chars_total"]
    ):
        gate = "PROMOTE_STRUCTURED_EFFECT_GEOMETRY_EQUAL_GAINS_NONDOMINATED"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-structured-effect-geometry-ab/2",
        "toolkit": "arc-agi==0.9.9",
        "repair_of": "run35609161094:rung121",
        "repair_kind": "REPRESENTATION_AND_FIXED_BUDGET_CHANGE_NOT_CALL_RETRY",
        "source_grounding": {
            "upstream_ref": SOURCE_REF,
            "license": "MIT-0",
            "clean_room_implementation": True,
        },
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "max_provider_calls": len(TARGETS) * len(ARMS) * STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "results": results,
        "summary": {"effect_memory": base, "effect_memory_plus_geometry": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "truth": {
            "public_development_environment_only": True,
            "same_exact_current_visible_frame_contract_between_arms": True,
            "no_new_frame_is_explicit_not_zero_effect": True,
            "last_visible_frame_carry_forward_is_shared_between_arms": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "candidate_adds_visible_same_run_geometry_only": True,
            "provider_call_retries": False,
            "promotion_requires_solver_behavior_gain": True,
            "efficiency_alone_cannot_promote_zero_gain": True,
            "game_source_read": False,
            "hidden_state_read": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
            "independent_generalization_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": receipt["summary"], "promotion_gate": gate, "inconclusive": inconclusive}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
