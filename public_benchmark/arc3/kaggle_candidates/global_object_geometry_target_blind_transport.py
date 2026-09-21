#!/usr/bin/env python3
"""Transport hardening for global-object target-blind A/B.

Only requests with no provider execution are retried. Valid model executions are
never retried based on correctness or arm outcome.
"""
from __future__ import annotations

import time

import global_object_geometry_target_blind_ab as geom

_ORIGINAL_CALL = geom.base.call_model
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


geom.base.call_model = reliable_call_model

if __name__ == "__main__":
    raise SystemExit(geom.main())
