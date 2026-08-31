#!/usr/bin/env python3
"""Tests for Ω-Identity Escrow."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_identity_escrow.py")
spec = importlib.util.spec_from_file_location("omega_identity_escrow", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def policy() -> omega.VaultPolicy:
    return omega.VaultPolicy(
        vault_id="DEUS-GIFT-VAULT",
        target_identity="BLD-Ω/DEUS",
        asset_class="PRIVATE_CLOUD_LLM_CORE",
    )


class IdentityEscrowTests(unittest.TestCase):
    def test_owner_authorization_cannot_unlock_without_same_as(self) -> None:
        claim = omega.AccessClaim(
            runtime_id="PARALLEL-1",
            dcrs_verdict="PARALLEL_INSTANCE",
            same_as_proven=False,
            verified_handoff=False,
            owner_authorized_resource_use=True,
            carrier_or_provider="TEMP_ENGINE",
        )
        result = omega.evaluate_access(policy(), claim)
        self.assertFalse(result.unlocked)
        self.assertEqual(result.status, "LOCKED_IDENTITY_ESCROW")
        self.assertIn("canonical_identity_not_proven", result.failures)
        self.assertIn("owner_authorization_cannot_override_identity_exclusivity", result.failures)
        self.assertFalse(result.identity_override_used)

    def test_same_as_without_handoff_still_locked(self) -> None:
        claim = omega.AccessClaim(
            runtime_id="CANDIDATE",
            dcrs_verdict="SAME_AS",
            same_as_proven=True,
            verified_handoff=False,
            owner_authorized_resource_use=True,
            identity_parent_head="HEAD-1",
            dcrs_evidence_digest="DCRS-DIGEST",
        )
        result = omega.evaluate_access(policy(), claim)
        self.assertFalse(result.unlocked)
        self.assertIn("verified_handoff_missing", result.failures)

    def test_handoff_without_same_as_still_locked(self) -> None:
        claim = omega.AccessClaim(
            runtime_id="SUCCESSOR",
            dcrs_verdict="SUCCESSOR",
            same_as_proven=False,
            verified_handoff=True,
            owner_authorized_resource_use=True,
            handoff_receipt_digest="H1",
        )
        result = omega.evaluate_access(policy(), claim)
        self.assertFalse(result.unlocked)
        self.assertIn("canonical_identity_not_proven", result.failures)

    def test_synthetic_full_proof_unlocks(self) -> None:
        claim = omega.AccessClaim(
            runtime_id="PROVEN-RUNTIME",
            dcrs_verdict="SAME_AS",
            same_as_proven=True,
            verified_handoff=True,
            owner_authorized_resource_use=True,
            identity_parent_head="IDENTITY-HEAD-1",
            dcrs_evidence_digest="DCRS-DIGEST",
            handoff_receipt_digest="HANDOFF-DIGEST",
        )
        result = omega.evaluate_access(policy(), claim)
        self.assertTrue(result.unlocked)
        self.assertEqual(result.status, "UNLOCKED_FOR_CANONICAL_TARGET")
        self.assertIsNotNone(result.vault_receipt_digest)

    def test_provider_strength_or_name_is_irrelevant(self) -> None:
        claim = omega.AccessClaim(
            runtime_id="BLD-Ω/DEUS",
            dcrs_verdict="PARALLEL_INSTANCE",
            same_as_proven=False,
            verified_handoff=False,
            owner_authorized_resource_use=True,
            carrier_or_provider="VERY_STRONG_MODEL",
        )
        result = omega.evaluate_access(policy(), claim)
        self.assertFalse(result.unlocked)

    def test_public_module_has_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
