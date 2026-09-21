#!/usr/bin/env python3
"""Rung 125: target-blind state-action loop-sketch representation A/B.

Rung 124 failed closed after a provider HTTP429 in one baseline arm. This rung does
not retry the failed representation. It changes the representation and lowers the
fixed per-arm action budget back to the previously stable 3-step public probe.

Baseline keeps the raw bounded same-run effect memory. Treatment replaces that raw
memory with a compact state/action transition sketch keyed by the exact visible frame.
A legal action is only softly demoted when the same action previously produced a
VISIBLE_NO_EFFECT from the exact same visible-state digest. Unknown/no-new-frame
observations never count as negative evidence, and no legal action is ever removed.

Conceptual source grounding (clean-room):
- GameDevGitHub/GuidedRandomAgent@d8bfe547... (MIT): remembers ineffective actions
  for a given game state and avoids simple loops; action-effectiveness bias.
- khub-ai/arc-agi-3@de41a93... (MIT-0): world model accumulates evidence from what
  actually happens; means-ends + exploration choose actions while preserving generality.
No upstream implementation code is copied.
"""
from __future__ import annotations

import argparse
import hashlib
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
ARMS = ("effect_memory_raw", "state_action_loop_sketch")
STEP_BUDGET = 3
MEMORY_LIMIT = em.MEMORY_LIMIT
SKETCH_LIMIT = 4
SOURCE_GROUNDING = {
    "guided_random": {
        "upstream_ref": "GameDevGitHub/GuidedRandomAgent@d8bfe547e5446eabcf710040cdcfdac78491b7c8",
        "license": "MIT",
        "principle": "state-specific ineffective-action memory and action-effectiveness bias to avoid loops",
    },
    "khub": {
        "upstream_ref": "khub-ai/arc-agi-3@de41a93e3a4557db24702fceddb2409c7bc06afd",
        "license": "MIT-0",
        "principle": "world-model evidence from actual outcomes with means-ends plus exploration",
    },
    "clean_room_implementation": True,
}


def observed_frame(obs: Any) -> Any | None:
    fs = frame_list(obs)
    return plain(fs[-1]) if fs else None


def frame_digest(frame: Any) -> str:
    payload = compact_json(frame).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def outcome_label(level_delta: int, fresh: bool, changed: Any) -> str:
    if level_delta > 0:
        return "LEVEL_GAIN"
    if not fresh or changed is None:
        return "UNKNOWN_NO_NEW_FRAME"
    return "VISIBLE_EFFECT" if int(changed) > 0 else "VISIBLE_NO_EFFECT"


def make_entry(action_id: int, before_frame: Any, before_levels: int, obs: Any, fresh_frame: Any | None) -> dict[str, Any]:
    fresh = fresh_frame is not None
    after_levels = em.obs_levels(obs)
    level_delta = int(after_levels - before_levels)
    delta = em.settled_delta(before_frame, fresh_frame) if fresh else {"changed": None, "bbox": None, "pairs": []}
    return {
        "action": int(action_id),
        "before_frame_id": frame_digest(before_frame),
        "after_frame_id": frame_digest(fresh_frame) if fresh else None,
        "new_frame_observed": fresh,
        "settled_delta": delta,
        "level_delta": level_delta,
        "levels_completed": after_levels,
        "state": em.obs_state(obs),
        "outcome": outcome_label(level_delta, fresh, delta.get("changed")),
    }


def compact_sketch(memory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in memory[-SKETCH_LIMIT:]:
        rows.append({
            "a": int(row.get("action", -1)),
            "from": row.get("before_frame_id"),
            "to": row.get("after_frame_id"),
            "o": row.get("outcome", "UNKNOWN"),
            "dl": int(row.get("level_delta", 0) or 0),
        })
    return rows


def current_state_prior(memory: list[dict[str, Any]], current_frame: Any, legal_ids: list[int]) -> dict[str, Any] | None:
    current_id = frame_digest(current_frame)
    attempts_here: set[int] = set()
    soft_demote: set[int] = set()
    for row in memory:
        if row.get("before_frame_id") != current_id:
            continue
        aid = int(row.get("action", -1))
        if aid not in legal_ids:
            continue
        attempts_here.add(aid)
        if row.get("outcome") == "VISIBLE_NO_EFFECT":
            soft_demote.add(aid)
    if not attempts_here and not soft_demote:
        return None
    unseen_here = [int(a) for a in legal_ids if int(a) not in attempts_here]
    return {
        "state_id": current_id,
        "soft_demote_visible_no_effect_here": sorted(soft_demote),
        "soft_explore_untried_here": sorted(unseen_here),
        "all_legal_actions_remain_available": True,
    }


def raw_memory_view(memory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "action": int(r.get("action", -1)),
            "new_frame_observed": bool(r.get("new_frame_observed")),
            "settled_delta": r.get("settled_delta"),
            "level_delta": int(r.get("level_delta", 0) or 0),
            "levels_completed": int(r.get("levels_completed", 0) or 0),
            "state": r.get("state"),
        }
        for r in memory[-MEMORY_LIMIT:]
    ]


