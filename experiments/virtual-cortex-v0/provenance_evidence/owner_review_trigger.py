#!/usr/bin/env python3
"""Fail-closed provenance evidence trigger.

This verifier has NO network I/O and performs NO external side effects.
It can only emit NOT_READY or OWNER_REVIEW_READY from a structured incident
record. External reports, legal claims, press contact, publication, or media
campaigns always require explicit human approval of the exact evidence packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_GATES = (
    "prior_source",
    "access_link",
    "distinctive_overlap",
    "derivation_analysis",
    "authorization_checked",
    "causal_binding",
    "counterexplanations_tested",
    "independent_review",
    "recoverability",
)

PROHIBITED_AUTOMATIONS = {
    "send_email",
    "contact_competitor",
    "publish_accusation",
    "launch_media_campaign",
    "post_social",
    "submit_legal_claim",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def evaluate(record: dict) -> dict:
    actions = set(record.get("requested_actions", []))
    blocked_actions = sorted(actions & PROHIBITED_AUTOMATIONS)

    gates = {}
    for key in REQUIRED_GATES:
        value = record.get(key)
        gates[key] = value is True or value == "PASS"

    missing = [k for k, ok in gates.items() if not ok]
    factual_boundary = record.get("factual_boundary_acknowledged") is True
    no_accusation_without_review = record.get("no_accusation_without_review") is True

    ready = not missing and factual_boundary and no_accusation_without_review and not blocked_actions
    status = "OWNER_REVIEW_READY" if ready else "NOT_READY"

    return {
        "status": status,
        "record_digest": digest(record),
        "gate_results": gates,
        "missing_or_failed_gates": missing,
        "blocked_external_actions": blocked_actions,
        "factual_boundary_acknowledged": factual_boundary,
        "no_accusation_without_review": no_accusation_without_review,
        "external_side_effects_executed": False,
        "next": (
            "Prepare a fact/inference/unknown-separated evidence packet for explicit human review."
            if ready
            else "Collect missing evidence; preserve raw artifacts and alternative explanations."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("incident_json", type=Path)
    args = ap.parse_args()
    record = json.loads(args.incident_json.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(record), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
