import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dsp", HERE / "deepseek_skillpack.py")
dsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsp)


class SkillpackTests(unittest.TestCase):
    def setUp(self):
        self.registry = dsp.load_registry(HERE / "technique_registry.json")

    def test_detects_mla_and_fp8(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "model.py").write_text("class MLA: pass\nfp8_gemm(x, w)\nkv_lora_rank=512\n")
            result = dsp.scan_worktree(root, dsp.compile_registry(self.registry))
            self.assertIn("mla", result["techniques"])
            self.assertIn("fp8", result["techniques"])

    def test_detects_new_2026_realms(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text(
                "Conditional memory via Engram. DSpark draft model for speculative decoding. "
                "Manifold HyperConnection mHC. LPLB dynamic load balancing."
            )
            result = dsp.scan_worktree(root, dsp.compile_registry(self.registry))
            for tech in (
                "conditional_memory_engram",
                "speculative_decoding",
                "manifold_hyperconnection",
                "lp_expert_balancing",
            ):
                self.assertIn(tech, result["techniques"])

    def test_variant_synthesis_excludes_observed_combo(self):
        pass1 = {"repos": [
            {"repo": "a", "techniques": ["mla", "fp8"]},
            {"repo": "b", "techniques": ["grpo_rl", "distillation"]},
        ]}
        out = dsp.pass3_synthesize_variants(pass1, self.registry, limit=100)
        combos = [set(v["techniques"]) for v in out["variants"]]
        self.assertNotIn({"mla", "fp8"}, combos)
        self.assertTrue(any({"mla", "grpo_rl"}.issubset(c) for c in combos))

    def test_cache_skips_unchanged_head(self):
        import shutil
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repos"
            repo = root / "sample"
            repo.mkdir(parents=True)
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            (repo / "README.md").write_text("Multi-head Latent Attention")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cache = Path(td) / "cache.json"
            first, _ = dsp.scan_repositories(root, self.registry, cache)
            second, _ = dsp.scan_repositories(root, self.registry, cache)
            self.assertFalse(first[0]["cache_hit"])
            self.assertTrue(second[0]["cache_hit"])


if __name__ == "__main__":
    unittest.main()
