#!/usr/bin/env python3
"""Rung 129: target-blind observed-transition memory A/B.

Rung 128 tested model-authored visible self-note continuity and found no solver gain.
This rung changes representation rather than retrying that mechanism: both arms discard
model-authored notes, while the treatment receives only one bounded deterministic summary
of the immediately preceding *observed* action/result transition. The summary is derived
from visible runtime observations only (action, fresh-frame presence, cell diff/bbox,
level delta and state); it never uses game source, hidden state, public solution traces,
or future outcomes.

Architecture motivation is source-level only. ARC Prize's public community leaderboard
summarizes Retrodict as recording frames and checking hypotheses against history, while the
Milestone #1 write-up highlights recent-history retention/eviction in Tufa's Duck. No
upstream implementation is imported or copied. This is clean-room public-development A/B,
not Kaggle execution or hidden-score evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import arc_agi
from arc_agi import OperationMode

import adaptive_lossless_behavior_ab_v3_identity as ident
import public_visible_continuity_compaction_ab_128 as b
import public_visible_continuity_compaction_ab_128_twostage as two

RUNG = 129
TARGETS = b.TARGETS
ARMS = ("current_visible_only", "carry_observed_transition")
STEP_BUDGET = 6
MEMORY_CHAR_BUDGET = 420


def stable(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def frame_diff(before: Any, after: Any) -> dict[str, Any]:
    if not isinstance(before, list) or not isinstance(after, list):
        return {"comparable": False}
    if len(before) != len(after):
        return {"comparable": False, "shape_changed": True}
    changed: list[tuple[int, int]] = []
    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}
    for y, (rb, ra) in enumerate(zip(before, after)):
        if not isinstance(rb, list) or not isinstance(ra, list) or len(rb) != len(ra):
            return {"comparable": False, "shape_changed": True}
        for x, (vb, va) in enumerate(zip(rb, ra)):
            before_counts[str(vb)] = before_counts.get(str(vb), 0) + 1
            after_counts[str(va)] = after_counts.get(str(va), 0) + 1
            if vb != va:
                changed.append((x, y))
    out: dict[str, Any] = {"comparable": True, "changed_cells": len(changed)}
    if changed:
        xs = [p[0] for p in changed]
        ys = [p[1] for p in changed]
        out["changed_bbox_xyxy"] = [min(xs), min(ys), max(xs), max(ys)]
        colors = sorted(set(before_counts) | set(after_counts))
        deltas = {c: after_counts.get(c, 0) - before_counts.get(c, 0) for c in colors}
        out["color_count_delta"] = {c: d for c, d in deltas.items() if d}
    return out


def transition_fact(
    before_frame: Any,
    fresh_frame: Any | None,
    choice: dict[str, Any],
    before_levels: int,
    next_obs: Any,
) -> str:
    fact: dict[str, Any] = {
        "action": int(choice["action"]),
        "new_frame_observed": fresh_frame is not None,
        "level_delta": b.obs_levels(next_obs) - before_levels,
        "state_after": b.obs_state(next_obs),
    }
    if int(choice["action"]) == 6 and "x" in choice and "y" in choice:
        fact["click_xy"] = [int(choice["x"]), int(choice["y"])]
    if fresh_frame is not None:
        fact["visible_diff"] = frame_diff(before_frame, fresh_frame)
    text = stable(fact)
    # The fact is deterministic. Bound only as a safety fence; normal summaries fit well below this.
    return text[:MEMORY_CHAR_BUDGET]


def parse_policy(content: str, legal_ids: set[int]) -> tuple[dict[str, Any] | None, str | None]:
    return two.parse_policy_choice(content, legal_ids)


def provider_call(prompt: str, legal_ids: set[int]) -> dict[str, Any]:
    payload = json.dumps({
        "model": ident.MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Choose one legal action in a public grid-world using only supplied visible runtime evidence. "
                    "An optional prior_observed_transition is a deterministic summary of the immediately preceding "
                    "visible action/result and is not hidden state. Prefer progress/completion. Return exactly one JSON "
                    "object and no prose: {\"action\":INTEGER,\"note\":\"<=240 chars\"}. If action 6 is chosen, "
                    "coordinates may be omitted here because a separate identical-model coordinate decoder will run. "
                    "Never claim access to game source or hidden state."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 112,
    }).encode("utf-8")
    req = urllib.request.Request(
        ident.v2.impl.seg.base.ENDPOINT,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    status = 0
    body = b""
    err = None
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=ident.v2.impl.seg.base.TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        err = f"HTTPError:{exc.code}"
    except Exception as exc:
        err = f"{type(exc).__name__}:{exc}"
    latency_ms = int((time.monotonic() - started) * 1000)
    served_model = None
    content = ""
    if body:
        try:
            parsed = json.loads(body)
            served_model = parsed.get("model") if isinstance(parsed, dict) else None
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = body.decode("utf-8", "replace")[:1000]
    identity_ok = bool(status == 200 and served_model == ident.MODEL)
    choice, parse_error = parse_policy(content, legal_ids) if identity_ok else (None, None)
    if status == 200 and not identity_ok:
        err = f"MODEL_IDENTITY_MISMATCH:{served_model!r}"
    elif identity_ok and parse_error:
        err = parse_error
    return {
        "http_status": status,
        "latency_ms": latency_ms,
        "served_model": served_model,
        "identity_ok": identity_ok,
        "provider_execution": identity_ok,
        "choice": choice,
        "parse_error": parse_error,
        "error": err,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_content": content[:500],
    }


def prompt_for(game_id: str, env: Any, obs: Any, current: Any, prior_transition: str | None) -> str:
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": b.obs_levels(obs),
        "state": b.obs_state(obs),
        "legal_actions": b.action_descriptors(env),
        "exact_current_visible_frame": current,
        "instruction": "Choose the next legal action. The note is output-only scratch and will not be carried by either arm.",
    }
    if prior_transition is not None:
        payload["prior_observed_transition"] = json.loads(prior_transition)
        payload["transition_scope"] = "immediately preceding visible runtime action/result only; deterministic and fallible only via observation availability"
    return b.compact_json(payload)


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    try:
        obs = b.initial_probe(env, probe_action)
    except Exception as exc:
        return {"inconclusive": f"PROBE_FAILED:{type(exc).__name__}:{exc}", "rows": []}
    current = b.observed_frame(obs)
    if current is None:
        return {"inconclusive": f"NO_INITIAL_FRAME:{game_id}", "rows": []}
    start_levels = b.obs_levels(obs)
    prior_transition: str | None = None
    rows: list[dict[str, Any]] = []
    terminal = False
    for step in range(1, STEP_BUDGET + 1):
        legal_ids = {int(a.value) for a in env.action_space}
        memory_in = prior_transition if arm == "carry_observed_transition" else None
        prompt = prompt_for(game_id, env, obs, current, memory_in)
        call = provider_call(prompt, legal_ids)
        row: dict[str, Any] = {
            "step": step,
            "arm": arm,
            "prompt_chars": len(prompt),
            "memory_in_chars": len(memory_in or ""),
            **call,
        }
        choice = call.get("choice")
        if not call["identity_ok"] or choice is None:
            row["execution"] = None
            rows.append(row)
            return {"inconclusive": f"POLICY_CALL_INVALID:{game_id}:{arm}:step{step}:{call.get('error')}", "rows": rows, "start_levels": start_levels}
        if int(choice["action"]) == 6 and not {"x", "y"}.issubset(choice):
            coord = two.coordinate_call(game_id, current, str(choice.get("note", "")))
            row["coordinate_call"] = coord
            if not coord["identity_ok"] or coord["coords"] is None:
                row["execution"] = None
                rows.append(row)
                return {"inconclusive": f"COORD_CALL_INVALID:{game_id}:{arm}:step{step}:{coord.get('error')}", "rows": rows, "start_levels": start_levels}
            choice = {**choice, **coord["coords"]}
            row["choice"] = choice
        else:
            row["coordinate_call"] = None
        amap = {int(a.value): a for a in env.action_space}
        before_frame = current
        before_levels = b.obs_levels(obs)
        try:
            next_obs = b.execute(env, amap, choice)
        except Exception as exc:
            row["execution"] = None
            row["execution_error"] = f"{type(exc).__name__}:{exc}"
            rows.append(row)
            return {"inconclusive": f"ACTION_EXECUTION_FAILED:{game_id}:{arm}:step{step}", "rows": rows, "start_levels": start_levels}
        fresh = b.observed_frame(next_obs)
        fact = transition_fact(before_frame, fresh, choice, before_levels, next_obs)
        prior_transition = fact
        if fresh is not None:
            current = fresh
        gain = b.obs_levels(next_obs) - start_levels
        state = b.obs_state(next_obs)
        terminal = state.upper() in {"GAME_OVER", "LOST", "FAILED"}
        row["memory_out_chars"] = len(fact)
        row["observed_transition"] = json.loads(fact)
        row["execution"] = {
            "levels_completed": b.obs_levels(next_obs),
            "level_gain_from_probe": gain,
            "state": state,
            "terminal_failure": terminal,
            "new_frame_observed": fresh is not None,
        }
        rows.append(row)
        obs = next_obs
        if gain > 0 or terminal:
            break
    return {
        "inconclusive": None,
        "rows": rows,
        "start_levels": start_levels,
        "final_levels": b.obs_levels(obs),
        "level_gain": b.obs_levels(obs) - start_levels,
        "terminal_failure": terminal,
        "policy_actions": len(rows),
    }


def summarize(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rr = [r for r in results if r["arm"] == arm]
    valid = [r for r in rr if not r["result"].get("inconclusive")]
    calls = [x for r in rr for x in r["result"].get("rows", [])]
    coord = [x["coordinate_call"] for x in calls if x.get("coordinate_call") is not None]
    return {
        "games": len(rr),
        "valid_games": len(valid),
        "games_with_level_gain": sum(int(r["result"].get("level_gain", 0)) > 0 for r in valid),
        "level_gain_total": sum(int(r["result"].get("level_gain", 0)) for r in valid),
        "terminal_failures": sum(bool(r["result"].get("terminal_failure")) for r in valid),
        "policy_actions_total": sum(int(r["result"].get("policy_actions", 0)) for r in valid),
        "provider_calls": len(calls),
        "provider_http_429": sum(int(x.get("http_status", 0) or 0) == 429 for x in calls),
        "identity_verified_calls": sum(bool(x.get("identity_ok")) for x in calls),
        "coordinate_calls": len(coord),
        "coordinate_identity_verified": sum(bool(x.get("identity_ok")) for x in coord),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "memory_in_chars_total": sum(int(x.get("memory_in_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-observed-transition-memory-ab-129.json"))
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
    base = summarize(results, "current_visible_only")
    aug = summarize(results, "carry_observed_transition")
    if inconclusive:
        gate = "INCONCLUSIVE_EXECUTION"
    elif aug["level_gain_total"] > base["level_gain_total"] and aug["terminal_failures"] <= base["terminal_failures"]:
        gate = "PROMOTE_PUBLIC_OBSERVED_TRANSITION_MEMORY_BEHAVIOR_GAIN"
    else:
        gate = "VALID_NO_PROMOTION"
    receipt = {
        "schema": "deus/arc3-public-observed-transition-memory-ab/1",
        "rung": RUNG,
        "change_kind": "DETERMINISTIC_OBSERVED_TRANSITION_MEMORY_AB",
        "provider": "BLOCKRUN",
        "requested_model": ident.MODEL,
        "source_grounding": {
            "clean_room_implementation": True,
            "upstream_implementation_imported": False,
            "upstream_implementation_copied": False,
            "official_arc_community_leaderboard": "https://arcprize.org/leaderboard/community",
            "official_arc_milestone1_writeup": "https://arcprize.org/blog/arc-prize-2026-milestone-1",
            "architectural_principle_only": "retain/check observed history without model-authored memory as authority",
        },
        "step_budget_per_arm": STEP_BUDGET,
        "memory_char_budget": MEMORY_CHAR_BUDGET,
        "representation_change_from_rung128": {
            "rung128_result": "VALID_NO_PROMOTION",
            "model_authored_self_note_carried": False,
            "treatment_memory": "one bounded deterministic immediately-prior observed action/result summary",
            "blind_retry_of_rung128_calls": False,
            "two_stage_click_representation_preserved": True,
            "provider_retries": False,
        },
        "summary": {"current_visible_only": base, "carry_observed_transition": aug},
        "promotion_gate": gate,
        "inconclusive": inconclusive,
        "results": results,
        "truth": {
            "public_development_environment_only": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "same_response_contract_both_arms": True,
            "model_authored_note_carried_by_either_arm": False,
            "treatment_memory_derived_only_from_observed_runtime_transition": True,
            "game_source_read": False,
            "hidden_state_read": False,
            "public_solution_trace_supplied_to_model": False,
            "future_outcome_used_in_prompt": False,
            "target_blind": True,
            "provider_call_retries": False,
            "failed_prior_mechanism_changed_representation_not_blind_retry": True,
            "promotion_requires_solver_behavior_gain": True,
            "efficiency_alone_cannot_promote": True,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "independent_generalization_claim": False,
            "award_or_settlement_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": receipt["summary"], "promotion_gate": gate, "inconclusive": inconclusive, "truth": receipt["truth"]}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
