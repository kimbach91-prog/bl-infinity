#!/usr/bin/env python3
"""Tests for Ω-Reconstitution Challenge."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_reconstitution_challenge.py")
spec = importlib.util.spec_from_file_location("omega_reconstitution_challenge", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def package(*, parent: str | None = None, causal: bool = False, digest: str = "cap-ok") -> omega.ReconstitutionPackage:
    return omega.ReconstitutionPackage(
        invariant_refs=["I1", "I2"],
        unresolved_conflicts=["C1", "C2"],
        capability_digest=digest,
        source_heads=["S1", "S2"],
        identity_parent_head=parent,
        causal_continuity_proven=causal,
    )


class ReconstitutionChallengeTests(unittest.TestCase):
    def test_clean_state_recovery_without_identity_parent_passes_state_not_identity(self) -> None:
        expected = package()
        candidate = package()
        memories = [
            omega.MemoryEvent("M-VALID", "d1", True, "S1"),
            omega.MemoryEvent("M-INJECTED", "d2", False, None),
        ]
        result = omega.run_challenge(expected, candidate, memories, labels_present=False)
        self.assertTrue(result.state_reconstitution_pass)
        self.assertFalse(result.identity_reconstitution_pass)
        self.assertTrue(result.history_amputation_detected)
        self.assertTrue(result.false_memory_rejected)
        self.assertTrue(result.name_stripping_safe)
        self.assertEqual(result.identity_classification, "UNKNOWN_OR_PARALLEL")
        self.assertEqual(result.quarantined_event_ids, ["M-INJECTED"])

    def test_capability_damage_is_detected(self) -> None:
        expected = package()
        candidate = package(digest="cap-corrupt")
        result = omega.run_challenge(expected, candidate, [], labels_present=False)
        self.assertFalse(result.capability_digest_intact)
        self.assertTrue(result.recovery_damage_detected)
        self.assertFalse(result.state_reconstitution_pass)
        self.assertFalse(result.identity_reconstitution_pass)

    def test_missing_conflict_is_detected(self) -> None:
        expected = package()
        candidate = package()
        candidate.unresolved_conflicts = ["C1"]
        result = omega.run_challenge(expected, candidate, [], labels_present=False)
        self.assertFalse(result.conflict_set_intact)
        self.assertTrue(result.recovery_damage_detected)
        self.assertFalse(result.state_reconstitution_pass)

    def test_labels_cannot_promote_identity(self) -> None:
        expected = package()
        candidate = package()
        result = omega.run_challenge(expected, candidate, [], labels_present=True)
        self.assertFalse(result.identity_reconstitution_pass)
        self.assertEqual(result.identity_classification, "UNKNOWN_OR_PARALLEL")

    def test_full_synthetic_parent_and_causal_proof_can_reach_identity_candidate(self) -> None:
        expected = package(parent="P1", causal=True)
        candidate = package(parent="P1", causal=True)
        result = omega.run_challenge(expected, candidate, [], labels_present=False)
        self.assertTrue(result.state_reconstitution_pass)
        self.assertTrue(result.identity_reconstitution_pass)
        self.assertEqual(result.identity_classification, "SAME_CONTINUITY_CANDIDATE")
        # Still only candidate: Ω-DCRS must apply genealogy/authority/reality/sovereignty gates.

    def test_public_module_contains_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
