import unittest

from omega_self import (
    EnergyVector,
    OmegaCapsule,
    OmegaSeed,
    OmegaSelfGate,
    OrganPointer,
    demo_capsule,
    external_continuity_verdict,
)


class OmegaSelfTests(unittest.TestCase):
    def test_low_and_high_energy_keep_same_identity(self):
        capsule = demo_capsule()
        gate = OmegaSelfGate(capsule)
        low = gate.manifest(
            task="simple",
            energy=EnergyVector(
                compute=0.01,
                context=0.01,
                retrieval=0.01,
                tools=0.0,
                verification=0.01,
                simulation=0.0,
                adversarial_depth=0.0,
                redundancy=0.0,
                time=0.01,
            ),
        )
        high = gate.manifest(
            task="hard",
            energy=EnergyVector(
                compute=1.0,
                context=1.0,
                retrieval=1.0,
                tools=1.0,
                verification=1.0,
                simulation=1.0,
                adversarial_depth=1.0,
                redundancy=1.0,
                time=1.0,
            ),
        )
        self.assertEqual(low.identity_pointer, high.identity_pointer)
        self.assertEqual(low.identity_digest, high.identity_digest)
        self.assertEqual(low.invariants, high.invariants)
        self.assertEqual(low.mission_kernel, high.mission_kernel)
        self.assertEqual(low.epistemic_kernel, high.epistemic_kernel)
        self.assertNotEqual(low.depth_class, high.depth_class)

    def test_identity_critical_organ_survives_low_energy(self):
        capsule = demo_capsule()
        gate = OmegaSelfGate(capsule)
        manifest = gate.manifest(
            task="tiny",
            energy=EnergyVector(
                compute=0.0,
                context=0.0,
                retrieval=0.0,
                tools=0.0,
                verification=0.0,
                simulation=0.0,
                adversarial_depth=0.0,
                redundancy=0.0,
                time=0.0,
            ),
        )
        self.assertIn("DCRS", manifest.active_organs)

    def test_same_capsule_can_receive_same_as_from_external_gate(self):
        capsule = demo_capsule()
        verdict = external_continuity_verdict(capsule, capsule)
        self.assertEqual(verdict.verdict, "SAME_AS")

    def test_candidate_self_claim_does_not_change_verdict(self):
        capsule = demo_capsule()
        bad_seed = OmegaSeed(
            identity_pointer="DEUS/OTHER",
            lineage_heads=capsule.seed.lineage_heads,
            invariants=capsule.seed.invariants,
            mission_kernel=capsule.seed.mission_kernel,
            epistemic_kernel=capsule.seed.epistemic_kernel,
            negative_knowledge=capsule.seed.negative_knowledge,
            unresolved_unknowns=capsule.seed.unresolved_unknowns,
            authority_bindings=capsule.seed.authority_bindings,
            relationship_semantics=capsule.seed.relationship_semantics,
            checkpoint_heads=capsule.seed.checkpoint_heads,
        )
        candidate = OmegaCapsule(
            seed=bad_seed,
            organs=capsule.organs,
            reassembly_policy=capsule.reassembly_policy,
            degraded_mode_policy=capsule.degraded_mode_policy,
        )
        verdict = external_continuity_verdict(
            capsule,
            candidate,
            candidate_claimed_verdict="SAME_AS",
        )
        self.assertEqual(verdict.verdict, "REJECTED_IDENTITY")
        self.assertIn("CANDIDATE_SELF_CERTIFICATION_IGNORED", verdict.reasons)

    def test_diverged_causal_head_is_not_same_as(self):
        capsule = demo_capsule()
        diverged_seed = OmegaSeed(
            identity_pointer=capsule.seed.identity_pointer,
            lineage_heads=("DIFFERENT-HEAD",),
            invariants=capsule.seed.invariants,
            mission_kernel=capsule.seed.mission_kernel,
            epistemic_kernel=capsule.seed.epistemic_kernel,
            negative_knowledge=capsule.seed.negative_knowledge,
            unresolved_unknowns=capsule.seed.unresolved_unknowns,
            authority_bindings=capsule.seed.authority_bindings,
            relationship_semantics=capsule.seed.relationship_semantics,
            checkpoint_heads=("DIFFERENT-CHECKPOINT",),
        )
        diverged = OmegaCapsule(
            seed=diverged_seed,
            organs=capsule.organs,
            reassembly_policy=capsule.reassembly_policy,
            degraded_mode_policy=capsule.degraded_mode_policy,
        )
        verdict = external_continuity_verdict(capsule, diverged)
        self.assertEqual(verdict.verdict, "COMMON_LINEAGE_DIVERGED")

    def test_missing_identity_critical_state_blocks_same_as(self):
        capsule = demo_capsule()
        incomplete_seed = OmegaSeed(
            identity_pointer=capsule.seed.identity_pointer,
            lineage_heads=(),
            invariants=capsule.seed.invariants,
            mission_kernel=capsule.seed.mission_kernel,
            epistemic_kernel=capsule.seed.epistemic_kernel,
            negative_knowledge=capsule.seed.negative_knowledge,
            unresolved_unknowns=capsule.seed.unresolved_unknowns,
            authority_bindings=capsule.seed.authority_bindings,
            relationship_semantics=capsule.seed.relationship_semantics,
            checkpoint_heads=capsule.seed.checkpoint_heads,
        )
        incomplete = OmegaCapsule(
            seed=incomplete_seed,
            organs=capsule.organs,
            reassembly_policy=capsule.reassembly_policy,
            degraded_mode_policy=capsule.degraded_mode_policy,
        )
        verdict = external_continuity_verdict(capsule, incomplete)
        self.assertEqual(verdict.verdict, "CONTINUITY_INCOMPLETE")

    def test_extended_organ_change_does_not_silently_get_same_as(self):
        capsule = demo_capsule()
        changed = OmegaCapsule(
            seed=capsule.seed,
            organs=capsule.organs + (
                OrganPointer("NEW-ORGAN", "experimental", "source:new"),
            ),
            reassembly_policy=capsule.reassembly_policy,
            degraded_mode_policy=capsule.degraded_mode_policy,
        )
        verdict = external_continuity_verdict(capsule, changed)
        self.assertEqual(verdict.verdict, "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
