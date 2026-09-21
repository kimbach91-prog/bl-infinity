#!/usr/bin/env python3
"""Fixed-budget public solver-behavior A/B for compact animation metadata.

For three fixed public ARC-AGI-3 games, replay one fixed probe action, then ask
the exact identity-grounded public provider model to choose the next legal action.
Baseline receives the exact final frame; augmented arm receives the same exact
final frame plus compact additive animation metadata when multiple frames exist.
Each chosen action is executed from a fresh replay-equivalent public environment.

Promotion is deliberately strict: animation can promote only if it produces more
immediate level completions without increasing game-over outcomes. Board-motion
or prompt-size differences alone never promote. This is public-development
solver-behavior evidence, not Kaggle execution or hidden-score evidence.
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
from animation_delta_signature import compact_json, encode_animation, plain
from public_multiframe_probe import changed_cells, frame_list

TARGETS = (("sp80", 5), ("bp35", 3), ("wa30", 1))
ARMS = ("final_only", "final_plus_animation")


def provider_action_call(prompt: str, legal_ids: list[int]) -> dict[str, Any]:
    payload = json.dumps({
        "model": ident.MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are choosing one legal action in a public grid-world. "
                    "Use only the supplied current observation and action list. "
                    "Prefer the action most likely to advance or complete the current level. "
                    "Reply with exactly one integer action id and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }).encode("utf-8")
    req = urllib.request.Request(
        ident.v2.impl.seg.base.ENDPOINT,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    status = 0
    body = b""
    error = None
    parsed: Any = None
    try:
        with urllib.request.urlopen(req, timeout=ident.v2.impl.seg.base.TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        error = f"HTTPError:{exc.code}"
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
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
    match = re.fullmatch(r"\s*(\d+)\s*", content or "")
    chosen = int(match.group(1)) if match else None
    legal = chosen in legal_ids if chosen is not None else False
    if status == 200 and not identity_ok:
        error = f"MODEL_IDENTITY_MISMATCH:{served_model!r}"
    elif identity_ok and not legal:
        error = f"INVALID_ACTION_RESPONSE:{content!r}"
    return {
        "http_status": status,
        "latency_ms": latency_ms,
        "content": content,
        "served_model": served_model,
        "identity_ok": identity_ok,
        "provider_execution": identity_ok,
        "chosen_action": chosen,
        "legal_action": legal,
        "error": error,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


def action_descriptors(env: Any) -> list[dict[str, Any]]:
    rows = []
    for a in env.action_space:
        rows.append({"id": int(a.value), "name": str(getattr(a, "name", a))})
    return sorted(rows, key=lambda x: x["id"])


def observe_after_probe(arcade: Any, game_id: str, probe_action: int) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        raise RuntimeError(f"could not create {game_id}")
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        raise RuntimeError(f"probe action {probe_action} unavailable in {game_id}: {sorted(amap)}")
    obs = env.step(amap[probe_action])
    frames = frame_list(obs)
    if not frames:
        raise RuntimeError(f"no frame data for {game_id}")
    return {
        "final_frame": plain(frames[-1]),
        "signature": encode_animation(frames),
        "frame_count": len(frames),
        "actions": action_descriptors(env),
        "levels_completed": int(getattr(obs, "levels_completed", 0) or 0),
        "state": str(getattr(getattr(obs, "state", None), "value", getattr(obs, "state", ""))),
    }


def prompt_for(game_id: str, observed: dict[str, Any], arm: str) -> str:
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": observed["levels_completed"],
        "state": observed["state"],
        "legal_actions": observed["actions"],
        "exact_current_final_frame": observed["final_frame"],
    }
    if arm == "final_plus_animation" and observed["signature"] is not None:
        payload["animation_metadata"] = observed["signature"]
        payload["animation_note"] = (
            "Lossy metadata about transient frames from the immediately preceding fixed probe action; "
            "the exact current board remains exact_current_final_frame."
        )
    return compact_json(payload)


def execute_choice(arcade: Any, game_id: str, probe_action: int, choice: int) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        raise RuntimeError(f"could not recreate {game_id}")
    amap = {int(a.value): a for a in env.action_space}
    before = env.step(amap[probe_action])
    before_frames = frame_list(before)
    before_final = plain(before_frames[-1]) if before_frames else None
    before_levels = int(getattr(before, "levels_completed", 0) or 0)
    after = env.step(amap[choice])
    after_frames = frame_list(after)
    after_final = plain(after_frames[-1]) if after_frames else None
    after_levels = int(getattr(after, "levels_completed", 0) or 0)
    state = str(getattr(getattr(after, "state", None), "value", getattr(after, "state", "")))
    return {
        "level_delta": after_levels - before_levels,
        "levels_completed_after": after_levels,
        "state_after": state,
        "game_over": state.upper() in {"GAME_OVER", "LOST", "FAILED"},
        "board_changed_cells": changed_cells(before_final, after_final) if before_final is not None and after_final is not None else None,
        "post_action_frame_count": len(after_frames),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-animation-action-ab.json"))
    args = ap.parse_args()

    arcade = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)
    rows: list[dict[str, Any]] = []
    observations: dict[str, Any] = {}
    for game_id, probe_action in TARGETS:
        observed = observe_after_probe(arcade, game_id, probe_action)
        observations[game_id] = {
            "probe_action": probe_action,
            "frame_count": observed["frame_count"],
            "has_animation_signature": observed["signature"] is not None,
            "legal_actions": observed["actions"],
        }
        legal_ids = [int(x["id"]) for x in observed["actions"]]
        for arm in ARMS:
            prompt = prompt_for(game_id, observed, arm)
            call = provider_action_call(prompt, legal_ids)
            execution = None
            if call["provider_execution"] and call["legal_action"]:
                execution = execute_choice(arcade, game_id, probe_action, int(call["chosen_action"]))
            rows.append({
                "game_id": game_id,
                "probe_action": probe_action,
                "arm": arm,
                "prompt_chars": len(prompt),
                **call,
                "execution": execution,
            })

    all_identity = bool(rows) and all(bool(r["identity_ok"]) for r in rows)
    all_legal = bool(rows) and all(bool(r["legal_action"]) for r in rows)
    all_executed = bool(rows) and all(r["execution"] is not None for r in rows)

    def arm_summary(arm: str) -> dict[str, Any]:
        rr = [r for r in rows if r["arm"] == arm]
        executed = [r for r in rr if r["execution"] is not None]
        return {
            "calls": len(rr),
            "provider_executed": sum(bool(r["provider_execution"]) for r in rr),
            "legal_choices": sum(bool(r["legal_action"]) for r in rr),
            "action_executions": len(executed),
            "level_delta_total": sum(int(r["execution"]["level_delta"]) for r in executed),
            "game_over_count": sum(bool(r["execution"]["game_over"]) for r in executed),
            "nonzero_board_change_count": sum((r["execution"]["board_changed_cells"] or 0) > 0 for r in executed),
            "prompt_chars_total": sum(int(r["prompt_chars"]) for r in rr),
            "mean_latency_ms": round(sum(int(r["latency_ms"]) for r in rr) / len(rr), 1) if rr else None,
        }

    base = arm_summary("final_only")
    aug = arm_summary("final_plus_animation")
    action_differences = sum(
        1
        for game_id, _ in TARGETS
        if next(r["chosen_action"] for r in rows if r["game_id"] == game_id and r["arm"] == "final_only")
        != next(r["chosen_action"] for r in rows if r["game_id"] == game_id and r["arm"] == "final_plus_animation")
    )

    if not all_identity:
        gate = "INCONCLUSIVE_PROVIDER_IDENTITY_MISMATCH"
    elif not all_legal or not all_executed:
        gate = "INCONCLUSIVE_INVALID_OR_UNEXECUTED_ACTION"
    elif aug["level_delta_total"] > base["level_delta_total"] and aug["game_over_count"] <= base["game_over_count"]:
        gate = "PROMOTE_ANIMATION_SOLVER_BEHAVIOR_LEVEL_GAIN"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-public-animation-action-ab/1",
        "toolkit": "arc-agi==0.9.9",
        "requested_model": ident.MODEL,
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "observations": observations,
        "rows": rows,
        "summary": {
            "final_only": base,
            "final_plus_animation": aug,
            "games_with_different_chosen_action": action_differences,
            "all_calls_exact_model_identity": all_identity,
            "all_choices_legal": all_legal,
            "all_chosen_actions_executed": all_executed,
        },
        "promotion_gate": gate,
        "truth": {
            "public_development_environment_only": True,
            "fixed_probe_actions": True,
            "exact_final_frame_identical_between_arms": True,
            "animation_metadata_additive_only": True,
            "promotion_requires_immediate_level_gain": True,
            "board_motion_alone_cannot_promote": True,
            "provider_model_identity_verified": all_identity,
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
    print(json.dumps({"summary": receipt["summary"], "promotion_gate": gate, "truth": receipt["truth"]}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
