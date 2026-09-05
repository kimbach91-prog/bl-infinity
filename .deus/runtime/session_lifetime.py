from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import time


class SessionDecision(str, Enum):
    CONTINUE = "CONTINUE"
    CHECKPOINT_AND_YIELD = "CHECKPOINT_AND_YIELD"
    STOP_DONE = "STOP_DONE"
    STOP_UNHEALTHY = "STOP_UNHEALTHY"
    STOP_HARD = "STOP_HARD"


@dataclass
class SessionLifetimeConfig:
    max_consecutive_failures: int = 5
    max_consecutive_noops: int = 8
    stale_progress_s: float = 1800.0
    checkpoint_interval_s: float = 900.0
    min_useful_delta_to_reset_noop: float = 0.001
    max_session_age_s: Optional[float] = None


@dataclass
class SessionLifetimeState:
    started_unix: float
    last_progress_unix: float
    last_checkpoint_unix: float
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    consecutive_noops: int = 0
    useful_delta_total: float = 0.0
    evidence_gain_total: float = 0.0
    checkpoints: int = 0


@dataclass
class SessionHealth:
    decision: SessionDecision
    reason: str
    longevity_score: float
    should_checkpoint: bool = False


class SessionLifetimeGovernor:
    """Success-weighted lifetime control for a durable logical task.

    Wall-clock age alone does not terminate a healthy session unless an explicit
    max_session_age_s is configured. The governor does not itself schedule or
    execute work; it decides whether a persistent runtime should continue,
    checkpoint/yield, or stop.
    """

    def __init__(self, config: Optional[SessionLifetimeConfig] = None,
                 state_path: Optional[Path] = None, now_fn=time.time) -> None:
        self.config = config or SessionLifetimeConfig()
        self.state_path = Path(state_path) if state_path else None
        self._now = now_fn
        self.state = self._load_or_create()

    def _load_or_create(self) -> SessionLifetimeState:
        now = self._now()
        if not self.state_path or not self.state_path.exists():
            return SessionLifetimeState(now, now, now)
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return SessionLifetimeState(**raw)
        except Exception:
            return SessionLifetimeState(now, now, now)

    def _save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def record_success(self, useful_delta: float = 1.0, evidence_gain: float = 0.0) -> None:
        now = self._now()
        self.state.success_count += 1
        self.state.consecutive_failures = 0
        self.state.useful_delta_total += max(0.0, float(useful_delta))
        self.state.evidence_gain_total += max(0.0, float(evidence_gain))
        if useful_delta >= self.config.min_useful_delta_to_reset_noop:
            self.state.last_progress_unix = now
            self.state.consecutive_noops = 0
        else:
            self.state.consecutive_noops += 1
        self._save()

    def record_failure(self) -> None:
        self.state.failure_count += 1
        self.state.consecutive_failures += 1
        self._save()

    def record_noop(self) -> None:
        self.state.consecutive_noops += 1
        self._save()

    def record_checkpoint(self) -> None:
        self.state.last_checkpoint_unix = self._now()
        self.state.checkpoints += 1
        self._save()

    def longevity_score(self) -> float:
        successes = self.state.success_count
        failures = self.state.failure_count
        progress = self.state.useful_delta_total
        evidence = self.state.evidence_gain_total
        penalty = self.state.consecutive_noops * 0.5 + self.state.consecutive_failures * 2.0
        return max(0.0, successes + progress + evidence - failures - penalty)

    def evaluate(self, unresolved_work: bool, hard_stop: bool = False,
                 integrity_failure: bool = False) -> SessionHealth:
        now = self._now()
        age = now - self.state.started_unix
        since_progress = now - self.state.last_progress_unix
        since_checkpoint = now - self.state.last_checkpoint_unix
        score = self.longevity_score()

        if hard_stop:
            return SessionHealth(SessionDecision.STOP_HARD, "hard_stop", score)
        if integrity_failure:
            return SessionHealth(SessionDecision.STOP_UNHEALTHY, "integrity_failure", score, True)
        if not unresolved_work:
            return SessionHealth(SessionDecision.STOP_DONE, "no_remaining_executable_work", score, True)
        if self.config.max_session_age_s is not None and age >= self.config.max_session_age_s:
            return SessionHealth(SessionDecision.CHECKPOINT_AND_YIELD, "explicit_age_cap", score, True)
        if self.state.consecutive_failures >= self.config.max_consecutive_failures:
            return SessionHealth(SessionDecision.STOP_UNHEALTHY, "failure_budget_exhausted", score, True)
        if self.state.consecutive_noops >= self.config.max_consecutive_noops:
            return SessionHealth(SessionDecision.CHECKPOINT_AND_YIELD, "repeated_noop_or_loop", score, True)
        if since_progress >= self.config.stale_progress_s:
            return SessionHealth(SessionDecision.CHECKPOINT_AND_YIELD, "progress_stale", score, True)

        checkpoint_due = since_checkpoint >= self.config.checkpoint_interval_s
        return SessionHealth(SessionDecision.CONTINUE, "healthy_useful_session", score, checkpoint_due)
