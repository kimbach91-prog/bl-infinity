#!/usr/bin/env python3
"""R199: TU93 timeout-aware symbolic planner with directional threat zones.

Repairs R198 from verified failure evidence:
- R198 mixed post-terminal keypresses into hazard labels.
- TU93's bottom HUD row is a countdown: color-6 cells fall toward zero; a
  pre-action count of one leads to timeout on the next action in observed traces.
- Color-8/15 3x3 entities are static directional threats.  The color-15 marker
  encodes facing.  The lethal square is the adjacent room one lattice step
  (6 px) in front of that threat.  Entering the threat's own room from a safe
  direction removes/bypasses it; it is not equivalent to entering its threat zone.

This rung is train-free and deterministic.  It classifies observed directional
actions from the pre-action board and runs a stateful BFS over
(player_room, remaining_threats), allowing safe removal of threats.

Public trace verification only; no hidden-game, Kaggle, or leaderboard claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

import public_tu93_symbolic_lattice_planner_198 as r198

GAME = r198.GAME
RUNG = 199
DIRS = r198.DIRS
Grid = list[list[int]]
TERMINAL = {"GAME_OVER", "LOST", "FAILED"}
FACE = {
    (0, 1): (-1, 0),
    (2, 1): (1, 0),
    (1, 0): (0, -1),
    (1, 2): (0, 1),
}


def timer_remaining(g: Grid) -> int | None:
    if len(g) < 64 or not g[63]:
        return None
    row = g[63]
    # R198 public TU93 traces expose the timer as a run of color-6 cells.
    if not all(v in (0, 6) for v in row):
        return None
    return sum(v == 6 for v in row)


def threat_sprites(g: Grid) -> list[dict[str, Any]]:
    out = []
    for r in range(0, len(g) - 2):
        for c in range(0, len(g[0]) - 2):
            w = r198.window(g, r, c)
            vals = r198.flat(w)
            if Counter(vals)[8] != 8 or Counter(vals)[15] != 1:
                continue
            marker = None
            for rr in range(3):
                for cc in range(3):
                    if w[rr][cc] == 15:
                        marker = (rr, cc)
            if marker not in FACE:
                continue
            dr, dc = FACE[marker]
            out.append(
                {
                    "pos": (r, c),
                    "marker": marker,
                    "facing": (dr, dc),
                    "danger": (r + 6 * dr, c + 6 * dc),
                }
            )
    # exact 3x3 sprite should only match at aligned top-left; de-dup defensively
    uniq = {}
    for x in out:
        uniq[x["pos"]] = x
    return [uniq[k] for k in sorted(uniq)]


def classify_preaction(g: Grid, action: str) -> tuple[str, dict[str, Any]]:
    if action not in DIRS:
        return "OTHER", {}
    p = r198.find_unique_sprite(g, r198.is_player)
    if p is None:
        return "NO_PLAYER", {}
    remain = timer_remaining(g)
    if remain is not None and remain <= 1:
        return "TIMEOUT", {"timer_remaining": remain, "player": p}

    r, c = p
    dr, dc = DIRS[action]
    if not r198.corridor_open(g, r, c, dr, dc):
        return "BLOCKED", {"timer_remaining": remain, "player": p}

    dest = r198.destination(r, c, action)
    threats = threat_sprites(g)
    danger = {x["danger"] for x in threats}
    if dest in danger:
        return "HAZARD", {
            "timer_remaining": remain,
            "player": p,
            "dest": dest,
            "danger_sources": [x["pos"] for x in threats if x["danger"] == dest],
        }

    goals = set(r198.find_goals(g))
    if dest in goals:
        return "GOAL", {"timer_remaining": remain, "player": p, "dest": dest}

    typ = r198.cell_type(g, *dest)
    threat_positions = {x["pos"] for x in threats}
    if dest in threat_positions or typ in {"EMPTY", "PLAYER"}:
        return "MOVE", {
            "timer_remaining": remain,
            "player": p,
            "dest": dest,
            "entered_threat": dest in threat_positions,
        }
    return "BLOCKED", {
        "timer_remaining": remain,
        "player": p,
        "dest": dest,
        "cell_type": typ,
    }


def observed_outcome(before: dict[str, Any], after: dict[str, Any]) -> str | None:
    if str(before.get("state", "")).upper() in TERMINAL:
        return None
    if int(after.get("level", 0)) > int(before.get("level", 0)) or int(
        after.get("score", 0)
    ) > int(before.get("score", 0)):
        return "GOAL"
    if str(after.get("state", "")).upper() in TERMINAL:
        remain = timer_remaining(before["board"])
        return "TIMEOUT" if remain is not None and remain <= 1 else "HAZARD"

    a, b = before["board"], after["board"]
    gameplay_changed = sum(
        a[r][c] != b[r][c]
        for r in range(min(63, len(a)))
        for c in range(len(a[0]))
    )
    return "MOVE" if gameplay_changed else "BLOCKED"


def room_kind(g: Grid, pos: tuple[int, int], threat_positions: set[tuple[int, int]], goals: set[tuple[int, int]]) -> str:
    if pos in threat_positions:
        return "THREAT"
    if pos in goals:
        return "GOAL"
    typ = r198.cell_type(g, *pos)
    return typ


def safe_plan(g: Grid) -> list[str] | None:
    start = r198.find_unique_sprite(g, r198.is_player)
    goals = set(r198.find_goals(g))
    threats = threat_sprites(g)
    if start is None or not goals:
        return None

    threat_by_pos = {x["pos"]: x for x in threats}
    all_ids = tuple(sorted(threat_by_pos))
    start_state = (start, all_ids)
    q = deque([(start_state, [])])
    seen = {start_state}

    while q:
        (pos, remaining_tuple), path = q.popleft()
        if pos in goals:
            return path
        remaining = set(remaining_tuple)
        live = [threat_by_pos[p] for p in remaining if p in threat_by_pos]
        danger = {x["danger"] for x in live}
        r, c = pos
        for action, (dr, dc) in DIRS.items():
            if not r198.corridor_open(g, r, c, dr, dc):
                continue
            dest = r198.destination(r, c, action)
            if dest in danger:
                continue
            kind = room_kind(g, dest, remaining, goals)
            if kind not in {"EMPTY", "GOAL", "PLAYER", "THREAT"}:
                continue
            nxt_remaining = set(remaining)
            if dest in nxt_remaining:
                nxt_remaining.remove(dest)
            state = (dest, tuple(sorted(nxt_remaining)))
            if state not in seen:
                seen.add(state)
                q.append((state, path + [action]))
    return None


def audit(paths: list[Path]) -> dict[str, Any]:
    cm = Counter()
    per_trace = []
    mismatches = []
    plans = Counter()
    no_plan_examples = []

    for path in paths:
        events = r198.load_events(path)
        pre = events[0]
        local = Counter()

        # Check only initial/reset/level-entry boards while nonterminal.
        for idx, e in enumerate(events):
            if not isinstance(e.get("board"), list):
                continue
            if str(e.get("state", "")).upper() in TERMINAL:
                continue
            prev = events[idx - 1] if idx > 0 else None
            is_reset = e.get("action_display") == "RESET"
            is_level_entry = idx == 0 or (
                isinstance(prev, dict)
                and int(e.get("level", 0)) > int(prev.get("level", 0))
            )
            if is_reset or is_level_entry:
                p = safe_plan(e["board"])
                plans["states"] += 1
                if p is None:
                    plans["no_plan"] += 1
                    if len(no_plan_examples) < 20:
                        no_plan_examples.append(
                            {
                                "file": path.name,
                                "event_index": idx,
                                "level": e.get("level"),
                                "timer": timer_remaining(e["board"]),
                                "player": r198.find_unique_sprite(e["board"], r198.is_player),
                                "goals": r198.find_goals(e["board"]),
                                "threats": threat_sprites(e["board"]),
                            }
                        )
                else:
                    plans["plan_found"] += 1
                    plans["total_plan_length"] += len(p)

        for e in events[1:]:
            if e.get("type") != "action":
                pre = e
                continue
            action = e.get("action_display")
            if action not in DIRS:
                pre = e
                continue
            obs = observed_outcome(pre, e)
            if obs is None:
                cm["skipped_postterminal"] += 1
                local["skipped_postterminal"] += 1
                pre = e
                continue
            pred, detail = classify_preaction(pre["board"], action)
            cm["tests"] += 1
            local["tests"] += 1
            cm[f"pred:{pred}"] += 1
            cm[f"obs:{obs}"] += 1
            if pred == obs:
                cm["correct"] += 1
                local["correct"] += 1
            else:
                cm["wrong"] += 1
                local["wrong"] += 1
                if len(mismatches) < 40:
                    mismatches.append(
                        {
                            "file": path.name,
                            "step": e.get("action_num"),
                            "action": action,
                            "pred": pred,
                            "obs": obs,
                            "detail": detail,
                        }
                    )
            pre = e

        per_trace.append(
            {
                "file": path.name,
                "tests": int(local["tests"]),
                "correct": int(local["correct"]),
                "wrong": int(local["wrong"]),
                "skipped_postterminal": int(local["skipped_postterminal"]),
            }
        )

    acc = cm["correct"] / cm["tests"] if cm["tests"] else 0.0
    plan_rate = plans["plan_found"] / plans["states"] if plans["states"] else 0.0
    pass_gate = acc >= 0.99 and plan_rate >= 0.99
    return {
        "schema": "deus/arc3-tu93-timeout-threat-symbolic/1",
        "rung": RUNG,
        "game": GAME,
        "transition_classifier": {
            "tests": int(cm["tests"]),
            "correct": int(cm["correct"]),
            "wrong": int(cm["wrong"]),
            "skipped_postterminal": int(cm["skipped_postterminal"]),
            "accuracy": round(acc, 6),
            "pred_counts": {
                k.split(":", 1)[1]: int(v)
                for k, v in cm.items()
                if k.startswith("pred:")
            },
            "obs_counts": {
                k.split(":", 1)[1]: int(v)
                for k, v in cm.items()
                if k.startswith("obs:")
            },
            "mismatch_examples": mismatches,
            "per_trace": per_trace,
        },
        "planner": {
            "states": int(plans["states"]),
            "plan_found": int(plans["plan_found"]),
            "no_plan": int(plans["no_plan"]),
            "plan_found_rate": round(plan_rate, 6),
            "mean_plan_length": round(
                plans["total_plan_length"] / plans["plan_found"], 3
            )
            if plans["plan_found"]
            else None,
            "no_plan_examples": no_plan_examples,
        },
        "diagnostic_gate": "TU93_SYMBOLIC_BEHAVIOR_SOLVER_PASS"
        if pass_gate
        else "TU93_SYMBOLIC_BEHAVIOR_SOLVER_NEEDS_REPAIR",
        "truth": {
            "public_trace_only": True,
            "train_free_deterministic_parser": True,
            "preaction_only_outcome_prediction": True,
            "postterminal_actions_excluded": True,
            "timeout_read_from_preaction_hud": True,
            "directional_threat_zone_from_preaction_board": True,
            "planner_state_includes_remaining_threats": True,
            "heldout_or_hidden_generalization_claim": False,
            "full_online_game_runtime_execution": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = audit(a.input)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "rung": RUNG,
                "gate": d["diagnostic_gate"],
                "classifier": {
                    k: v
                    for k, v in d["transition_classifier"].items()
                    if k not in ("per_trace", "mismatch_examples")
                },
                "planner": {
                    k: v
                    for k, v in d["planner"].items()
                    if k != "no_plan_examples"
                },
                "mismatches": d["transition_classifier"]["mismatch_examples"][:12],
                "no_plan_examples": d["planner"]["no_plan_examples"][:6],
            },
            sort_keys=True,
        )
    )
    return 0 if d["diagnostic_gate"] == "TU93_SYMBOLIC_BEHAVIOR_SOLVER_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
