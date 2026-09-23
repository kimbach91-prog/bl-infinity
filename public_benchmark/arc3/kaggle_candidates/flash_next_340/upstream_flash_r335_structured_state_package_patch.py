#!/usr/bin/env python3
"""Apply the frozen R335 relational/phase state schema to a generated Flash package.

This is a bounded second-stage patch. It preserves the already digest-bound
reasoning-world-model-v1 patch as stage 1, then appends only a generic,
game-ID-blind structured-state instruction to the agent prompt.

The package must already have been built with --agent-state-patch.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

PACKAGE_MARKER = ".arc-agi-kaggle-package"
STAGE1_SHA256 = "978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
PATCH_NAME = "r335-relational-phase-state-v1"
SCHEMA_MARKER = "R335_STRUCTURED_STATE_SCHEMA_V1"

PATCH_SOURCE = r'''
R335_STRUCTURED_STATE_PATCH_NAME = "r335-relational-phase-state-v1"
R335_STRUCTURED_STATE_SOURCE_SHA256 = "978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
R335_STRUCTURED_STATE_SCHEMA_MARKER = "R335_STRUCTURED_STATE_SCHEMA_V1"
R335_WORLD_MODEL_ANCHOR = (
    "Maintain a compact working world model of what the current level seems to contain, "
    "what actions appear to do, what the goal seems to be, what is still uncertain, "
    "and what plan currently looks best."
)
R335_WORLD_MODEL_EXTENSION = (
    R335_WORLD_MODEL_ANCHOR
    + r"\n- R335_STRUCTURED_STATE_SCHEMA_V1: When the visible evidence uniquely supports it, represent relational state using translation/D4-equivalent token identity, relation or sequence segmentation, composition, and inverse constraints; represent control state using editable sites, cursor position, cyclic phase or offset, and observed action effects."
    + r"\n- Keep this schema generic and evidence-bounded. Never branch on a game ID, never replay a memorized script, and never force a relational or phase model when the frame topology or transition evidence is ambiguous."
    + r"\n- Prefer unique-or-abstain: if multiple structural programs or action interpretations remain consistent, record the ambiguity in the existing world/action model and gather discriminating evidence before acting."
)

def patch_tool_agent_r335(source: bytes) -> str:
    if "\n" in R335_WORLD_MODEL_EXTENSION:
        raise ValueError("R335 extension must contain escaped newline tokens, not physical newlines.")
    if hashlib.sha256(source).hexdigest() != R335_STRUCTURED_STATE_SOURCE_SHA256:
        raise ValueError("Flash stage-1 agent digest changed; refusing R335 structured-state patch.")
    text = source.decode("utf-8")
    if text.count(R335_WORLD_MODEL_ANCHOR) != 1:
        raise ValueError("R335 world-model prompt anchor did not match exactly once.")
    text = text.replace(R335_WORLD_MODEL_ANCHOR, R335_WORLD_MODEL_EXTENSION, 1)
    if text.count(R335_STRUCTURED_STATE_SCHEMA_MARKER) != 1:
        raise ValueError("R335 structured-state marker count mismatch.")
    compile(text, "flash_tool_agent_r335.py", "exec")
    return text
'''

OLD_APPLY = '_agent_patched = patch_tool_agent(_agent_original)\n'
NEW_APPLY = '''_agent_state_patched = patch_tool_agent(_agent_original)
if hashlib.sha256(_agent_state_patched.encode("utf-8")).hexdigest() != R335_STRUCTURED_STATE_SOURCE_SHA256:
    raise RuntimeError("Flash stage-1 state patch digest changed before R335 integration.")
_agent_patched = patch_tool_agent_r335(_agent_state_patched.encode("utf-8"))
'''

OLD_RECORD = '''_agent_patch_record = {
    "patch": PATCH_NAME,
    "source_sha256": hashlib.sha256(_agent_original).hexdigest(),
    "patched_sha256": hashlib.sha256(_agent_patched.encode("utf-8")).hexdigest(),
    "overlay_tool_agent_sha256": hashlib.sha256(_agent_overlay_path.read_bytes()).hexdigest(),
}
if _agent_patch_record["patched_sha256"] != _agent_patch_record["overlay_tool_agent_sha256"]:
    raise RuntimeError("Flash agent-state overlay digest changed while staging.")
(WORKING_DIR / "flash_agent_state_patch.json").write_text(
    json.dumps(_agent_patch_record, indent=2) + "\\n", encoding="utf-8"
)
print("FLASH_AGENT_STATE_PATCH", json.dumps(_agent_patch_record), flush=True)
'''

NEW_RECORD = '''_agent_state_patch_record = {
    "patch": PATCH_NAME,
    "source_sha256": hashlib.sha256(_agent_original).hexdigest(),
    "patched_sha256": hashlib.sha256(_agent_state_patched.encode("utf-8")).hexdigest(),
}
_r335_patch_record = {
    "patch": R335_STRUCTURED_STATE_PATCH_NAME,
    "schema_marker": R335_STRUCTURED_STATE_SCHEMA_MARKER,
    "source_sha256": hashlib.sha256(_agent_state_patched.encode("utf-8")).hexdigest(),
    "patched_sha256": hashlib.sha256(_agent_patched.encode("utf-8")).hexdigest(),
    "overlay_tool_agent_sha256": hashlib.sha256(_agent_overlay_path.read_bytes()).hexdigest(),
}
if _r335_patch_record["patched_sha256"] != _r335_patch_record["overlay_tool_agent_sha256"]:
    raise RuntimeError("Flash R335 structured-state overlay digest changed while staging.")
(WORKING_DIR / "flash_agent_state_patch.json").write_text(
    json.dumps(_agent_state_patch_record, indent=2) + "\\n", encoding="utf-8"
)
(WORKING_DIR / "flash_r335_structured_state_patch.json").write_text(
    json.dumps(_r335_patch_record, indent=2) + "\\n", encoding="utf-8"
)
print("FLASH_AGENT_STATE_PATCH", json.dumps(_agent_state_patch_record), flush=True)
print("FLASH_R335_STRUCTURED_STATE_PATCH", json.dumps(_r335_patch_record), flush=True)
_agent_patch_record = _r335_patch_record
'''


def patch_package(root: Path) -> dict:
    root = root.resolve()
    marker = root / PACKAGE_MARKER
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != "owned":
        raise ValueError("Refusing to patch an unowned Flash package.")

    notebooks = list(root.glob("*.ipynb"))
    if len(notebooks) != 1:
        raise ValueError(f"Expected exactly one notebook, got {len(notebooks)}")
    path = notebooks[0]
    doc = json.loads(path.read_text(encoding="utf-8"))

    target = None
    for cell in doc.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        text = "".join(cell.get("source", []))
        if "_agent_source_path = BUNDLE_DIR" in text and OLD_APPLY in text:
            if target is not None:
                raise ValueError("R335 target cell matched more than once.")
            target = cell
    if target is None:
        raise ValueError("R335 target cell not found.")

    text = "".join(target["source"])
    if text.count(OLD_APPLY) != 1:
        raise ValueError("R335 stage-1 apply anchor did not match exactly once.")
    if text.count(OLD_RECORD) != 1:
        raise ValueError("R335 patch-record anchor did not match exactly once.")
    if SCHEMA_MARKER in text:
        raise ValueError("Package already contains the R335 structured-state marker.")

    text = PATCH_SOURCE + "\n" + text
    text = text.replace(OLD_APPLY, NEW_APPLY, 1)
    text = text.replace(OLD_RECORD, NEW_RECORD, 1)
    target["source"] = text.splitlines(keepends=True)

    compile(PATCH_SOURCE, "r335_structured_state_patch_source.py", "exec")
    ns = {"hashlib": hashlib}
    exec(PATCH_SOURCE, ns)
    anchor = ns["R335_WORLD_MODEL_ANCHOR"]
    extension = ns["R335_WORLD_MODEL_EXTENSION"]
    sample = 'PROMPT = ("' + anchor + '\\n")\n'
    patched_sample = sample.replace(anchor, extension, 1)
    compile(patched_sample, "r335_prompt_escape_selftest.py", "exec")
    if SCHEMA_MARKER not in patched_sample:
        raise ValueError("R335 prompt-escape selftest marker missing.")
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    reparsed = json.loads(path.read_text(encoding="utf-8"))
    for idx, cell in enumerate(reparsed.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        compile(source, f"{path.name}:cell-{idx}", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in reparsed.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    if code.count(SCHEMA_MARKER) < 1:
        raise ValueError("R335 structured-state marker absent after patch.")
    if "patch_tool_agent_r335" not in code:
        raise ValueError("R335 patch function absent after patch.")

    return {
        "schema": "deus/arc3-flash-r335-package-patch/1",
        "patch": PATCH_NAME,
        "stage1_source_sha256": STAGE1_SHA256,
        "schema_marker": SCHEMA_MARKER,
        "notebook": path.name,
        "notebook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-dir", type=Path, required=True)
    ap.add_argument("--receipt", type=Path)
    a = ap.parse_args()
    receipt = patch_package(a.package_dir)
    if a.receipt:
        a.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
