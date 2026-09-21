#!/usr/bin/env python3
"""Bounded public solver A/B for causal settled-effect memory.

This experiment deliberately changes representation after compact animation metadata
failed to change solver behavior. Both arms start from the same fixed public probe
action and use the same identity-grounded provider model. The baseline sees the
exact settled current frame only. The augmented arm sees the same exact frame plus
a compact ledger of recent *settled* action effects (persistent frame deltas,
level/state changes, and frame-count metadata). It does not read game source,
hidden state, Kaggle data, or target answers.

Each arm is allowed a fixed number of model-chosen actions and stops early after
its first new level completion or a terminal state. Promotion requires a real
public solver-behavior gain: more games with a level gain, or equal positive gains
with fewer policy actions, without more terminal failures. Prompt compression or
board motion alone cannot promote.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

from animation_delta_signature import compact_json, plain
from public_animation_action_ab import provider_action_call
from public_multiframe_probe import frame_list

TARGETS = (("sp80", 5), ("bp35", 3), ("wa30", 1))
ARMS = ("final_only", "final_plus_effect_memory")
STEP_BUDGET = 6
MEMORY_LIMIT = 4


def action_descriptors(env: Any) -> list[dict[str, Any]]:
    return sorted(
        ({"id": int(a.value), "name": str(getattr(a, "name", a))} for a in env.action_space),
        key=lambda x: x["id"],
    )


def obs_state(obs: Any) -> str:
    return str(getattr(getattr(obs, "state", None), "value", getattr(obs, "state", "")))


def obs_levels(obs: Any) -> int:
    return int(getattr(obs, "levels_completed", 0) or 0)


def final_frame(obs: Any) -> Any | None:
    frames = frame_list(obs)
    return plain(frames[-1]) if frames else None


def settled_delta(before: Any, after: Any) -> dict[str, Any]:
    before = plain(before)
    after = plain(after)
    if not (
        isinstance(before, list)
        and isinstance(after, list)
        and len(before) == len(after)
        and all(isinstance(r, list) for r in before)
        and all(isinstance(r, list) for r in after)
    ):
        return {"changed": None, "bbox": None, "pairs": []}
    coords: list[tuple[int, int]] = []
    pairs: collections.Counter[tuple[Any, Any]] = collections.Counter()
    for r, (ra, rb) in enumerate(zip(before, after)):
        if len(ra) != len(rb):
            return {"changed": None, "bbox": None, "pairs": []}
        for c, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                coords.append((r, c))
                pairs[(x, y)] += 1
    if not coords:
        return {"changed": 0, "bbox": None, "pairs": []}
    rs = [r for r, _ in coords]
    cs = [c for _, c in coords]
    top = sorted(
        ((str(a), str(b), int(n)) for (a, b), n in pairs.items()),
        key=lambda x: (-x[2], x[0], x[1]),
    )[:4]
    return {
        "changed": len(coords),
        "bbox": [min(rs), min(cs), max(rs), max(cs)],
        "pairs": [list(x) for x in top],
    }


def memory_entry(action_id: int, before_frame: Any | None, obs: Any) -> dict[str, Any]:
    frames = frame_list(obs)
    after_frame = plain(frames[-1]) if frames else None
    delta = settled_delta(before_frame, after_frame) if before_frame is not None and after_frame is not None else {
        "changed": None,
        "bbox": None,
        "pairs": [],
    }
    return {
        "action": int(action_id),
        "frames": len(frames),
        "settled_delta": delta,
        "levels_completed": obs_levels(obs),
        "state": obs_state(obs),
    }


def prompt_for(game_id: str, env: Any, obs: Any, arm: str, memory: list[dict[str, Any]]) -> str:
    current = final_frame(obs)
    if current is None:
        raise RuntimeError(f"no current frame for {game_id}")
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": obs_levels(obs),
        "state": obs_state(obs),
        "legal_actions": action_descriptors(env),
        "exact_current_final_frame": current,
    }
    if arm == "final_plus_effect_memory":
        payload["recent_settled_action_effects"] = memory[-MEMORY_LIMIT:]
        payload["memory_note"] = (
            "Each row is observed causal history from this same public run. "
            "settled_delta compares persistent final frames before/after the action; "
            "frames reports transient frame count only. Treat this as evidence, not a rule guarantee."
        )
    return compact_json(payload)


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        return {"inconclusive": f"PROBE_UNAVAILABLE:{game_id}:{probe_action}", "rows": []}

    probe_obs = env.step(amap[probe_action])
    current = final_frame(probe_obs)
    if current is None:
        return {"inconclusive": f"NO_FRAME_AFTER_PROBE:{game_id}", "rows": []}
    start_levels = obs_levels(probe_obs)
    memory = [memory_entry(probe_action, None, probe_obs)]
    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0

    for step in range(1, STEP_BUDGET + 1):
        actions = action_descriptors(env)
        legal_ids = [int(a["id"]) for a in actions]
        prompt = prompt_for(game_id, env, probe_obs, arm, memory)
        call = provider_action_call(prompt, legal_ids)
        row: dict[str, Any] = {
            "step": step,
            "arm": arm,
            "prompt_chars": len(prompt),
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

        before = final_frame(probe_obs)
        next_obs = env.step(amap[chosen])
        after = final_frame(next_obs)
        entry = memory_entry(chosen, before, next_obs)
        memory.append(entry)
        levels_now = obs_levels(next_obs)
        state_now = obs_state(next_obs)
        gain = levels_now - start_levels
        terminal = state_now.upper() in {"GAME_OVER", "LOST", "FAILED"}
        row["execution"] = {
            "levels_completed": levels_now,
            "level_gain_from_probe": gain,
            "state": state_now,
            "terminal_failure": terminal,
            "frame_count": len(frame_list(next_obs)),
            "settled_delta": entry["settled_delta"],
        }
        rows.append(row)
        probe_obs = next_obs
        if gain > 0 or terminal:
            break
        if after is None:
            return {
                "inconclusive": f"NO_FRAME_AFTER_ACTION:{game_id}:{arm}:step{step}",
                "rows": rows,
                "start_levels": start_levels,
            }

    return {
        "inconclusive": None,
        "rows": rows,
        "start_levels": start_levels,
        "final_levels": obs_levels(probe_obs),
        "level_gain": gain,
        "terminal_failure": terminal,
        "policy_actions": len(rows),
        "final_memory": memory[-MEMORY_LIMIT:],
    }


def summarize(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rr = [r for r in results if r["arm"] == arm]
    valid = [r for r in rr if not r["result"].get("inconclusive")]
    return {
        "games": len(rr),
        "valid_games": len(valid),
        "games_with_level_gain": sum(int(r["result"].get("level_gain", 0)) > 0 for r in valid),
        "level_gain_total": sum(int(r["result"].get("level_gain", 0)) for r in valid),
        "terminal_failures": sum(bool(r["result"].get("terminal_failure")) for r in valid),
        "policy_actions_total": sum(int(r["result"].get("policy_actions", 0)) for r in valid),
        "provider_calls": sum(len(r["result"].get("rows", [])) for r in rr),
        "prompt_chars_total": sum(
            int(x.get("prompt_chars", 0)) for r in rr for x in r["result"].get("rows", [])
        ),
        "mean_latency_ms": round(
            sum(int(x.get("latency_ms", 0)) for r in rr for x in r["result"].get("rows", []))
            / max(1, sum(len(r["result"].get("rows", [])) for r in rr)),
            1,
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-effect-memory-rollout-ab.json"))
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
    elif aug["terminal_failures"] > base["terminal_failures"]:
        gate = "VALID_NO_PROMOTION_MORE_TERMINAL_FAILURES"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"]:
        gate = "PROMOTE_EFFECT_MEMORY_MORE_GAINS"
    elif (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["policy_actions_total"] < base["policy_actions_total"]
    ):
        gate = "PROMOTE_EFFECT_MEMORY_EQUAL_GAINS_FEWER_ACTIONS"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-effect-memory-rollout-ab/1",
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
            "promotion_requires_solver_behavior_gain": True,
            "prompt_or_footprint_change_alone_cannot_promote": True,
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
