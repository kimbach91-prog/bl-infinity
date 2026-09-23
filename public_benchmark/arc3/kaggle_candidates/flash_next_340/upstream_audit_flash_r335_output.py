#!/usr/bin/env python3
"""Strict read-only audit for the Flash R335 structured-state provider candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import upstream_audit_flash_output as base

STAGE1_PATCH_NAME = "reasoning-world-model-v1"
STAGE1_SOURCE_HASH = "535ee88b81b262fa5aedb785466ade9f3183a6417656fb6733427242baac7c9d"
STAGE1_PATCH_HASH = "978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
R335_PATCH_NAME = "r335-relational-phase-state-v1"
R335_MARKER = "R335_STRUCTURED_STATE_SCHEMA_V1"
R335_RECORD = "flash_r335_structured_state_patch.json"


def audit_r335(root: Path, mode: str, **kwargs) -> dict:
    report = base.audit(
        root,
        mode,
        require_agent_state_patch=False,
        **kwargs,
    )

    state = base.document(root, "flash_agent_state_patch.json")
    base.require(state == {
        "patch": STAGE1_PATCH_NAME,
        "source_sha256": STAGE1_SOURCE_HASH,
        "patched_sha256": STAGE1_PATCH_HASH,
    }, "stage-1 reasoning state patch identity mismatch")

    r335 = base.document(root, R335_RECORD)
    base.require(r335.get("patch") == R335_PATCH_NAME, "R335 patch name mismatch")
    base.require(r335.get("schema_marker") == R335_MARKER, "R335 schema marker mismatch")
    base.require(r335.get("source_sha256") == STAGE1_PATCH_HASH, "R335 source digest mismatch")
    final_hash = r335.get("patched_sha256")
    base.require(
        isinstance(final_hash, str) and len(final_hash) == 64,
        "R335 final digest invalid",
    )
    base.require(
        r335.get("overlay_tool_agent_sha256") == final_hash,
        "R335 overlay record digest mismatch",
    )
    base.require(
        base.digest(root, base.AGENT_OVERLAY_PATH) == final_hash,
        "R335 downloaded overlay digest mismatch",
    )
    overlay = base.read(root, base.AGENT_OVERLAY_PATH).decode("utf-8")
    base.require(overlay.count(R335_MARKER) == 1, "R335 schema marker missing or duplicated")

    kernel_log = kwargs.get("kernel_log")
    if kernel_log:
        log_names=[kernel_log]
    else:
        suffix = "preflight.log" if mode == "preflight" else "full.log"
        log_names=[
            p.name for p in root.iterdir()
            if p.is_file() and not p.is_symlink()
            and p.name.startswith("arc-agi3-flash-next-mtp-")
            and p.name.endswith(suffix)
        ]
    base.require(len(log_names) == 1, "expected one R335 kernel log")
    log = json.loads(base.read(root, log_names[0]))
    text = "".join(row.get("data", "") for row in log)

    base.require(
        state in base.log_json_records(text, "FLASH_AGENT_STATE_PATCH"),
        "stage-1 patch log missing or mismatched",
    )
    base.require(
        r335 in base.log_json_records(text, "FLASH_R335_STRUCTURED_STATE_PATCH"),
        "R335 structured-state patch log missing or mismatched",
    )
    ready = base.log_json_records(text, "FLASH_AGENT_OVERLAY_READY")
    base.require(any(
        isinstance(rec.get("root"), str)
        and rec.get("tool_agent_sha256") == final_hash
        for rec in ready
    ), "R335 final overlay-ready log missing")
    base.require("FLASH_AGENT_OVERLAY_REASSERTED" in text, "R335 overlay not reasserted")
    imported = base.log_json_records(text, "FLASH_AGENT_OVERLAY_IMPORTED")
    base.require(any(
        isinstance(rec.get("tool_agent_path"), str)
        and rec["tool_agent_path"].endswith(base.AGENT_OVERLAY_PATH)
        and rec.get("tool_agent_sha256") == final_hash
        for rec in imported
    ), "R335 final overlay import log missing")

    report["r335_structured_state_patch_required"] = True
    report["r335_patch_name"] = R335_PATCH_NAME
    report["r335_schema_marker"] = R335_MARKER
    report["r335_final_overlay_sha256"] = final_hash
    return report


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--mode", choices=("preflight","full-offline"), required=True)
    ap.add_argument("--expected-games", type=int)
    ap.add_argument("--expected-concurrency", type=int)
    ap.add_argument("--expected-game-id")
    ap.add_argument("--expected-runtime-seconds", type=int)
    ap.add_argument("--expected-gameplay-budget-seconds", type=int)
    ap.add_argument("--require-clean", action="store_true")
    ap.add_argument("--require-runtime-from-ready", action="store_true")
    ap.add_argument("--expected-terminal-grace-seconds", type=int)
    ap.add_argument("--expected-analyzer-timeout", type=int, default=900)
    ap.add_argument("--kernel-log")
    args=ap.parse_args()
    try:
        report=audit_r335(
            args.output_dir,
            args.mode,
            expected_games=args.expected_games,
            expected_concurrency=args.expected_concurrency,
            expected_game_id=args.expected_game_id,
            expected_runtime_seconds=args.expected_runtime_seconds,
            expected_gameplay_budget_seconds=args.expected_gameplay_budget_seconds,
            require_clean=args.require_clean,
            require_runtime_from_ready=args.require_runtime_from_ready,
            expected_terminal_grace_seconds=args.expected_terminal_grace_seconds,
            expected_analyzer_timeout=args.expected_analyzer_timeout,
            kernel_log=args.kernel_log,
        )
    except (ValueError, KeyError, TypeError, IndexError, OSError, ImportError, UnicodeError) as error:
        print(json.dumps({"passed":False,"error_type":type(error).__name__}))
        return 1
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
