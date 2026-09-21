#!/usr/bin/env python3
"""Fixed-budget same-model A/B for the history2 temporal ARC3 representation.

This is a public source-assisted episodic-memory test. It is NOT independent
generalization, a Kaggle execution, or a hidden-score estimate. Cases are drawn
only from pinned public traces after the temporal representation passes the
representation-granularity guard.

For every case, target and query share the exact history2_visual_action key but
have distinct raw_board_action keys. A same-current-action distractor is used so
an action-name-only shortcut is insufficient. Both arms use the same cases,
labels, model, endpoint, temperature, call budget, and alternating arm order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / "harness"
sys.path.insert(0, str(HARNESS))
import public_trace_temporal_state_audit as tsa

ENDPOINT = "https://blockrun.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-lightning"
TIMEOUT_S = 45
TOKENS = ("ALPHA", "BETA")
ARMS = ("raw_board_action", "history2_visual_action")


def stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(stable(value).encode("utf-8")).hexdigest()


def normalize_choice(text: str) -> tuple[str, bool]:
    up = text.strip().upper().strip("'\" .,:;![](){}")
    if up in TOKENS:
        return up, True
    hits = [tok for tok in TOKENS if tok in up.split()]
    if len(set(hits)) == 1:
        return hits[0], False
    return "", False


def call_model(prompt: str) -> dict[str, Any]:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You perform deterministic episodic state/action memory retrieval. "
                    "The query comes from one of two underlying public memories. Match "
                    "persistent temporal/visual state and intended action, not future outcome. "
                    "Reply with exactly ALPHA or BETA and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 12,
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
    parsed: Any = None
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
        "response_schema_ok": isinstance(parsed, dict) and isinstance(parsed.get("choices"), list),
    }


def load_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    trace_stats: list[dict[str, Any]] = []
    for path in paths:
        trace_rows = tsa.trace_rows(tsa.load_events(path))
        trace_stats.append({"path": path.name, "audited_transitions": len(trace_rows)})
        for idx, row in enumerate(trace_rows):
            rows.append({"trace": path.name, "trace_index": idx, **row})
    return rows, trace_stats


def current_action(row: dict[str, Any]) -> str:
    return str(row["representations"]["history2_visual_action"].get("action") or "")


def build_cases(rows: list[dict[str, Any]], max_cases: int) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[stable(row["representations"]["history2_visual_action"])].append(row)

    eligible: list[tuple[str, list[dict[str, Any]]]] = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        outcomes = {stable(r["outcome"]) for r in group}
        raw_keys = {stable(r["representations"]["raw_board_action"]) for r in group}
        if len(outcomes) == 1 and len(raw_keys) >= 2:
            eligible.append((key, group))
    eligible.sort(key=lambda kv: hashlib.sha256(kv[0].encode("utf-8")).hexdigest())

    cases: list[dict[str, Any]] = []
    for key, group in eligible:
        target = group[0]
        target_raw = stable(target["representations"]["raw_board_action"])
        query = next(
            (r for r in group[1:] if stable(r["representations"]["raw_board_action"]) != target_raw),
            None,
        )
        if query is None:
            continue
        action = current_action(target)
        distractor = None
        for other_key, other_group in eligible:
            if other_key == key:
                continue
            candidate = other_group[0]
            if current_action(candidate) == action:
                distractor = candidate
                break
        if distractor is None:
            continue

        idx = len(cases)
        target_token = TOKENS[idx % 2]
        cases.append({
            "case": idx,
            "target_token": target_token,
            "distractor_token": TOKENS[(idx + 1) % 2],
            "target": target,
            "distractor": distractor,
            "query": query,
            "history_key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "target_outcome_sha256": digest(target["outcome"]),
            "action": action,
        })
        if len(cases) >= max_cases:
            break
    return cases


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    target = stable(case["target"]["representations"][arm])
    distractor = stable(case["distractor"]["representations"][arm])
    query = stable(case["query"]["representations"][arm])
    if case["target_token"] == "ALPHA":
        alpha, beta = target, distractor
    else:
        alpha, beta = distractor, target
    prompt = (
        f"Representation arm: {arm}\n"
        "Memory ALPHA:\n" + alpha + "\n"
        "Memory BETA:\n" + beta + "\n"
        "Query:\n" + query + "\n"
        "Which memory token matches the query's underlying persistent state/action? "
        "Allowed choices: ALPHA, BETA. Reply exactly one token."
    )
    return prompt, len(target) + len(distractor) + len(query)


def summarize(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    vals = [r for r in rows if r["arm"] == arm]
    lats = [r["latency_ms"] for r in vals if r["provider_execution"]]
    return {
        "calls": len(vals),
        "executed": sum(bool(r["provider_execution"]) for r in vals),
        "failures": sum(not bool(r["provider_execution"]) for r in vals),
        "correct": sum(bool(r["correct"]) for r in vals),
        "accuracy": round(sum(bool(r["correct"]) for r in vals) / len(vals), 6) if vals else None,
        "exact_format_rate": round(sum(bool(r["exact_format"]) for r in vals) / len(vals), 6) if vals else None,
        "prompt_chars_total": sum(int(r["prompt_chars"]) for r in vals),
        "representation_chars_total": sum(int(r["representation_chars"]) for r in vals),
        "mean_latency_ms": round(statistics.mean(lats), 1) if lats else None,
        "median_latency_ms": round(statistics.median(lats), 1) if lats else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--receipt", type=Path, default=Path("temporal-state-model-behavior-ab.json"))
    ap.add_argument("--max-cases", type=int, default=8)
    args = ap.parse_args()

    rows, trace_stats = load_rows(args.input)
    cases = build_cases(rows, args.max_cases)
    selection_ok = len(cases) >= 4

    canary = call_model(
        "Public S0 canary. The correct allowed choice is ALPHA. Allowed choices: ALPHA, BETA. Reply exactly ALPHA."
    )
    canary_choice, canary_exact = normalize_choice(canary["content"])
    canary_ok = canary["provider_execution"] and canary_choice == "ALPHA"

    call_rows: list[dict[str, Any]] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(cases):
            arms = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, rep_chars = prompt_for(case, arm)
                res = call_model(prompt)
                selected, exact = normalize_choice(res["content"])
                call_rows.append({
                    "case": case["case"],
                    "arm": arm,
                    "expected": case["target_token"],
                    "selected": selected,
                    "correct": selected == case["target_token"],
                    "exact_format": exact,
                    "action": case["action"],
                    "history_key_sha256": case["history_key_sha256"],
                    "target_outcome_sha256": case["target_outcome_sha256"],
                    "prompt_chars": len(prompt),
                    "representation_chars": rep_chars,
                    "http_status": res["http_status"],
                    "provider_execution": res["provider_execution"],
                    "response_schema_ok": res["response_schema_ok"],
                    "latency_ms": res["latency_ms"],
                    "error": res["error"],
                    "raw_response_excerpt": res["content"][:160],
                })

    raw = summarize(call_rows, "raw_board_action")
    temporal = summarize(call_rows, "history2_visual_action")
    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_ELIGIBLE_PUBLIC_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or temporal["failures"] or raw["calls"] != len(cases) or temporal["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif temporal["correct"] > raw["correct"] and temporal["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_HARNESS_MEMORY_BEHAVIOR_GAIN"
    elif (
        temporal["correct"] == raw["correct"]
        and raw["representation_chars_total"] > 0
        and temporal["representation_chars_total"] <= 0.50 * raw["representation_chars_total"]
        and temporal["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_NONDOMINATED_EQUAL_MEMORY_ACCURACY_EFFICIENCY_GAIN"
    else:
        gate = "NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-temporal-state-same-model-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_SOURCE_ASSISTED",
        "source_grounding": {
            "trace_repo": tsa.TUFA_REPO,
            "trace_commit": tsa.TUFA_COMMIT,
            "continuation_repo": tsa.CONTINUATION_REPO,
            "continuation_commit": tsa.CONTINUATION_COMMIT,
            "continuation_source": tsa.CONTINUATION_SOURCE,
            "implementation": "clean-room; high-level behavioral principle only",
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
        },
        "selection": {
            "eligible_cases_selected": len(cases),
            "minimum_required": 4,
            "same_action_distractor": True,
            "query_history2_equals_target_history2": True,
            "query_raw_differs_from_target_raw": True,
            "fixed_hash_order": True,
        },
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_board_action": raw, "history2_visual_action": temporal},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_tokens": True,
            "alternating_arm_order": True,
            "temporal_accuracy_gain_promotes_only_if_mean_latency_lte_150pct_raw": True,
            "equal_accuracy_efficiency_gate": "temporal representation chars <=50% raw and mean latency <=135% raw",
            "provider_failure": "INCONCLUSIVE",
        },
        "cases": [
            {
                "case": c["case"],
                "target_token": c["target_token"],
                "action": c["action"],
                "history_key_sha256": c["history_key_sha256"],
                "target_outcome_sha256": c["target_outcome_sha256"],
            }
            for c in cases
        ],
        "rows": call_rows,
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "independent_generalization": False,
            "model_behavior_test": True,
            "provider_execution_is_not_kaggle_execution": True,
            "hidden_kaggle_data_read": False,
            "offline_public_development_score": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_observed": False,
            "owner_score_claim": False,
            "prize_or_award_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 2 if gate.startswith("INCONCLUSIVE_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
