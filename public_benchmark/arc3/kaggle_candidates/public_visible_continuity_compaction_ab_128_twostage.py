#!/usr/bin/env python3
"""Rung 128 representation repair: split click selection from coordinate decoding.

The first execution exposed a representation failure, not a solver verdict: the model chose
ACTION6 on both sp80 arms but omitted x/y. This wrapper does not retry those calls. It changes
the action representation prospectively to a two-stage protocol: policy chooses action+note;
only if ACTION6 is chosen, a separate exact-model call chooses coordinates. The same protocol
is used for both A/B arms and neither provider call is retried.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import public_visible_continuity_compaction_ab_128 as b


def parse_policy_choice(content: str, legal_ids: set[int]) -> tuple[dict[str, Any] | None, str | None]:
    text = (content or "").strip()
    obj: Any = None
    try:
        obj = json.loads(text)
    except Exception:
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
    out: dict[str, Any] = {"action": aid, "note": " ".join(note.split())[: b.NOTE_CHAR_BUDGET]}
    # Coordinates supplied in stage one are accepted only if valid, but never required.
    if aid == 6:
        try:
            x, y = int(obj.get("x")), int(obj.get("y"))
            if 0 <= x <= 63 and 0 <= y <= 63:
                out.update({"x": x, "y": y})
        except Exception:
            pass
    return out, None


def parse_coords(content: str) -> tuple[dict[str, int] | None, str | None]:
    text = (content or "").strip()
    obj: Any = None
    try:
        obj = json.loads(text)
    except Exception:
        m = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S | re.I)
        if m:
            try:
                obj = json.loads(m.group(1))
            except Exception:
                obj = None
    if not isinstance(obj, dict) or set(obj) != {"x", "y"}:
        return None, "COORD_JSON_SCHEMA_INVALID"
    try:
        x, y = int(obj["x"]), int(obj["y"])
    except Exception:
        return None, "COORD_NONINTEGER"
    if not (0 <= x <= 63 and 0 <= y <= 63):
        return None, "COORD_OUT_OF_RANGE"
    return {"x": x, "y": y}, None


def coordinate_call(game_id: str, current: Any, policy_note: str) -> dict[str, Any]:
    prompt = b.compact_json({
        "game_id": game_id,
        "chosen_action": 6,
        "exact_current_visible_frame": current,
        "current_self_note": policy_note,
        "instruction": "Choose the single visible-grid click coordinate for ACTION6. Coordinates are x=column,y=row, each 0..63.",
    })
    payload = json.dumps({
        "model": b.ident.MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Decode coordinates for an already-selected click action in a public grid-world. "
                    "Use only the supplied visible frame and self-note. Return exactly JSON {\"x\":INTEGER,\"y\":INTEGER} "
                    "with each coordinate 0..63. No prose."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 32,
    }).encode("utf-8")
    req = urllib.request.Request(
        b.ident.v2.impl.seg.base.ENDPOINT,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    status = 0
    body = b""
    err = None
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=b.ident.v2.impl.seg.base.TIMEOUT_S) as resp:
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
    identity_ok = bool(status == 200 and served_model == b.ident.MODEL)
    coords, parse_error = parse_coords(content) if identity_ok else (None, None)
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
        "coords": coords,
        "parse_error": parse_error,
        "error": err,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_content": content[:500],
    }


def run_arm_twostage(arcade: Any, game_id: str, probe_action: int, arm: str) -> dict[str, Any]:
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
    previous_note: str | None = None
    rows: list[dict[str, Any]] = []
    terminal = False
    for step in range(1, b.STEP_BUDGET + 1):
        legal_ids = {int(a.value) for a in env.action_space}
        note_in = previous_note if arm == "carry_compacted_self_note" else None
        prompt = b.prompt_for(game_id, env, obs, current, note_in)
        call = b.provider_call(prompt, legal_ids)
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
                "inconclusive": f"POLICY_CALL_INVALID:{game_id}:{arm}:step{step}:{call.get('error')}",
                "rows": rows,
                "start_levels": start_levels,
            }
        if int(choice["action"]) == 6 and not {"x", "y"}.issubset(choice):
            coord = coordinate_call(game_id, current, str(choice["note"]))
            row["coordinate_call"] = coord
            if not coord["identity_ok"] or coord["coords"] is None:
                row["execution"] = None
                rows.append(row)
                return {
                    "inconclusive": f"COORD_CALL_INVALID:{game_id}:{arm}:step{step}:{coord.get('error')}",
                    "rows": rows,
                    "start_levels": start_levels,
                }
            choice = {**choice, **coord["coords"]}
            row["choice"] = choice
        else:
            row["coordinate_call"] = None
        amap = {int(a.value): a for a in env.action_space}
        try:
            next_obs = b.execute(env, amap, choice)
        except Exception as exc:
            row["execution"] = None
            row["execution_error"] = f"{type(exc).__name__}:{exc}"
            rows.append(row)
            return {
                "inconclusive": f"ACTION_EXECUTION_FAILED:{game_id}:{arm}:step{step}",
                "rows": rows,
                "start_levels": start_levels,
            }
        fresh = b.observed_frame(next_obs)
        if fresh is not None:
            current = fresh
        gain = b.obs_levels(next_obs) - start_levels
        state = b.obs_state(next_obs)
        terminal = state.upper() in {"GAME_OVER", "LOST", "FAILED"}
        previous_note = str(choice["note"])[: b.NOTE_CHAR_BUDGET]
        row["note_out_chars"] = len(previous_note)
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


def receipt_path() -> Path:
    for i, arg in enumerate(sys.argv):
        if arg == "--receipt" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
        if arg.startswith("--receipt="):
            return Path(arg.split("=", 1)[1])
    return Path("public-visible-continuity-compaction-ab-128.json")


def main() -> int:
    # Prospective representation repair. No calls from the failed first attempt are replayed.
    b.parse_choice = parse_policy_choice
    b.run_arm = run_arm_twostage
    rc = b.main()
    path = receipt_path()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        coord_calls = [
            row.get("coordinate_call")
            for result in data.get("results", [])
            for row in result.get("result", {}).get("rows", [])
            if row.get("coordinate_call") is not None
        ]
        data["representation_repair"] = {
            "trigger_from_prior_run": "ACTION6_COORDS_MISSING_ON_BOTH_SP80_ARMS",
            "prior_run_id": 35636800270,
            "repair": "TWO_STAGE_ACTION_THEN_COORDINATE_DECODING",
            "blind_retry_of_failed_policy_calls": False,
            "same_protocol_both_arms": True,
            "coordinate_calls": len(coord_calls),
            "coordinate_calls_identity_verified": sum(bool(c.get("identity_ok")) for c in coord_calls),
            "coordinate_provider_retries": False,
        }
        data.setdefault("truth", {}).update({
            "failed_branch_repaired_by_representation_change_not_blind_retry": True,
            "click_action_representation_two_stage": True,
            "coordinate_provider_retries": False,
        })
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
