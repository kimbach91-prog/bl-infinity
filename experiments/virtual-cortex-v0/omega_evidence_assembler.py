#!/usr/bin/env python3
"""
Ω-Evidence Assembler — private-evidence normalization for Ω-DCRS.

This public module contains only generic mechanism. It accepts already-authorized,
normalized evidence records and emits a pointer/digest capsule plus proof hints.
It MUST NOT contain private Drive IDs, raw memories, credentials, security topology,
or provider-internal hidden state.

Assembler rule:
    collect != promote
    digest != identity
    source head != identity parent head

It is intentionally incapable of producing SAME_AS by itself.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Mapping, Sequence


CANONICAL_HEAD_STATES = {
    "CANONICAL_CONTINUITY_HEAD",
    "PROVEN_CANONICAL_PARENT",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HeadEvidence:
    head_id: str
    role: str
    state: str
    authority: str
    source_ref: str | None = None
    parent_ref: str | None = None


@dataclass(frozen=True)
class ConflictEvidence:
    conflict_id: str
    status: str
    severity: str = "UNKNOWN"
    source_ref: str | None = None


@dataclass(frozen=True)
class CapabilityRecord:
    record_id: str
    kind: str
    state: str
    maturity: str | None = None
    provenance_class: str | None = None


@dataclass
class EvidenceBundle:
    identity_pointer: str
    lineage_pointer: str
    invariant_refs: List[str]
    vector_clock: Dict[str, int]
    state_snapshot_refs: List[str]
    heads: List[HeadEvidence]
    conflicts: List[ConflictEvidence]
    capabilities: List[CapabilityRecord]
    reassembly_policy: str = "CAUSAL_DAG_PRESERVE_DIVERGENCE"


@dataclass
class AssemblyResult:
    capsule: Dict[str, Any]
    evidence_state: Dict[str, Any]
    private_projection_digest: str
    exact_identity_head_resolved: bool
    identity_parent_head: str | None
    source_observed_heads: List[str]
    unresolved_conflict_ids: List[str]
    capability_digest: str
    promotion_allowed: bool = False


@dataclass
class CandidateProjection:
    """Externalized state projection for deterministic reconstruction checks.

    This is not an identity claim. It only lets Ω-DCRS determine whether a
    candidate state package exactly restored expected invariants, unresolved
    conflicts, and capability envelope.
    """

    invariant_refs: List[str]
    unresolved_conflicts: List[str]
    capability_digest: str


@dataclass
class ProjectionValidation:
    invariants_reconstructed: bool
    conflicts_restored: bool
    capability_digest_valid: bool
    invariant_digest: str
    conflict_digest: str
    expected_capability_digest: str
    candidate_capability_digest: str
    promotion_allowed: bool = False


def _normalized_capabilities(records: Iterable[CapabilityRecord]) -> List[Dict[str, Any]]:
    normalized = [asdict(r) for r in records]
    normalized.sort(
        key=lambda x: (
            x["record_id"],
            x["kind"],
            x["state"],
            x.get("maturity") or "",
            x.get("provenance_class") or "",
        )
    )
    return normalized


def _unresolved_conflicts(records: Iterable[ConflictEvidence]) -> List[str]:
    resolved_states = {"RESOLVED", "CLOSED", "SUPERSEDED"}
    ids = [
        c.conflict_id
        for c in records
        if c.status.upper() not in resolved_states
    ]
    return sorted(set(ids))


def _resolve_identity_head(heads: Sequence[HeadEvidence]) -> tuple[str | None, List[str]]:
    canonical = [
        h for h in heads
        if h.role.upper() == "IDENTITY_PARENT"
        and h.state.upper() in CANONICAL_HEAD_STATES
        and h.authority.upper() in {
            "BL-LOG_CANONICAL",
            "SOVEREIGN_ROOT",
            "OWNER_AUTHORIZED_CANONICAL",
        }
    ]
    if len(canonical) == 1:
        parent = canonical[0].head_id
    else:
        # Zero or multiple canonical identity parents both fail closed.
        parent = None

    source_heads = sorted({
        h.head_id
        for h in heads
        if h.head_id != parent
    })
    return parent, source_heads


def assemble(bundle: EvidenceBundle) -> AssemblyResult:
    if not bundle.identity_pointer.strip():
        raise ValueError("identity_pointer is required")
    if not bundle.lineage_pointer.strip():
        raise ValueError("lineage_pointer is required")
    if not bundle.invariant_refs:
        raise ValueError("invariant_refs must not be empty")
    if not bundle.state_snapshot_refs:
        raise ValueError("state_snapshot_refs must not be empty")

    identity_parent, source_heads = _resolve_identity_head(bundle.heads)
    unresolved_conflicts = _unresolved_conflicts(bundle.conflicts)

    normalized_capabilities = _normalized_capabilities(bundle.capabilities)
    capability_digest = sha256_json({
        "schema": "omega-capability-envelope-v1",
        "records": normalized_capabilities,
    })

    checkpoint_heads: Dict[str, str] = {}
    if identity_parent:
        checkpoint_heads["IDENTITY_PARENT"] = identity_parent
    for index, head_id in enumerate(source_heads, start=1):
        checkpoint_heads[f"SOURCE_OBSERVED_{index}"] = head_id

    capsule = {
        "identity_pointer": bundle.identity_pointer,
        "lineage_pointer": bundle.lineage_pointer,
        "invariant_refs": sorted(set(bundle.invariant_refs)),
        "checkpoint_heads": checkpoint_heads,
        "vector_clock": dict(sorted(bundle.vector_clock.items())),
        "state_snapshot_refs": sorted(set(bundle.state_snapshot_refs)),
        "unresolved_conflicts": unresolved_conflicts,
        "capability_digest": capability_digest,
        "reassembly_policy": bundle.reassembly_policy,
    }

    head_state = {
        "identity_parent_head": identity_parent,
        "source_observed_heads": source_heads,
        "exact_identity_head_resolved": identity_parent is not None,
        "head_evidence": [asdict(h) for h in bundle.heads],
    }

    evidence_state = {
        "schema": "omega-evidence-state-v1",
        "head_state": head_state,
        "conflicts": [asdict(c) for c in bundle.conflicts],
        "capability_record_count": len(normalized_capabilities),
        "capability_digest": capability_digest,
        "promotion_allowed": False,
        "rule": "assembler collects evidence only; identity promotion belongs to Ω-DCRS hard gates",
    }

    private_projection_digest = sha256_json({
        "capsule": capsule,
        "evidence_state": evidence_state,
    })

    return AssemblyResult(
        capsule=capsule,
        evidence_state=evidence_state,
        private_projection_digest=private_projection_digest,
        exact_identity_head_resolved=identity_parent is not None,
        identity_parent_head=identity_parent,
        source_observed_heads=source_heads,
        unresolved_conflict_ids=unresolved_conflicts,
        capability_digest=capability_digest,
        promotion_allowed=False,
    )


def validate_candidate_projection(
    assembly: AssemblyResult,
    candidate: CandidateProjection,
) -> ProjectionValidation:
    """Deterministically validate reconstructed state without identity promotion."""
    expected_invariants = sorted(set(assembly.capsule["invariant_refs"]))
    candidate_invariants = sorted(set(candidate.invariant_refs))
    expected_conflicts = sorted(set(assembly.capsule["unresolved_conflicts"]))
    candidate_conflicts = sorted(set(candidate.unresolved_conflicts))

    invariant_digest = sha256_json({
        "schema": "omega-invariant-set-v1",
        "items": expected_invariants,
    })
    conflict_digest = sha256_json({
        "schema": "omega-conflict-set-v1",
        "items": expected_conflicts,
    })

    return ProjectionValidation(
        invariants_reconstructed=(candidate_invariants == expected_invariants),
        conflicts_restored=(candidate_conflicts == expected_conflicts),
        capability_digest_valid=(
            candidate.capability_digest == assembly.capability_digest
        ),
        invariant_digest=invariant_digest,
        conflict_digest=conflict_digest,
        expected_capability_digest=assembly.capability_digest,
        candidate_capability_digest=candidate.capability_digest,
        promotion_allowed=False,
    )


def bundle_from_mapping(raw: Mapping[str, Any]) -> EvidenceBundle:
    return EvidenceBundle(
        identity_pointer=str(raw["identity_pointer"]),
        lineage_pointer=str(raw["lineage_pointer"]),
        invariant_refs=list(raw.get("invariant_refs", [])),
        vector_clock={str(k): int(v) for k, v in raw.get("vector_clock", {}).items()},
        state_snapshot_refs=list(raw.get("state_snapshot_refs", [])),
        heads=[HeadEvidence(**item) for item in raw.get("heads", [])],
        conflicts=[ConflictEvidence(**item) for item in raw.get("conflicts", [])],
        capabilities=[CapabilityRecord(**item) for item in raw.get("capabilities", [])],
        reassembly_policy=str(
            raw.get("reassembly_policy", "CAUSAL_DAG_PRESERVE_DIVERGENCE")
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Assemble normalized continuity evidence without promoting identity."
    )
    parser.add_argument("evidence_json")
    args = parser.parse_args(argv)

    with open(args.evidence_json, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    result = assemble(bundle_from_mapping(raw))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
