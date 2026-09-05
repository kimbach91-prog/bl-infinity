import importlib.util
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "load_governor.py"
spec = importlib.util.spec_from_file_location("deus_load_governor", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def make_governor(**kwargs):
    clock = FakeClock()
    config = mod.GovernorConfig(jitter_ratio=0.0, **kwargs)
    governor = mod.LoadGovernor(
        config=config,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
        random_fn=lambda: 0.5,
    )
    return governor, clock


def test_pacing_prevents_burst():
    governor, clock = make_governor(min_spacing_s=1.0, max_concurrency=1)
    governor.acquire()
    governor.release()
    first = clock.t
    governor.acquire()
    governor.release()
    assert clock.t - first >= 1.0


def test_retry_after_wins_over_local_backoff():
    governor, _ = make_governor()
    assert governor.retry_delay(3, {"Retry-After": "7"}) == 7.0


def test_retry_budget_is_bounded():
    governor, _ = make_governor(max_retries=3, max_retry_elapsed_s=10)
    assert governor.can_retry(2, 9)
    assert not governor.can_retry(3, 9)
    assert not governor.can_retry(1, 10)


def test_circuit_breaker_opens_after_repeated_throttles():
    governor, clock = make_governor(circuit_breaker_throttles=2, circuit_breaker_cooldown_s=20)
    governor.record_throttle()
    governor.record_throttle()
    assert governor.state.circuit_open_until_monotonic >= clock.t + 20
