#!/usr/bin/env python3
"""Rung 129 transport repair: prospectively pace fresh provider calls.

The first rung129 execution fail-closed because the provider returned HTTP 429 on both arms.
No failed request is retried. This wrapper changes only the prospective transport schedule:
all fresh policy and coordinate calls share one deterministic minimum inter-call interval.
The same pacing applies to both A/B arms. Solver representation, model identity contract,
targets, action budget and promotion gate are unchanged.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import public_observed_transition_memory_ab_129 as m
import public_visible_continuity_compaction_ab_128_twostage as two

MIN_INTERCALL_S = 6.0
PRIOR_FAILED_RUN_ID = 35638493458
_last_call_started = 0.0
_base_policy_call = m.provider_call
_base_coordinate_call = two.coordinate_call


def _pace() -> None:
    global _last_call_started
    now = time.monotonic()
    remain = MIN_INTERCALL_S - (now - _last_call_started)
    if remain > 0:
        time.sleep(remain)
    _last_call_started = time.monotonic()


def paced_policy_call(prompt: str, legal_ids: set[int]) -> dict[str, Any]:
    _pace()
    return _base_policy_call(prompt, legal_ids)


def paced_coordinate_call(game_id: str, current: Any, policy_note: str) -> dict[str, Any]:
    _pace()
    return _base_coordinate_call(game_id, current, policy_note)


def receipt_path() -> Path:
    for i, arg in enumerate(sys.argv):
        if arg == "--receipt" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
        if arg.startswith("--receipt="):
            return Path(arg.split("=", 1)[1])
    return Path("public-observed-transition-memory-ab-129.json")


def main() -> int:
    m.provider_call = paced_policy_call
    two.coordinate_call = paced_coordinate_call
    rc = m.main()
    p = receipt_path()
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        data["transport_repair"] = {
            "prior_failed_run_id": PRIOR_FAILED_RUN_ID,
            "prior_failure": "PROVIDER_HTTP_429_BOTH_ARMS",
            "failed_requests_retried": False,
            "repair": "GLOBAL_DETERMINISTIC_INTERCALL_PACING_FOR_FRESH_CALLS",
            "minimum_intercall_seconds": MIN_INTERCALL_S,
            "same_pacing_both_arms": True,
            "provider_retries": False,
            "solver_representation_changed_from_original_rung129": False,
        }
        data.setdefault("truth", {}).update({
            "prior_failed_provider_calls_retried": False,
            "transport_schedule_repaired_prospectively": True,
            "same_transport_pacing_both_arms": True,
        })
        p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
