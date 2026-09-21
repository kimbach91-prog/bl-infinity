#!/usr/bin/env python3
"""Rung 126: target-blind scene-causal abstraction A/B.

This is a clean-room experiment motivated by public descriptions of successful
ARC-AGI-3 harnesses: reason over objects/relations, separate likely HUD/timer state
from puzzle state, retain observed before/after causal evidence, and use soft
information-seeking guidance when the mechanism is uncertain.

No upstream implementation code is copied. Both arms use the same public games,
probe actions, served-model contract, and three model-chosen actions. Baseline is
the already-tested raw settled-effect memory. Treatment keeps the exact current
visible frame but adds a compact independently implemented object scene and replaces
raw effect rows with compact scene-transition evidence. Likely-HUD labels are hints
only; no legal action is hidden or hard-banned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

from animation_delta_signature import compact_json, plain
from public_animation_action_ab import provider_action_call
from public_multiframe_probe import frame_list
import public_effect_memory_rollout_ab as em

TARGETS = em.TARGETS
ARMS = ("effect_memory_raw", "scene_causal_compact")
STEP_BUDGET = 3
MEMORY_LIMIT = 4
MAX_OBJECTS = 28
SOURCE_GROUNDING = {
    "duck_public_mirror": {
        "upstream_ref": "mariogemoll/arc-prize-2026-arc-agi-3@0a05c529ab58121843b5aaa29a411e175d159118",
        "project_license_metadata": "MIT classifier in ARC3-Inference/pyproject.toml",
        "principles_only": [
            "object-centric segmentation as primary structural view",
            "before/after transition reasoning",
            "distinguish likely HUD/timer changes from gameplay changes",
            "compact working world model and discriminating probes",
        ],
    },
    "clean_room_implementation": True,
    "upstream_code_copied": False,
}


def observed_frame(obs: Any) -> Any | None:
    fs = frame_list(obs)
    return plain(fs[-1]) if fs else None


def grid_ok(frame: Any) -> bool:
    return (
        isinstance(frame, list)
        and bool(frame)
        and all(isinstance(r, list) for r in frame)
        and len({len(r) for r in frame}) == 1
        and bool(frame[0])
    )


def _shape_sig(cells: list[tuple[int, int]], value: Any) -> str:
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    norm = sorted((r - r0, c - c0) for r, c in cells)
    return hashlib.sha256(repr((str(value), norm)).encode("utf-8")).hexdigest()[:12]


def scene(frame: Any) -> dict[str, Any]:
    """Independent 4-connected component scene summary; standard flood fill only."""
    frame = plain(frame)
    if not grid_ok(frame):
        return {"valid": False, "objects": [], "adjacency": [], "shape": None}
    h, w = len(frame), len(frame[0])
    seen: set[tuple[int, int]] = set()
    cells_by_obj: list[list[tuple[int, int]]] = []
    values: list[Any] = []
    owner = [[-1] * w for _ in range(h)]
    for sr in range(h):
        for sc in range(w):
            if (sr, sc) in seen:
                continue
            value = frame[sr][sc]
            q = deque([(sr, sc)])
            seen.add((sr, sc))
            cells: list[tuple[int, int]] = []
            oid = len(cells_by_obj)
            while q:
                r, c = q.popleft()
                cells.append((r, c))
                owner[r][c] = oid
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and frame[nr][nc] == value:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            cells_by_obj.append(cells)
            values.append(value)

    contact: Counter[tuple[int, int]] = Counter()
    for r in range(h):
        for c in range(w):
            a = owner[r][c]
            if r + 1 < h and owner[r + 1][c] != a:
                b = owner[r + 1][c]
                contact[tuple(sorted((a, b)))] += 1
            if c + 1 < w and owner[r][c + 1] != a:
                b = owner[r][c + 1]
                contact[tuple(sorted((a, b)))] += 1

    objects: list[dict[str, Any]] = []
    for oid, (cells, value) in enumerate(zip(cells_by_obj, values)):
        rs = [r for r, _ in cells]
        cs = [c for _, c in cells]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        bh, bw = r1 - r0 + 1, c1 - c0 + 1
        border = r0 == 0 or c0 == 0 or r1 == h - 1 or c1 == w - 1
        long_edge_strip = border and (
            (bh <= 2 and bw >= max(8, w // 3)) or
            (bw <= 2 and bh >= max(8, h // 3))
        )
        dominant = len(cells) >= int(0.45 * h * w)
        objects.append({
            "id": oid,
            "v": str(value),
            "n": len(cells),
            "bbox": [r0, c0, r1, c1],
            "sig": _shape_sig(cells, value),
            "touch_border": border,
            "role_hint": "likely_hud_edge_strip" if long_edge_strip else ("dominant_region" if dominant else "scene_object"),
        })

    # Preserve small/structured objects first; large dominant regions last.
    objects.sort(key=lambda o: (o["role_hint"] == "dominant_region", o["role_hint"] == "likely_hud_edge_strip", o["n"], o["id"]))
    keep_ids = {o["id"] for o in objects[:MAX_OBJECTS]}
    compact_objects = objects[:MAX_OBJECTS]
    adjacency = [
        [a, b, int(n)] for (a, b), n in sorted(contact.items())
        if a in keep_ids and b in keep_ids
    ][:64]
    return {
        "valid": True,
        "shape": [h, w],
        "object_count": len(objects),
        "objects": compact_objects,
        "adjacency_contacts": adjacency,
        "truncated_objects": max(0, len(objects) - len(compact_objects)),
    }


def scene_transition(before: Any, after: Any | None, action_id: int, level_delta: int) -> dict[str, Any]:
    if after is None:
        return {"a": int(action_id), "obs": "NO_NEW_FRAME_UNKNOWN", "dl": int(level_delta)}
    sb, sa = scene(before), scene(after)
    if not sb.get("valid") or not sa.get("valid"):
        return {"a": int(action_id), "obs": "UNSTRUCTURED", "dl": int(level_delta)}
    b = sb["objects"]
    a = sa["objects"]
    by_sig_b: dict[str, list[dict[str, Any]]] = {}
    by_sig_a: dict[str, list[dict[str, Any]]] = {}
    for o in b:
        by_sig_b.setdefault(o["sig"], []).append(o)
    for o in a:
        by_sig_a.setdefault(o["sig"], []).append(o)
    moved = 0
    appeared = 0
    disappeared = 0
    hud_changed = 0
    gameplay_changed = 0
    for sig in set(by_sig_b) | set(by_sig_a):
        bb, aa = by_sig_b.get(sig, []), by_sig_a.get(sig, [])
        matched = min(len(bb), len(aa))
        appeared += max(0, len(aa) - len(bb))
        disappeared += max(0, len(bb) - len(aa))
        for x, y in zip(bb[:matched], aa[:matched]):
            if x["bbox"] != y["bbox"]:
                moved += 1
                if x["role_hint"] == "likely_hud_edge_strip" and y["role_hint"] == "likely_hud_edge_strip":
                    hud_changed += 1
                else:
                    gameplay_changed += 1
    delta = em.settled_delta(before, after)
    return {
        "a": int(action_id),
        "obs": "VISIBLE",
        "dl": int(level_delta),
        "changed_cells": delta.get("changed"),
        "moved_objects": moved,
        "appeared_objects": appeared,
        "disappeared_objects": disappeared,
        "gameplay_object_motion": gameplay_changed,
        "likely_hud_motion": hud_changed,
        "hud_only_hint": bool((moved or appeared or disappeared) and gameplay_changed == 0 and hud_changed > 0),
    }


def raw_memory_view(memory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "action": r["action"],
            "new_frame_observed": r["new_frame_observed"],
            "settled_delta": r["settled_delta"],
            "level_delta": r["level_delta"],
            "levels_completed": r["levels_completed"],
            "state": r["state"],
        }
        for r in memory[-MEMORY_LIMIT:]
    ]


def make_memory(action_id: int, before: Any, before_levels: int, obs: Any, fresh: Any | None) -> dict[str, Any]:
    levels = em.obs_levels(obs)
    dl = levels - before_levels
    delta = em.settled_delta(before, fresh) if fresh is not None else {"changed": None, "bbox": None, "pairs": []}
    return {
        "action": int(action_id),
        "new_frame_observed": fresh is not None,
        "settled_delta": delta,
        "level_delta": int(dl),
        "levels_completed": int(levels),
        "state": em.obs_state(obs),
        "scene_transition": scene_transition(before, fresh, action_id, dl),
    }


def prompt_for(game_id: str, env: Any, obs: Any, current: Any, current_fresh: bool,
               arm: str, memory: list[dict[str, Any]]) -> str:
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": em.obs_levels(obs),
        "state": em.obs_state(obs),
        "legal_actions": em.action_descriptors(env),
        "exact_current_visible_frame": current,
        "current_frame_is_new_in_latest_observation": current_fresh,
    }
    if arm == "effect_memory_raw":
        payload["recent_settled_action_effects"] = raw_memory_view(memory)
        payload["decision_note"] = "Use same-run observed effects as evidence; no-new-frame is unknown, not zero effect."
    else:
        payload["scene_now"] = scene(current)
        payload["recent_causal_scene_transitions"] = [r["scene_transition"] for r in memory[-MEMORY_LIMIT:]]
        payload["decision_note"] = (
            "Reason scene-first over objects/relations and observed before/after effects. role_hint is uncertain evidence only. "
            "Do not treat likely HUD/timer-only motion as puzzle progress without corroboration. No action is banned. "
            "If mechanism is uncertain, prefer a legal discriminating probe with high information value; once an effect is clear, exploit it."
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
    current = observed_frame(obs)
    if current is None:
        return {"inconclusive": f"NO_INITIAL_FRAME:{game_id}", "rows": []}
    current_fresh = True
    start_levels = em.obs_levels(obs)
    memory: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    terminal = False
    gain = 0
    for step in range(1, STEP_BUDGET + 1):
        legal_ids = [int(x["id"]) for x in em.action_descriptors(env)]
        prompt = prompt_for(game_id, env, obs, current, current_fresh, arm, memory)
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
        before = current
        before_levels = em.obs_levels(obs)
        next_obs = env.step(amap[chosen])
        fresh = observed_frame(next_obs)
        current_fresh = fresh is not None
        if fresh is not None:
            current = fresh
        mem = make_memory(chosen, before, before_levels, next_obs, fresh)
        memory.append(mem)
        levels_now = em.obs_levels(next_obs)
        state_now = em.obs_state(next_obs)
        gain = levels_now - start_levels
        terminal = state_now.upper() in {"GAME_OVER", "LOST", "FAILED"}
        row["execution"] = {
            "levels_completed": levels_now,
            "level_gain_from_probe": gain,
            "state": state_now,
            "terminal_failure": terminal,
            "new_frame_observed": current_fresh,
            "scene_transition": mem["scene_transition"],
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
        "final_scene": scene(current),
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
        "provider_http_429": sum(int(x.get("http_status", 0) or 0) == 429 for x in calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-scene-causal-ab.json"))
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
    aug = summarize(results, "scene_causal_compact")
    equal_positive = (
        aug["games_with_level_gain"] == base["games_with_level_gain"]
        and aug["games_with_level_gain"] > 0
        and aug["level_gain_total"] == base["level_gain_total"]
    )
    nondominated = (
        aug["policy_actions_total"] <= base["policy_actions_total"]
        and aug["provider_calls"] <= base["provider_calls"]
        and aug["prompt_chars_total"] <= base["prompt_chars_total"]
        and (aug["policy_actions_total"] < base["policy_actions_total"] or aug["provider_calls"] < base["provider_calls"] or aug["prompt_chars_total"] < base["prompt_chars_total"])
    )
    if inconclusive:
        gate = "INCONCLUSIVE_RUNTIME_OR_PROVIDER"
    elif aug["terminal_failures"] > base["terminal_failures"]:
        gate = "VALID_NO_PROMOTION_MORE_TERMINAL_FAILURES"
    elif aug["games_with_level_gain"] > base["games_with_level_gain"] or aug["level_gain_total"] > base["level_gain_total"]:
        gate = "PROMOTE_SCENE_CAUSAL_MORE_GAINS"
    elif equal_positive and nondominated:
        gate = "PROMOTE_SCENE_CAUSAL_EQUAL_POSITIVE_NONDOMINATED"
    else:
        gate = "VALID_NO_PROMOTION"
    receipt = {
        "schema": "deus/arc3-public-scene-causal-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "change_kind": "SCENE_CAUSAL_ABSTRACTION_NOT_FAILED_RUN_RETRY",
        "source_grounding": SOURCE_GROUNDING,
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "summary": {"baseline": base, "treatment": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "results": results,
        "truth": {
            "public_development_environment_only": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "candidate_uses_same_run_visible_outcomes_only": True,
            "candidate_changes_representation_and_planning_context": True,
            "likely_hud_is_soft_hint_only": True,
            "no_legal_action_hidden_or_hard_banned": True,
            "no_new_frame_is_unknown_not_zero_effect": True,
            "last_visible_frame_carry_forward_shared": True,
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
    print(json.dumps({"source_grounding": SOURCE_GROUNDING, "summary": receipt["summary"], "promotion_gate": gate, "inconclusive": inconclusive, "truth": receipt["truth"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
