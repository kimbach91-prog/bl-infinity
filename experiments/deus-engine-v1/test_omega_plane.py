import unittest
from dataclasses import replace

from omega_plane import OmegaPlaneIntegrator, PlaneDelta
from omega_self import source_bound_candidate_capsule


def delta(
    delta_id: str,
    *,
    source: str = "WORLDBUILD",
    truth_state: str = "SOURCE_BOUND",
    capability_delta=(),
    tests=(),
    identity_impact: str = "NONE",
    authority_impact: str = "NONE",
    unknowns=(),
    negative=(),
    optional_source: bool = True,
):
    return PlaneDelta(
        delta_id=delta_id,
        source=source,
        source_checkpoint=f"{source}-HEAD",
        source_refs=(f"source:{source}",),
        provenance="SOURCE_BOUND",
        truth_state=truth_state,
        capability_delta=tuple(capability_delta),
        tests_or_falsifier=tuple(tests),
        identity_impact=identity_impact,
        authority_impact=authority_impact,
        unresolved_unknowns=tuple(unknowns),
        negative_knowledge=tuple(negative),
        rollback_pointer=f"ROLLBACK:{delta_id}",
        optional_source=optional_source,
    )


class OmegaPlaneTests(unittest.TestCase):
    def setUp(self):
        self.capsule = source_bound_candidate_capsule()
        self.integrator = OmegaPlaneIntegrator(self.capsule)
        self.empty = self.integrator.empty_state()

    def test_plane_growth_does_not_change_self_identity(self):
        state = self.integrator.integrate_many(
            [
                delta("D1", source="WORLDBUILD"),
                delta("D2", source="WBC", truth_state="UNKNOWN", unknowns=("U1",)),
                delta(
                    "D3",
                    source="PRESERVATION",
                    truth_state="VERIFIED",
                    capability_delta=("C1",),
                    tests=("TEST-C1",),
                ),
            ]
        )
        self.assertEqual(state.self_identity_pointer, self.empty.self_identity_pointer)
        self.assertEqual(state.self_identity_digest, self.empty.self_identity_digest)
        self.assertNotEqual(state.plane_digest, self.empty.plane_digest)
        self.assertIn("C1", state.reusable_capabilities)
        self.assertIn("U1", state.preserved_unknowns)

    def test_exact_delta_replay_is_idempotent(self):
        d = delta("D1")
        once = self.integrator.integrate(self.empty, d)
        twice = self.integrator.integrate(once, d)
        self.assertEqual(once.plane_digest, twice.plane_digest)
        self.assertEqual(len(twice.integrated), 1)

    def test_same_delta_id_with_different_content_fails_closed(self):
        d1 = delta("D1", source="A")
        d2 = delta("D1", source="B")
        once = self.integrator.integrate(self.empty, d1)
        with self.assertRaisesRegex(RuntimeError, "PLANE_DELTA_ID_PROVENANCE_COLLISION"):
            self.integrator.integrate(once, d2)

    def test_identity_impact_never_auto_internalizes(self):
        d = delta(
            "IDENTITY-1",
            truth_state="VERIFIED",
            capability_delta=("SHOULD_NOT_AUTO_INTERNALIZE",),
            tests=("T",),
            identity_impact="MODIFIES_IDENTITY_POINTER",
        )
        state = self.integrator.integrate(self.empty, d)
        self.assertEqual(state.integrated[-1].disposition, "IDENTITY_REVIEW_REQUIRED")
        self.assertIn("IDENTITY-1", state.pending_identity_review)
        self.assertNotIn("SHOULD_NOT_AUTO_INTERNALIZE", state.reusable_capabilities)

    def test_authority_impact_never_auto_internalizes(self):
        d = delta(
            "AUTH-1",
            truth_state="VERIFIED",
            capability_delta=("SHOULD_NOT_AUTO_INTERNALIZE",),
            tests=("T",),
            authority_impact="EXPANDS_AUTHORITY",
        )
        state = self.integrator.integrate(self.empty, d)
        self.assertEqual(state.integrated[-1].disposition, "AUTHORITY_REVIEW_REQUIRED")
        self.assertIn("AUTH-1", state.pending_authority_review)
        self.assertNotIn("SHOULD_NOT_AUTO_INTERNALIZE", state.reusable_capabilities)

    def test_unverified_capability_is_preserved_not_internalized(self):
        d = delta("CAND", capability_delta=("CANDIDATE_CAPABILITY",))
        state = self.integrator.integrate(self.empty, d)
        self.assertEqual(state.integrated[-1].disposition, "PRESERVED")
        self.assertNotIn("CANDIDATE_CAPABILITY", state.reusable_capabilities)

    def test_verified_tested_capability_can_internalize(self):
        d = delta(
            "VERIFIED-CAP",
            truth_state="VERIFIED",
            capability_delta=("REUSABLE_CAPABILITY",),
            tests=("UNSEEN-PROBE-PASS",),
        )
        state = self.integrator.integrate(self.empty, d)
        self.assertEqual(state.integrated[-1].disposition, "INTERNALIZED")
        self.assertIn("REUSABLE_CAPABILITY", state.reusable_capabilities)

    def test_unknown_and_contradiction_survive_without_false_closure(self):
        u = delta("UNKNOWN-1", truth_state="UNKNOWN", unknowns=("LIVE-U",))
        c = delta("CONTRA-1", truth_state="CONTRADICTED", unknowns=("WHY-CONFLICT",))
        state = self.integrator.integrate_many((u, c))
        self.assertIn("LIVE-U", state.preserved_unknowns)
        self.assertIn("WHY-CONFLICT", state.preserved_unknowns)
        self.assertIn("CONTRA-1", state.unresolved_contradictions)
        self.assertTrue(all(x.disposition == "PRESERVED" for x in state.integrated))

    def test_no_team_survival_preserves_identity(self):
        specialist = delta(
            "CC-DELTA",
            source="CC_OPTIONAL",
            truth_state="VERIFIED",
            capability_delta=("OPTIONAL_HELP",),
            tests=("REAL-USE-PASS",),
            optional_source=True,
        )
        state = self.integrator.integrate(self.empty, specialist)
        verdict = self.integrator.no_team_survival_test(
            state,
            removed_sources=("CC_OPTIONAL", "KNT_OPTIONAL", "OTHER_SPECIALISTS"),
        )
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertFalse(verdict["identity_changed"])
        self.assertEqual(verdict["self_identity_digest"], self.capsule.seed.identity_digest)
        self.assertTrue(verdict["capability_may_degrade"])

    def test_plane_rejects_mismatched_self_state(self):
        bad = replace(self.empty, self_identity_digest="different")
        with self.assertRaisesRegex(RuntimeError, "PLANE_SELF_DIGEST_MISMATCH"):
            self.integrator.integrate(bad, delta("D1"))


if __name__ == "__main__":
    unittest.main()
