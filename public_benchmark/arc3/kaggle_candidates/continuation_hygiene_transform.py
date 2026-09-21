#!/usr/bin/env python3
"""Clean-room ARC-AGI-3 continuation-hygiene notebook transformer.

Motivation is public behavioral evidence only. No implementation code is copied from
canivel/kaggle, whose repository reports no root license. The transform is deliberately
small: after the Flash/Duck source is importable, make the existing system-prompt
instruction distinguish a terminal action batch from a non-terminal game_over reset.

This module performs no Kaggle calls and does not alter the c8-r2 primary candidate.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path
import re

MARKER = "DEUS_CONTINUATION_HYGIENE_ACTIVE"
OLD_FRAGMENT = "stop acting immediately and re-ground on the next turn."
NEW_FRAGMENT = (
    "stop the current action batch and re-ground on the next turn. "
    "When game_over is reported, treat the next state as a fresh attempt on the "
    "same level and continue the run if valid actions remain."
)
SETUP_MARKER = "# Honour any PYTHONPATH a setup command exported."

RUNTIME_BLOCK = r"""
# DEUS clean-room continuation hygiene v1.
# Behavior-only implementation; no third-party patch code is copied.
import importlib as _deus_importlib

_deus_cont_modules = [
    _deus_importlib.import_module("inference.agent.prompts"),
    _deus_importlib.import_module("inference.agent.tool_agent"),
]
_deus_cont_old = "stop acting immediately and re-ground on the next turn."
_deus_cont_new = (
    "stop the current action batch and re-ground on the next turn. "
    "When game_over is reported, treat the next state as a fresh attempt on the "
    "same level and continue the run if valid actions remain."
)
for _deus_mod in _deus_cont_modules:
    _deus_text = getattr(_deus_mod, "PYTHON_ADDENDUM", None)
    if not isinstance(_deus_text, str):
        raise RuntimeError(
            f"DEUS continuation hygiene: {getattr(_deus_mod, '__name__', '?')} "
            "has no string PYTHON_ADDENDUM"
        )
    if _deus_text.count(_deus_cont_old) != 1:
        raise RuntimeError(
            "DEUS continuation hygiene: prompt anchor drift; refusing to patch"
        )
for _deus_mod in _deus_cont_modules:
    _deus_mod.PYTHON_ADDENDUM = _deus_mod.PYTHON_ADDENDUM.replace(
        _deus_cont_old, _deus_cont_new, 1
    )
print("DEUS_CONTINUATION_HYGIENE_ACTIVE v1 modules=2", flush=True)
"""


def _compile_notebook(notebook: dict, label: str) -> None:
    compiled = 0
    for i, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        compile(
            "".join(cell.get("source", [])),
            f"{label}:cell-{i}",
            "exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        )
        compiled += 1
    if not compiled:
        raise ValueError("notebook has no code cells")


def transform(notebook: dict) -> tuple[dict, int]:
    out = copy.deepcopy(notebook)
    hits = []
    for i, cell in enumerate(out.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if SETUP_MARKER in source:
            hits.append(i)
    if len(hits) != 1:
        raise ValueError(f"setup marker matched {len(hits)} cells; expected 1")
    idx = hits[0]
    source = "".join(out["cells"][idx].get("source", []))
    if MARKER in source:
        raise ValueError("continuation hygiene marker already present")
    source = source.rstrip() + "\n\n" + RUNTIME_BLOCK.strip() + "\n"
    out["cells"][idx]["source"] = source.splitlines(keepends=True)
    _compile_notebook(out, "continuation-hygiene")
    return out, idx


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-notebook", required=True, type=Path)
    p.add_argument("--output-notebook", required=True, type=Path)
    p.add_argument("--metadata", type=Path)
    p.add_argument("--kernel-id")
    p.add_argument("--title")
    p.add_argument("--receipt", type=Path)
    args = p.parse_args()

    source = json.loads(args.input_notebook.read_text(encoding="utf-8"))
    transformed, changed_cell = transform(source)
    args.output_notebook.write_text(
        json.dumps(transformed, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if args.metadata is not None:
        if not (args.kernel_id and args.title):
            raise SystemExit("--metadata requires --kernel-id and --title")
        meta = json.loads(args.metadata.read_text(encoding="utf-8"))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.kernel_id):
            raise SystemExit("invalid kernel id")
        meta["id"] = args.kernel_id
        meta["title"] = args.title
        args.metadata.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "schema": "deus/arc3-cleanroom-continuation-hygiene-transform/1",
        "changed_cell_index": changed_cell,
        "marker": MARKER,
        "old_fragment_present_in_transformer": OLD_FRAGMENT in RUNTIME_BLOCK,
        "new_fragment_present_in_transformer": NEW_FRAGMENT in RUNTIME_BLOCK,
        "truth": {
            "clean_room_behavioral_implementation": True,
            "third_party_patch_code_copied": False,
            "kaggle_calls": False,
            "gpu_model_behavior_verified": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "c8r2_primary_mutated": False,
        },
    }
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
