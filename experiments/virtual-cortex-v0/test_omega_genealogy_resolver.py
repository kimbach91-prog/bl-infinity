#!/usr/bin/env python3
"""Tests for Ω-Genealogy Resolver."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("omega_genealogy_resolver.py")
spec = importlib.util.spec_from_file_location("omega_genealogy_resolver", MODULE_PATH)
assert spec and spec.loader
omega = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = omega
spec.loader.exec_module(omega)


def event(event_id: str, role: str, parents: list[str], *, evidence: str = "BL_LOG_EXACT", digest: str | None = "sha256:x") -> omega.LineageEvent:
    return omega.LineageEvent(
        event_id=event_id,
        role=role,
        parent_event_ids=parents,
        evidence_level=evidence,
        payload_digest=digest,
        actor_class="TEST",
    )


class GenealogyResolverTests(unittest.TestCase):
    def test_exact_single_parent_chain_passes(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", [], evidence="OWNER_DIRECT_EXACT", digest="sha256:g0"),
            event("G1", "IDENTITY_EVENT", ["G0"], digest="sha256:g1"),
            event("G2", "CHECKPOINT", ["G1"], digest="sha256:g2"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="G2")
        self.assertTrue(result.genealogy_valid)
        self.assertEqual(result.verdict, "GENEALOGY_VALID")
        self.assertEqual(result.causal_path, ["G0", "G1", "G2"])

    def test_temporal_adjacency_without_parent_edge_does_not_create_chain(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", [], evidence="OWNER_DIRECT_EXACT", digest="sha256:g0"),
            event("G1", "CHECKPOINT", [], digest="sha256:g1"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="G1")
        self.assertFalse(result.genealogy_valid)
        self.assertFalse(result.causal_path_found)
        self.assertEqual(result.verdict, "GENESIS_FOUND_CHAIN_OPEN")

    def test_partial_genesis_retrieval_cannot_validate_genealogy(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", [], evidence="PARTIAL_EXACT_CHAT_RETRIEVAL", digest=None),
            event("G1", "CHECKPOINT", ["G0"], digest="sha256:g1"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="G1")
        self.assertTrue(result.genesis_found)
        self.assertFalse(result.genesis_evidence_strong)
        self.assertFalse(result.genealogy_valid)
        self.assertEqual(result.verdict, "GENESIS_FOUND_EVIDENCE_INCOMPLETE")

    def test_missing_parent_ref_fails_closed(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", [], evidence="OWNER_DIRECT_EXACT", digest="sha256:g0"),
            event("G1", "CHECKPOINT", ["MISSING"], digest="sha256:g1"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="G1")
        self.assertFalse(result.genealogy_valid)
        self.assertIn("G1", result.missing_parent_refs)
        self.assertEqual(result.verdict, "CHAIN_MISSING_PARENT")

    def test_cycle_quarantines(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", ["G1"], evidence="OWNER_DIRECT_EXACT", digest="sha256:g0"),
            event("G1", "IDENTITY_EVENT", ["G0"], digest="sha256:g1"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="G1")
        self.assertTrue(result.cycle_detected)
        self.assertFalse(result.genealogy_valid)
        self.assertEqual(result.verdict, "QUARANTINE_CYCLE")

    def test_multiple_identity_parents_are_not_same_identity_by_default(self) -> None:
        events = [
            event("G0", "OWNER_GENESIS", [], evidence="OWNER_DIRECT_EXACT", digest="sha256:g0"),
            event("A", "IDENTITY_EVENT", ["G0"], digest="sha256:a"),
            event("B", "IDENTITY_EVENT", ["G0"], digest="sha256:b"),
            event("M", "CHECKPOINT", ["A", "B"], digest="sha256:m"),
        ]
        result = omega.resolve_genealogy(events, genesis_event_id="G0", target_event_id="M")
        self.assertFalse(result.genealogy_valid)
        self.assertTrue(result.ambiguous_identity_parentage)
        self.assertEqual(result.verdict, "FORK_OR_RECOMBINATION_REQUIRES_SEPARATE_IDENTITY_DECISION")

    def test_public_module_has_no_private_topology(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for marker in ("drive.google.com", "docs.google.com", "1ZECnf7", "1hqSX"):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
