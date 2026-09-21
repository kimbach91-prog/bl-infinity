#!/usr/bin/env python3
"""Clean-room ARC-AGI-3 temporal/persistent-state representation audit.

This is a public-trace CPU audit only. It tests whether adding *past-observable*
transition context can produce a non-degenerate state/action key without using
the current action's outcome. It does not claim model gain, Kaggle execution,
or independent generalization.

Behavioral grounding only (no implementation copied):
- 82deutschmark/arc-explainer@a76499818d10b4c2b5526d56953bf946d2012ee9
  treats ARC3 continuation as persistent state: previousResponseId,
  existingGameGuid, scorecardId, and a cached lastFrame are carried across
  continuation turns. The repository currently declares no top-level license,
  so this audit uses only that high-level behavioral principle and is written
  clean-room from first principles.
- Tufalabs/duck-harness public example-run traces pinned at
  7652836056c59e044f093e3c13ed7438c814169e provide the runtime observations.

Every tested representation for transition t is computed from observations at
or before the pre-action frame for t. Features derived from transition t's
result are used only as the audit outcome and never enter its representation.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from representation_granularity_guard import audit_representation

TUFA_REPO = "Tufalabs/duck-harness"
TUFA_COMMIT = "7652836056c59e044f093e3c13ed7438c814169e"
CONTINUATION_REPO = "82deutschmark/arc-explainer"
CONTINUATION_COMMIT = "a76499818d10b4c2b5526d56953bf946d2012ee9"
CONTINUATION_SOURCE = "server/services/arc3/Arc3StreamService.ts"

Grid = tuple[tuple[int, ...], ...]


def stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def rep_chars(value: Any) -> int:
    return len(stable(value))


def as_grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value:
        raise ValueError("board must be a non-empty list")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError("board rows must be non-empty lists")
        vals = tuple(int(v) for v in row)
        if width is None:
            width = len(vals)
        elif len(vals) != width:
            raise ValueError("ragged board")
        rows.append(vals)
    return tuple(rows)


def load_events(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: object required")
        if obj.get("type") not in {"initial", "action"} or "board" not in obj:
            continue
        as_grid(obj["board"])
        out.append(obj)
    if len(out) < 3:
        raise ValueError(f"{path}: need initial + at least two board-bearing actions")
    return out


def action_name(event: dict[str, Any]) -> str:
    return str(event.get("action_display") or event.get("action_name") or "")


def bucket_count(n: int) -> int:
    if n <= 0:
        return 0
    return min(8, int(math.log2(n)) + 1)


def changed_cells(before: Grid, after: Grid) -> list[tuple[int, int, int, int]]:
    if len(before) != len(after) or len(before[0]) != len(after[0]):
        return []
    cells: list[tuple[int, int, int, int]] = []
    for r, (ra, rb) in enumerate(zip(before, after)):
        for c, (a, b) in enumerate(zip(ra, rb)):
            if a != b:
                cells.append((r, c, a, b))
    return cells


def quantile_bin(pos: int, size: int, bins: int = 4) -> int:
    if size <= 1:
        return 0
    return min(bins - 1, (pos * bins) // size)


def transition_signature(before: Grid, after: Grid, event: dict[str, Any]) -> dict[str, Any]:
    """Summarize a completed *past* transition; safe for the next action key."""
    cells = changed_cells(before, after)
    h, w = len(after), len(after[0])
    if cells:
        rs = [x[0] for x in cells]
        cs = [x[1] for x in cells]
        bbox = [bucket_count(max(rs) - min(rs) + 1), bucket_count(max(cs) - min(cs) + 1)]
        spatial = sorted({(quantile_bin(r, h), quantile_bin(c, w)) for r, c, _, _ in cells})
        edge = [
            any(r == 0 for r, _, _, _ in cells),
            any(r == h - 1 for r, _, _, _ in cells),
            any(c == 0 for _, c, _, _ in cells),
            any(c == w - 1 for _, c, _, _ in cells),
        ]
        color_delta = Counter((a, b) for _, _, a, b in cells)
        top_delta = [[a, b, bucket_count(n)] for (a, b), n in sorted(color_delta.items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
    else:
        bbox, spatial, edge, top_delta = [0, 0], [], [False] * 4, []
    return {
        "a": action_name(event),
        "n": bucket_count(len(cells)),
        "bb": bbox,
        "q": [list(x) for x in spatial],
        "edge": edge,
        "dc": top_delta,
        "r+": float(event.get("reward") or 0.0) > 0.0,
        "lvl+": int(event.get("level") or 0),
    }


def visual_signature(grid: Grid) -> dict[str, Any]:
    """Compact current-frame signature; no future transition information."""
    h, w = len(grid), len(grid[0])
    counts = Counter(v for row in grid for v in row)
    palette = [[color, bucket_count(count)] for color, count in sorted(counts.items())]

    # 4x4 spatial sketch: dominant color and number of distinct colors per bin.
    bins: list[list[list[int]]] = [[[] for _ in range(4)] for _ in range(4)]
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            bins[quantile_bin(r, h)][quantile_bin(c, w)].append(value)
    sketch: list[list[list[int]]] = []
    for br in range(4):
        out_row: list[list[int]] = []
        for bc in range(4):
            vals = bins[br][bc]
            cnt = Counter(vals)
            dominant = min(cnt, key=lambda color: (-cnt[color], color)) if cnt else -1
            out_row.append([dominant, min(9, len(cnt))])
        sketch.append(out_row)
    return {"shape": [h, w], "pal": palette, "sketch": sketch}


def current_level(event: dict[str, Any]) -> int:
    return int(event.get("level") or 0)


def outcome(prev: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_changed": bool(event.get("board_changed")),
        "level_completed": bool(event.get("level_completed")),
        "game_over": bool(event.get("game_over")),
        "run_complete": bool(event.get("run_complete")),
        "reward_positive": float(event.get("reward") or 0.0) > 0.0,
        "level_delta": current_level(event) - current_level(prev),
    }


def trace_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Need one completed past transition before the current action.
    for i in range(2, len(events)):
        before_prev, prev, event = events[i - 2], events[i - 1], events[i]
        if prev.get("type") != "action" or event.get("type") != "action":
            continue
        before_grid = as_grid(before_prev["board"])
        pre_action_grid = as_grid(prev["board"])
        current_result_grid = as_grid(event["board"])
        if len(before_grid) != len(pre_action_grid) or len(before_grid[0]) != len(pre_action_grid[0]):
            continue
        if len(pre_action_grid) != len(current_result_grid) or len(pre_action_grid[0]) != len(current_result_grid[0]):
            continue

        past1 = transition_signature(before_grid, pre_action_grid, prev)
        past2 = None
        if i >= 3 and events[i - 2].get("type") == "action" and events[i - 3].get("type") in {"initial", "action"}:
            older = as_grid(events[i - 3]["board"])
            if len(older) == len(before_grid) and len(older[0]) == len(before_grid[0]):
                past2 = transition_signature(older, before_grid, before_prev)

        act = action_name(event)
        visual = visual_signature(pre_action_grid)
        raw = {"board": [list(x) for x in pre_action_grid], "action": act}
        temporal_effect = {
            "shape": [len(pre_action_grid), len(pre_action_grid[0])],
            "level": current_level(prev),
            "action": act,
            "past1": past1,
        }
        temporal_visual = {
            "level": current_level(prev),
            "action": act,
            "visual": visual,
            "past1": past1,
        }
        history2_visual = {
            "level": current_level(prev),
            "action": act,
            "visual": visual,
            "past1": past1,
            "past2": past2,
        }
        rows.append({
            "outcome": outcome(prev, event),
            "representations": {
                "raw_board_action": raw,
                "temporal_effect_action": temporal_effect,
                "temporal_visual_action": temporal_visual,
                "history2_visual_action": history2_visual,
            },
        })
    return rows


def audit_paths(paths: Iterable[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    trace_stats: list[dict[str, Any]] = []
    for path in paths:
        tr = trace_rows(load_events(path))
        rows.extend(tr)
        trace_stats.append({"path": path.name, "audited_transitions": len(tr)})
    if not rows:
        raise ValueError("no auditable transitions")

    names = [
        "raw_board_action",
        "temporal_effect_action",
        "temporal_visual_action",
        "history2_visual_action",
    ]
    audits = {name: audit_representation(rows, name) for name in names}
    chars = {name: sum(rep_chars(r["representations"][name]) for r in rows) for name in names}
    raw_chars = chars["raw_board_action"]
    ratios = {name: chars[name] / raw_chars if raw_chars else 1.0 for name in names}

    eligible = [
        name for name in names[1:]
        if audits[name].promotable_evidence and chars[name] < raw_chars
    ]
    eligible.sort(key=lambda name: (
        audits[name].contradictory_repeated_state_ratio,
        -audits[name].repeat_support_ratio,
        ratios[name],
        name,
    ))
    selected = eligible[0] if eligible else None

    return {
        "schema": "deus/arc3-public-trace-temporal-state-audit/1",
        "source_grounding": {
            "runtime_trace_repo": TUFA_REPO,
            "runtime_trace_commit": TUFA_COMMIT,
            "continuation_behavior_repo": CONTINUATION_REPO,
            "continuation_behavior_commit": CONTINUATION_COMMIT,
            "continuation_behavior_source": CONTINUATION_SOURCE,
            "continuation_repo_top_level_license_declared": False,
            "implementation": "clean-room; high-level behavioral principle only; no source code copied",
        },
        "causality_guard": {
            "representation_uses_current_action_outcome": False,
            "representation_uses_current_result_frame": False,
            "past_transition_features_only": True,
            "current_pre_action_frame_allowed": True,
        },
        "truth": {
            "public_trace_only": True,
            "source_assisted": True,
            "independent_generalization": False,
            "offline_public_development_score": False,
            "model_behavior_gain": False,
            "kaggle_execution": False,
            "kaggle_hidden_score": False,
            "owner_score": False,
            "competition_submission": False,
            "submission_quota_spent": False,
        },
        "traces": trace_stats,
        "aggregate": {
            "rows": len(rows),
            "representation_chars": chars,
            "char_ratio_vs_raw": {name: round(ratios[name], 6) for name in names},
            "char_reduction_pct_vs_raw": {name: round((1.0 - ratios[name]) * 100.0, 3) for name in names},
        },
        "audits": {name: asdict(audits[name]) for name in names},
        "selection": {
            "eligible_nonraw": eligible,
            "selected_for_future_same_model_ab": selected,
            "candidate_promotion": False,
            "reason": "representation audit can only nominate a model-behavior A/B; it cannot establish solver or Kaggle gain",
        },
    }


def self_test() -> dict[str, Any]:
    h = w = 8
    board = [[0 for _ in range(w)] for _ in range(h)]
    board[4][2] = 7
    events: list[dict[str, Any]] = [{"type": "initial", "board": [r[:] for r in board], "level": 1}]
    for t in range(12):
        nxt = [r[:] for r in board]
        old = 2 + (t % 3)
        new = 2 + ((t + 1) % 3)
        nxt[4][old] = 0
        nxt[4][new] = 7
        events.append({
            "type": "action",
            "board": nxt,
            "level": 1,
            "action_display": "RIGHT",
            "board_changed": True,
            "level_completed": False,
            "game_over": False,
            "run_complete": False,
            "reward": 0,
        })
        board = nxt
    rows = trace_rows(events)
    assert len(rows) == 11
    for row in rows:
        reps = row["representations"]
        assert "past1" in reps["temporal_effect_action"]
        assert "board_changed" not in stable(reps["temporal_effect_action"])
        assert "reward_positive" not in stable(reps["temporal_effect_action"])
    return {
        "schema": "deus/arc3-public-trace-temporal-state-selftest/1",
        "passed": True,
        "rows": len(rows),
        "truth": {"synthetic_only": True, "kaggle_score": False, "model_behavior_gain": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    result = self_test() if args.self_test else audit_paths(args.input)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
