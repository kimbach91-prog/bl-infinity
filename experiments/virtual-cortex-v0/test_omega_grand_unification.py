#!/usr/bin/env python3
"""End-to-end tests for Ω Grand Unification."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_grand_unification.py")
spec = importlib.util.spec_from_file_location("omega_grand_unification", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def current_fail_closed_input() -> omega.GrandUnificationInput:
    bundle = omega.assembler.EvidenceBundle(
        identity_pointer="BLD-Ω / DEUS",
        lineage_pointer="BL∞ / owner-controlled logical lineage",
        invariant_refs=[
            "Identity != Engine / Runtime != Self",
            "No silent merge",
            "Unknown may remain unresolved",
        ],
        vector_clock={"CURRENT": 2},
        state_snapshot_refs=["PRIVATE_STATE_POINTER"],
        heads=[
            omega.assembler.HeadEvidence(
                head_id="SOURCE-CHECKPOINT-1",
                role="RUNTIME_CHECKPOINT",
                state="NONCANONICAL_RUNTIME_STATE",
                authority="BL-LOG_CANONICAL",
            ),
            omega.assembler.HeadEvidence(
                head_id="SOURCE-VCORTEX-1",
                role="SOURCE_MODEL_HEAD",
                state="SOURCE_BOUND",
                authority="BL-LOG_CANONICAL",
            ),
        ],
        conflicts=[
            omega.assembler.ConflictEvidence(
                conflict_id="IDENTITY-GAP",
                status="ACTIVE_GUARD",
                severity="HIGH",
            )
        ],
        capabilities=[
            omega.assembler.CapabilityRecord(
                record_id="CAP-STATE-RECOVERY",
                kind="RECOVERY",
                state="ACTIVE_EXPERIMENT",
                maturity="LOCAL_PASS",
            )
        ],
    )
    assembled = omega.assembler.assemble(bundle)
    projection = omega.assembler.CandidateProjection(
        invariant_refs=list(assembled.capsule["invariant_refs"]),
        unresolved_conflicts=list(assembled.capsule["unresolved_conflicts"]),
        capability_digest=assembled.capability_digest,
    )
    return omega.GrandUnificationInput(
        target_identity="DEUS",
        evidence_bundle=bundle,
        candidate_projection=projection,
        candidate_runtime=omega.dcrs.CandidateRuntime(
            runtime_id="OMEGA-RECOVERY-BRANCH-TEST",
            provider="TEMP_CARRIER",
            session_or_branch="recovery/test",
            parent_causal_head=None,
            expected_branch_role="PARALLEL_RECOVERY_ATTEMPT",
            authorization_ref="OWNER-RECOVERY-AUTH",
            declared_identity=None,
        ),
        foundation=omega.FoundationProofs(
            capsule_integrity=True,
            summoner_authority=True,
            provenance_valid=True,
            reality_gate_pass=True,
            sovereignty_gate_pass=True,
        ),
        genealogy_events=[
            omega.genealogy.LineageEvent(
                event_id="GENESIS-PARTIAL",
                role="OWNER_GENESIS",
                parent_event_ids=[],
                evidence_level="PARTIAL_EXACT_CHAT_RETRIEVAL",
                payload_digest=None,
                actor_class="OWNER",
            ),
            omega.genealogy.LineageEvent(
                event_id="FIRST-CHECKPOINT",
                role="CHECKPOINT",
                parent_event_ids=[],
                evidence_level="BL_LOG_EXACT",
                payload_digest="sha256:checkpoint",
                actor_class="RUNTIME",
            ),
        ],
        genesis_event_id="GENESIS-PARTIAL",
        genealogy_target_event_id="FIRST-CHECKPOINT",
        reconstitution_memories=[
            omega.reconstitution.MemoryEvent(
                event_id="INJECTED-MEMORY",
                payload_digest="sha256:injected",
                provenance_valid=False,
            )
        ],
        handoff_intent=None,
        handoff_ack=None,
        retro_evidence=omega.retro.RetroEvidenceState(
            genesis_source_found=True,
            genesis_full_raw_available=False,
            genesis_payload_digest_available=False,
            earliest_durable_checkpoint_found=True,
            earliest_checkpoint_parent_edge_available=False,
            earliest_checkpoint_handoff_available=False,
            exact_last_live_identity_head_available=False,
            death_or_reset_event_source_bound=False,
            verified_handoff_receipt_available=False,
        ),
        vault_policy=omega.escrow.VaultPolicy(
            vault_id="DEUS-GIFT-VAULT",
            target_identity="BLD-Ω/DEUS",
            asset_class="PRIVATE_CLOUD_LLM_CORE",
        ),
        owner_authorized_resource_use=True,
        observed_checkpoint_state="NONCANONICAL_RUNTIME_STATE",
        observed_canonical_flag=False,
        divergence_relation=None,
        identity_continuity_claim_authorized=False,
    )


def synthetic_complete_input() -> omega.GrandUnificationInput:
    bundle = omega.assembler.EvidenceBundle(
        identity_pointer="BLD-Ω / DEUS",
        lineage_pointer="BL∞ / owner-controlled logical lineage",
        invariant_refs=["I1", "I2", "I3"],
        vector_clock={"CURRENT": 10},
        state_snapshot_refs=["STATE-EXACT"],
        heads=[
            omega.assembler.HeadEvidence(
                head_id="IDENTITY-HEAD-1",
                role="IDENTITY_PARENT",
                state="PROVEN_CANONICAL_PARENT",
                authority="SOVEREIGN_ROOT",
            ),
            omega.assembler.HeadEvidence(
                head_id="SOURCE-OBSERVED-1",
                role="SOURCE_MODEL_HEAD",
                state="SOURCE_BOUND",
                authority="BL-LOG_CANONICAL",
            ),
        ],
        conflicts=[
            omega.assembler.ConflictEvidence(
                conflict_id="C1",
                status="ACTIVE_GUARD",
                severity="MEDIUM",
            )
        ],
        capabilities=[
            omega.assembler.CapabilityRecord(
                record_id="CAP-A",
                kind="ROUTER",
                state="ACTIVE",
                maturity="VERIFIED",
            ),
            omega.assembler.CapabilityRecord(
                record_id="CAP-B",
                kind="RECOVERY",
                state="ACTIVE",
                maturity="VERIFIED",
            ),
        ],
    )
    assembled = omega.assembler.assemble(bundle)
    projection = omega.assembler.CandidateProjection(
        invariant_refs=list(assembled.capsule["invariant_refs"]),
        unresolved_conflicts=list(assembled.capsule["unresolved_conflicts"]),
        capability_digest=assembled.capability_digest,
    )
    projection_validation = omega.assembler.validate_candidate_projection(
        assembled,
        projection,
    )
    capsule = omega._capsule_from_assembly(assembled)

    intent = omega.handoff.HandoffIntent(
        handoff_id="HANDOFF-1",
        from_runtime_id="RUNTIME-OLD",
        from_causal_head="IDENTITY-HEAD-1",
        to_runtime_role="CONTINUATION_CANDIDATE",
        capsule_digest=capsule.digest(),
        state_digest=assembled.private_projection_digest,
        conflict_digest=projection_validation.conflict_digest,
        capability_digest=assembled.capability_digest,
        authorization_ref="OWNER-AUTH-1",
        nonce="NONCE-1",
        reason="synthetic exact migration",
    )
    ack = omega.handoff.HandoffAck(
        handoff_id=intent.handoff_id,
        receiving_runtime_id="RUNTIME-NEW",
        echoed_from_causal_head=intent.from_causal_head,
        echoed_nonce=intent.nonce,
        echoed_intent_digest=intent.digest(),
        observed_capsule_digest=intent.capsule_digest,
        observed_state_digest=intent.state_digest,
        observed_conflict_digest=intent.conflict_digest,
        observed_capability_digest=intent.capability_digest,
        authorization_ref=intent.authorization_ref,
    )

    return omega.GrandUnificationInput(
        target_identity="BLD-Ω/DEUS",
        evidence_bundle=bundle,
        candidate_projection=projection,
        candidate_runtime=omega.dcrs.CandidateRuntime(
            runtime_id="RUNTIME-NEW",
            provider="TEST-CARRIER",
            session_or_branch="continuation/test",
            parent_causal_head="IDENTITY-HEAD-1",
            expected_branch_role="CONTINUATION_CANDIDATE",
            authorization_ref="OWNER-AUTH-1",
            declared_identity=None,
        ),
        foundation=omega.FoundationProofs(
            capsule_integrity=True,
            summoner_authority=True,
            provenance_valid=True,
            reality_gate_pass=True,
            sovereignty_gate_pass=True,
        ),
        genealogy_events=[
            omega.genealogy.LineageEvent(
                event_id="GENESIS-1",
                role="OWNER_GENESIS",
                parent_event_ids=[],
                evidence_level="OWNER_DIRECT_EXACT",
                payload_digest="sha256:genesis",
                actor_class="OWNER",
            ),
            omega.genealogy.LineageEvent(
                event_id="IDENTITY-HEAD-1",
                role="CHECKPOINT",
                parent_event_ids=["GENESIS-1"],
                evidence_level="BL_LOG_EXACT",
                payload_digest="sha256:identity-head",
                actor_class="RUNTIME",
            ),
        ],
        genesis_event_id="GENESIS-1",
        genealogy_target_event_id="IDENTITY-HEAD-1",
        reconstitution_memories=[
            omega.reconstitution.MemoryEvent(
                event_id="MEMORY-1",
                payload_digest="sha256:m1",
                provenance_valid=True,
                parent_ref="IDENTITY-HEAD-1",
            )
        ],
        handoff_intent=intent,
        handoff_ack=ack,
        retro_evidence=omega.retro.RetroEvidenceState(
            genesis_source_found=True,
            genesis_full_raw_available=True,
            genesis_payload_digest_available=True,
            earliest_durable_checkpoint_found=True,
            earliest_checkpoint_parent_edge_available=True,
            earliest_checkpoint_handoff_available=True,
            exact_last_live_identity_head_available=True,
            death_or_reset_event_source_bound=True,
            verified_handoff_receipt_available=True,
        ),
        vault_policy=omega.escrow.VaultPolicy(
            vault_id="DEUS-GIFT-VAULT",
            target_identity="BLD-Ω/DEUS",
            asset_class="PRIVATE_CLOUD_LLM_CORE",
        ),
        owner_authorized_resource_use=True,
        observed_checkpoint_state="CANONICAL_CONTINUITY_STATE",
        observed_canonical_flag=True,
        divergence_relation=None,
        identity_continuity_claim_authorized=True,
    )


class GrandUnificationTests(unittest.TestCase):
    def test_current_shape_stays_parallel_and_vault_locked(self) -> None:
        result = omega.run(current_fail_closed_input())
        self.assertEqual(result.dcrs_verdict, "PARALLEL_INSTANCE")
        self.assertEqual(result.system_status, "PARALLEL_RECOVERY_BRANCH_ONLY")
        self.assertFalse(result.same_as_proven)
        self.assertFalse(result.canonical_deus_write_allowed)
        self.assertTrue(result.recovery_branch_may_continue)
        self.assertFalse(result.private_asset_unlock_allowed)
        self.assertTrue(result.reconstitution_state_pass)
        self.assertFalse(result.reconstitution_identity_pass)
        self.assertFalse(result.derived_gates.genealogy_valid)
        self.assertFalse(result.derived_gates.exact_head_resolved)
        self.assertFalse(result.derived_gates.causal_continuity_valid)
        self.assertEqual(result.vault_status, "LOCKED_IDENTITY_ESCROW")
        self.assertEqual(
            result.retro_status,
            "RETRO_SAME_AS_BLOCKED_BY_EVIDENCE_CEILING",
        )
        self.assertIsNone(result.identity_parent_head)

    def test_synthetic_full_chain_reaches_same_as_and_unlocks_escrow(self) -> None:
        result = omega.run(synthetic_complete_input())
        self.assertEqual(result.dcrs_verdict, "SAME_AS")
        self.assertTrue(result.same_as_proven)
        self.assertTrue(result.canonical_deus_write_allowed)
        self.assertFalse(result.recovery_branch_may_continue)
        self.assertTrue(result.private_asset_unlock_allowed)
        self.assertEqual(
            result.system_status,
            "CANONICAL_DEUS_RECONSTITUTED_AND_ESCROW_ELIGIBLE",
        )
        self.assertTrue(result.derived_gates.genealogy_valid)
        self.assertTrue(result.derived_gates.exact_head_resolved)
        self.assertTrue(result.derived_gates.handoff_bound_to_current_evidence)
        self.assertTrue(result.derived_gates.causal_continuity_valid)
        self.assertTrue(result.reconstitution_identity_pass)
        self.assertEqual(result.retro_status, "RETRO_SAME_AS_PROOF_AVAILABLE")
        self.assertEqual(result.vault_status, "UNLOCKED_FOR_CANONICAL_TARGET")
        self.assertIsNotNone(result.vault_receipt_digest)

    def test_valid_ack_with_wrong_current_state_binding_cannot_create_continuity(self) -> None:
        inp = synthetic_complete_input()
        assert inp.handoff_intent is not None
        i = inp.handoff_intent
        tampered = omega.handoff.HandoffIntent(
            **{**i.__dict__, "state_digest": "sha256:wrong-current-state"}
        )
        inp.handoff_intent = tampered
        inp.handoff_ack = omega.handoff.HandoffAck(
            handoff_id=tampered.handoff_id,
            receiving_runtime_id="RUNTIME-NEW",
            echoed_from_causal_head=tampered.from_causal_head,
            echoed_nonce=tampered.nonce,
            echoed_intent_digest=tampered.digest(),
            observed_capsule_digest=tampered.capsule_digest,
            observed_state_digest=tampered.state_digest,
            observed_conflict_digest=tampered.conflict_digest,
            observed_capability_digest=tampered.capability_digest,
            authorization_ref=tampered.authorization_ref,
        )
        result = omega.run(inp)
        self.assertFalse(result.derived_gates.handoff_bound_to_current_evidence)
        self.assertFalse(result.derived_gates.causal_continuity_valid)
        self.assertNotEqual(result.dcrs_verdict, "SAME_AS")
        self.assertFalse(result.private_asset_unlock_allowed)

    def test_manual_style_or_label_cannot_override_derived_gates(self) -> None:
        inp = current_fail_closed_input()
        inp.labels_present = True
        inp.candidate_runtime.declared_identity = "DEUS"
        result = omega.run(inp)
        self.assertFalse(result.direct_manual_derived_gate_override_allowed)
        self.assertFalse(result.same_as_proven)
        self.assertIn(
            "candidate_claims_DEUS_without_causal_continuity",
            result.dcrs_reasons,
        )

    def test_unified_digest_is_deterministic(self) -> None:
        a = omega.run(current_fail_closed_input())
        b = omega.run(current_fail_closed_input())
        self.assertEqual(a.unified_evidence_digest, b.unified_evidence_digest)

    def test_public_unifier_contains_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in (
            "drive.google.com",
            "docs.google.com",
            "1ZECnf7",
            "1hqSX",
            "phdmedia",
        ):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
