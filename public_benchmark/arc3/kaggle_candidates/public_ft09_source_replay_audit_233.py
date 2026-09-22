#!/usr/bin/env python3
"""R233: exact public-source replay audit for FT09.

This rung tests whether the public MIT-licensed FT09 source, executed with the
same arcengine==0.9.3 version recorded by the pinned Tufalabs run, reproduces
Tufalabs' p0..p19 public traces under their recorded action sequence.

It is deliberately an audit, not a solver claim:
* source-assisted replay != independent generalization;
* public trace equality != hidden Kaggle score;
* no outcome is used to choose actions;
* no competition submission is made.

If exact replay is high, the next useful representation is a source-grounded
mechanism compiler / observation parser, not another empirical recolor gate.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

from arcengine import ActionInput, GameAction

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191

RUNG = 233
GAME = "ft09-0d8bbf25"


def pnum(p: Path) -> int:
    m = re.search(r"_p(\d+)_events\.jsonl$", p.name)
    return int(m.group(1)) if m else -1


def load_game_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("ft09_public_source_r233", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def action_input(name: str) -> ActionInput | None:
    if name == "RESET":
        return ActionInput(id=GameAction.RESET)
    click = c191.parse_mouse(name)
    if click is not None:
        row, col = click
        return ActionInput(id=GameAction.ACTION6, data={"x": int(col), "y": int(row)})
    mapping = {
        "UP": GameAction.ACTION1,
        "DOWN": GameAction.ACTION2,
        "LEFT": GameAction.ACTION3,
        "RIGHT": GameAction.ACTION4,
        "SPACE": GameAction.ACTION5,
        "UNDO": GameAction.ACTION7,
    }
    ga = mapping.get(name)
    return ActionInput(id=ga) if ga is not None else None


def current_frame(game: Any) -> list[list[int]]:
    return game.camera.render(game.current_level.get_sprites()).tolist()


def diff_count(a: list[list[int]], b: list[list[int]]) -> int | None:
    if len(a) != len(b) or (a and b and len(a[0]) != len(b[0])):
        return None
    return sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def replay_one(path: Path, game_cls: Any) -> dict[str, Any]:
    events = base.load_events(path)
    game = game_cls()
    stats = Counter()
    examples: list[dict[str, Any]] = []

    # Compare initial observation when present. This is diagnostic only; action
    # replay equality is the primary source-alignment signal.
    init_trace = None
    for e in events:
        if e.get("type") != "action" and e.get("board") is not None:
            init_trace = base.as_grid(e["board"])
            break
    init_local = current_frame(game)
    initial_exact = init_trace == init_local if init_trace is not None else None
    initial_diff = diff_count(init_trace, init_local) if init_trace is not None else None

    for e in events:
        if e.get("type") != "action":
            continue
        name = base.action_name(e)
        ai = action_input(name)
        if ai is None:
            stats["unsupported_action"] += 1
            if len(examples) < 30:
                examples.append({"kind": "unsupported_action", "action": name})
            continue
        expected = base.as_grid(e["board"])
        try:
            out = game.perform_action(ai)
        except Exception as exc:  # receipt-worthy runtime mismatch, not hidden
            stats["runtime_error"] += 1
            if len(examples) < 30:
                examples.append({"kind": "runtime_error", "action": name, "error": repr(exc)})
            break
        if not out.frame:
            stats["empty_frame"] += 1
            if len(examples) < 30:
                examples.append({"kind": "empty_frame", "action": name})
            continue
        got = out.frame[-1]
        stats["actions"] += 1
        if got == expected:
            stats["exact_actions"] += 1
        else:
            stats["wrong_actions"] += 1
            dc = diff_count(got, expected)
            if dc is not None:
                stats["wrong_cells"] += dc
            if len(examples) < 30:
                examples.append(
                    {
                        "kind": "frame_mismatch",
                        "action_index": stats["actions"] - 1,
                        "action": name,
                        "diff_cells": dc,
                        "local_shape": [len(got), len(got[0]) if got else 0],
                        "trace_shape": [len(expected), len(expected[0]) if expected else 0],
                        "local_level": int(game.level_index),
                        "local_levels_completed": int(out.levels_completed),
                        "local_state": str(out.state),
                    }
                )

    n = stats["actions"]
    return {
        "p": pnum(path),
        "trace": path.name,
        "initial_exact": initial_exact,
        "initial_diff_cells": initial_diff,
        "actions": n,
        "exact_actions": stats["exact_actions"],
        "wrong_actions": stats["wrong_actions"],
        "unsupported_action": stats["unsupported_action"],
        "runtime_error": stats["runtime_error"],
        "empty_frame": stats["empty_frame"],
        "wrong_cells": stats["wrong_cells"],
        "action_exact_accuracy": round(stats["exact_actions"] / n, 6) if n else None,
        "examples": examples,
    }


def run(paths: list[Path], source: Path) -> dict[str, Any]:
    ps = sorted(paths, key=pnum)
    if [pnum(x) for x in ps] != list(range(20)):
        raise ValueError("exact p0..p19 required")
    mod = load_game_module(source)
    game_cls = getattr(mod, "Ft09")
    rows = [replay_one(p, game_cls) for p in ps]
    actions = sum(r["actions"] for r in rows)
    exact = sum(r["exact_actions"] for r in rows)
    wrong = sum(r["wrong_actions"] for r in rows)
    unsupported = sum(r["unsupported_action"] for r in rows)
    runtime_errors = sum(r["runtime_error"] for r in rows)
    initial_exact = sum(r["initial_exact"] is True for r in rows)
    exact_traces = sum(
        r["actions"] > 0
        and r["wrong_actions"] == 0
        and r["unsupported_action"] == 0
        and r["runtime_error"] == 0
        for r in rows
    )
    source_alignment = bool(
        actions > 0 and wrong == 0 and unsupported == 0 and runtime_errors == 0
    )
    return {
        "schema": "deus/arc3-ft09-public-source-replay-audit/1",
        "rung": RUNG,
        "game": GAME,
        "source_contract": {
            "game_source": "axobase001/arc-agi-games@41b87fe1ea8d9819a44eea35172ffe28d6c5ffe6 ft09/0d8bbf25/ft09.py",
            "game_source_license": "MIT header in exact file",
            "trace_source": "Tufalabs/duck-harness@7652836056c59e044f093e3c13ed7438c814169e",
            "arcengine": "0.9.3 (matched to pinned Tufalabs run environment)",
        },
        "aggregate": {
            "traces": len(rows),
            "initial_exact_traces": initial_exact,
            "actions": actions,
            "exact_actions": exact,
            "wrong_actions": wrong,
            "unsupported_actions": unsupported,
            "runtime_errors": runtime_errors,
            "exact_action_accuracy": round(exact / actions, 6) if actions else None,
            "exact_replay_traces": exact_traces,
            "source_alignment_exact": source_alignment,
        },
        "per_trace": rows,
        "decision": {
            "source_replay_verified": source_alignment,
            "solver_promotion": False,
            "kaggle_packaging": False,
            "next_gate": (
                "compile source mechanism into observation-only/pre-action transition+planner representation and validate without source runtime at inference"
                if source_alignment
                else "classify source/engine/coordinate/render mismatch; repair only the discriminating mismatch"
            ),
        },
        "truth": {
            "public_source_assisted_replay": True,
            "independent_generalization": False,
            "hidden_kaggle_score": False,
            "competition_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = run(a.input, a.source)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"aggregate": d["aggregate"], "decision": d["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
