#!/usr/bin/env python3
"""Bounded public A/B for zero-effect causal replanning.

This rung follows the settled-effect-memory signal without promoting it. Both arms
receive the exact current frame and the same recent same-run action-effect ledger.
The treatment adds one general causal hint only after the immediately preceding
action produced zero persistent final-frame change and no level progress: reconsider
repeating that action. No target answer, source code, hidden state, or future outcome
is used. Promotion still requires real level gain (or equal positive gain with fewer
actions), never mere action diversity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

import public_effect_memory_rollout_ab as v1

TARGETS = v1.TARGETS
ARMS = ("effect_memory", "effect_memory_zero_effect_replan")
STEP_BUDGET = 10
MEMORY_LIMIT = 5


def prompt_for(game_id: str, env: Any, obs: Any, arm: str, memory: list[dict[str, Any]]) -> str:
    current = v1.final_frame(obs)
    if current is None:
        raise RuntimeError(f"no current frame for {game_id}")
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": v1.obs_levels(obs),
        "state": v1.obs_state(obs),
        "legal_actions": v1.action_descriptors(env),
        "exact_current_final_frame": current,
        "recent_settled_action_effects": memory[-MEMORY_LIMIT:],
        "memory_note": (
            "History is observed from this same public run. settled_delta compares persistent "
            "final frames before/after each action; frames reports transient frame count only."
        ),
    }
    if arm == "effect_memory_zero_effect_replan" and memory:
        last = memory[-1]
        changed = (last.get("settled_delta") or {}).get("changed")
        if changed == 0:
            payload["causal_replan_hint"] = (
                f"The immediately preceding action {last.get('action')} produced zero persistent "
                "final-frame change and no level progress. Do not assume repetition will help; "
                "prefer a different legal action unless the visible state gives a concrete reason to repeat."
            )
    return v1.compact_json(payload)


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        return {"inconclusive": f"PROBE_UNAVAILABLE:{game_id}:{probe_action}", "rows": []}
    obs = env.step(amap[probe_action])
    if v1.final_frame(obs) is None:
        return {"inconclusive": f"NO_FRAME_AFTER_PROBE:{game_id}", "rows": []}

    start_levels = v1.obs_levels(obs)
    memory = [v1.memory_entry(probe_action, None, obs)]
    rows: list[dict[str, Any]] = []
    gain = 0
    terminal = False
    observation_lost = False

    for step in range(1, STEP_BUDGET + 1):
        legal_ids = [int(a["id"]) for a in v1.action_descriptors(env)]
        prompt = prompt_for(game_id, env, obs, arm, memory)
        hint_active = "causal_replan_hint" in prompt
        call = v1.provider_action_call(prompt, legal_ids)
        row: dict[str, Any] = {
            "step": step,
            "arm": arm,
            "prompt_chars": len(prompt),
            "zero_effect_replan_hint_active": hint_active,
            **call,
        }
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

        before = v1.final_frame(obs)
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
        if observation_lost:
            break
        obs = next_obs
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
        "hint_activations": sum(bool(r.get("zero_effect_replan_hint_active")) for r in rows),
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
        "hint_activations_total": sum(int(r["result"].get("hint_activations", 0)) for r in valid),
        "provider_calls": len(calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-zero-effect-replan-ab.json"))
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
    aug = summarize(results, "effect_memory_zero_effect_replan")
    if inconclusive:
        gate = "INCONCLUSIVE_RUNTIME_OR_PROVIDER"
    elif aug["terminal_failures"] > base["terminal_failures"] or aug["observation_losses"] > base["observation_losses"]:
        gate = "VALID_NO_PROMOTION_WORSE_FAILURE_OUTCOME"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"]:
        gate = "PROMOTE_ZERO_EFFECT_REPLAN_MORE_GAINS"
    elif (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["policy_actions_total"] < base["policy_actions_total"]
    ):
        gate = "PROMOTE_ZERO_EFFECT_REPLAN_EQUAL_GAINS_FEWER_ACTIONS"
    else:
        changed_games = 0
        for game_id, _ in TARGETS:
            b = next(r for r in results if r["game_id"] == game_id and r["arm"] == "effect_memory")
            a = next(r for r in results if r["game_id"] == game_id and r["arm"] == "effect_memory_zero_effect_replan")
            bc = [x.get("chosen_action") for x in b["result"].get("rows", [])]
            ac = [x.get("chosen_action") for x in a["result"].get("rows", [])]
            if bc != ac:
                changed_games += 1
        gate = "VALID_BEHAVIOR_SIGNAL_NO_PROMOTION" if changed_games else "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-zero-effect-replan-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "results": results,
        "summary": {"effect_memory": base, "effect_memory_zero_effect_replan": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "truth": {
            "public_development_environment_only": True,
            "same_exact_current_frame_contract_between_arms": True,
            "same_effect_memory_contract_between_arms": True,
            "treatment_hint_uses_only_prior_same_run_zero_effect": True,
            "action_diversity_alone_cannot_promote": True,
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
