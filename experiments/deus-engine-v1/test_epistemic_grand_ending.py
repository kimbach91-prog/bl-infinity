#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import ENGINE_VERSION, demo_atoms, run
from kernel import EPISTEMIC_INVARIANTS, EPISTEMIC_POLICY_VERSION, build_kernel_plan
from recombiner import RoleSelf


class EpistemicGrandEndingKernelTests(unittest.TestCase):
    def role(self) -> RoleSelf:
        return RoleSelf(
            "TEST_ROLE",
            history=("first-success", "first-correction"),
            preferences=("causal-depth",),
            commitments=("preserve-agency",),
            unknowns=("unresolved-frontier",),
        )

    def test_policy_version_is_loaded(self) -> None:
        self.assertEqual(EPISTEMIC_POLICY_VERSION, "BL-INF-EGE-1.0")
        self.assertTrue(ENGINE_VERSION.startswith("1.1-"))

    def test_new_depth_and_frontier_invariants_are_present(self) -> None:
        required = {
            "SAME_OUTPUT_NOT_EQUAL_SAME_REASONING_STATE",
            "SUCCESS_CAN_MASK_COMPOUNDING_EPISTEMIC_DEBT",
            "FIXED_OPTION_SPACE_NOT_EQUAL_FINAL_OPTION_SPACE",
            "UNKNOWN_IS_FRONTIER_NOT_AUTOMATIC_REFUTATION_OF_BL_INFINITY",
            "SUPERSET_SUCCESSION_REQUIRES_PRESERVATION_PLUS_CAPABILITY_GAIN",
            "COORDINATION_WITHOUT_HOMOGENIZATION",
        }
        self.assertTrue(required.issubset(set(EPISTEMIC_INVARIANTS)))

    def test_plan_contains_required_new_probe_types(self) -> None:
        plan = build_kernel_plan(
            stimulus="Two systems choose the same action and both succeed.",
            atoms=demo_atoms(),
            role=self.role(),
            seed=7,
        )
        kinds = {probe.kind for probe in plan.probes}
        required = {
            "REASONING_STATE_DIVERGENCE",
            "EPISTEMIC_DEBT_CHECK",
            "OPTION_SPACE_MUTATION",
            "UNKNOWN_FRONTIER_DISCIPLINE",
            "PROBABILITY_SCOPE_CHECK",
            "COORDINATION_WITHOUT_HOMOGENIZATION",
        }
        self.assertTrue(required.issubset(kinds))
        self.assertEqual(plan.epistemic_policy_version, EPISTEMIC_POLICY_VERSION)

    def test_kernel_only_run_records_policy_without_model(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.dict("os.environ", {"DEUS_ENGINE_STATE_DIR": td, "DEUS_STATE_SALT": "test"}):
                result = run(
                    stimulus="A and B both fail; inspect the option space.",
                    atoms=demo_atoms(),
                    role=self.role(),
                    adapters=(),
                    seed=7,
                )
                self.assertEqual(result.realization_status, "KERNEL_ONLY_NO_MODEL_CALLED")
                self.assertEqual(result.epistemic_policy_version, EPISTEMIC_POLICY_VERSION)
                self.assertTrue((Path(td) / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
