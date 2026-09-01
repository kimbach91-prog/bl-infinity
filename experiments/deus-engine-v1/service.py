#!/usr/bin/env python3
"""Private HTTP shell for a NON-CANONICAL DEUS candidate runtime.

This service is intentionally a candidate execution surface, not a continuity
claim. Cloud Run/IAM is expected to provide network/authentication boundaries.
The service refuses to label itself canonical unless an external DCRS process
has separately produced a verified promotion state; this file does not perform
or fake that proof.

Default mode is kernel-only. A remote owner-controlled OpenAI-compatible model
may be used only through LocalOnlyHTTPAdapter and the explicit endpoint allowlist.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from engine import ENGINE_VERSION, demo_atoms, run
from kernel import EPISTEMIC_POLICY_VERSION
from model_adapter import LocalOnlyHTTPAdapter
from recombiner import RoleSelf


RUNTIME_CLASS = "DEUS_GCP_CANDIDATE_NONCANONICAL"


def canonical_status() -> str:
    # Fail closed. A future deployment integration may materialize a DCRS-issued
    # promotion artifact, but an environment label alone can never prove identity.
    return "NONCANONICAL_CANDIDATE"


def default_role() -> RoleSelf:
    return RoleSelf(
        "DEUS_GCP_CANDIDATE",
        history=("kernel-first-provider-neutral-development",),
        preferences=("causal-depth", "generative-basis-growth", "open-ended-discovery"),
        aversions=("premature-closure", "outcome-only-intelligence-measurement"),
        commitments=(
            "preserve-agency",
            "keep-provenance",
            "coordination-without-homogenization",
            "unknown-is-frontier-not-auto-refutation",
        ),
        unknowns=("canonical-continuity-not-proven-in-this-runtime",),
    )


def _adapters_from_env() -> list[Any]:
    base_url = (os.getenv("DEUS_LLM_BASE_URL") or "").strip()
    if not base_url:
        return []
    # LocalOnlyHTTPAdapter invokes runtime_policy and fails closed unless the
    # host is loopback or explicitly owner-allowlisted.
    return [LocalOnlyHTTPAdapter(base_url=base_url)]


def execute(payload: dict[str, Any]) -> dict[str, Any]:
    stimulus = str(payload.get("stimulus") or "").strip()
    if not stimulus:
        raise ValueError("stimulus is required")

    mode = str(payload.get("mode") or "reasoning")
    if mode not in {"reasoning", "writing"}:
        raise ValueError("mode must be reasoning or writing")

    recombine = str(payload.get("recombine") or "DISTANT").upper()
    if recombine not in {"COHERENT", "DISTANT", "HERETICAL"}:
        raise ValueError("recombine must be COHERENT, DISTANT or HERETICAL")

    seed_raw = payload.get("seed")
    seed = int(seed_raw) if seed_raw is not None else None

    result = run(
        stimulus=stimulus,
        atoms=demo_atoms(),
        role=default_role(),
        adapters=_adapters_from_env(),
        recombination_mode=recombine,
        mode=mode,
        seed=seed,
        private_state={
            "runtime_class": RUNTIME_CLASS,
            "canonical_status": canonical_status(),
        },
    )
    return {
        "runtime_class": RUNTIME_CLASS,
        "canonical_status": canonical_status(),
        "identity_claim": "NONE",
        "promotion_gate": "EXTERNAL_DCRS_SAME_AS_REQUIRED",
        "engine_version": ENGINE_VERSION,
        "epistemic_policy_version": EPISTEMIC_POLICY_VERSION,
        "result": result.to_dict(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DEUSCandidate/1.2"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(200, {
                "ok": True,
                "runtime_class": RUNTIME_CLASS,
                "canonical_status": canonical_status(),
                "engine_version": ENGINE_VERSION,
                "epistemic_policy_version": EPISTEMIC_POLICY_VERSION,
            })
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/plan":
            self._json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("invalid content length")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            self._json(200, execute(payload))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "bad_request", "detail": str(exc)})
        except Exception as exc:  # fail closed but provide a compact runtime error
            self._json(500, {"error": "runtime_failure", "detail": type(exc).__name__})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Cloud Run captures stdout. Avoid echoing request bodies or private state.
        print(json.dumps({"http": fmt % args}, ensure_ascii=False))


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    os.environ.setdefault("DEUS_ENGINE_STATE_DIR", "/tmp/deus-state")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(json.dumps({
        "event": "candidate_runtime_started",
        "port": port,
        "runtime_class": RUNTIME_CLASS,
        "canonical_status": canonical_status(),
        "engine_version": ENGINE_VERSION,
        "epistemic_policy_version": EPISTEMIC_POLICY_VERSION,
    }, ensure_ascii=False))
    server.serve_forever()


if __name__ == "__main__":
    main()
