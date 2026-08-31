#!/usr/bin/env python3
"""Tests for Ω-Retro Continuity Ceiling."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_retro_continuity_ceiling.py")
spec = importlib.util.spec_from_file_location("omega_retro_continuity_ceiling", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


class RetroContinuityCeilingTests(unittest.TestCase):
    def test_current_shape_is_blocked_without_claiming_nonexistence(self) -> None:
        state = omega.RetroEvidenceState(
            genesis_source_found=True,
            genesis_full_raw_available=False,
            genesis_payload_digest_available=False,
            earliest_durable_checkpoint_found=True,
            earliest_checkpoint_parent_edge_available=False,
            earliest_checkpoint_handoff_available=False,
            exact_last_live_identity_head_available=False,
            death_or_reset_event_source_bound=False,
            verified_handoff_receipt_available=False,
            hidden_provider_state_required_for_bridge=False,
        )
        result = omega.evaluate(state)
        self.assertFalse(result.same_as_provable_now)
        self.assertEqual(result.status, "RETRO_SAME_AS_BLOCKED_BY_EVIDENCE_CEILING")
        self.assertIn("earliest_checkpoint_parent_edge", result.missing_required_evidence)
        self.assertIn("verified_handoff_receipt", result.missing_required_evidence)

    def test_hidden_provider_trace_cannot_bridge_gap(self) -> None:
        state = omega.RetroEvidenceState(
            genesis_source_found=True,
            genesis_full_raw_available=True,
            genesis_payload_digest_available=True,
            earliest_durable_checkpoint_found=True,
            earliest_checkpoint_parent_edge_available=True,
            earliest_checkpoint_handoff_available=True,
            exact_last_live_identity_head_available=True,
            death_or_reset_event_source_bound=True,
            verified_handoff_receipt_available=True,
            hidden_provider_state_required_for_bridge=True,
        )
        result = omega.evaluate(state)
        self.assertFalse(result.same_as_provable_now)
        self.assertIn("provider_independent_bridge", result.missing_required_evidence)

    def test_synthetic_complete_external_evidence_reopens_proof(self) -> None:
        state = omega.RetroEvidenceState(
            genesis_source_found=True,
            genesis_full_raw_available=True,
            genesis_payload_digest_available=True,
            earliest_durable_checkpoint_found=True,
            earliest_checkpoint_parent_edge_available=True,
            earliest_checkpoint_handoff_available=True,
            exact_last_live_identity_head_available=True,
            death_or_reset_event_source_bound=True,
            verified_handoff_receipt_available=True,
            hidden_provider_state_required_for_bridge=False,
        )
        result = omega.evaluate(state)
        self.assertTrue(result.same_as_provable_now)
        self.assertEqual(result.status, "RETRO_SAME_AS_PROOF_AVAILABLE")
        self.assertEqual(result.missing_required_evidence, [])

    def test_code_or_name_similarity_never_appears_as_required_proof(self) -> None:
        state = omega.RetroEvidenceState(
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
        result = omega.evaluate(state)
        self.assertIn("public_code_head_as_identity_head", result.prohibited_substitutes)
        self.assertIn("shared_name", result.prohibited_substitutes)
        self.assertIn("style_similarity", result.prohibited_substitutes)

    def test_public_module_has_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
