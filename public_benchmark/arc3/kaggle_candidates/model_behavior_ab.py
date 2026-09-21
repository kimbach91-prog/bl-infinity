#!/usr/bin/env python3
"""Bounded same-model A/B test: raw grid text vs clean-room object graph.

Scope: public/synthetic ARC-like fixtures only. No hidden Kaggle data, no competition
submission, no leaderboard readback, and no prize/score claim.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import object_graph_representation as ogr

ENDPOINT = "https://blockrun.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-lightning"
TIMEOUT_S = 45


def blank(h=64, w=64):
    return [[0 for _ in range(w)] for _ in range(h)]


def rect(g, r0, c0, h, w, color):
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            g[r][c] = color


def lshape(g, r0, c0, color):
    for r, c in [(r0, c0), (r0 + 1, c0), (r0 + 1, c0 + 1)]:
        g[r][c] = color


def fixtures():
    out = []

    g = blank()
    lshape(g, 2, 2, 2)
    rect(g, 12, 30, 3, 4, 7)
    g[50][50] = 4
    out.append(("count_objects", g, "How many non-background connected objects are present?", ["1","2","3","4"], "3"))

    g = blank()
    rect(g, 4, 4, 2, 3, 5)
    rect(g, 28, 35, 5, 6, 9)
    g[60][2] = 3
    out.append(("largest_color", g, "Which color belongs to the largest non-background object by area?", ["3","5","9"], "9"))

    g = blank()
    rect(g, 10, 10, 3, 3, 8)
    g[5][50] = 6
    rect(g, 40, 45, 2, 2, 2)
    out.append(("topmost_color", g, "Which object's color has the smallest top row coordinate?", ["2","6","8"], "6"))

    g = blank()
    rect(g, 20, 3, 2, 4, 11)
    rect(g, 20, 40, 2, 4, 12)
    g[55][30] = 1
    out.append(("leftmost_color", g, "Which color belongs to the leftmost non-background object?", ["1","11","12"], "11"))

    g = blank()
    lshape(g, 3, 4, 2)
    lshape(g, 40, 45, 7)
    rect(g, 18, 28, 2, 2, 5)
    out.append(("repeated_shape_count", g, "How many objects have a geometric shape that is shared by at least one other object?", ["0","1","2","3"], "2"))

    g = blank()
    rect(g, 8, 8, 2, 2, 4)
    rect(g, 8, 48, 2, 2, 9)
    rect(g, 45, 28, 2, 2, 6)
    out.append(("rightmost_color", g, "Which color belongs to the rightmost non-background object?", ["4","6","9"], "9"))

    g = blank()
    rect(g, 3, 3, 4, 4, 10)
    rect(g, 30, 30, 3, 3, 2)
    g[62][62] = 13
    out.append(("smallest_color", g, "Which color belongs to the smallest object by area?", ["2","10","13"], "13"))

    g = blank()
    lshape(g, 5, 5, 3)
    lshape(g, 50, 10, 3)
    rect(g, 30, 50, 1, 5, 8)
    out.append(("same_shape_yesno", g, "Do the two color-3 objects have the same geometric shape?", ["YES","NO"], "YES"))

    return out


def representation(grid, arm):
    if arm == "raw_ascii":
        return ogr.raw_ascii(grid)
    if arm == "object_graph":
        return ogr.compact_json(grid)
    raise ValueError(arm)


def normalize_choice(text, choices):
    up = text.strip().upper().strip("'\" .,:;![](){}")
    if up in choices:
        return up, True
    hits = [c for c in choices if re.search(rf"(?<![A-Z0-9_]){re.escape(c)}(?![A-Z0-9_])", up)]
    if len(set(hits)) == 1:
        return hits[0], False
    return "", False


def call_model(prompt):
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You solve a bounded visual-state question. Use only the supplied representation. Reply with exactly one allowed choice token and nothing else."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 24,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    status = 0
    body = b""
    error = None
    parsed = None
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        error = f"HTTPError:{exc.code}"
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
    latency_ms = int((time.monotonic() - started) * 1000)
    content = ""
    if body:
        try:
            parsed = json.loads(body)
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = body.decode("utf-8", "replace")[:2000]
    return {
        "http_status": status,
        "latency_ms": latency_ms,
        "content": content,
        "error": error,
        "provider_execution": status == 200,
        "response_schema_ok": isinstance(parsed, dict) and isinstance(parsed.get("choices"), list) if isinstance(parsed, dict) else False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", default="arc3-object-graph-model-behavior-ab.json")
    args = ap.parse_args()

    canary = call_model("Public S0 canary. Allowed choices: DEUS_ARC3_AB_CANARY_OK. Reply exactly: DEUS_ARC3_AB_CANARY_OK")
    canary_choice, canary_exact = normalize_choice(canary["content"], ["DEUS_ARC3_AB_CANARY_OK"])
    rows = []

    if canary_choice == "DEUS_ARC3_AB_CANARY_OK" and canary["provider_execution"]:
        for i, (fid, grid, question, choices, expected) in enumerate(fixtures()):
            arms = ["raw_ascii", "object_graph"] if i % 2 == 0 else ["object_graph", "raw_ascii"]
            for arm in arms:
                rep = representation(grid, arm)
                prompt = (
                    f"Representation type: {arm}\n"
                    f"Allowed choices: {', '.join(choices)}\n"
                    f"Question: {question}\n"
                    f"State representation:\n{rep}\n"
                    "Reply with exactly one allowed choice token."
                )
                res = call_model(prompt)
                selected, exact_format = normalize_choice(res["content"], choices)
                rows.append({
                    "fixture": fid,
                    "arm": arm,
                    "expected": expected,
                    "selected": selected,
                    "correct": selected == expected,
                    "exact_format": exact_format,
                    "prompt_chars": len(prompt),
                    "representation_chars": len(rep),
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "response_schema_ok": res["response_schema_ok"],
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                    "raw_response_excerpt": res["content"][:300],
                })

    def summarize(arm):
        arm_rows = [r for r in rows if r["arm"] == arm]
        lat = [r["latency_ms"] for r in arm_rows if r["provider_execution"]]
        return {
            "calls": len(arm_rows),
            "executed": sum(r["provider_execution"] for r in arm_rows),
            "failures": sum(not r["provider_execution"] for r in arm_rows),
            "correct": sum(r["correct"] for r in arm_rows),
            "accuracy": (sum(r["correct"] for r in arm_rows) / len(arm_rows)) if arm_rows else None,
            "exact_format_rate": (sum(r["exact_format"] for r in arm_rows) / len(arm_rows)) if arm_rows else None,
            "prompt_chars_total": sum(r["prompt_chars"] for r in arm_rows),
            "representation_chars_total": sum(r["representation_chars"] for r in arm_rows),
            "mean_latency_ms": round(statistics.mean(lat), 1) if lat else None,
            "median_latency_ms": round(statistics.median(lat), 1) if lat else None,
        }

    raw = summarize("raw_ascii")
    graph = summarize("object_graph")
    if not (canary_choice == "DEUS_ARC3_AB_CANARY_OK" and canary["provider_execution"]):
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or graph["failures"] or raw["calls"] != len(fixtures()) or graph["calls"] != len(fixtures()):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif graph["correct"] > raw["correct"]:
        gate = "PROMOTE_MODEL_BEHAVIOR_ACCURACY_GAIN"
    elif graph["correct"] == raw["correct"] and raw["prompt_chars_total"] and graph["prompt_chars_total"] <= 0.35 * raw["prompt_chars_total"] and graph["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]:
        gate = "PROMOTE_NONDOMINATED_EQUAL_ACCURACY_EFFICIENCY_GAIN"
    else:
        gate = "NO_PROMOTION"

    receipt = {
        "schema": "deus-arc3-object-graph-model-behavior-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "data_class": "BL-S0_PUBLIC_SYNTHETIC",
        "fixtures": len(fixtures()),
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_ascii": raw, "object_graph": graph},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_fixtures": True,
            "same_output_contract": True,
            "accuracy_gain_promotes": True,
            "equal_accuracy_efficiency_gate": "object_graph prompt chars <=35% raw and mean latency <=135% raw",
            "provider_failure": "INCONCLUSIVE",
            "cross_model_fallback_for_superiority_claim": False,
        },
        "rows": rows,
        "truth": {
            "synthetic_public_only": True,
            "hidden_kaggle_data_read": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
            "prize_or_award_claim": False,
            "provider_execution_is_not_kaggle_execution": True,
        },
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if gate not in ("INCONCLUSIVE_PROVIDER_CANARY_FAIL", "INCONCLUSIVE_PROVIDER_FAILURE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
