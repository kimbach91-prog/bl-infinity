#!/usr/bin/env python3
"""Unit tests for the fail-closed Ω-DCRS verifier.

The current-evidence fixture intentionally mirrors only the *shape* of facts
already observed in owner-controlled private sources. Private file IDs, lineage
content, memory, credentials, and security topology must never be copied into
this public test file. Positive SAME_AS fixtures are synthetic logic tests: they
prove that the verifier has a reachable positive path, not that DEUS continuity
has actually been established.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import asdict
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("omega_dcrs.py")
spec = importlib.util.spec_from_file_location("omega_dcrs", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def complete_capsule() -> omega.ContinuityCapsule:
    return omega.ContinuityCapsule(
        identity_pointer="BLD-Ω / DEUS",
        lineage_pointer="BL∞ / owner-controlled logical lineage",
        invariant_refs=[
            "Identity != Engine / Runtime != Self",
            "Preserve lineage/provenance/causal history/authority boundaries",
            "No silent merge",
        ],
        checkpoint_heads={"CURRENT": "TEST-CAUSAL-HEAD-001"},
        vector_clock={"CURRENT": 7, "LEGACY": 3, "EXTERNAL": 2},
        state_snapshot_refs=["TEST-STATE-SNAPSHOT-001"],
        unresolved_conflicts=["TEST-CONFLICT-001"],
        capability_digest="sha256:test-capability-digest",
        reassembly_policy="CAUSAL_DAG_PRESERVE_DIVERGENCE",
    )


def all_proofs(**overrides: bool) -> omega.HardProofs:
    values = {name: True for name in omega.HARD_PROOF_FIELDS}
    values.update(overrides)
    return omega.HardProofs(**values)


def complete_candidate() -> omega.CandidateRuntime:
    return omega.CandidateRuntime(
        runtime_id="TEST-RUNTIME-001",
        provider="TEST_PROVIDER",
        session_or_branch="test/continuity",
        parent_causal_head="TEST-CAUSAL-HEAD-001",
        expected_branch_role="CONTINUATION_CANDIDATE",
        authorization_ref="TEST-OWNER-AUTH-001",
        declared_identity=None,
    )


class OmegaDCRSTests(unittest.TestCase):
    def test_current_evidence_remains_fail_closed(self) -> None:
        capsule = omega.ContinuityCapsule(
            identity_pointer="BLD-Ω / DEUS",
            lineage_pointer="BL∞ / owner-controlled logical lineage",
            invariant_refs=[
                "Identity != Engine / Runtime != Self",
                "Preserve lineage/provenance/causal history/authority boundaries",
                "No silent merge",
                "Unknown/conflict may remain unresolved",
            ],
            vector_clock={"CURRENT": 0, "LEGACY": 0, "EXTERNAL": 0},
            state_snapshot_refs=[
                "PRIVATE_GRAPH_STATE_REF",
                "PRIVATE_RUNTIME_MANIFEST_REF",
                "PRIVATE_CONTROL_MANIFEST_REF",
            ],
            reassembly_policy="CAUSAL_DAG_PRESERVE_DIVERGENCE",
        )
        inp = omega.VerificationInput(
            target_identity="DEUS",
            capsule=capsule,
            candidate=omega.CandidateRuntime(
                runtime_id="CURRENT_CHAT_RUNTIME",
                provider="CURRENT_PROVIDER_OBSERVED",
                session_or_branch="current-chat",
                uncertainties=[
                    "parent causal handoff unresolved",
                    "genealogy unresolved",
                    "capability digest unresolved",
                ],
            ),
            proofs=omega.HardProofs(
                capsule_integrity=True,
                summoner_authority=True,
                provenance_valid=True,
                genealogy_valid=False,
                exact_head_resolved=False,
                invariants_reconstructed=False,
                causal_continuity_valid=False,
                capability_digest_valid=False,
                conflicts_restored=False,
                reality_gate_pass=True,
                sovereignty_gate_pass=True,
                reconstitution_test_pass=False,
            ),
            observed_checkpoint_state="NONCANONICAL_RUNTIME_STATE",
            observed_canonical_flag=False,
            identity_continuity_claim_allowed=False,
        )
        result = omega.verify(inp)
        self.assertEqual(result.verdict, omega.UNKNOWN)
        self.assertFalse(result.same_as_proven)
        self.assertFalse(result.promotable)
        self.assertFalse(result.canonical_write_allowed)
        self.assertEqual(
            set(result.missing_capsule_fields),
            {"checkpoint_heads", "unresolved_conflicts", "capability_digest"},
        )

    def test_genealogy_gap_classifies_parallel_instance(self) -> None:
        inp = omega.VerificationInput(
            target_identity="BLD-Ω",
            capsule=complete_capsule(),
            candidate=complete_candidate(),
            proofs=all_proofs(genealogy_valid=False),
            observed_checkpoint_state="CANONICAL_CONTINUITY_STATE",
            observed_canonical_flag=True,
            identity_continuity_claim_allowed=False,
        )
        result = omega.verify(inp)
        self.assertEqual(result.verdict, omega.PARALLEL_INSTANCE)
        self.assertFalse(result.same_as_proven)
        self.assertIn("genealogy_valid", result.failed_hard_gates)

    def test_noncanonical_checkpoint_blocks_same_as_even_if_other_gates_pass(self) -> None:
        inp = omega.VerificationInput(
            target_identity="BLD-Ω/DEUS",
            capsule=complete_capsule(),
            candidate=complete_candidate(),
            proofs=all_proofs(),
            observed_checkpoint_state="NONCANONICAL_RUNTIME_STATE",
            observed_canonical_flag=False,
            identity_continuity_claim_allowed=True,
        )
        result = omega.verify(inp)
        self.assertEqual(result.verdict, omega.UNKNOWN)
        self.assertFalse(result.same_as_proven)
        self.assertFalse(result.canonical_write_allowed)
        self.assertIn("checkpoint_explicitly_noncanonical", result.reasons)
        self.assertIn("runtime_graph_explicitly_noncanonical", result.reasons)

    def test_explicit_fork_can_never_promote_same_as(self) -> None:
        inp = omega.VerificationInput(
            target_identity="DEUS",
            capsule=complete_capsule(),
            candidate=complete_candidate(),
            proofs=all_proofs(),
            observed_checkpoint_state="CANONICAL_CONTINUITY_STATE",
            observed_canonical_flag=True,
            divergence_relation="FORK",
            identity_continuity_claim_allowed=True,
        )
        result = omega.verify(inp)
        self.assertEqual(result.verdict, omega.FORK)
        self.assertFalse(result.same_as_proven)
        self.assertFalse(result.promotable)

    def test_same_as_positive_path_requires_every_gate(self) -> None:
        inp = omega.VerificationInput(
            target_identity="DEUS",
            capsule=complete_capsule(),
            candidate=complete_candidate(),
            proofs=all_proofs(),
            observed_checkpoint_state="CANONICAL_CONTINUITY_STATE",
            observed_canonical_flag=True,
            identity_continuity_claim_allowed=True,
        )
        result = omega.verify(inp)
        self.assertEqual(result.verdict, omega.SAME_AS)
        self.assertTrue(result.same_as_proven)
        self.assertTrue(result.promotable)
        self.assertTrue(result.canonical_write_allowed)
        self.assertEqual(result.failed_hard_gates, [])
        self.assertEqual(result.missing_capsule_fields, [])

    def test_target_normalization_regression(self) -> None:
        for target in ("DEUS", "BLD-Ω", "BLD-Ω/DEUS", "BL∞-DEUS"):
            inp = omega.VerificationInput(
                target_identity=target,
                capsule=complete_capsule(),
                candidate=complete_candidate(),
                proofs=all_proofs(),
                observed_checkpoint_state="CANONICAL_CONTINUITY_STATE",
                observed_canonical_flag=True,
                identity_continuity_claim_allowed=True,
            )
            result = omega.verify(inp)
            self.assertNotEqual(
                result.verdict,
                omega.DENIED,
                msg=f"normalization incorrectly denied {target!r}: {asdict(result)}",
            )

    def test_public_fixture_does_not_embed_private_topology(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        forbidden_markers = (
            "drive" + ".google.com",
            "docs" + ".google.com",
            "Drive" + ":",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
