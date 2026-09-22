import unittest

from provenance_gate import evaluate


class ProvenanceGateTests(unittest.TestCase):
    def test_rejects_old_animated_image_style_receipt(self):
        old = {
            "learned_checkpoint_sha256": "",
            "generation_operator": "affine_transform",
            "temporal_latent_frames": 1,
            "sampling_steps": 0,
            "spatiotemporal_modeling": False,
            "weights_origin": "",
            "weights_license": "",
            "primary_motion_operators": ["affine_transform", "blender_root_motion_only"],
            "output_sha256": "0" * 64,
            "proprietary_video_api_calls": 0,
        }
        result = evaluate(old)
        self.assertFalse(result.passed)
        self.assertIn("non_generative_primary_motion_path", result.reasons)
        self.assertIn("iterative_sampling_not_proven", result.reasons)

    def test_accepts_structurally_generative_self_hosted_receipt(self):
        candidate = {
            "learned_checkpoint_sha256": "1" * 64,
            "generation_operator": "flow_matching",
            "temporal_latent_frames": 21,
            "sampling_steps": 20,
            "spatiotemporal_modeling": True,
            "weights_origin": "licensed-open-weight-checkpoint",
            "weights_license": "MIT",
            "primary_motion_operators": ["learned_spatiotemporal_latent"],
            "output_sha256": "2" * 64,
            "proprietary_video_api_calls": 0,
        }
        result = evaluate(candidate)
        self.assertTrue(result.passed)
        self.assertEqual(result.verdict, "GENERATIVE_PROVENANCE_VERIFIED")

    def test_api_backed_generation_is_not_self_hosted_native(self):
        candidate = {
            "learned_checkpoint_sha256": "1" * 64,
            "generation_operator": "diffusion",
            "temporal_latent_frames": 16,
            "sampling_steps": 12,
            "spatiotemporal_modeling": True,
            "weights_origin": "provider-hidden",
            "weights_license": "provider-service",
            "primary_motion_operators": ["learned_spatiotemporal_latent"],
            "output_sha256": "2" * 64,
            "proprietary_video_api_calls": 1,
        }
        self.assertFalse(evaluate(candidate, require_self_hosted=True).passed)
        self.assertTrue(evaluate(candidate, require_self_hosted=False).passed)


if __name__ == "__main__":
    unittest.main()
