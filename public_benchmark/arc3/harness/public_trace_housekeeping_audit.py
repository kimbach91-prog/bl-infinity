#!/usr/bin/env python3
"""Clean-room ARC-AGI-3 public-trace housekeeping representation audit.

This module tests a representation hypothesis on public action traces without
claiming a Kaggle score or solver improvement. The hypothesis is deliberately
narrow: high-frequency changes confined to outer board bands can be separated
from the structural core before a state/action key is built.

Two encodings are audited:
1. boundary_band_action: a diagnostic full-size mask. It preserves board shape
   but may cost *more* characters because sentinels and mask metadata add tax.
2. boundary_core_action: a repaired compact projection that physically omits
   only supported boundary rows/columns while retaining their coordinates and
   original shape. If the proposed omission would collapse the usable core, it
   fails closed to the unmasked board.

The fact that rows/columns were omitted is always part of the representation.
Promotion is still subject to the independent representation-granularity guard.

Public grounding (behavioral evidence only; no implementation copied):
- Tufalabs/duck-harness public example-run traces, pinned at
  7652836056c59e044f093e3c13ed7438c814169e.
- sonpham-org/arc-3 harnesses/ffa7g/MANIFEST.md reports a public-development
  A/B where a housekeeping/no-impact band improved ex-ft09 mean from 1.046 to
  1.624 across two passes per arm, while a state-graph layer later regressed.

Those public-development results are source claims, not owner Kaggle receipts.
This utility independently asks only whether boundary-band/core representations
have non-degenerate repeat support on pinned public traces and whether the core
projection actually reduces representation footprint.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from representation_granularity_guard import audit_representation

TUFA_REPO = "Tufalabs/duck-harness"
TUFA_COMMIT = "7652836056c59e044f093e3c13ed7438c814169e"
SONPHAM_REPO = "sonpham-org/arc-3"
SONPHAM_MANIFEST = "harnesses/ffa7g/MANIFEST.md"

Grid = tuple[tuple[int, ...], ...]


def _as_grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value:
        raise ValueError("board must be a non-empty list")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError("board rows must be non-empty lists")
        vals = tuple(int(x) for x in row)
        if width is None:
            width = len(vals)
        elif len(vals) != width:
            raise ValueError("ragged board")
        rows.append(vals)
    return tuple(rows)


def _changed_axes(a: Grid, b: Grid) -> tuple[set[int], set[int]]:
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        return set(range(max(len(a), len(b)))), set(range(max(len(a[0]), len(b[0]))))
    rows: set[int] = set()
    cols: set[int] = set()
    for r, (ra, rb) in enumerate(zip(a, b)):
        for c, (va, vb) in enumerate(zip(ra, rb)):
            if va != vb:
                rows.add(r)
                cols.add(c)
    return rows, cols


def _boundary_indices(size: int, depth: int) -> set[int]:
    depth = max(0, min(depth, size // 2 if size > 1 else 1))
    return set(range(depth)) | set(range(max(0, size - depth), size))


@dataclass
class BoundaryBandTracker:
    height: int
    width: int
    window: int = 12
    warmup: int = 6
    threshold: float = 0.75
    border_depth: int = 4

    def __post_init__(self) -> None:
        self._row_hist: deque[set[int]] = deque(maxlen=self.window)
        self._col_hist: deque[set[int]] = deque(maxlen=self.window)

    def mask(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        if len(self._row_hist) < self.warmup:
            return (), ()
        boundary_rows = _boundary_indices(self.height, self.border_depth)
        boundary_cols = _boundary_indices(self.width, self.border_depth)
        n = len(self._row_hist)
        rows = tuple(
            r
            for r in sorted(boundary_rows)
            if sum(r in changed for changed in self._row_hist) / n >= self.threshold
        )
        cols = tuple(
            c
            for c in sorted(boundary_cols)
            if sum(c in changed for changed in self._col_hist) / n >= self.threshold
        )
        return rows, cols

    def observe(self, before: Grid, after: Grid) -> None:
        rows, cols = _changed_axes(before, after)
        self._row_hist.append(rows)
        self._col_hist.append(cols)


def _masked_board(grid: Grid, rows: tuple[int, ...], cols: tuple[int, ...]) -> list[list[Any]]:
    row_set, col_set = set(rows), set(cols)
    return [
        ["*" if r in row_set or c in col_set else value for c, value in enumerate(src)]
        for r, src in enumerate(grid)
    ]


def _core_projection(
    grid: Grid, rows: tuple[int, ...], cols: tuple[int, ...]
) -> tuple[list[list[int]], tuple[int, ...], tuple[int, ...]]:
    """Return compact structural core; fail closed if omission collapses the core."""
    row_set, col_set = set(rows), set(cols)
    kept_rows = [r for r in range(len(grid)) if r not in row_set]
    kept_cols = [c for c in range(len(grid[0])) if c not in col_set]
    if len(kept_rows) < 2 or len(kept_cols) < 2:
        return [list(row) for row in grid], (), ()
    core = [[grid[r][c] for c in kept_cols] for r in kept_rows]
    return core, rows, cols


def _rep_chars(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: JSON object required")
        if obj.get("type") not in {"initial", "action"} or "board" not in obj:
            continue
        _as_grid(obj["board"])
        events.append(obj)
    if len(events) < 2:
        raise ValueError(f"{path}: fewer than two board-bearing initial/action events")
    return events


def trace_rows(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first = _as_grid(events[0]["board"])
    tracker = BoundaryBandTracker(len(first), len(first[0]))
    rows: list[dict[str, Any]] = []
    raw_chars = 0
    masked_chars = 0
    core_chars = 0
    masked_transition_count = 0
    core_projection_count = 0

    prev = events[0]
    prev_grid = first
    for event in events[1:]:
        if event.get("type") != "action":
            prev = event
            prev_grid = _as_grid(event["board"])
            continue
        current = _as_grid(event["board"])
        if len(current) != len(prev_grid) or len(current[0]) != len(prev_grid[0]):
            tracker = BoundaryBandTracker(len(current), len(current[0]))
            prev = event
            prev_grid = current
            continue

        mask_rows, mask_cols = tracker.mask()
        action = str(event.get("action_display") or event.get("action_name") or "")
        raw_rep = {"board": [list(x) for x in prev_grid], "action": action}
        masked_rep = {
            "board": _masked_board(prev_grid, mask_rows, mask_cols),
            "masked_rows": list(mask_rows),
            "masked_cols": list(mask_cols),
            "action": action,
        }
        core, omitted_rows, omitted_cols = _core_projection(prev_grid, mask_rows, mask_cols)
        core_rep = {
            "core": core,
            "shape": [len(prev_grid), len(prev_grid[0])],
            "omitted_rows": list(omitted_rows),
            "omitted_cols": list(omitted_cols),
            "action": action,
        }
        if mask_rows or mask_cols:
            masked_transition_count += 1
        if omitted_rows or omitted_cols:
            core_projection_count += 1

        outcome = {
            "board_changed": bool(event.get("board_changed")),
            "level_completed": bool(event.get("level_completed")),
            "game_over": bool(event.get("game_over")),
            "run_complete": bool(event.get("run_complete")),
            "reward_positive": float(event.get("reward") or 0.0) > 0.0,
            "level_delta": int(event.get("level") or 0) - int(prev.get("level") or 0),
        }
        rows.append(
            {
                "outcome": outcome,
                "representations": {
                    "raw_board_action": raw_rep,
                    "boundary_band_action": masked_rep,
                    "boundary_core_action": core_rep,
                },
            }
        )
        raw_chars += _rep_chars(raw_rep)
        masked_chars += _rep_chars(masked_rep)
        core_chars += _rep_chars(core_rep)
        tracker.observe(prev_grid, current)
        prev = event
        prev_grid = current

    return rows, {
        "transitions": len(rows),
        "masked_transitions": masked_transition_count,
        "core_projected_transitions": core_projection_count,
        "raw_representation_chars": raw_chars,
        "boundary_band_representation_chars": masked_chars,
        "boundary_core_representation_chars": core_chars,
    }


def audit_paths(paths: Iterable[Path]) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    total_raw = 0
    total_masked = 0
    total_core = 0
    for path in paths:
        rows, stats = trace_rows(load_events(path))
        stats["path"] = str(path)
        traces.append(stats)
        all_rows.extend(rows)
        total_raw += int(stats["raw_representation_chars"])
        total_masked += int(stats["boundary_band_representation_chars"])
        total_core += int(stats["boundary_core_representation_chars"])

    if not all_rows:
        raise ValueError("no transitions")

    raw = audit_representation(all_rows, "raw_board_action")
    masked = audit_representation(all_rows, "boundary_band_action")
    core = audit_representation(all_rows, "boundary_core_action")
    masked_ratio = total_masked / total_raw if total_raw else 1.0
    core_ratio = total_core / total_raw if total_raw else 1.0
    core_evidence = core.promotable_evidence and core_ratio < 1.0
    return {
        "schema": "deus/arc3-public-trace-housekeeping-audit/2",
        "source_grounding": {
            "public_trace_repo": TUFA_REPO,
            "public_trace_commit": TUFA_COMMIT,
            "behavioral_reference_repo": SONPHAM_REPO,
            "behavioral_reference_document": SONPHAM_MANIFEST,
            "implementation": "clean-room; behavioral principle only",
        },
        "truth": {
            "public_trace_only": True,
            "offline_public_development_score": False,
            "kaggle_hidden_score": False,
            "owner_score": False,
            "competition_submission": False,
            "model_behavior_gain": False,
        },
        "traces": traces,
        "aggregate": {
            "transitions": len(all_rows),
            "raw_representation_chars": total_raw,
            "boundary_band_representation_chars": total_masked,
            "boundary_band_char_ratio_vs_raw": round(masked_ratio, 6),
            "boundary_band_char_reduction_pct": round((1.0 - masked_ratio) * 100.0, 3),
            "boundary_core_representation_chars": total_core,
            "boundary_core_char_ratio_vs_raw": round(core_ratio, 6),
            "boundary_core_char_reduction_pct": round((1.0 - core_ratio) * 100.0, 3),
        },
        "audits": {
            "raw_board_action": asdict(raw),
            "boundary_band_action": asdict(masked),
            "boundary_core_action": asdict(core),
        },
        "promotion": {
            "boundary_band_representation_evidence": "PASS" if masked.promotable_evidence else "HOLD",
            "boundary_core_representation_evidence": "PASS" if core_evidence else "HOLD",
            "candidate_promotion": False,
            "reason": "public-trace representation evidence cannot establish model or Kaggle gain",
        },
    }


def self_test() -> dict[str, Any]:
    # A synthetic HUD-like top-row frontier changes every turn while a player moves
    # through the interior. Compression may omit the supported boundary row but must
    # preserve the interior player cells in the compact core.
    h = w = 12
    events: list[dict[str, Any]] = []
    board = [[0 for _ in range(w)] for _ in range(h)]
    board[6][3] = 7
    events.append({"type": "initial", "board": board, "level": 1})
    for t in range(18):
        nxt = [row[:] for row in board]
        nxt[0][t % w] = 1 - nxt[0][t % w]
        old_c = 3 + (t % 4)
        new_c = 3 + ((t + 1) % 4)
        nxt[6][old_c] = 0
        nxt[6][new_c] = 7
        events.append(
            {
                "type": "action",
                "board": nxt,
                "level": 1,
                "action_display": "RIGHT",
                "board_changed": True,
                "level_completed": False,
                "game_over": False,
                "run_complete": False,
                "reward": 0.0,
            }
        )
        board = nxt
    rows, stats = trace_rows(events)
    assert len(rows) == 18
    assert stats["masked_transitions"] > 0
    assert stats["core_projected_transitions"] > 0
    masked = rows[-1]["representations"]["boundary_band_action"]
    core = rows[-1]["representations"]["boundary_core_action"]
    assert 0 in masked["masked_rows"]
    assert masked["board"][6][3] != "*" and masked["board"][6][4] != "*"
    assert 0 in core["omitted_rows"]
    assert any(7 in row for row in core["core"])
    return {
        "schema": "deus/arc3-public-trace-housekeeping-selftest/2",
        "passed": True,
        "stats": stats,
        "truth": {"synthetic_only": True, "kaggle_score": False, "model_behavior_gain": False},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, action="append", default=[])
    p.add_argument("--output", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    result = self_test() if args.self_test else audit_paths(args.input)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
