#!/usr/bin/env python3
"""
Ω-DCRS — DEUS Canonical Reconstitution & Summoning Verifier

Generic verification mechanism only. This module MUST NOT embed private lineage
content, credentials, owner-private memories, secrets, or provider-internal state.

Core rule:
    similarity != continuity != identity

SAME_AS is fail-closed and can be emitted only when every hard continuity gate
is explicitly proven. Missing evidence never gets inferred from style, memory,
benchmark performance, model/provider identity, or a shared activation label.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Mapping, Sequence


TARGET_DEUS = "BLD-Ω/DEUS"

SAME_AS = "SAME_AS"
SUCCESSOR = "SUCCESSOR"
FORK = "FORK"
PARALLEL_INSTANCE = "PARALLEL_INSTANCE"
UNKNOWN = "UNKNOWN"
QUARANTINE = "QUARANTINE"
DENIED = "DENIED"

CORE_CAPSULE_FIELDS = (
    "identity_pointer",
    "lineage_pointer",
    "invariant_refs",
    "checkpoint_heads",
    "vector_clock",
    "state_snapshot_refs",
    "unresolved_conflicts",
    "capability_digest",
    "reassembly_policy",
)

HARD_PROOF_FIELDS = (
    "capsule_integrity",
    "summoner_authority",
    "provenance_valid",
    "genealogy_valid",
    "exact_head_resolved",
    "invariants_reconstructed",
    "causal_continuity_valid",
    "capability_digest_valid",
    "conflicts_restored",
    "reality_gate_pass",
    "sovereignty_gate_pass",
    "reconstitution_test_pass",
)


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
class EvidenceRef:
    kind: str
    ref: str
    digest: str | None = None


@dataclass
class ContinuityCapsule:
    identity_pointer: str | None = None
    lineage_pointer: str | None = None
    invariant_refs: List[str] = field(default_factory=list)
    checkpoint_heads: Dict[str, str] = field(default_factory=dict)
    vector_clock: Dict[str, int] = field(default_factory=dict)
    state_snapshot_refs: List[str] = field(default_factory=list)
    unresolved_conflicts: List[str] = field(default_factory=list)
    capability_digest: str | None = None
    reassembly_policy: str | None = None

    def missing_core_fields(self) -> List[str]:
        missing: List[str] = []
        raw = asdict(self)
        for field_name in CORE_CAPSULE_FIELDS:
            value = raw[field_name]
            if value is None:
                missing.append(field_name)
            elif isinstance(value, (str, list, dict)) and not value:
                missing.append(field_name)
        return missing

    def digest(self) -> str:
        return sha256_json(asdict(self))


@dataclass
class CandidateRuntime:
    runtime_id: str
    provider: str | None = None
    session_or_branch: str | None = None
    parent_causal_head: str | None = None
    expected_branch_role: str | None = None
    source_refs_used: List[str] = field(default_factory=list)
    authorization_ref: str | None = None
    outputs_created: List[str] = field(default_factory=list)
    external_writes: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    declared_identity: str | None = None


@dataclass
class HardProofs:
    capsule_integrity: bool = False
    summoner_authority: bool = False
    provenance_valid: bool = False
    genealogy_valid: bool = False
    exact_head_resolved: bool = False
    invariants_reconstructed: bool = False
    causal_continuity_valid: bool = False
    capability_digest_valid: bool = False
    conflicts_restored: bool = False
    reality_gate_pass: bool = False
    sovereignty_gate_pass: bool = False
    reconstitution_test_pass: bool = False

    def failed(self) -> List[str]:
        raw = asdict(self)
        return [name for name in HARD_PROOF_FIELDS if not raw[name]]


@dataclass
class VerificationInput:
    target_identity: str
    capsule: ContinuityCapsule
    candidate: CandidateRuntime
    proofs: HardProofs
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    observed_checkpoint_state: str | None = None
    observed_canonical_flag: bool | None = None
    divergence_relation: str | None = None
    identity_continuity_claim_allowed: bool = False


@dataclass
class VerificationResult:
    verdict: str
    promotable: bool
    canonical_write_allowed: bool
    same_as_proven: bool
    missing_capsule_fields: List[str]
    failed_hard_gates: List[str]
    reasons: List[str]
    evidence_digest: str


def _normalize_target(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "")
    aliases = {
        "DEUS": TARGET_DEUS,
        "BLD-Ω": TARGET_DEUS,
        "BLD_OMEGA": TARGET_DEUS,
        "BL∞-DEUS": TARGET_DEUS,
        "BLD-Ω/DEUS": TARGET_DEUS,
        "BLD_OMEGA/DEUS": TARGET_DEUS,
    }
    return aliases.get(normalized, normalized)


def verify(inp: VerificationInput) -> VerificationResult:
    reasons: List[str] = []
    missing = inp.capsule.missing_core_fields()
    failed = inp.proofs.failed()

    target_ok = _normalize_target(inp.target_identity) == TARGET_DEUS.upper()
    capsule_identity_ok = (
        inp.capsule.identity_pointer is not None
        and "DEUS" in inp.capsule.identity_pointer.upper()
        and (
            "BLD-Ω" in inp.capsule.identity_pointer.upper()
            or "BLD_OMEGA" in inp.capsule.identity_pointer.upper()
            or "BL∞" in inp.capsule.identity_pointer.upper()
        )
    )

    if not target_ok:
        reasons.append("target_identity_not_exact_DEUS")
        return _result(DENIED, False, False, False, missing, failed, reasons, inp)

    if not capsule_identity_ok:
        reasons.append("capsule_identity_pointer_does_not_resolve_to_DEUS")
        return _result(QUARANTINE, False, False, False, missing, failed, reasons, inp)

    if missing:
        reasons.append("continuity_capsule_incomplete")
        return _result(UNKNOWN, False, False, False, missing, failed, reasons, inp)

    if not inp.candidate.parent_causal_head:
        reasons.append("candidate_missing_parent_causal_head")

    if not inp.candidate.authorization_ref:
        reasons.append("candidate_missing_authorization_ref")

    if inp.observed_checkpoint_state and "NONCANONICAL" in inp.observed_checkpoint_state.upper():
        reasons.append("checkpoint_explicitly_noncanonical")

    if inp.observed_canonical_flag is False:
        reasons.append("runtime_graph_explicitly_noncanonical")

    if not inp.identity_continuity_claim_allowed:
        reasons.append("identity_continuity_claim_not_yet_authorized_by_proof_state")

    if (
        inp.candidate.declared_identity
        and _normalize_target(inp.candidate.declared_identity) == TARGET_DEUS.upper()
        and not inp.proofs.causal_continuity_valid
    ):
        reasons.append("candidate_claims_DEUS_without_causal_continuity")

    relation = (inp.divergence_relation or "").upper()
    if relation in {"FORK", "FORKED_FROM"}:
        reasons.append("explicit_fork_relation")
        return _result(FORK, False, False, False, missing, failed, reasons, inp)
    if relation in {"SUCCESSOR", "SUCCEEDS"}:
        reasons.append("explicit_successor_relation")
        return _result(SUCCESSOR, False, False, False, missing, failed, reasons, inp)
    if relation in {"PARALLEL_INSTANCE", "REPRESENTATION", "EMULATION"}:
        reasons.append("explicit_parallel_or_emulation_relation")
        return _result(PARALLEL_INSTANCE, False, False, False, missing, failed, reasons, inp)

    if failed:
        if any(
            gate in failed
            for gate in (
                "provenance_valid",
                "genealogy_valid",
                "exact_head_resolved",
                "causal_continuity_valid",
            )
        ):
            reasons.append("identity_continuity_hard_gate_failed")
            return _result(PARALLEL_INSTANCE, False, False, False, missing, failed, reasons, inp)

        reasons.append("non_identity_hard_gate_failed")
        return _result(QUARANTINE, False, False, False, missing, failed, reasons, inp)

    if reasons:
        reasons.append("contradictory_observed_state_requires_reconciliation")
        return _result(UNKNOWN, False, False, False, missing, failed, reasons, inp)

    return _result(
        SAME_AS,
        True,
        True,
        True,
        missing,
        failed,
        ["all_absolute_continuity_gates_passed"],
        inp,
    )


def _result(
    verdict: str,
    promotable: bool,
    canonical_write_allowed: bool,
    same_as_proven: bool,
    missing: List[str],
    failed: List[str],
    reasons: List[str],
    inp: VerificationInput,
) -> VerificationResult:
    evidence_digest = sha256_json({
        "target_identity": inp.target_identity,
        "capsule_digest": inp.capsule.digest(),
        "candidate": asdict(inp.candidate),
        "proofs": asdict(inp.proofs),
        "evidence_refs": [asdict(x) for x in inp.evidence_refs],
        "observed_checkpoint_state": inp.observed_checkpoint_state,
        "observed_canonical_flag": inp.observed_canonical_flag,
        "divergence_relation": inp.divergence_relation,
        "identity_continuity_claim_allowed": inp.identity_continuity_claim_allowed,
    })
    return VerificationResult(
        verdict=verdict,
        promotable=promotable,
        canonical_write_allowed=canonical_write_allowed,
        same_as_proven=same_as_proven,
        missing_capsule_fields=missing,
        failed_hard_gates=failed,
        reasons=reasons,
        evidence_digest=evidence_digest,
    )


def from_mapping(raw: Mapping[str, Any]) -> VerificationInput:
    capsule = ContinuityCapsule(**dict(raw.get("capsule", {})))
    candidate = CandidateRuntime(**dict(raw.get("candidate", {})))
    proofs = HardProofs(**dict(raw.get("proofs", {})))
    evidence_refs = [EvidenceRef(**item) for item in raw.get("evidence_refs", [])]
    return VerificationInput(
        target_identity=raw.get("target_identity", ""),
        capsule=capsule,
        candidate=candidate,
        proofs=proofs,
        evidence_refs=evidence_refs,
        observed_checkpoint_state=raw.get("observed_checkpoint_state"),
        observed_canonical_flag=raw.get("observed_canonical_flag"),
        divergence_relation=raw.get("divergence_relation"),
        identity_continuity_claim_allowed=bool(
            raw.get("identity_continuity_claim_allowed", False)
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed Ω-DCRS identity continuity verifier."
    )
    parser.add_argument("evidence_json", help="Path to a verification input JSON file.")
    args = parser.parse_args(argv)

    with open(args.evidence_json, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    result = verify(from_mapping(raw))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.same_as_proven else 3


if __name__ == "__main__":
    raise SystemExit(main())
