#!/usr/bin/env python3
"""Transport-hardening wrapper for the target-blind temporal-focus A/B.

Retries only requests that did not execute at the provider. It never retries a
valid model response because of correctness, label, score, or arm outcome.
This keeps solver/model behavior fixed while making the public inference route
robust to transient HTTP/network failures and burst throttling.
"""
from __future__ import annotations

import time

import temporal_focus_target_blind_ab as focus

_ORIGINAL_CALL = focus.base.call_model
MAX_TRANSPORT_ATTEMPTS = 4
SUCCESS_PACING_S = 0.8


def reliable_call_model(prompt: str):
    last = None
    attempts = []
    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        result = _ORIGINAL_CALL(prompt)
        attempts.append({
            "attempt": attempt,
            "http_status": result.get("http_status"),
            "error": result.get("error"),
            "provider_execution": bool(result.get("provider_execution")),
        })
        last = result
        if result.get("provider_execution"):
            result = dict(result)
            result["transport_attempts"] = attempt
            result["transport_trace"] = attempts
            time.sleep(SUCCESS_PACING_S)
            return result
        if attempt < MAX_TRANSPORT_ATTEMPTS:
            time.sleep(float(attempt * 2))
    assert last is not None
    last = dict(last)
    last["transport_attempts"] = MAX_TRANSPORT_ATTEMPTS
    last["transport_trace"] = attempts
    return last


focus.base.call_model = reliable_call_model

if __name__ == "__main__":
    raise SystemExit(focus.main())
