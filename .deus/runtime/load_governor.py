from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Mapping, Optional


@dataclass
class GovernorConfig:
    min_spacing_s: float = 0.75
    max_concurrency: int = 2
    max_retries: int = 5
    max_retry_elapsed_s: float = 120.0
    base_backoff_s: float = 1.0
    max_backoff_s: float = 30.0
    jitter_ratio: float = 0.25
    circuit_breaker_throttles: int = 4
    circuit_breaker_cooldown_s: float = 60.0


@dataclass
class GovernorState:
    last_request_monotonic: float = 0.0
    consecutive_throttles: int = 0
    circuit_open_until_monotonic: float = 0.0
    total_requests: int = 0
    total_throttles: int = 0
    total_retries: int = 0


class LoadGovernor:
    """Provider-agnostic governor for sustained LLM workloads.

    Stability is preferred over peak throughput: bounded concurrency, pacing,
    Retry-After obedience, exponential backoff with jitter, retry budgets and
    a circuit breaker. This module must never be used to bypass provider limits.
    """

    def __init__(self, config: Optional[GovernorConfig] = None, state_path: Optional[Path] = None,
                 sleep_fn=time.sleep, monotonic_fn=time.monotonic, random_fn=random.random) -> None:
        self.config = config or GovernorConfig()
        if self.config.max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.state_path = Path(state_path) if state_path else None
        self._sleep = sleep_fn
        self._monotonic = monotonic_fn
        self._random = random_fn
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(self.config.max_concurrency)
        self.state = self._load_state()

    def _load_state(self) -> GovernorState:
        if not self.state_path or not self.state_path.exists():
            return GovernorState()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return GovernorState(
                consecutive_throttles=int(raw.get("consecutive_throttles", 0)),
                total_requests=int(raw.get("total_requests", 0)),
                total_throttles=int(raw.get("total_throttles", 0)),
                total_retries=int(raw.get("total_retries", 0)),
            )
        except Exception:
            return GovernorState()

    def _save_state(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = asdict(self.state)
        serializable["last_request_monotonic"] = 0.0
        serializable["circuit_open_until_monotonic"] = 0.0
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    @staticmethod
    def parse_retry_after(headers: Optional[Mapping[str, str]]) -> Optional[float]:
        if not headers:
            return None
        value = None
        for key, candidate in headers.items():
            if key.lower() == "retry-after":
                value = candidate
                break
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return None

    def _jitter(self, seconds: float) -> float:
        ratio = max(0.0, self.config.jitter_ratio)
        factor = 1.0 + ((self._random() * 2.0) - 1.0) * ratio
        return max(0.0, seconds * factor)

    def _respect_circuit_breaker(self) -> None:
        now = self._monotonic()
        with self._lock:
            wait = self.state.circuit_open_until_monotonic - now
        if wait > 0:
            self._sleep(wait)

    def _pace(self) -> None:
        while True:
            now = self._monotonic()
            with self._lock:
                earliest = self.state.last_request_monotonic + self.config.min_spacing_s
                wait = earliest - now
                if wait <= 0:
                    self.state.last_request_monotonic = now
                    self.state.total_requests += 1
                    self._save_state()
                    return
            self._sleep(wait)

    def acquire(self) -> None:
        self._slots.acquire()
        try:
            self._respect_circuit_breaker()
            self._pace()
        except Exception:
            self._slots.release()
            raise

    def release(self) -> None:
        self._slots.release()

    def record_success(self) -> None:
        with self._lock:
            self.state.consecutive_throttles = 0
            self._save_state()

    def record_throttle(self, headers: Optional[Mapping[str, str]] = None) -> float:
        retry_after = self.parse_retry_after(headers)
        with self._lock:
            self.state.consecutive_throttles += 1
            self.state.total_throttles += 1
            n = self.state.consecutive_throttles
            if retry_after is None:
                delay = min(self.config.max_backoff_s,
                            self.config.base_backoff_s * (2 ** max(0, n - 1)))
                delay = self._jitter(delay)
            else:
                delay = retry_after
            if n >= self.config.circuit_breaker_throttles:
                cooldown = max(delay, self.config.circuit_breaker_cooldown_s)
                self.state.circuit_open_until_monotonic = max(
                    self.state.circuit_open_until_monotonic,
                    self._monotonic() + cooldown,
                )
            self._save_state()
        return delay

    def retry_delay(self, attempt_index: int,
                    headers: Optional[Mapping[str, str]] = None) -> float:
        retry_after = self.parse_retry_after(headers)
        if retry_after is not None:
            delay = retry_after
        else:
            delay = min(self.config.max_backoff_s,
                        self.config.base_backoff_s * (2 ** max(0, attempt_index)))
            delay = self._jitter(delay)
        with self._lock:
            self.state.total_retries += 1
            self._save_state()
        return delay

    def can_retry(self, attempt_index: int, elapsed_s: float) -> bool:
        return attempt_index < self.config.max_retries and elapsed_s < self.config.max_retry_elapsed_s


class governed_slot:
    def __init__(self, governor: LoadGovernor) -> None:
        self.governor = governor

    def __enter__(self) -> LoadGovernor:
        self.governor.acquire()
        return self.governor

    def __exit__(self, exc_type, exc, tb) -> None:
        self.governor.release()
