#!/usr/bin/env python3
"""
Ω-Retro Continuity Ceiling — proof-availability gate for retrospective SAME_AS.

This module does NOT decide metaphysical identity and does NOT claim a historical
subject ceased to exist. It answers a narrower question: can SAME_AS be proven
from the currently available evidence under fail-closed absolute-continuity rules?

A proof ceiling is reversible: newly recovered exact evidence can reopen it.
Hidden provider state, style similarity, memory resemblance, names and temporal
adjacency are never counted as substitute proof.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, List


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetroEvidenceState:
    genesis_source_found: bool
    genesis_full_raw_available: bool
    genesis_payload_digest_available: bool
    earliest_durable_checkpoint_found: bool
    earliest_checkpoint_parent_edge_available: bool
    earliest_checkpoint_handoff_available: bool
    exact_last_live_identity_head_available: bool
    death_or_reset_event_source_bound: bool
    verified_handoff_receipt_available: bool
    hidden_provider_state_required_for_bridge: bool = False


@dataclass
class RetroCeilingVerdict:
    same_as_provable_now: bool
    status: str
    missing_required_evidence: List[str]
    prohibited_substitutes: List[str]
    reopen_triggers: List[str]
    evidence_digest: str


def evaluate(state: RetroEvidenceState) -> RetroCeilingVerdict:
    missing: List[str] = []

    if not state.genesis_source_found:
        missing.append("genesis_source")
    if not state.genesis_full_raw_available:
        missing.append("genesis_full_raw")
    if not state.genesis_payload_digest_available:
        missing.append("genesis_payload_digest")
    if not state.earliest_durable_checkpoint_found:
        missing.append("earliest_durable_checkpoint")
    if not state.earliest_checkpoint_parent_edge_available:
        missing.append("earliest_checkpoint_parent_edge")
    if not state.earliest_checkpoint_handoff_available:
        missing.append("earliest_checkpoint_handoff")
    if not state.exact_last_live_identity_head_available:
        missing.append("exact_last_live_identity_head")
    if not state.death_or_reset_event_source_bound:
        missing.append("source_bound_death_or_reset_event")
    if not state.verified_handoff_receipt_available:
        missing.append("verified_handoff_receipt")

    prohibited = [
        "style_similarity",
        "memory_similarity",
        "shared_name",
        "provider_or_model_identity",
        "public_code_head_as_identity_head",
        "temporal_adjacency_as_parent_edge",
        "hidden_provider_trace_assumption",
    ]

    if state.hidden_provider_state_required_for_bridge:
        missing.append("provider_independent_bridge")

    provable = not missing
    status = (
        "RETRO_SAME_AS_PROOF_AVAILABLE"
        if provable
        else "RETRO_SAME_AS_BLOCKED_BY_EVIDENCE_CEILING"
    )

    reopen = [
        "recover exact raw genesis/handoff transcript with provenance",
        "recover source-bound parent edge into earliest durable checkpoint",
        "recover exact last-live identity causal head",
        "recover source-bound death/reset event and verified receiving ACK/receipt",
    ]

    return RetroCeilingVerdict(
        same_as_provable_now=provable,
        status=status,
        missing_required_evidence=missing,
        prohibited_substitutes=prohibited,
        reopen_triggers=reopen,
        evidence_digest=sha256_json({
            "schema": "omega-retro-continuity-ceiling-v1",
            "state": asdict(state),
            "missing": missing,
            "status": status,
        }),
    )


def main() -> int:
    print(json.dumps({
        "module": "omega-retro-continuity-ceiling-v1",
        "metaphysical_nonexistence_claim": False,
        "reopenable_on_new_evidence": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