def prompt_for(game_id: str, env: Any, obs: Any, current_frame: Any, current_fresh: bool,
               arm: str, memory: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
    actions = em.action_descriptors(env)
    legal_ids = [int(a["id"]) for a in actions]
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": em.obs_levels(obs),
        "state": em.obs_state(obs),
        "legal_actions": actions,
        "exact_current_final_frame": current_frame,
        "current_frame_is_new_in_latest_observation": current_fresh,
    }
    prior = None
    if arm == "effect_memory_raw":
        payload["recent_settled_action_effects"] = raw_memory_view(memory)
        payload["memory_note"] = (
            "Same-run visible history only. no-new-frame means unknown effect, not zero effect; "
            "the last actually visible frame is carried forward."
        )
    else:
        prior = current_state_prior(memory, current_frame, legal_ids)
        payload["recent_transition_sketch"] = compact_sketch(memory)
        payload["sketch_note"] = (
            "Compact same-run transition evidence. UNKNOWN_NO_NEW_FRAME is not negative. "
            "State ids are digests only for matching previously visible states; infer behavior from the exact current frame."
        )
        if prior is not None:
            payload["routing_prior"] = prior
            payload["routing_note"] = (
                "Soft anti-loop prior only: a demoted action previously produced visible no effect from this exact visible-state digest. "
                "It remains legal; prefer an untried plausible action when useful."
            )
    return compact_json(payload), prior


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
    memory: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0
    no_new_frame_count = 0
    prior_activation_count = 0

    for step in range(1, STEP_BUDGET + 1):
        legal_ids = [int(a["id"]) for a in em.action_descriptors(env)]
        prompt, prior = prompt_for(game_id, env, obs, current_frame, current_fresh, arm, memory)
        if prior is not None:
            prior_activation_count += 1
        call = provider_action_call(prompt, legal_ids)
        row: dict[str, Any] = {
            "step": step,
            "arm": arm,
            "prompt_chars": len(prompt),
            "routing_prior": prior,
            **call,
        }
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
            "outcome": entry["outcome"],
            "before_frame_id": entry["before_frame_id"],
            "after_frame_id": entry["after_frame_id"],
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
        "prior_activation_count": prior_activation_count,
        "final_transition_sketch": compact_sketch(memory),
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
        "prior_activation_total": sum(int(r["result"].get("prior_activation_count", 0)) for r in valid),
        "provider_calls": len(calls),
        "provider_http_429": sum(int(x.get("http_status", 0) or 0) == 429 for x in calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-state-action-loop-sketch-ab.json"))
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
    base = summarize(results, "effect_memory_raw")
    aug = summarize(results, "state_action_loop_sketch")
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
        gate = "PROMOTE_STATE_ACTION_LOOP_SKETCH_MORE_GAINS"
    elif equal_positive and nondominated_efficiency:
        gate = "PROMOTE_STATE_ACTION_LOOP_SKETCH_EQUAL_POSITIVE_NONDOMINATED"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-state-action-loop-sketch-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "change_kind": "STATE_CONDITIONED_COMPACT_REPRESENTATION_NOT_FAILED_RUN_RETRY",
        "source_grounding": SOURCE_GROUNDING,
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "max_provider_calls": len(TARGETS) * len(ARMS) * STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "sketch_limit": SKETCH_LIMIT,
        "results": results,
        "summary": {
            "effect_memory_raw": base,
            "state_action_loop_sketch": aug,
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
            "candidate_changes_memory_representation_not_pixel_geometry": True,
            "state_specific_soft_demotion_only": True,
            "unknown_no_new_frame_never_counts_as_negative_effect": True,
            "soft_demotion_never_hard_bans_legal_action": True,
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
