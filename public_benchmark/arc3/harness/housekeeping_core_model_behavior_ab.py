#!/usr/bin/env python3
"""Bounded same-model A/B for the ARC3 housekeeping core representation.

This is deliberately a public source-assisted episodic-memory test, not an
independent-generalization benchmark and not a Kaggle score. It asks whether a
fixed model can retrieve the matching state/action memory more reliably when
high-frequency supported boundary housekeeping is projected out.

Inputs are pinned public Tufalabs action traces. For every selected case the
query and target memory share the exact boundary_core_action key while their
raw_board_action keys differ; a same-action distractor prevents action-name-only
matching. Both arms use the same cases, memory tokens, model, endpoint, output
contract, and call budget.
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
sys.path.insert(0, str(HERE))
import public_trace_housekeeping_audit as hka

ENDPOINT = "https://blockrun.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-lightning"
TIMEOUT_S = 45
TOKENS = ("ALPHA", "BETA")


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
                    "persistent structural state/action identity, not next-outcome semantics. "
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
    except Exception as exc:  # provider/network failure is evidence, not retried blindly
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
        trace_rows, stats = hka.trace_rows(hka.load_events(path))
        trace_stats.append({"path": path.name, **stats})
        for idx, row in enumerate(trace_rows):
            rows.append({"trace": path.name, "trace_index": idx, **row})
    return rows, trace_stats


def build_cases(rows: list[dict[str, Any]], max_cases: int) -> list[dict[str, Any]]:
    # We specifically test the representation mechanism already grounded by the
    # granularity guard: repeated non-contradictory core keys that merge >1 raw key.
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        reps = row["representations"]
        core = reps["boundary_core_action"]
        if not core.get("omitted_rows") and not core.get("omitted_cols"):
            continue
        groups[stable(core)].append(row)

    eligible: list[tuple[str, list[dict[str, Any]]]] = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        outcomes = {stable(r["outcome"]) for r in group}
        raw_keys = {stable(r["representations"]["raw_board_action"]) for r in group}
        if len(outcomes) == 1 and len(raw_keys) >= 2:
            eligible.append((key, group))

    # Hash order makes the fixed subset independent of file-system/dict ordering.
    eligible.sort(key=lambda kv: hashlib.sha256(kv[0].encode("utf-8")).hexdigest())
    cases: list[dict[str, Any]] = []
    for key, group in eligible:
        target_demo = group[0]
        target_raw = stable(target_demo["representations"]["raw_board_action"])
        query = next(
            (r for r in group[1:] if stable(r["representations"]["raw_board_action"]) != target_raw),
            None,
        )
        if query is None:
            continue
        action = target_demo["representations"]["boundary_core_action"].get("action")
        distractor = None
        for other_key, other_group in eligible:
            if other_key == key:
                continue
            candidate = other_group[0]
            other_action = candidate["representations"]["boundary_core_action"].get("action")
            if other_action == action:
                distractor = candidate
                break
        if distractor is None:
            continue

        case_idx = len(cases)
        target_token = TOKENS[case_idx % 2]
        distractor_token = TOKENS[(case_idx + 1) % 2]
        cases.append({
            "case": case_idx,
            "target_token": target_token,
            "distractor_token": distractor_token,
            "target_demo": target_demo,
            "distractor_demo": distractor,
            "query": query,
            "core_key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "target_outcome_sha256": digest(target_demo["outcome"]),
            "action": action,
        })
        if len(cases) >= max_cases:
            break
    return cases


def arm_rep(row: dict[str, Any], arm: str) -> Any:
    name = "raw_board_action" if arm == "raw_board_action" else "boundary_core_action"
    return row["representations"][name]


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    target = stable(arm_rep(case["target_demo"], arm))
    distractor = stable(arm_rep(case["distractor_demo"], arm))
    query = stable(arm_rep(case["query"], arm))
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
    ap.add_argument("--receipt", type=Path, default=Path("housekeeping-core-model-behavior-ab.json"))
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
            arms = ["raw_board_action", "boundary_core_action"] if i % 2 == 0 else ["boundary_core_action", "raw_board_action"]
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
                    "core_key_sha256": case["core_key_sha256"],
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
    core = summarize(call_rows, "boundary_core_action")
    if not selection_ok:
        gate = "INCONCLUSIVE_INSUFFICIENT_ELIGIBLE_PUBLIC_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or core["failures"] or raw["calls"] != len(cases) or core["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif core["correct"] > raw["correct"] and core["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_HARNESS_MEMORY_BEHAVIOR_GAIN"
    elif (
        core["correct"] == raw["correct"]
        and raw["representation_chars_total"] > 0
        and core["representation_chars_total"] <= 0.98 * raw["representation_chars_total"]
        and core["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_NONDOMINATED_EQUAL_MEMORY_ACCURACY_EFFICIENCY_GAIN"
    else:
        gate = "NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-housekeeping-core-same-model-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_SOURCE_ASSISTED",
        "source_grounding": {
            "repo": hka.TUFA_REPO,
            "commit": hka.TUFA_COMMIT,
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
        },
        "selection": {
            "eligible_cases_selected": len(cases),
            "minimum_required": 4,
            "same_action_distractor": True,
            "query_core_equals_target_core": True,
            "query_raw_differs_from_target_raw": True,
            "fixed_hash_order": True,
        },
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_board_action": raw, "boundary_core_action": core},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_tokens": True,
            "alternating_arm_order": True,
            "core_accuracy_gain_promotes_only_if_mean_latency_lte_150pct_raw": True,
            "equal_accuracy_efficiency_gate": "core representation chars <=98% raw and mean latency <=135% raw",
            "provider_failure": "INCONCLUSIVE",
        },
        "cases": [
            {
                "case": c["case"],
                "target_token": c["target_token"],
                "action": c["action"],
                "core_key_sha256": c["core_key_sha256"],
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
