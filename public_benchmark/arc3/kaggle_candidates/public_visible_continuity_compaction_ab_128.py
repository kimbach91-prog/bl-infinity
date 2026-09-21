#!/usr/bin/env python3
"""Rung 128: target-blind visible self-note continuity/compaction A/B.

Motivation is architecture-level only: fresh official ARC Prize reporting on Astra shows a
large harness effect when provider state is preserved and long context is compacted. The
current public route does not expose opaque provider reasoning-state continuity, so this
clean-room rung tests only a portable analogue: a short model-authored *visible* self-note
fed into the next request.

Both arms use the same exact served model, fixed public games/probes, action budget, current
visible observation, and response contract. Both arms ask the model to generate the note.
The baseline discards it; the treatment carries only the previous note, capped to a fixed
character budget. No public solution trace is supplied to the model. Promotion requires
solver-behavior gain; prompt/latency/token efficiency alone can never promote.
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
from arcengine import GameAction

import adaptive_lossless_behavior_ab_v3_identity as ident

TARGETS = (("sp80", 5), ("bp35", 3), ("wa30", 1))
ARMS = ("discard_self_note", "carry_compacted_self_note")
STEP_BUDGET = 3
NOTE_CHAR_BUDGET = 240


def plain(x: Any) -> Any:
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, tuple):
        return [plain(v) for v in x]
    if isinstance(x, list):
        return [plain(v) for v in x]
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    return x


def compact_json(x: Any) -> str:
    return json.dumps(x, separators=(",", ":"), ensure_ascii=False)


def obs_levels(obs: Any) -> int:
    return int(getattr(obs, "levels_completed", 0) or 0)


def obs_state(obs: Any) -> str:
    raw = getattr(obs, "state", "")
    return str(getattr(raw, "value", raw))


def frame_list(obs: Any) -> list[Any]:
    raw = getattr(obs, "frame", None)
    if raw is None:
        return []
    # ARC observations can expose a single 64x64 frame or a stack/animation.
    shape = getattr(raw, "shape", None)
    if shape is not None and len(shape) == 3:
        return [plain(raw[i]) for i in range(shape[0])]
    v = plain(raw)
    if isinstance(v, list) and v and isinstance(v[0], list) and v[0] and isinstance(v[0][0], list):
        return v
    return [v]


def observed_frame(obs: Any) -> Any | None:
    fs = frame_list(obs)
    return fs[-1] if fs else None


def action_descriptors(env: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in env.action_space:
        aid = int(a.value)
        row: dict[str, Any] = {"id": aid, "name": str(getattr(a, "name", a))}
        if aid == 6:
            row["params"] = {"x": "integer 0..63", "y": "integer 0..63"}
        rows.append(row)
    return sorted(rows, key=lambda r: r["id"])


def execute(env: Any, amap: dict[int, Any], choice: dict[str, Any]) -> Any:
    aid = int(choice["action"])
    if aid not in amap:
        raise ValueError(f"action unavailable: {aid}")
    if aid == 6:
        return env.step(amap[aid], {"x": int(choice["x"]), "y": int(choice["y"])})
    return env.step(amap[aid])


def parse_choice(content: str, legal_ids: set[int]) -> tuple[dict[str, Any] | None, str | None]:
    text = (content or "").strip()
    obj: Any = None
    try:
        obj = json.loads(text)
    except Exception:
        # Accept one fenced JSON object, but never infer an action from prose.
        m = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S | re.I)
        if m:
            try:
                obj = json.loads(m.group(1))
            except Exception:
                obj = None
    if not isinstance(obj, dict):
        return None, "MALFORMED_JSON"
    if set(obj) - {"action", "x", "y", "note"}:
        return None, "UNEXPECTED_FIELDS"
    try:
        aid = int(obj["action"])
    except Exception:
        return None, "ACTION_MISSING_OR_NONINTEGER"
    if aid not in legal_ids:
        return None, f"ILLEGAL_ACTION:{aid}"
    note = obj.get("note")
    if not isinstance(note, str):
        return None, "NOTE_MISSING_OR_NONSTRING"
    note = " ".join(note.split())[:NOTE_CHAR_BUDGET]
    out: dict[str, Any] = {"action": aid, "note": note}
    if aid == 6:
        try:
            x, y = int(obj["x"]), int(obj["y"])
        except Exception:
            return None, "ACTION6_COORDS_MISSING"
        if not (0 <= x <= 63 and 0 <= y <= 63):
            return None, "ACTION6_COORDS_OUT_OF_RANGE"
        out.update({"x": x, "y": y})
    return out, None


def provider_call(prompt: str, legal_ids: set[int]) -> dict[str, Any]:
    payload = json.dumps({
        "model": ident.MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are choosing one legal action in a public grid-world. Use only the supplied visible "
                    "observation, legal action list, and optional previous self-note. Prefer progress/completion. "
                    "Return exactly one JSON object and no prose: "
                    "{\"action\":INTEGER,\"note\":\"<=240 chars useful state/rule/plan memory\"}. "
                    "If action 6 is chosen, also include integer x and y in 0..63. The note must summarize only "
                    "your current inference and next-useful memory; never claim hidden state."
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
    parsed: Any = None
    served_model = None
    content = ""
    if body:
        try:
            parsed = json.loads(body)
            served_model = parsed.get("model") if isinstance(parsed, dict) else None
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = body.decode("utf-8", "replace")[:2000]
    identity_ok = bool(status == 200 and served_model == ident.MODEL)
    choice, parse_error = parse_choice(content, legal_ids) if identity_ok else (None, None)
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
        "raw_content": content[:1000],
    }


def initial_probe(env: Any, probe_action: int) -> Any:
    amap = {int(a.value): a for a in env.action_space}
    if probe_action not in amap:
        raise ValueError(f"probe unavailable {probe_action}")
    return env.step(amap[probe_action])


def prompt_for(game_id: str, env: Any, obs: Any, current: Any, previous_note: str | None) -> str:
    payload: dict[str, Any] = {
        "game_id": game_id,
        "current_level_progress": obs_levels(obs),
        "state": obs_state(obs),
        "legal_actions": action_descriptors(env),
        "exact_current_visible_frame": current,
        "instruction": "Choose the next legal action; write a compact self-note useful on the next step.",
    }
    if previous_note is not None:
        payload["previous_self_note"] = previous_note
        payload["continuity_note"] = (
            "This is only your own prior visible self-note. Treat it as fallible working memory and revise it "
            "against the exact current observation; it is not privileged state."
        )
    return compact_json(payload)


def run_arm(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
    env = arcade.make(game_id, save_recording=False, include_frame_data=True)
    if env is None:
        return {"inconclusive": f"MAKE_FAILED:{game_id}", "rows": []}
    try:
        obs = initial_probe(env, probe_action)
    except Exception as exc:
        return {"inconclusive": f"PROBE_FAILED:{type(exc).__name__}:{exc}", "rows": []}
    current = observed_frame(obs)
    if current is None:
        return {"inconclusive": f"NO_INITIAL_FRAME:{game_id}", "rows": []}
    start_levels = obs_levels(obs)
    previous_note: str | None = None
    rows: list[dict[str, Any]] = []
    terminal = False
    for step in range(1, STEP_BUDGET + 1):
        legal_ids = {int(a.value) for a in env.action_space}
        note_in = previous_note if arm == "carry_compacted_self_note" else None
        prompt = prompt_for(game_id, env, obs, current, note_in)
        call = provider_call(prompt, legal_ids)
        row: dict[str, Any] = {
            "step": step,
            "arm": arm,
            "prompt_chars": len(prompt),
            "note_in_chars": len(note_in or ""),
            **call,
        }
        choice = call.get("choice")
        if not call["identity_ok"] or choice is None:
            row["execution"] = None
            rows.append(row)
            return {
                "inconclusive": f"CALL_OR_RESPONSE_INVALID:{game_id}:{arm}:step{step}:{call.get('error')}",
                "rows": rows,
                "start_levels": start_levels,
            }
        amap = {int(a.value): a for a in env.action_space}
        try:
            next_obs = execute(env, amap, choice)
        except Exception as exc:
            row["execution"] = None
            row["execution_error"] = f"{type(exc).__name__}:{exc}"
            rows.append(row)
            return {
                "inconclusive": f"ACTION_EXECUTION_FAILED:{game_id}:{arm}:step{step}",
                "rows": rows,
                "start_levels": start_levels,
            }
        fresh = observed_frame(next_obs)
        if fresh is not None:
            current = fresh
        gain = obs_levels(next_obs) - start_levels
        state = obs_state(next_obs)
        terminal = state.upper() in {"GAME_OVER", "LOST", "FAILED"}
        previous_note = str(choice["note"])[:NOTE_CHAR_BUDGET]
        row["note_out_chars"] = len(previous_note)
        row["execution"] = {
            "levels_completed": obs_levels(next_obs),
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
        "final_levels": obs_levels(obs),
        "level_gain": obs_levels(obs) - start_levels,
        "terminal_failure": terminal,
        "policy_actions": len(rows),
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
        "identity_verified_calls": sum(bool(x.get("identity_ok")) for x in calls),
        "prompt_chars_total": sum(int(x.get("prompt_chars", 0)) for x in calls),
        "mean_latency_ms": round(sum(int(x.get("latency_ms", 0)) for x in calls) / max(1, len(calls)), 1),
        "note_in_chars_total": sum(int(x.get("note_in_chars", 0)) for x in calls),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-visible-continuity-compaction-ab-128.json"))
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
    base = summarize(results, "discard_self_note")
    aug = summarize(results, "carry_compacted_self_note")
    if inconclusive:
        gate = "INCONCLUSIVE_EXECUTION"
    elif aug["level_gain_total"] > base["level_gain_total"] and aug["terminal_failures"] <= base["terminal_failures"]:
        gate = "PROMOTE_VISIBLE_CONTINUITY_SOLVER_BEHAVIOR_GAIN"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-visible-continuity-compaction-ab/1",
        "rung": 128,
        "change_kind": "VISIBLE_SELF_NOTE_CONTINUITY_COMPACTION_AB_NOT_OPAQUE_PROVIDER_STATE",
        "source_grounding": {
            "official_arc_prize_astra_report_date": "2026-09-03",
            "principle": "provider state continuity and compaction can materially affect ARC-AGI-3 harness performance",
            "clean_room_implementation": True,
            "opaque_provider_reasoning_state_available_on_this_route": False,
            "opaque_provider_state_reproduction_claim": False,
            "portable_visible_self_note_analogue_only": True,
        },
        "toolkit": "arc-agi==0.9.9",
        "requested_model": ident.MODEL,
        "targets": [{"game_id": g, "probe_action": a} for g, a in TARGETS],
        "step_budget_per_arm": STEP_BUDGET,
        "note_char_budget": NOTE_CHAR_BUDGET,
        "results": results,
        "summary": {"discard_self_note": base, "carry_compacted_self_note": aug},
        "inconclusive": inconclusive,
        "promotion_gate": gate,
        "truth": {
            "public_development_environment_only": True,
            "same_served_model_contract": True,
            "same_targets_probe_and_policy_budget": True,
            "same_response_contract_both_arms": True,
            "both_arms_generate_self_note": True,
            "baseline_discards_self_note": True,
            "treatment_carries_only_previous_bounded_self_note": True,
            "visible_self_note_is_fallible_working_memory_not_hidden_state": True,
            "provider_call_retries": False,
            "public_solution_trace_supplied_to_model": False,
            "game_source_read": False,
            "hidden_state_read": False,
            "target_blind": True,
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
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"promotion_gate": gate, "summary": receipt["summary"], "inconclusive": inconclusive}, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
