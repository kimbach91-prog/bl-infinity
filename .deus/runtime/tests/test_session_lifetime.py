import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sl", HERE / "session_lifetime.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


class Clock:
    def __init__(self, t=1000.0):
        self.t = t
    def now(self):
        return self.t
    def advance(self, seconds):
        self.t += seconds


class SessionLifetimeTests(unittest.TestCase):
    def test_no_default_age_cap(self):
        clock = Clock()
        gov = sl.SessionLifetimeGovernor(now_fn=clock.now)
        gov.record_success(useful_delta=2.0, evidence_gain=1.0)
        clock.advance(7 * 24 * 3600)
        gov.record_success(useful_delta=1.0)
        health = gov.evaluate(unresolved_work=True)
        self.assertEqual(health.decision, sl.SessionDecision.CONTINUE)

    def test_repeated_noop_yields(self):
        clock = Clock()
        cfg = sl.SessionLifetimeConfig(max_consecutive_noops=3, stale_progress_s=999999)
        gov = sl.SessionLifetimeGovernor(cfg, now_fn=clock.now)
        for _ in range(3):
            gov.record_noop()
        health = gov.evaluate(unresolved_work=True)
        self.assertEqual(health.decision, sl.SessionDecision.CHECKPOINT_AND_YIELD)

    def test_failure_budget_stops(self):
        clock = Clock()
        cfg = sl.SessionLifetimeConfig(max_consecutive_failures=2)
        gov = sl.SessionLifetimeGovernor(cfg, now_fn=clock.now)
        gov.record_failure(); gov.record_failure()
        health = gov.evaluate(unresolved_work=True)
        self.assertEqual(health.decision, sl.SessionDecision.STOP_UNHEALTHY)

    def test_success_extends_useful_session_and_checkpoint_due(self):
        clock = Clock()
        cfg = sl.SessionLifetimeConfig(checkpoint_interval_s=60, stale_progress_s=3600)
        gov = sl.SessionLifetimeGovernor(cfg, now_fn=clock.now)
        gov.record_success(useful_delta=3.0, evidence_gain=2.0)
        clock.advance(61)
        health = gov.evaluate(unresolved_work=True)
        self.assertEqual(health.decision, sl.SessionDecision.CONTINUE)
        self.assertTrue(health.should_checkpoint)
        self.assertGreater(health.longevity_score, 0)

    def test_state_roundtrip(self):
        clock = Clock()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            gov = sl.SessionLifetimeGovernor(state_path=path, now_fn=clock.now)
            gov.record_success(useful_delta=2.0)
            gov.record_checkpoint()
            restored = sl.SessionLifetimeGovernor(state_path=path, now_fn=clock.now)
            self.assertEqual(restored.state.success_count, 1)
            self.assertEqual(restored.state.checkpoints, 1)


if __name__ == "__main__":
    unittest.main()
