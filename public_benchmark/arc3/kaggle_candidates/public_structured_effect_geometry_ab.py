#!/usr/bin/env python3
"""Target-blind public A/B: settled effect memory vs compact structured effect geometry.

Both arms see the exact same current final frame, legal actions, same-run settled action
history, same served model, targets, probe action, and fixed policy budget. The candidate
adds only descriptive geometry computed from visible before/after final frames: connected
changed regions and color-mass centroid shifts. It reads no source, hidden state, Kaggle
data, or target outcome. Promotion requires public solver-behavior gain; representation
compression/latency alone cannot promote a zero-gain arm.

Concept grounding: KHUB ARC-AGI-3 public work at pinned commit de41a93... documents
context-aware action effectiveness and game-agnostic relational kinematics (displacement,
adjacency, overlap). This implementation is clean-room and deliberately narrower: it
only summarizes directly observed pixel transitions and does not copy KHUB code.
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
import public_effect_memory_rollout_ab as em

TARGETS = em.TARGETS
ARMS = ("effect_memory", "effect_memory_plus_geometry")
STEP_BUDGET = em.STEP_BUDGET
MEMORY_LIMIT = em.MEMORY_LIMIT
SOURCE_REF = "khub-ai/arc-agi-3@de41a93e3a4557db24702fceddb2409c7bc06afd"


def _valid_grid(x: Any) -> bool:
    return bool(
        isinstance(x, list) and x and all(isinstance(r, list) for r in x)
        and len({len(r) for r in x}) == 1
    )


def _components(coords: set[tuple[int, int]]) -> list[dict[str, Any]]:
    left = set(coords)
    out: list[dict[str, Any]] = []
    while left:
        seed = min(left)
        stack = [seed]
        left.remove(seed)
        comp = [seed]
        while stack:
            r, c = stack.pop()
            for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if q in left:
                    left.remove(q)
                    stack.append(q)
                    comp.append(q)
        rs = [r for r, _ in comp]
        cs = [c for _, c in comp]
        out.append({
            "n": len(comp),
            "bbox": [min(rs), min(cs), max(rs), max(cs)],
            "centroid": [round(sum(rs) / len(rs), 2), round(sum(cs) / len(cs), 2)],
        })
    return sorted(out, key=lambda z: (-z["n"], z["bbox"]))[:6]


def effect_geometry(before: Any, after: Any) -> dict[str, Any]:
    before = plain(before)
    after = plain(after)
    if not (_valid_grid(before) and _valid_grid(after)):
        return {"valid": False}
    if len(before) != len(after) or len(before[0]) != len(after[0]):
        return {"valid": False}

    changed: set[tuple[int, int]] = set()
    removed: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    added: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    for r in range(len(before)):
        for c in range(len(before[0])):
            a, b = before[r][c], after[r][c]
            if a == b:
                continue
            changed.add((r, c))
            removed[str(a)].append((r, c))
            added[str(b)].append((r, c))

    shifts: list[dict[str, Any]] = []
    for color in sorted(set(removed) & set(added)):
        ra, aa = removed[color], added[color]
        if len(ra) != len(aa) or not ra:
            continue
        r0 = sum(r for r, _ in ra) / len(ra)
        c0 = sum(c for _, c in ra) / len(ra)
        r1 = sum(r for r, _ in aa) / len(aa)
        c1 = sum(c for _, c in aa) / len(aa)
        dr, dc = round(r1 - r0, 2), round(c1 - c0, 2)
        if dr or dc:
            shifts.append({"color": color, "n": len(ra), "dcentroid": [dr, dc]})
    shifts.sort(key=lambda z: (-z["n"], z["color"]))

    return {
        "valid": True,
        "changed_components": _components(changed),
        "component_count": len(_components(changed)),
        "mass_shifts": shifts[:6],
    }


def memory_entry(action_id: int, before_frame: Any | None, obs: Any, with_geometry: bool) -> dict[str, Any]:
    base = em.memory_entry(action_id, before_frame, obs)
    if with_geometry and before_frame is not None:
        after = em.final_frame(obs)
        if after is not None:
            base["effect_geometry"] = effect_geometry(before_frame, after)
    return base


def prompt_for(game_id: str, env: Any, obs: Any, arm: str, memory: list[dict[str, Any]]) -> str:
    current = em.final_frame(obs)
    if current is None:
        raise RuntimeError(f"no current frame for {game_id}")
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": em.obs_levels(obs),
        "state": em.obs_state(obs),
        "legal_actions": em.action_descriptors(env),
        "exact_current_final_frame": current,
        "recent_settled_action_effects": memory[-MEMORY_LIMIT:],
        "memory_note": (
            "Each row is observed same-run settled history. settled_delta compares persistent "
            "final frames before/after the action; treat observations as evidence, not rules."
        ),
    }
    if arm == "effect_memory_plus_geometry":
        payload["geometry_note"] = (
            "effect_geometry is target-blind descriptive pixel geometry from the same visible "
            "before/after frames: connected changed regions and same-color centroid shifts."
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
    if em.final_frame(obs) is None:
        return {"inconclusive": f"NO_FRAME_AFTER_PROBE:{game_id}", "rows": []}
    start_levels = em.obs_levels(obs)
    with_geometry = arm == "effect_memory_plus_geometry"
    memory = [memory_entry(probe_action, None, obs, with_geometry)]
    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0

    for step in range(1, STEP_BUDGET + 1):
        actions = em.action_descriptors(env)
        legal_ids = [int(a["id"]) for a in actions]
        prompt = prompt_for(game_id, env, obs, arm, memory)
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

        before = em.final_frame(obs)
        next_obs = env.step(amap[chosen])
        entry = memory_entry(chosen, before, next_obs, with_geometry)
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
            "settled_delta": entry["settled_delta"],
            "effect_geometry_present": "effect_geometry" in entry,
        }
        rows.append(row)
        obs = next_obs
        if gain > 0 or terminal:
            break
        if em.final_frame(obs) is None:
            return {"inconclusive": f"NO_FRAME_AFTER_ACTION:{game_id}:{arm}:step{step}", "rows": rows, "start_levels": start_levels}

    return {
        "inconclusive": None,
        "rows": rows,
        "start_levels": start_levels,
        "final_levels": em.obs_levels(obs),
        "level_gain": gain,
        "terminal_failure": terminal,
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
        "policy_actions_total": sum(int(r["result"].get("policy_actions", 0)) for r in valid),
        "provider_calls": len(calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-structured-effect-geometry-ab.json"))
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
        "schema": "deus/arc3-public-structured-effect-geometry-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "source_grounding": {
            "upstream_ref": SOURCE_REF,
            "license": "MIT-0",
            "concepts": ["context-aware action effectiveness", "game-agnostic relational kinematics"],
            "clean_room_implementation": True,
        },
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "memory_limit": MEMORY_LIMIT,
        "results": results,
        "summary": {"effect_memory": base, "effect_memory_plus_geometry": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "truth": {
            "public_development_environment_only": True,
            "same_exact_current_final_frame_contract_between_arms": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "candidate_adds_visible_same_run_geometry_only": True,
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
