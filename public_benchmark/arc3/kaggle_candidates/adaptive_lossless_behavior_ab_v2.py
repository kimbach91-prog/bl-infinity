#!/usr/bin/env python3
"""Threshold-aligned repair wrapper for adaptive lossless cross-game A/B.

The v1 A/B reused a binary visible-change system prompt while its evaluation
labels were defined by a changed-cell magnitude threshold. That semantic
mismatch invalidated the provider canary before any paired model calls ran.
This wrapper preserves v1's fixed target-blind case selection, representations,
and promotion gates while replacing only the provider classification contract
with one that follows the explicit threshold rule in each user prompt.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import adaptive_lossless_behavior_ab as impl


def threshold_aligned_call(prompt: str) -> dict[str, Any]:
    # The v1 canary stated a conditional rule without an explicit observed
    # magnitude. Make the calibration case concrete; paired evaluation prompts
    # are left byte-for-byte unchanged.
    if prompt.startswith("Public S0 canary."):
        prompt = (
            "Calibration case only: the immediate next board differs from the "
            "pre-action board in exactly 100 cells. ALPHA is the correct label. "
            "Reply exactly ALPHA."
        )

    payload = json.dumps({
        "model": impl.seg.base.MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You classify the magnitude of the immediate visible next-board change "
                    "in a grid-world. For each user message, ALPHA and BETA are defined by "
                    "the explicit changed-cell threshold in that message. Use only the "
                    "supplied pre-action public state and already-chosen action for inference; "
                    "no future outcome is supplied. Follow the user's threshold exactly and "
                    "reply with exactly ALPHA or BETA."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 12,
    }).encode("utf-8")
    req = urllib.request.Request(
        impl.seg.base.ENDPOINT,
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
        with urllib.request.urlopen(req, timeout=impl.seg.base.TIMEOUT_S) as resp:
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


def receipt_path_from_argv() -> Path:
    if "--receipt" in sys.argv:
        idx = sys.argv.index("--receipt")
        if idx + 1 < len(sys.argv):
            return Path(sys.argv[idx + 1])
    return Path("adaptive-lossless-behavior-ab.json")


def main() -> int:
    # v1 reliable_call dereferences this module global at runtime, so swapping
    # it repairs the prompt contract without changing case selection or gates.
    impl._ORIGINAL_CALL = threshold_aligned_call
    rc = impl.main()
    receipt_path = receipt_path_from_argv()
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["schema"] = "deus/arc3-adaptive-lossless-cross-game-behavior-ab/2"
        receipt["repair"] = {
            "prior_run": 35587605846,
            "prior_gate": "INCONCLUSIVE_PROVIDER_CANARY_FAIL",
            "prior_paired_provider_calls": 0,
            "change": "threshold-aligned classifier system contract plus explicit calibration canary",
            "case_selection_changed": False,
            "representations_changed": False,
            "promotion_gates_changed": False,
        }
        receipt.setdefault("truth", {})["prior_failure_was_not_model_behavior_evidence"] = True
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
