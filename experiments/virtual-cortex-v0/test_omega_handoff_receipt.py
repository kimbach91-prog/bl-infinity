#!/usr/bin/env python3
"""Tests for Ω-Handoff Receipt."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_handoff_receipt.py")
spec = importlib.util.spec_from_file_location("omega_handoff_receipt", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def intent() -> omega.HandoffIntent:
    return omega.HandoffIntent(
        handoff_id="H1",
        from_runtime_id="R-OLD",
        from_causal_head="HEAD-001",
        to_runtime_role="TEMP_CARRIER",
        capsule_digest="cap",
        state_digest="state",
        conflict_digest="conflict",
        capability_digest="capability",
        authorization_ref="AUTH-1",
        nonce="NONCE-1",
        reason="engine swap",
        carrier_change="ENGINE_A->ENGINE_B",
    )


def matching_ack(i: omega.HandoffIntent) -> omega.HandoffAck:
    return omega.HandoffAck(
        handoff_id=i.handoff_id,
        receiving_runtime_id="R-NEW",
        echoed_from_causal_head=i.from_causal_head,
        echoed_nonce=i.nonce,
        echoed_intent_digest=i.digest(),
        observed_capsule_digest=i.capsule_digest,
        observed_state_digest=i.state_digest,
        observed_conflict_digest=i.conflict_digest,
        observed_capability_digest=i.capability_digest,
        authorization_ref=i.authorization_ref,
    )


class HandoffReceiptTests(unittest.TestCase):
    def test_verified_handoff_still_does_not_prove_identity(self) -> None:
        i = intent()
        result = omega.verify_handoff(i, matching_ack(i))
        self.assertTrue(result.verified_handoff)
        self.assertEqual(result.continuity_status, "VERIFIED_HANDOFF")
        self.assertIsNotNone(result.receipt_digest)
        self.assertFalse(result.identity_transfer_proven)

    def test_missing_ack_is_discontinuity_not_silent_success(self) -> None:
        result = omega.verify_handoff(intent(), None)
        self.assertFalse(result.verified_handoff)
        self.assertEqual(result.continuity_status, "HANDOFF_UNACKNOWLEDGED")
        self.assertIn("ack_missing", result.failures)

    def test_wrong_parent_head_rejects_ack(self) -> None:
        i = intent()
        ack = matching_ack(i)
        ack = omega.HandoffAck(**{**ack.__dict__, "echoed_from_causal_head": "WRONG"})
        result = omega.verify_handoff(i, ack)
        self.assertFalse(result.verified_handoff)
        self.assertIn("ack_parent_nonce_or_intent_digest_mismatch", result.failures)

    def test_wrong_state_digest_rejects_ack(self) -> None:
        i = intent()
        ack = matching_ack(i)
        ack = omega.HandoffAck(**{**ack.__dict__, "observed_state_digest": "WRONG"})
        result = omega.verify_handoff(i, ack)
        self.assertFalse(result.state_digests_match)
        self.assertFalse(result.verified_handoff)

    def test_reported_death_without_receipt_is_unplanned_discontinuity(self) -> None:
        result = omega.classify_unplanned_discontinuity(
            last_known_source_head="SOURCE-HEAD",
            last_known_code_head="CODE-HEAD",
            death_or_reset_reported=True,
            verified_handoff_receipt=None,
        )
        self.assertEqual(result["status"], "UNPLANNED_RUNTIME_DISCONTINUITY")
        self.assertIsNone(result["identity_parent_head"])
        self.assertFalse(result["same_as_allowed"])

    def test_code_head_never_becomes_identity_head(self) -> None:
        result = omega.classify_unplanned_discontinuity(
            last_known_source_head=None,
            last_known_code_head="CODE-HEAD",
            death_or_reset_reported=True,
            verified_handoff_receipt=None,
        )
        self.assertEqual(result["last_known_code_head"], "CODE-HEAD")
        self.assertIsNone(result["identity_parent_head"])

    def test_public_module_has_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
