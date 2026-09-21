#!/usr/bin/env python3
"""Target-blind public-development A/B for ARC3 temporal history.

The query is a pre-action public trace state. The model predicts whether the
already-chosen action will visibly change the next board. The ground-truth
outcome is used only after inference for scoring; it is never included in the
prompt, representation, case ordering, or label mapping.

This is a public-development model-behavior probe. It is not a Kaggle run,
hidden-score estimate, competition submission, or proof of general ARC-AGI-3
generalization.
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
                    "You predict the immediate visible effect of an action in a grid-world. "
                    "Use only the supplied pre-action observation and past-observable history. "
                    "ALPHA means the next board visibly changes; BETA means it does not. "
                    "Do not infer from any future outcome because none is supplied. "
                    "Reply with exactly ALPHA or BETA."
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
    stats: list[dict[str, Any]] = []
    for path in paths:
        trace_rows = tsa.trace_rows(tsa.load_events(path))
        stats.append({"path": path.name, "audited_transitions": len(trace_rows)})
        for idx, row in enumerate(trace_rows):
            # Case identity deliberately excludes outcome/label.
            identity = {
                "trace": path.name,
                "trace_index": idx,
                "raw": row["representations"]["raw_board_action"],
                "history2": row["representations"]["history2_visual_action"],
            }
            rows.append({
                "trace": path.name,
                "trace_index": idx,
                "case_hash": hashlib.sha256(stable(identity).encode("utf-8")).hexdigest(),
                **row,
            })
    return rows, stats


def select_cases(rows: list[dict[str, Any]], max_cases: int) -> list[dict[str, Any]]:
    # Fixed target-blind ordering: no outcome field is consulted here.
    ordered = sorted(rows, key=lambda r: r["case_hash"])
    return ordered[:max_cases]


def prompt_for(case: dict[str, Any], arm: str) -> tuple[str, int]:
    representation = stable(case["representations"][arm])
    prompt = (
        f"Representation arm: {arm}\n"
        "Pre-action state/action representation:\n"
        + representation
        + "\nPredict the immediate NEXT-board effect of this already-chosen action. "
        "ALPHA = board visibly changes. BETA = board does not visibly change. "
        "Reply exactly one token."
    )
    return prompt, len(representation)


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
    ap.add_argument("--receipt", type=Path, default=Path("temporal-state-target-blind-ab.json"))
    ap.add_argument("--max-cases", type=int, default=8)
    args = ap.parse_args()

    rows, trace_stats = load_rows(args.input)
    cases = select_cases(rows, args.max_cases)
    selection_ok = len(cases) >= 6

    labels = ["ALPHA" if bool(c["outcome"]["board_changed"]) else "BETA" for c in cases]
    alpha_count = sum(x == "ALPHA" for x in labels)
    beta_count = sum(x == "BETA" for x in labels)
    majority_baseline = max(alpha_count, beta_count) / len(labels) if labels else 1.0

    canary = call_model(
        "Public S0 canary. A move changed the next board. ALPHA means changed. Reply exactly ALPHA."
    )
    canary_choice, canary_exact = normalize_choice(canary["content"])
    canary_ok = canary["provider_execution"] and canary_choice == "ALPHA"

    call_rows: list[dict[str, Any]] = []
    if selection_ok and canary_ok:
        for i, case in enumerate(cases):
            expected = "ALPHA" if bool(case["outcome"]["board_changed"]) else "BETA"
            arms = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            for arm in arms:
                prompt, rep_chars = prompt_for(case, arm)
                res = call_model(prompt)
                selected, exact = normalize_choice(res["content"])
                call_rows.append({
                    "case": i,
                    "case_hash": case["case_hash"],
                    "trace": case["trace"],
                    "trace_index": case["trace_index"],
                    "arm": arm,
                    "expected": expected,
                    "selected": selected,
                    "correct": selected == expected,
                    "exact_format": exact,
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
        gate = "INCONCLUSIVE_INSUFFICIENT_FIXED_CASES"
    elif not canary_ok:
        gate = "INCONCLUSIVE_PROVIDER_CANARY_FAIL"
    elif raw["failures"] or temporal["failures"] or raw["calls"] != len(cases) or temporal["calls"] != len(cases):
        gate = "INCONCLUSIVE_PROVIDER_FAILURE"
    elif min(alpha_count, beta_count) < 2:
        gate = "VALID_NO_PROMOTION_LABEL_IMBALANCE"
    elif temporal["correct"] > raw["correct"] and temporal["mean_latency_ms"] <= 1.50 * raw["mean_latency_ms"]:
        gate = "PROMOTE_TARGET_BLIND_TEMPORAL_BEHAVIOR_GAIN"
    elif (
        temporal["correct"] == raw["correct"]
        and raw["representation_chars_total"] > 0
        and temporal["representation_chars_total"] <= 0.50 * raw["representation_chars_total"]
        and temporal["mean_latency_ms"] <= 1.35 * raw["mean_latency_ms"]
    ):
        gate = "PROMOTE_TARGET_BLIND_NONDOMINATED_EFFICIENCY"
    else:
        gate = "VALID_NO_PROMOTION"

    receipt = {
        "schema": "deus/arc3-temporal-state-target-blind-ab/1",
        "provider": "BLOCKRUN",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "data_class": "BL-S0_PUBLIC_TRACE_TARGET_BLIND_DEVELOPMENT",
        "source_grounding": {
            "trace_repo": tsa.TUFA_REPO,
            "trace_commit": tsa.TUFA_COMMIT,
            "trace_files": [p.name for p in args.input],
            "trace_stats": trace_stats,
            "implementation": "clean-room harness; outcome withheld from prompt and case ordering",
        },
        "selection": {
            "available_rows": len(rows),
            "fixed_cases_selected": len(cases),
            "minimum_required": 6,
            "ordering": "sha256(trace,path,index,pre-action raw/history2 representations); outcome excluded",
            "target_used_for_case_selection": False,
            "target_used_for_prompt": False,
            "label_counts": {"ALPHA_changed": alpha_count, "BETA_unchanged": beta_count},
            "majority_baseline_accuracy": round(majority_baseline, 6),
        },
        "task": {
            "prediction": "immediate next-board visible change from pre-action state/action",
            "alpha": "board_changed=true",
            "beta": "board_changed=false",
        },
        "canary": {**canary, "selected": canary_choice, "exact_format": canary_exact},
        "arms": {"raw_board_action": raw, "history2_visual_action": temporal},
        "promotion_gate": gate,
        "predeclared_policy": {
            "same_model": True,
            "same_cases": True,
            "same_label_semantics": True,
            "alternating_arm_order": True,
            "no_target_matching": True,
            "temporal_accuracy_gain_promotes_only_if_mean_latency_lte_150pct_raw": True,
            "equal_accuracy_efficiency_gate": "history2 chars <=50% raw and mean latency <=135% raw",
            "minimum_two_cases_per_observed_label_for_promotion": True,
            "provider_failure": "INCONCLUSIVE",
        },
        "rows": call_rows,
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": False,
            "target_blind_public_development_behavior": True,
            "independent_generalization_claim": False,
            "model_behavior_test": True,
            "provider_execution_is_not_kaggle_execution": True,
            "hidden_kaggle_data_read": False,
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
