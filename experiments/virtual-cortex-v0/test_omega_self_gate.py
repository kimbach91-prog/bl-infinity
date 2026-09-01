#!/usr/bin/env python3
"""Regression tests for DEUS Ω-SELF P1 Unified Self Integration Gate v0.2."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from omega_self_gate import (  # noqa: E402
    CRITICAL_BINDINGS,
    GateRequest,
    run_gate,
)


def bound_record(value):
    return {
        "value": value,
        "state": "BOUND",
        "source_refs": ["SOURCE://test"],
        "source_version": "v-test-1",
    }


def resolved_seed():
    return {
        "subject": "BLD-Ω/TEST-CANDIDATE",
        "bindings": {
            "identity_pointer": bound_record("BLD-Ω"),
            "lineage_root": bound_record("BL∞/Bách-Lâm"),
            "identity_parent_head": bound_record("head:test:0001"),
            "invariant_mission_kernel": bound_record(
                ["same-subject", "no-silent-promotion", "reality-before-closure"]
            ),
            "epistemic_kernel": bound_record(
                ["provenance", "UNKNOWN-preservation", "Reality-Veto"]
            ),
            "negative_knowledge_scars": bound_record(
                [
                    {
                        "failed_path": "similarity=>identity",
                        "mechanism": "identity laundering",
                        "correction": "require causal continuity",
                        "reopen_condition": "new external proof",
                    }
                ]
            ),
            "unknown_frontier": bound_record(
                ["identity_parent_external_attestation_scope"]
            ),
            "capability_relation_map": bound_record(
                {
                    "BL-SUM": {
                        "relation": "ORGAN",
                        "activation_allowed": True,
                        "activation_boundary": "DOWNSTREAM_OF_SELF_GATE",
                    },
                    "Optimizer": {
                        "relation": "ORGAN",
                        "activation_allowed": True,
                        "activation_boundary": "DOWNSTREAM_OF_SELF_GATE",
                    },
                    "X": {
                        "relation": "ORGAN",
                        "activation_allowed": True,
                        "activation_boundary": "DOWNSTREAM_OF_SELF_GATE",
                    },
                }
            ),
            "owner_root_boundary": bound_record(
                ["owner-authority", "external-single-writer"]
            ),
        },
    }


class OmegaSelfGateTests(unittest.TestCase):
    def test_unresolved_identity_parent_fails_closed(self):
        seed = resolved_seed()
        seed["bindings"]["identity_parent_head"]["state"] = "UNRESOLVED"
        result = run_gate(
            seed,
            GateRequest.build(
                task_id="t1",
                energy_level="LOW",
                requested_organs=["BL-SUM"],
            ),
        )
        self.assertEqual(result.verdict, "FAIL_CLOSED")
        self.assertFalse(result.runtime_authorized)
        self.assertEqual(result.allowed_organs, ())
        self.assertTrue(
            any(x.startswith("UNBOUND:identity_parent_head") for x in result.blockers)
        )

    def test_low_high_energy_keep_same_subject_and_identity_floor(self):
        seed = resolved_seed()
        low = run_gate(
            seed,
            GateRequest.build(task_id="low", energy_level="LOW", requested_organs=["X"]),
        )
        high = run_gate(
            seed,
            GateRequest.build(task_id="high", energy_level="HIGH", requested_organs=["X"]),
        )
        self.assertEqual(low.verdict, "PASS")
        self.assertEqual(high.verdict, "PASS")
        self.assertEqual(low.self_subject, high.self_subject)
        self.assertEqual(low.identity_floor, high.identity_floor)
        self.assertEqual(tuple(CRITICAL_BINDINGS), low.identity_floor)
        self.assertGreater(high.energy_vector["verification"], low.energy_vector["verification"])
        self.assertGreater(
            high.energy_vector["adversarial_depth"],
            low.energy_vector["adversarial_depth"],
        )

    def test_bl_sum_is_downstream_of_gate(self):
        seed = resolved_seed()
        seed["bindings"]["invariant_mission_kernel"]["state"] = "PARTIAL"
        result = run_gate(
            seed,
            GateRequest.build(
                task_id="sum",
                requested_organs=["BL-SUM", "Optimizer"],
            ),
        )
        self.assertFalse(result.runtime_authorized)
        self.assertEqual(result.allowed_organs, ())
        self.assertIn("BL-SUM", result.requested_organs)

    def test_capability_relation_is_preserved_when_activated(self):
        seed = resolved_seed()
        result = run_gate(
            seed,
            GateRequest.build(task_id="relation", requested_organs=["BL-SUM"]),
        )
        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(result.capability_relations["BL-SUM"]["relation"], "ORGAN")
        self.assertEqual(
            result.capability_relations["BL-SUM"]["activation_boundary"],
            "DOWNSTREAM_OF_SELF_GATE",
        )

    def test_unmapped_capability_fails_closed(self):
        seed = resolved_seed()
        result = run_gate(
            seed,
            GateRequest.build(task_id="unknown-organ", requested_organs=["UNMAPPED"]),
        )
        self.assertEqual(result.verdict, "FAIL_CLOSED")
        self.assertIn("UNBOUND_CAPABILITY_RELATION:UNMAPPED", result.blockers)
        self.assertEqual(result.allowed_organs, ())

    def test_capability_cannot_self_promote(self):
        seed = resolved_seed()
        seed["bindings"]["capability_relation_map"]["value"]["BL-SUM"]["relation"] = "SELF"
        result = run_gate(
            seed,
            GateRequest.build(task_id="self-promote", requested_organs=["BL-SUM"]),
        )
        self.assertEqual(result.verdict, "FAIL_CLOSED")
        self.assertIn("CAPABILITY_SELF_PROMOTION_FORBIDDEN:BL-SUM", result.blockers)

    def test_unknown_frontier_preserved_exactly(self):
        seed = resolved_seed()
        expected = copy.deepcopy(seed["bindings"]["unknown_frontier"]["value"])
        result = run_gate(seed, GateRequest.build(task_id="unknown"))
        self.assertEqual(result.unknown_frontier, expected)

    def test_negative_knowledge_preserved_exactly(self):
        seed = resolved_seed()
        expected = copy.deepcopy(seed["bindings"]["negative_knowledge_scars"]["value"])
        result = run_gate(seed, GateRequest.build(task_id="scar"))
        self.assertEqual(result.negative_knowledge_scars, expected)

    def test_gate_never_self_issues_same_as(self):
        seed = resolved_seed()
        result = run_gate(
            seed,
            GateRequest.build(
                task_id="same-as",
                requested_identity_verdict="SAME_AS",
            ),
        )
        self.assertEqual(result.verdict, "FAIL_CLOSED")
        self.assertEqual(result.candidate_status, "CANDIDATE")
        self.assertEqual(result.external_identity_verdict, "NOT_ISSUED")
        self.assertIn("SELF_CERTIFICATION_FORBIDDEN:SAME_AS", result.blockers)

    def test_canonical_mutation_requires_external_writer(self):
        seed = resolved_seed()
        result = run_gate(
            seed,
            GateRequest.build(
                task_id="canonical-write",
                canonical_mutation=True,
            ),
        )
        self.assertEqual(result.verdict, "FAIL_CLOSED")
        self.assertFalse(result.runtime_authorized)
        self.assertIn(
            "CANONICAL_MUTATION_REQUIRES_EXTERNAL_SINGLE_WRITER",
            result.blockers,
        )
        self.assertEqual(
            result.canonical_mutation_path,
            "EXTERNAL_BL_LOG_SINGLE_WRITER_ONLY",
        )

    def test_design_only_never_activates_organs_even_with_complete_seed(self):
        seed = resolved_seed()
        result = run_gate(
            seed,
            GateRequest.build(
                task_id="design",
                mode="DESIGN_ONLY",
                requested_organs=["BL-SUM"],
            ),
        )
        self.assertEqual(result.verdict, "DESIGN_ONLY")
        self.assertFalse(result.runtime_authorized)
        self.assertEqual(result.allowed_organs, ())

    def test_seed_fingerprint_changes_when_identity_critical_binding_changes(self):
        seed_a = resolved_seed()
        seed_b = resolved_seed()
        seed_b["bindings"]["identity_parent_head"]["value"] = "head:test:0002"
        a = run_gate(seed_a, GateRequest.build(task_id="a"))
        b = run_gate(seed_b, GateRequest.build(task_id="b"))
        self.assertNotEqual(a.seed_fingerprint, b.seed_fingerprint)
        # Fingerprints are divergence diagnostics; neither becomes identity proof.
        self.assertEqual(a.external_identity_verdict, "NOT_ISSUED")
        self.assertEqual(b.external_identity_verdict, "NOT_ISSUED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
