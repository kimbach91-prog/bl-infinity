#!/usr/bin/env python3
"""Bounded local continuity contract for ARC-AGI-3 candidate harnesses.

Truth boundary: this is a deterministic state/representation primitive. It does
not execute a model, play hidden Kaggle games, submit to Kaggle, or claim a
leaderboard score.

The design is source-shaped by ARC Prize's public runtime-state contract:
provisional state is committed only after a valid parsed action, retries leave
the last accepted state unchanged, bounded compaction keeps durable discoveries
plus an exact recent tail, and state resets across game boundaries.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCHEMA_VERSION = 1
STRATEGY = "local_bounded_continuity_v1"
DISCOVERY_KINDS = ("rules", "goals", "action_effects", "uncertainties")
UPSTREAM_HARNESS_COMMIT = "249c1b6843ff14bfc38ce1709070c171b98c6676"


def _clip(value: Any, limit: int = 512) -> str:
    return " ".join(str(value).split())[:limit]


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        item = _clip(item, 320)
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _normalize_discoveries(raw: Any) -> Dict[str, List[str]]:
    raw = raw if isinstance(raw, dict) else {}
    return {kind: _dedupe(raw.get(kind, [])) for kind in DISCOVERY_KINDS}


class ContinuityContract:
    """Accepted-state ledger with fail-closed provisional-turn semantics."""

    def __init__(
        self,
        game_id: str,
        *,
        max_state_chars: int = 4096,
        summary_char_budget: int = 1400,
        exact_tail_turns: int = 2,
    ) -> None:
        if not game_id:
            raise ValueError("game_id is required")
        if max_state_chars < 1600:
            raise ValueError("max_state_chars too small")
        if summary_char_budget < 400:
            raise ValueError("summary_char_budget too small")
        if exact_tail_turns < 1:
            raise ValueError("exact_tail_turns must be >= 1")
        self.max_state_chars = max_state_chars
        self.summary_char_budget = summary_char_budget
        self.exact_tail_turns = exact_tail_turns
        self._state: Dict[str, Any] = self._fresh_state(game_id)

    @staticmethod
    def _fresh_state(game_id: str) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "strategy": STRATEGY,
            "game_id": game_id,
            "summary": {kind: [] for kind in DISCOVERY_KINDS},
            "accepted_turns": [],
            "compacted_turn_count": 0,
        }

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self._state)

    def digest(self) -> str:
        payload = json.dumps(self._state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def reset_for_game(self, game_id: str) -> None:
        if not game_id:
            raise ValueError("game_id is required")
        self._state = self._fresh_state(game_id)

    def propose_turn(
        self,
        *,
        observation: Any,
        model_output: Any,
        action: Any,
        discoveries: Any = None,
    ) -> Dict[str, Any]:
        """Build provisional state without mutating the accepted state."""
        return {
            "schema_version": SCHEMA_VERSION,
            "game_id": self._state["game_id"],
            "base_digest": self.digest(),
            "turn": {
                "observation": _clip(observation),
                "model_output": _clip(model_output),
                "action": _clip(action, 160),
                "discoveries": _normalize_discoveries(discoveries),
            },
        }

    def commit_turn(self, provisional: Dict[str, Any], *, action_is_valid: bool) -> bool:
        """Commit a valid turn transactionally; invalid/rejected turns do nothing."""
        if not action_is_valid:
            return False
        if provisional.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("schema version mismatch")
        if provisional.get("game_id") != self._state["game_id"]:
            raise ValueError("cross-game provisional state rejected")
        if provisional.get("base_digest") != self.digest():
            raise ValueError("stale provisional state rejected")
        turn = copy.deepcopy(provisional.get("turn") or {})
        if not turn.get("action"):
            raise ValueError("valid action must be non-empty")
        turn["discoveries"] = _normalize_discoveries(turn.get("discoveries"))

        # All mutation is provisional until the size/compaction checks pass.
        accepted_before = copy.deepcopy(self._state)
        try:
            self._state["accepted_turns"].append(turn)
            if self._encoded_size() > self.max_state_chars:
                self._compact()
            if self._encoded_size() > self.max_state_chars:
                raise RuntimeError("continuation state exceeds protected bound")
        except Exception:
            self._state = accepted_before
            raise
        return True

    def _encoded_size(self) -> int:
        return len(json.dumps(self._state, sort_keys=True, separators=(",", ":")))

    def _compact(self) -> None:
        turns = self._state["accepted_turns"]
        if len(turns) <= self.exact_tail_turns:
            raise RuntimeError("cannot compact protected exact tail")
        prefix = turns[:-self.exact_tail_turns]
        tail = turns[-self.exact_tail_turns :]
        summary = copy.deepcopy(self._state["summary"])
        for turn in prefix:
            disc = _normalize_discoveries(turn.get("discoveries"))
            for kind in DISCOVERY_KINDS:
                summary[kind] = _dedupe([*summary[kind], *disc[kind]])
        self._state["summary"] = self._fit_summary(summary)
        self._state["accepted_turns"] = tail
        self._state["compacted_turn_count"] += len(prefix)

    def _fit_summary(self, summary: Dict[str, List[str]]) -> Dict[str, List[str]]:
        fitted = {kind: list(values) for kind, values in summary.items()}
        while len(json.dumps(fitted, sort_keys=True)) > self.summary_char_budget:
            candidates = [(kind, len(values)) for kind, values in fitted.items() if values]
            if not candidates:
                break
            kind = max(candidates, key=lambda pair: pair[1])[0]
            fitted[kind].pop(0)  # Prefer newer discoveries under pressure.
        if len(json.dumps(fitted, sort_keys=True)) > self.summary_char_budget:
            raise RuntimeError("summary cannot fit protected budget")
        return fitted


def self_test() -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    state = ContinuityContract("game-A", max_state_chars=4600, summary_char_budget=900)

    before = state.digest()
    bad = state.propose_turn(
        observation="frame 0",
        model_output="not an action",
        action="",
        discoveries={"rules": ["red cell blocks movement"]},
    )
    checks["invalid_action_is_transactional"] = (
        state.commit_turn(bad, action_is_valid=False) is False and state.digest() == before
    )

    p1 = state.propose_turn(
        observation="frame 1",
        model_output="ACTION1",
        action="ACTION1",
        discoveries={
            "rules": ["red cell blocks movement"],
            "goals": ["reach the marked exit"],
            "action_effects": ["ACTION1 moves one cell right"],
        },
    )
    checks["valid_action_commits"] = state.commit_turn(p1, action_is_valid=True)

    try:
        state.commit_turn(p1, action_is_valid=True)
        checks["stale_provisional_fails_closed"] = False
    except ValueError:
        checks["stale_provisional_fails_closed"] = True

    for i in range(2, 10):
        p = state.propose_turn(
            observation=(f"frame {i} " + "x" * 700),
            model_output=(f"reasoning {i} " + "y" * 700),
            action=f"ACTION{i % 4 + 1}",
            discoveries={
                "rules": ["red cell blocks movement"],
                "goals": ["reach the marked exit"],
                "action_effects": [f"ACTION{i % 4 + 1} effect observed at turn {i}"],
                "uncertainties": [f"door hypothesis {i}"],
            },
        )
        state.commit_turn(p, action_is_valid=True)

    snap = state.snapshot()
    summary_blob = json.dumps(snap["summary"], sort_keys=True)
    checks["compaction_occurred"] = snap["compacted_turn_count"] > 0
    checks["exact_tail_preserved"] = 1 <= len(snap["accepted_turns"]) <= 2
    checks["rule_goal_survive_compaction"] = (
        "red cell blocks movement" in summary_blob and "reach the marked exit" in summary_blob
    )
    checks["state_bound_enforced"] = state._encoded_size() <= state.max_state_chars
    checks["state_json_serializable"] = isinstance(json.dumps(snap), str)
    checks["no_score_or_submission_fields"] = not any(
        key in snap for key in ("score", "leaderboard", "submission")
    )

    # A deliberately undersized envelope must fail without corrupting accepted state.
    tiny = ContinuityContract("tiny", max_state_chars=1600, summary_char_budget=400)
    tiny_p1 = tiny.propose_turn(
        observation="a" * 700,
        model_output="b" * 700,
        action="ACTION1",
        discoveries={"rules": ["r" * 300]},
    )
    tiny.commit_turn(tiny_p1, action_is_valid=True)
    tiny_before = tiny.digest()
    tiny_p2 = tiny.propose_turn(
        observation="c" * 700,
        model_output="d" * 700,
        action="ACTION2",
        discoveries={"goals": ["g" * 300]},
    )
    try:
        tiny.commit_turn(tiny_p2, action_is_valid=True)
        checks["overflow_fails_closed_transactionally"] = False
    except RuntimeError:
        checks["overflow_fails_closed_transactionally"] = tiny.digest() == tiny_before

    old_digest = state.digest()
    state.reset_for_game("game-B")
    reset = state.snapshot()
    checks["cross_game_reset"] = (
        reset["game_id"] == "game-B"
        and not reset["accepted_turns"]
        and reset["compacted_turn_count"] == 0
        and state.digest() != old_digest
    )

    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "truth_boundary": "STATE_CONTRACT_ONLY_NO_MODEL_EXECUTION_NO_KAGGLE_SCORE",
        "upstream_harness_commit": UPSTREAM_HARNESS_COMMIT,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("use --self-test")
    result = self_test()
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.receipt:
        Path(args.receipt).write_text(text + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
