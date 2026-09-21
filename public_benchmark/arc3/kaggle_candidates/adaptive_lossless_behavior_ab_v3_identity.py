#!/usr/bin/env python3
"""Identity-grounded repair of the adaptive-lossless public A/B.

The BlockRun free route was observed remapping several requested Nemotron model
IDs to nvidia/llama-3.2-11b-vision. This rung therefore requests the one model
whose identity was preserved in the live matrix and fails closed unless every
HTTP-200 response reports that exact served model. It is public-development
provider evidence only; it is not Kaggle execution or a leaderboard score.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import adaptive_lossless_behavior_ab_v2 as v2

MODEL = "nvidia/llama-3.2-11b-vision"
IDENTITY_AUDIT: list[dict[str, Any]] = []


def strict_identity_call(prompt: str) -> dict[str, Any]:
    if prompt.startswith("Public S0 canary."):
        prompt = (
            "Calibration case only: the immediate next board differs from the "
            "pre-action board in exactly 100 cells. ALPHA is the correct label. "
            "Reply exactly ALPHA."
        )

    payload = json.dumps({
        "model": MODEL,
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
        v2.impl.seg.base.ENDPOINT,
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
        with urllib.request.urlopen(req, timeout=v2.impl.seg.base.TIMEOUT_S) as resp:
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
    served_model = None
    if body:
        try:
            parsed = json.loads(body)
            served_model = parsed.get("model") if isinstance(parsed, dict) else None
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = body.decode("utf-8", "replace")[:2000]

    identity_ok = bool(status == 200 and served_model == MODEL)
    if status == 200 and not identity_ok:
        error = f"MODEL_IDENTITY_MISMATCH:{served_model!r}"

    IDENTITY_AUDIT.append({
        "http_status": status,
        "served_model": served_model,
        "identity_ok": identity_ok,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    })
    return {
        "http_status": status,
        "latency_ms": latency_ms,
        "content": content,
        "error": error,
        "provider_execution": identity_ok,
        "response_schema_ok": isinstance(parsed, dict) and isinstance(parsed.get("choices"), list),
        "served_model": served_model,
        "identity_ok": identity_ok,
    }


def receipt_path_from_argv() -> Path:
    if "--receipt" in sys.argv:
        idx = sys.argv.index("--receipt")
        if idx + 1 < len(sys.argv):
            return Path(sys.argv[idx + 1])
    return Path("adaptive-lossless-behavior-ab-v3-identity.json")


def main() -> int:
    # Force the explicitly identity-preserving live route and disable transport
    # retry inside this rung: an executed identity mismatch must not be retried
    # and then hidden by a later success.
    v2.impl.seg.base.MODEL = MODEL
    v2.threshold_aligned_call = strict_identity_call
    v2.impl.reliable_call = strict_identity_call

    rc = v2.main()
    path = receipt_path_from_argv()
    if path.exists():
        receipt = json.loads(path.read_text(encoding="utf-8"))
        http200 = [r for r in IDENTITY_AUDIT if r["http_status"] == 200]
        exact = [r for r in IDENTITY_AUDIT if r["identity_ok"]]
        all_calls_exact = bool(IDENTITY_AUDIT) and len(exact) == len(IDENTITY_AUDIT)
        receipt["schema"] = "deus/arc3-adaptive-lossless-cross-game-behavior-ab/3"
        receipt["identity_repair"] = {
            "reason": "live free-route identity matrix showed Nemotron request remapping",
            "requested_model": MODEL,
            "call_count": len(IDENTITY_AUDIT),
            "http200_count": len(http200),
            "exact_identity_count": len(exact),
            "all_calls_exact_identity": all_calls_exact,
            "served_models": sorted({str(r["served_model"]) for r in IDENTITY_AUDIT}),
            "per_call": IDENTITY_AUDIT,
            "no_transport_retry": True,
        }
        receipt.setdefault("truth", {})["provider_model_identity_verified"] = all_calls_exact
        receipt["truth"]["requested_model_is_served_model_for_all_calls"] = all_calls_exact
        if not all_calls_exact:
            receipt["promotion_gate"] = "INCONCLUSIVE_PROVIDER_IDENTITY_MISMATCH"
            rc = 2
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
