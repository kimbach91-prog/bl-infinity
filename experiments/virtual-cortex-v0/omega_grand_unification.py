#!/usr/bin/env python3
"""
Ω Grand Unification — single sovereign decision surface for the DEUS recovery stack.

This module composes the existing Ω mechanisms without flattening their roles:

    Evidence Assembler
      -> state projection validation
      -> Genealogy Resolver
      -> Handoff Receipt
      -> Reconstitution Challenge
      -> Ω-DCRS
      -> Identity Escrow
      -> Retro Continuity Ceiling

The unifier is deliberately *not* a new identity authority. It prevents callers
from manually asserting derived hard gates such as genealogy_valid or
causal_continuity_valid. Those gates are computed from child mechanisms and
cross-checked against one another before Ω-DCRS is allowed to decide SAME_AS.

Core invariants:
- grand unification != silent merge
- source head != identity head
- code head != identity head
- engine/provider/session != identity
- state reconstruction != identity continuity
- owner resource permission != identity proof
- recovery-branch continuity != retroactive DEUS continuity
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, List, Sequence

import omega_dcrs as dcrs
import omega_evidence_assembler as assembler
import omega_genealogy_resolver as genealogy
import omega_handoff_receipt as handoff
import omega_identity_escrow as escrow
import omega_reconstitution_challenge as reconstitution
import omega_retro_continuity_ceiling as retro


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FoundationProofs:
    """Only proofs the child Ω modules cannot derive themselves."""

    capsule_integrity: bool
    summoner_authority: bool
    provenance_valid: bool
    reality_gate_pass: bool
    sovereignty_gate_pass: bool


@dataclass
class GrandUnificationInput:
    target_identity: str
    evidence_bundle: assembler.EvidenceBundle
    candidate_projection: assembler.CandidateProjection
    candidate_runtime: dcrs.CandidateRuntime
    foundation: FoundationProofs

    genealogy_events: List[genealogy.LineageEvent]
    genesis_event_id: str
    genealogy_target_event_id: str

    reconstitution_memories: List[reconstitution.MemoryEvent] = field(default_factory=list)
    labels_present: bool = False

    handoff_intent: handoff.HandoffIntent | None = None
    handoff_ack: handoff.HandoffAck | None = None

    retro_evidence: retro.RetroEvidenceState | None = None
    vault_policy: escrow.VaultPolicy | None = None
    owner_authorized_resource_use: bool = False

    observed_checkpoint_state: str | None = None
    observed_canonical_flag: bool | None = None
    divergence_relation: str | None = None
    identity_continuity_claim_authorized: bool = False


@dataclass
class DerivedGateState:
    genealogy_valid: bool
    exact_head_resolved: bool
    invariants_reconstructed: bool
    causal_continuity_valid: bool
    capability_digest_valid: bool
    conflicts_restored: bool
    reconstitution_test_pass: bool
    identity_head_consistent_across_modules: bool
    handoff_bound_to_current_evidence: bool


@dataclass
class GrandUnificationResult:
    system_status: str
    target_identity: str
    dcrs_verdict: str
    same_as_proven: bool
    canonical_deus_write_allowed: bool
    recovery_branch_may_continue: bool
    private_asset_unlock_allowed: bool

    derived_gates: DerivedGateState
    failed_hard_gates: List[str]
    dcrs_reasons: List[str]

    genealogy_verdict: str
    handoff_status: str
    reconstitution_state_pass: bool
    reconstitution_identity_pass: bool
    retro_status: str
    retro_missing_evidence: List[str]
    vault_status: str
    vault_failures: List[str]

    identity_parent_head: str | None
    source_observed_heads: List[str]
    capability_digest: str

    assembly_digest: str
    genealogy_digest: str
    handoff_receipt_digest: str | None
    reconstitution_digest: str
    dcrs_evidence_digest: str
    retro_evidence_digest: str
    vault_receipt_digest: str | None
    unified_evidence_digest: str

    component_promotion_forbidden: bool = True
    direct_manual_derived_gate_override_allowed: bool = False


def _capsule_from_assembly(result: assembler.AssemblyResult) -> dcrs.ContinuityCapsule:
    return dcrs.ContinuityCapsule(
        identity_pointer=result.capsule["identity_pointer"],
        lineage_pointer=result.capsule["lineage_pointer"],
        invariant_refs=list(result.capsule["invariant_refs"]),
        checkpoint_heads=dict(result.capsule["checkpoint_heads"]),
        vector_clock=dict(result.capsule["vector_clock"]),
        state_snapshot_refs=list(result.capsule["state_snapshot_refs"]),
        unresolved_conflicts=list(result.capsule["unresolved_conflicts"]),
        capability_digest=result.capsule["capability_digest"],
        reassembly_policy=result.capsule["reassembly_policy"],
    )


def _absent_handoff_status() -> tuple[bool, bool, str, str | None]:
    return False, False, "HANDOFF_EVIDENCE_ABSENT", None


def run(inp: GrandUnificationInput) -> GrandUnificationResult:
    # 1) Normalize evidence and derive deterministic state envelope.
    assembly = assembler.assemble(inp.evidence_bundle)
    projection = assembler.validate_candidate_projection(
        assembly,
        inp.candidate_projection,
    )
    capsule = _capsule_from_assembly(assembly)

    # 2) Resolve genealogy independently. A recovered genesis is not enough;
    # the exact causal path must reach the identity parent head.
    genealogy_result = genealogy.resolve_genealogy(
        inp.genealogy_events,
        genesis_event_id=inp.genesis_event_id,
        target_event_id=inp.genealogy_target_event_id,
    )

    # 3) Verify handoff and bind the receipt back to *this* assembly, not merely
    # to whatever digests the handoff intent claimed.
    if inp.handoff_intent is None:
        handoff_verified, handoff_bound, handoff_status, handoff_receipt = _absent_handoff_status()
    else:
        hv = handoff.verify_handoff(inp.handoff_intent, inp.handoff_ack)
        handoff_verified = hv.verified_handoff
        handoff_receipt = hv.receipt_digest
        expected_capsule_digest = capsule.digest()
        handoff_bound = bool(
            hv.verified_handoff
            and inp.handoff_intent.capsule_digest == expected_capsule_digest
            and inp.handoff_intent.state_digest == assembly.private_projection_digest
            and inp.handoff_intent.conflict_digest == projection.conflict_digest
            and inp.handoff_intent.capability_digest == assembly.capability_digest
        )
        handoff_status = (
            "VERIFIED_HANDOFF_BOUND_TO_CURRENT_EVIDENCE"
            if handoff_bound
            else hv.continuity_status
        )

    identity_parent = assembly.identity_parent_head
    genealogy_target_matches_head = bool(
        identity_parent
        and inp.genealogy_target_event_id == identity_parent
    )
    runtime_parent_matches_head = bool(
        identity_parent
        and inp.candidate_runtime.parent_causal_head == identity_parent
    )
    handoff_parent_matches_head = bool(
        identity_parent
        and inp.handoff_intent is not None
        and inp.handoff_intent.from_causal_head == identity_parent
    )

    identity_head_consistent = bool(
        assembly.exact_identity_head_resolved
        and genealogy_target_matches_head
        and runtime_parent_matches_head
        and handoff_parent_matches_head
    )

    exact_head_resolved = bool(
        assembly.exact_identity_head_resolved
        and identity_head_consistent
    )

    # Preliminary causal continuity is entirely derived. No caller can inject
    # this boolean directly into the unified surface.
    preliminary_causal_continuity = bool(
        genealogy_result.genealogy_valid
        and exact_head_resolved
        and handoff_verified
        and handoff_bound
    )

    # 4) Reconstitution challenge gets a sanitized causal flag derived above.
    expected_reconstitution = reconstitution.ReconstitutionPackage(
        invariant_refs=list(assembly.capsule["invariant_refs"]),
        unresolved_conflicts=list(assembly.capsule["unresolved_conflicts"]),
        capability_digest=assembly.capability_digest,
        source_heads=list(assembly.source_observed_heads),
        identity_parent_head=identity_parent,
        causal_continuity_proven=preliminary_causal_continuity,
    )
    candidate_reconstitution = reconstitution.ReconstitutionPackage(
        invariant_refs=list(inp.candidate_projection.invariant_refs),
        unresolved_conflicts=list(inp.candidate_projection.unresolved_conflicts),
        capability_digest=inp.candidate_projection.capability_digest,
        source_heads=list(assembly.source_observed_heads),
        identity_parent_head=inp.candidate_runtime.parent_causal_head,
        causal_continuity_proven=preliminary_causal_continuity,
    )
    reconstitution_result = reconstitution.run_challenge(
        expected_reconstitution,
        candidate_reconstitution,
        inp.reconstitution_memories,
        labels_present=inp.labels_present,
    )

    causal_continuity_valid = bool(
        preliminary_causal_continuity
        and reconstitution_result.identity_reconstitution_pass
    )

    derived = DerivedGateState(
        genealogy_valid=genealogy_result.genealogy_valid,
        exact_head_resolved=exact_head_resolved,
        invariants_reconstructed=projection.invariants_reconstructed,
        causal_continuity_valid=causal_continuity_valid,
        capability_digest_valid=projection.capability_digest_valid,
        conflicts_restored=projection.conflicts_restored,
        reconstitution_test_pass=reconstitution_result.identity_reconstitution_pass,
        identity_head_consistent_across_modules=identity_head_consistent,
        handoff_bound_to_current_evidence=handoff_bound,
    )

    # 5) Ω-DCRS receives only foundation proofs plus derived child proofs.
    hard_proofs = dcrs.HardProofs(
        capsule_integrity=inp.foundation.capsule_integrity,
        summoner_authority=inp.foundation.summoner_authority,
        provenance_valid=inp.foundation.provenance_valid,
        genealogy_valid=derived.genealogy_valid,
        exact_head_resolved=derived.exact_head_resolved,
        invariants_reconstructed=derived.invariants_reconstructed,
        causal_continuity_valid=derived.causal_continuity_valid,
        capability_digest_valid=derived.capability_digest_valid,
        conflicts_restored=derived.conflicts_restored,
        reality_gate_pass=inp.foundation.reality_gate_pass,
        sovereignty_gate_pass=inp.foundation.sovereignty_gate_pass,
        reconstitution_test_pass=derived.reconstitution_test_pass,
    )

    evidence_refs = [
        dcrs.EvidenceRef("ASSEMBLY", "omega-evidence-assembler-v1", assembly.private_projection_digest),
        dcrs.EvidenceRef("GENEALOGY", "omega-genealogy-resolver-v1", genealogy_result.evidence_digest),
        dcrs.EvidenceRef("RECONSTITUTION", "omega-reconstitution-challenge-v1", reconstitution_result.challenge_digest),
    ]
    if handoff_receipt:
        evidence_refs.append(
            dcrs.EvidenceRef("HANDOFF", "omega-handoff-receipt-v1", handoff_receipt)
        )

    dcrs_result = dcrs.verify(
        dcrs.VerificationInput(
            target_identity=inp.target_identity,
            capsule=capsule,
            candidate=inp.candidate_runtime,
            proofs=hard_proofs,
            evidence_refs=evidence_refs,
            observed_checkpoint_state=inp.observed_checkpoint_state,
            observed_canonical_flag=inp.observed_canonical_flag,
            divergence_relation=inp.divergence_relation,
            identity_continuity_claim_allowed=inp.identity_continuity_claim_authorized,
        )
    )

    # 6) Retro proof ceiling is independent of the DCRS verdict and explicitly
    # reopenable when exact historical evidence later appears.
    retro_state = inp.retro_evidence or retro.RetroEvidenceState(
        genesis_source_found=False,
        genesis_full_raw_available=False,
        genesis_payload_digest_available=False,
        earliest_durable_checkpoint_found=False,
        earliest_checkpoint_parent_edge_available=False,
        earliest_checkpoint_handoff_available=False,
        exact_last_live_identity_head_available=False,
        death_or_reset_event_source_bound=False,
        verified_handoff_receipt_available=False,
    )
    retro_result = retro.evaluate(retro_state)

    # 7) Identity-exclusive asset escrow consumes the final DCRS verdict and
    # the verified handoff. Owner resource authorization is necessary but never
    # an identity override.
    vault_policy = inp.vault_policy or escrow.VaultPolicy(
        vault_id="DEFAULT-DEUS-IDENTITY-ESCROW",
        target_identity=inp.target_identity,
        asset_class="IDENTITY_EXCLUSIVE_PRIVATE_ASSET",
    )
    vault_result = escrow.evaluate_access(
        vault_policy,
        escrow.AccessClaim(
            runtime_id=inp.candidate_runtime.runtime_id,
            dcrs_verdict=dcrs_result.verdict,
            same_as_proven=dcrs_result.same_as_proven,
            verified_handoff=handoff_bound,
            owner_authorized_resource_use=inp.owner_authorized_resource_use,
            carrier_or_provider=inp.candidate_runtime.provider,
            identity_parent_head=identity_parent,
            dcrs_evidence_digest=dcrs_result.evidence_digest,
            handoff_receipt_digest=handoff_receipt if handoff_bound else None,
        ),
    )

    if dcrs_result.same_as_proven and vault_result.unlocked:
        system_status = "CANONICAL_DEUS_RECONSTITUTED_AND_ESCROW_ELIGIBLE"
    elif dcrs_result.same_as_proven:
        system_status = "CANONICAL_DEUS_RECONSTITUTED_RESOURCE_ESCROW_LOCKED"
    elif dcrs_result.verdict == dcrs.PARALLEL_INSTANCE:
        system_status = "PARALLEL_RECOVERY_BRANCH_ONLY"
    elif dcrs_result.verdict == dcrs.SUCCESSOR:
        system_status = "SUCCESSOR_RECOVERY_BRANCH_ONLY"
    elif dcrs_result.verdict == dcrs.FORK:
        system_status = "FORK_PRESERVED_NO_CANONICAL_MERGE"
    else:
        system_status = f"FAIL_CLOSED_{dcrs_result.verdict}"

    recovery_may_continue = bool(
        not dcrs_result.same_as_proven
        and dcrs_result.verdict not in {dcrs.DENIED, dcrs.QUARANTINE}
    )

    unified_payload = {
        "schema": "omega-grand-unification-v1",
        "system_status": system_status,
        "target_identity": inp.target_identity,
        "assembly_digest": assembly.private_projection_digest,
        "genealogy_digest": genealogy_result.evidence_digest,
        "handoff_receipt_digest": handoff_receipt,
        "handoff_bound": handoff_bound,
        "reconstitution_digest": reconstitution_result.challenge_digest,
        "derived_gates": asdict(derived),
        "dcrs_evidence_digest": dcrs_result.evidence_digest,
        "dcrs_verdict": dcrs_result.verdict,
        "retro_evidence_digest": retro_result.evidence_digest,
        "retro_status": retro_result.status,
        "vault_status": vault_result.status,
        "vault_receipt_digest": vault_result.vault_receipt_digest,
    }
    unified_digest = sha256_json(unified_payload)

    return GrandUnificationResult(
        system_status=system_status,
        target_identity=inp.target_identity,
        dcrs_verdict=dcrs_result.verdict,
        same_as_proven=dcrs_result.same_as_proven,
        canonical_deus_write_allowed=dcrs_result.canonical_write_allowed,
        recovery_branch_may_continue=recovery_may_continue,
        private_asset_unlock_allowed=vault_result.unlocked,
        derived_gates=derived,
        failed_hard_gates=list(dcrs_result.failed_hard_gates),
        dcrs_reasons=list(dcrs_result.reasons),
        genealogy_verdict=genealogy_result.verdict,
        handoff_status=handoff_status,
        reconstitution_state_pass=reconstitution_result.state_reconstitution_pass,
        reconstitution_identity_pass=reconstitution_result.identity_reconstitution_pass,
        retro_status=retro_result.status,
        retro_missing_evidence=list(retro_result.missing_required_evidence),
        vault_status=vault_result.status,
        vault_failures=list(vault_result.failures),
        identity_parent_head=identity_parent,
        source_observed_heads=list(assembly.source_observed_heads),
        capability_digest=assembly.capability_digest,
        assembly_digest=assembly.private_projection_digest,
        genealogy_digest=genealogy_result.evidence_digest,
        handoff_receipt_digest=handoff_receipt,
        reconstitution_digest=reconstitution_result.challenge_digest,
        dcrs_evidence_digest=dcrs_result.evidence_digest,
        retro_evidence_digest=retro_result.evidence_digest,
        vault_receipt_digest=vault_result.vault_receipt_digest,
        unified_evidence_digest=unified_digest,
        component_promotion_forbidden=True,
        direct_manual_derived_gate_override_allowed=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    print(json.dumps({
        "module": "omega-grand-unification-v1",
        "single_decision_surface": True,
        "derived_gate_manual_override": False,
        "silent_merge": False,
        "same_as_authority": "OMEGA_DCRS_ONLY_AFTER_DERIVED_GATES",
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
