#!/usr/bin/env python3
"""Public settled-effect-memory rollout A/B v2.

Repairs v1's observation semantics without retrying the same failed interpretation:
a legal action that executes and returns no observation/frame is recorded as an
observed dead-end outcome, not a transport/provider inconclusive. This lets the
harness distinguish solver behavior from runtime failure while keeping promotion
strictly tied to real level gain (or equal positive gain with fewer actions).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

import public_effect_memory_rollout_ab as v1

ARMS = v1.ARMS
TARGETS = v1.TARGETS
STEP_BUDGET = v1.STEP_BUDGET
MEMORY_LIMIT = v1.MEMORY_LIMIT


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        return {"inconclusive": f"PROBE_UNAVAILABLE:{game_id}:{probe_action}", "rows": []}

    probe_obs = env.step(amap[probe_action])
    current = v1.final_frame(probe_obs)
    if current is None:
        return {"inconclusive": f"NO_FRAME_AFTER_PROBE:{game_id}", "rows": []}

    start_levels = v1.obs_levels(probe_obs)
    memory = [v1.memory_entry(probe_action, None, probe_obs)]
    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0
    observation_lost = False

    for step in range(1, STEP_BUDGET + 1):
        legal_ids = [int(a["id"]) for a in v1.action_descriptors(env)]
        prompt = v1.prompt_for(game_id, env, probe_obs, arm, memory)
        call = v1.provider_action_call(prompt, legal_ids)
        row: dict[str, Any] = {"step": step, "arm": arm, "prompt_chars": len(prompt), **call}
        if not call["provider_execution"] or not call["legal_action"]:
            row["execution"] = None
            rows.append(row)
            return {
                "inconclusive": f"CALL_OR_ACTION_INVALID:{game_id}:{arm}:step{step}",
                "rows": rows,
                "start_levels": start_levels,
            }

        chosen = int(call["chosen_action"])
        amap = {int(a.value): a for a in env.action_space}
        if chosen not in amap:
            row["execution"] = None
            rows.append(row)
            return {
                "inconclusive": f"ACTION_DISAPPEARED:{game_id}:{arm}:step{step}:{chosen}",
                "rows": rows,
                "start_levels": start_levels,
            }

        before = v1.final_frame(probe_obs)
        next_obs = env.step(amap[chosen])
        after = v1.final_frame(next_obs)
        entry = v1.memory_entry(chosen, before, next_obs)
        memory.append(entry)
        levels_now = v1.obs_levels(next_obs)
        state_now = v1.obs_state(next_obs)
        gain = levels_now - start_levels
        terminal = state_now.upper() in {"GAME_OVER", "LOST", "FAILED"}
        observation_lost = after is None
        row["execution"] = {
            "levels_completed": levels_now,
            "level_gain_from_probe": gain,
            "state": state_now,
            "terminal_failure": terminal,
            "observation_lost": observation_lost,
            "frame_count": len(v1.frame_list(next_obs)),
            "settled_delta": entry["settled_delta"],
        }
        rows.append(row)

        # A provider-selected legal action already executed. If the public env
        # yields no next observation, that is solver-path evidence. Stop this arm
        # rather than pretending it was a provider/runtime failure or replaying it.
        if observation_lost:
            break
        probe_obs = next_obs
        if gain > 0 or terminal:
            break

    return {
        "inconclusive": None,
        "rows": rows,
        "start_levels": start_levels,
        "final_levels": start_levels + gain,
        "level_gain": gain,
        "terminal_failure": terminal,
        "observation_lost": observation_lost,
        "policy_actions": len(rows),
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
        "observation_losses": sum(bool(r["result"].get("observation_lost")) for r in valid),
        "policy_actions_total": sum(int(r["result"].get("policy_actions", 0)) for r in valid),
        "provider_calls": len(calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-effect-memory-rollout-ab-v2.json"))
    args = ap.parse_args()

    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    results: list[dict[str, Any]] = []
    for game_id, probe_action in TARGETS:
        for arm in ARMS:
            results.append({
                "game_id": game_id,
                "probe_action": probe_action,
                "arm": arm,
                "result": run_arm(arcade, game_id, probe_action, arm),
            })

    inconclusive = [
        {"game_id": r["game_id"], "arm": r["arm"], "reason": r["result"].get("inconclusive")}
        for r in results if r["result"].get("inconclusive")
    ]
    base = summarize(results, "final_only")
    aug = summarize(results, "final_plus_effect_memory")

    if inconclusive:
        gate = "INCONCLUSIVE_RUNTIME_OR_PROVIDER"
    elif aug["terminal_failures"] > base["terminal_failures"] or aug["observation_losses"] > base["observation_losses"]:
        gate = "VALID_NO_PROMOTION_WORSE_FAILURE_OUTCOME"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"]:
        gate = "PROMOTE_EFFECT_MEMORY_MORE_GAINS"
    elif (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["policy_actions_total"] < base["policy_actions_total"]
    ):
        gate = "PROMOTE_EFFECT_MEMORY_EQUAL_GAINS_FEWER_ACTIONS"
    elif aug["observation_losses"] < base["observation_losses"]:
        gate = "VALID_BEHAVIOR_SIGNAL_NO_PROMOTION_OBSERVATION_SURVIVAL"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-effect-memory-rollout-ab/2",
        "toolkit": "arc-agi==0.9.9",
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "results": results,
        "summary": {"final_only": base, "final_plus_effect_memory": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "truth": {
            "public_development_environment_only": True,
            "same_exact_final_frame_contract_between_arms": True,
            "effect_memory_additive_only": True,
            "effect_memory_uses_observed_same_run_history_only": True,
            "executed_no_observation_is_solver_path_outcome_not_provider_failure": True,
            "observation_survival_alone_cannot_promote": True,
            "promotion_requires_level_gain_or_equal_positive_gain_efficiency": True,
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
