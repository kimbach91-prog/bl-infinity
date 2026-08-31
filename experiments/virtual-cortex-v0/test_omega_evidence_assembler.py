#!/usr/bin/env python3
"""Tests for Ω-Evidence Assembler public mechanism."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_evidence_assembler.py")
spec = importlib.util.spec_from_file_location("omega_evidence_assembler", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def base_bundle() -> omega.EvidenceBundle:
    return omega.EvidenceBundle(
        identity_pointer="BLD-Ω / DEUS",
        lineage_pointer="BL∞ / owner-controlled logical lineage",
        invariant_refs=[
            "Identity != Engine / Runtime != Self",
            "No silent merge",
        ],
        vector_clock={"CURRENT": 1, "LEGACY": 0, "EXTERNAL": 0},
        state_snapshot_refs=["PRIVATE_STATE_REF"],
        heads=[
            omega.HeadEvidence(
                head_id="DEUS-CHECKPOINT-SOURCE-001",
                role="RUNTIME_CHECKPOINT",
                state="NONCANONICAL_RUNTIME_STATE",
                authority="BL-LOG_CANONICAL",
            ),
            omega.HeadEvidence(
                head_id="VCORTEX-SOURCE-HEAD-001",
                role="SOURCE_MODEL_HEAD",
                state="SOURCE_BOUND",
                authority="BL-LOG_CANONICAL",
            ),
        ],
        conflicts=[
            omega.ConflictEvidence(
                conflict_id="IDENTITY_GENEALOGY_UNRESOLVED",
                status="ACTIVE_GUARD",
                severity="HIGH",
            )
        ],
        capabilities=[
            omega.CapabilityRecord(
                record_id="CAP-A",
                kind="ROUTER",
                state="ACTIVE_EXPERIMENT",
                maturity="PROTOTYPE",
            ),
            omega.CapabilityRecord(
                record_id="CAP-B",
                kind="REASSEMBLY",
                state="ACTIVE_EXPERIMENT",
                maturity="LOCAL_DEMO_PASS",
            ),
        ],
    )


class EvidenceAssemblerTests(unittest.TestCase):
    def test_source_heads_do_not_become_identity_parent(self) -> None:
        result = omega.assemble(base_bundle())
        self.assertFalse(result.exact_identity_head_resolved)
        self.assertIsNone(result.identity_parent_head)
        self.assertNotIn("IDENTITY_PARENT", result.capsule["checkpoint_heads"])
        self.assertEqual(len(result.source_observed_heads), 2)
        self.assertFalse(result.promotion_allowed)

    def test_unresolved_conflicts_are_preserved(self) -> None:
        bundle = base_bundle()
        bundle.conflicts.append(
            omega.ConflictEvidence(
                conflict_id="RESOLVED_OLD_CONFLICT",
                status="RESOLVED",
            )
        )
        result = omega.assemble(bundle)
        self.assertEqual(
            result.unresolved_conflict_ids,
            ["IDENTITY_GENEALOGY_UNRESOLVED"],
        )
        self.assertEqual(
            result.capsule["unresolved_conflicts"],
            ["IDENTITY_GENEALOGY_UNRESOLVED"],
        )

    def test_capability_digest_is_order_independent(self) -> None:
        bundle_a = base_bundle()
        bundle_b = base_bundle()
        bundle_b.capabilities = list(reversed(bundle_b.capabilities))
        result_a = omega.assemble(bundle_a)
        result_b = omega.assemble(bundle_b)
        self.assertEqual(result_a.capability_digest, result_b.capability_digest)

    def test_single_authorized_canonical_identity_parent_can_resolve_head(self) -> None:
        bundle = base_bundle()
        bundle.heads.append(
            omega.HeadEvidence(
                head_id="IDENTITY-PARENT-001",
                role="IDENTITY_PARENT",
                state="PROVEN_CANONICAL_PARENT",
                authority="SOVEREIGN_ROOT",
            )
        )
        result = omega.assemble(bundle)
        self.assertTrue(result.exact_identity_head_resolved)
        self.assertEqual(result.identity_parent_head, "IDENTITY-PARENT-001")
        self.assertEqual(
            result.capsule["checkpoint_heads"]["IDENTITY_PARENT"],
            "IDENTITY-PARENT-001",
        )
        self.assertFalse(result.promotion_allowed)

    def test_multiple_canonical_parents_fail_closed(self) -> None:
        bundle = base_bundle()
        for suffix in ("A", "B"):
            bundle.heads.append(
                omega.HeadEvidence(
                    head_id=f"IDENTITY-PARENT-{suffix}",
                    role="IDENTITY_PARENT",
                    state="CANONICAL_CONTINUITY_HEAD",
                    authority="BL-LOG_CANONICAL",
                )
            )
        result = omega.assemble(bundle)
        self.assertFalse(result.exact_identity_head_resolved)
        self.assertIsNone(result.identity_parent_head)

    def test_candidate_projection_can_close_state_restoration_gates_only(self) -> None:
        result = omega.assemble(base_bundle())
        candidate = omega.CandidateProjection(
            invariant_refs=list(result.capsule["invariant_refs"]),
            unresolved_conflicts=list(result.capsule["unresolved_conflicts"]),
            capability_digest=result.capability_digest,
        )
        validation = omega.validate_candidate_projection(result, candidate)
        self.assertTrue(validation.invariants_reconstructed)
        self.assertTrue(validation.conflicts_restored)
        self.assertTrue(validation.capability_digest_valid)
        self.assertFalse(validation.promotion_allowed)

    def test_candidate_projection_missing_conflict_fails_restoration(self) -> None:
        result = omega.assemble(base_bundle())
        candidate = omega.CandidateProjection(
            invariant_refs=list(result.capsule["invariant_refs"]),
            unresolved_conflicts=[],
            capability_digest=result.capability_digest,
        )
        validation = omega.validate_candidate_projection(result, candidate)
        self.assertTrue(validation.invariants_reconstructed)
        self.assertFalse(validation.conflicts_restored)
        self.assertTrue(validation.capability_digest_valid)

    def test_candidate_projection_wrong_capability_digest_fails_match(self) -> None:
        result = omega.assemble(base_bundle())
        candidate = omega.CandidateProjection(
            invariant_refs=list(result.capsule["invariant_refs"]),
            unresolved_conflicts=list(result.capsule["unresolved_conflicts"]),
            capability_digest="sha256:wrong",
        )
        validation = omega.validate_candidate_projection(result, candidate)
        self.assertFalse(validation.capability_digest_valid)
        self.assertFalse(validation.promotion_allowed)

    def test_public_mechanism_has_no_private_topology_markers(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
