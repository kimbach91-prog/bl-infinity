#!/usr/bin/env python3
"""Rung 123: target-blind context-aware action-effect utility / soft-demotion A/B.

This rung changes decision routing rather than adding more pixel geometry. Both arms
receive the same exact current visible frame, explicit no-new-frame freshness semantics,
and the same bounded same-run action-effect memory. The treatment derives a compact
per-action utility summary only from outcomes already observed in that arm. Negative
evidence is a soft demotion, never a hard ban, and no-new-frame observations remain
unknown rather than being treated as zero effect.

Source grounding is conceptual and clean-room:
- GameDevGitHub/GuidedRandomAgent documents action-effectiveness bias and reduced
  probability for actions that repeatedly produce no visible change.
- khub-ai/arc-agi-3 documents world-model updates from what actually happens and
  context-aware exploration/means-ends routing.
No upstream implementation code is copied here.
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

TARGETS = em.TARGETS
ARMS = ("effect_memory", "effect_memory_plus_utility")
STEP_BUDGET = 3
MEMORY_LIMIT = em.MEMORY_LIMIT
SOURCE_GROUNDING = {
    "guided_random": {
        "upstream_ref": "GameDevGitHub/GuidedRandomAgent@d8bfe547e5446eabcf710040cdcfdac78491b7c8",
        "license": "MIT",
        "principle": "action-effectiveness bias with reduced weight for repeatedly ineffective actions",
    },
    "khub": {
        "upstream_ref": "khub-ai/arc-agi-3@de41a93e3a4557db24702fceddb2409c7bc06afd",
        "license": "MIT-0",
        "principle": "world-model evidence from observed outcomes with context-aware exploration/means-ends routing",
    },
    "clean_room_implementation": True,
}


def observed_frame(obs: Any) -> Any | None:
    fs = frame_list(obs)
    return plain(fs[-1]) if fs else None


def make_entry(action_id: int, before_frame: Any, before_levels: int, obs: Any, fresh_frame: Any | None) -> dict[str, Any]:
    fresh = fresh_frame is not None
    after_levels = em.obs_levels(obs)
    delta = em.settled_delta(before_frame, fresh_frame) if fresh else {"changed": None, "bbox": None, "pairs": []}
    return {
        "action": int(action_id),
        "frames": len(frame_list(obs)),
        "new_frame_observed": fresh,
        "settled_delta": delta,
        "level_delta": int(after_levels - before_levels),
        "levels_completed": after_levels,
        "state": em.obs_state(obs),
    }


def action_effect_utility(memory: list[dict[str, Any]], legal_ids: list[int]) -> list[dict[str, Any]]:
    stats: dict[int, dict[str, Any]] = {
        int(a): {
            "action": int(a),
            "attempts": 0,
            "visible_effects": 0,
            "visible_no_effects": 0,
            "unknown_effects": 0,
            "level_gain_total": 0,
            "last_observed_outcome": "UNSEEN",
        }
        for a in legal_ids
    }
    for row in memory[-MEMORY_LIMIT:]:
        aid = int(row.get("action", -1))
        if aid not in stats:
            continue
        s = stats[aid]
        s["attempts"] += 1
        level_delta = int(row.get("level_delta", 0) or 0)
        s["level_gain_total"] += max(0, level_delta)
        fresh = bool(row.get("new_frame_observed"))
        changed = row.get("settled_delta", {}).get("changed")
        if level_delta > 0:
            s["visible_effects"] += 1
            s["last_observed_outcome"] = "LEVEL_GAIN"
        elif not fresh or changed is None:
            s["unknown_effects"] += 1
            s["last_observed_outcome"] = "UNKNOWN_NO_NEW_FRAME"
        elif int(changed) > 0:
            s["visible_effects"] += 1
            s["last_observed_outcome"] = "VISIBLE_EFFECT"
        else:
            s["visible_no_effects"] += 1
            s["last_observed_outcome"] = "VISIBLE_NO_EFFECT"

    rows: list[dict[str, Any]] = []
    for aid in sorted(stats):
        s = stats[aid]
        raw = 3.0 * float(s["level_gain_total"]) + 1.0 * float(s["visible_effects"]) - 0.75 * float(s["visible_no_effects"])
        score = max(-2.0, min(4.0, raw))
        if s["attempts"] == 0:
            routing = "UNSEEN_NEUTRAL"
        elif s["level_gain_total"] > 0 or s["visible_effects"] > s["visible_no_effects"]:
            routing = "SOFT_PREFER"
        elif s["visible_no_effects"] > s["visible_effects"] and s["unknown_effects"] == 0:
            routing = "SOFT_DEMOTE"
        else:
            routing = "MIXED_OR_UNKNOWN"
        rows.append({**s, "utility_score": round(score, 3), "routing": routing})
    return rows


def prompt_for(game_id: str, env: Any, obs: Any, current_frame: Any, current_fresh: bool, arm: str, memory: list[dict[str, Any]]) -> str:
    actions = em.action_descriptors(env)
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": em.obs_levels(obs),
        "state": em.obs_state(obs),
        "legal_actions": actions,
        "exact_current_final_frame": current_frame,
        "current_frame_is_new_in_latest_observation": current_fresh,
        "recent_settled_action_effects": memory[-MEMORY_LIMIT:],
        "memory_note": (
            "Rows are same-run visible observations. If new_frame_observed=false, the action effect is unknown, not zero; "
            "the last actually visible frame is carried forward. Treat history as context-dependent evidence, not a guaranteed rule."
        ),
    }
    if arm == "effect_memory_plus_utility":
        legal_ids = [int(a["id"]) for a in actions]
        payload["action_effect_utility"] = action_effect_utility(memory, legal_ids)
        payload["routing_note"] = (
            "Use action_effect_utility only as a soft context-aware routing prior. SOFT_DEMOTE means lower priority after observed "
            "no-effect evidence, never forbidden. UNSEEN and unknown effects remain viable. Prefer actions likely to advance the level "
            "given the exact current frame."
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
    memory: list[dict[str, Any]] = [{
        "action": int(probe_action),
        "frames": len(frame_list(obs)),
        "new_frame_observed": True,
        "settled_delta": {"changed": None, "bbox": None, "pairs": []},
        "level_delta": 0,
        "levels_completed": start_levels,
        "state": em.obs_state(obs),
    }]
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

        before_frame = current_frame
        before_levels = em.obs_levels(obs)
        next_obs = env.step(amap[chosen])
        fresh_frame = observed_frame(next_obs)
        current_fresh = fresh_frame is not None
        if fresh_frame is not None:
            current_frame = fresh_frame
        else:
            no_new_frame_count += 1
        entry = make_entry(chosen, before_frame, before_levels, next_obs, fresh_frame)
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
            "level_delta": entry["level_delta"],
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
        "final_action_effect_utility": action_effect_utility(memory, [int(a["id"]) for a in em.action_descriptors(env)]),
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
    ap.add_argument("--receipt", type=Path, default=Path("public-action-effect-utility-ab.json"))
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
    aug = summarize(results, "effect_memory_plus_utility")

    equal_positive = (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["level_gain_total"] == base["level_gain_total"]
    )
    nondominated_efficiency = (
        aug["policy_actions_total"] <= base["policy_actions_total"]
        and aug["provider_calls"] <= base["provider_calls"]
        and aug["prompt_chars_total"] <= base["prompt_chars_total"]
        and (
            aug["policy_actions_total"] < base["policy_actions_total"]
            or aug["provider_calls"] < base["provider_calls"]
            or aug["prompt_chars_total"] < base["prompt_chars_total"]
        )
    )

    if inconclusive:
        gate = "INCONCLUSIVE_RUNTIME_OR_PROVIDER"
    elif aug["terminal_failures"] > base["terminal_failures"]:
        gate = "VALID_NO_PROMOTION_MORE_TERMINAL_FAILURES"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"]:
        gate = "PROMOTE_ACTION_EFFECT_UTILITY_MORE_GAINS"
    elif equal_positive and nondominated_efficiency:
        gate = "PROMOTE_ACTION_EFFECT_UTILITY_EQUAL_POSITIVE_NONDOMINATED"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-action-effect-utility-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "source_grounding": SOURCE_GROUNDING,
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "max_provider_calls": len(TARGETS) * len(ARMS) * STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "results": results,
        "summary": {
            "effect_memory": base,
            "effect_memory_plus_utility": aug,
            "equal_positive_behavior": equal_positive,
            "strictly_nondominated_efficiency": nondominated_efficiency,
        },
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "truth": {
            "public_development_environment_only": True,
            "same_exact_current_visible_frame_contract_between_arms": True,
            "no_new_frame_is_explicit_not_zero_effect": True,
            "last_visible_frame_carry_forward_is_shared_between_arms": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "candidate_uses_same_run_visible_outcomes_only": True,
            "candidate_changes_decision_routing_not_pixel_geometry": True,
            "soft_demotion_never_hard_bans_legal_action": True,
            "unknown_no_new_frame_never_counts_as_negative_effect": True,
            "provider_call_retries": False,
            "promotion_requires_solver_behavior_gain": True,
            "equal_positive_promotion_requires_strictly_nondominated_efficiency": True,
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
