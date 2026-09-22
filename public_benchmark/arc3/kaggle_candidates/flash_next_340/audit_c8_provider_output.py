#!/usr/bin/env python3
"""Audit the exact C8 Kaggle output without mutating downloaded artifacts.

The upstream auditor historically expects an explicit kernel log basename to
start with ``arc-agi3-flash-next-mtp-``. Kaggle names the downloaded notebook
log from the notebook slug (``deus-arc-agi3-flash-next-mtp-c8-full-r2.log``).
This adapter verifies the pinned upstream auditor bytes and removes only that
prefix check for the explicit ``--kernel-log`` path. The existing basename
(traversal) and ``.log`` checks remain intact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

UPSTREAM = "upstream_audit_flash_output.py"
UPSTREAM_SHA256 = "0ec3ddbc423f6e51f7564f59b1224be75cea7dc8db2ef174f63daa15c4fcefc2"
PATCH_ANCHOR = "kernel_log.startswith(log_prefix) and "
DEFAULT_PROVIDER_LOG = "deus-arc-agi3-flash-next-mtp-c8-full-r2.log"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_adapted_auditor():
    source_path = Path(__file__).with_name(UPSTREAM)
    source = source_path.read_text()
    if sha256_text(source) != UPSTREAM_SHA256:
        raise ValueError("upstream auditor digest mismatch")
    if source.count(PATCH_ANCHOR) != 1:
        raise ValueError("provider-log patch anchor mismatch")
    patched = source.replace(PATCH_ANCHOR, "", 1)
    handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    try:
        handle.write(patched)
        handle.close()
        path = Path(handle.name)
        spec = importlib.util.spec_from_file_location("c8_provider_auditor", path)
        if spec is None or spec.loader is None:
            raise ImportError("unable to load adapted auditor")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module, sha256_text(patched)
    finally:
        try:
            Path(handle.name).unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--kernel-log", default=DEFAULT_PROVIDER_LOG)
    args = parser.parse_args()

    try:
        auditor, adapted_sha256 = load_adapted_auditor()
        result = auditor.audit(
            args.output_dir,
            "full-offline",
            expected_games=25,
            expected_concurrency=8,
            expected_runtime_seconds=7200,
            require_clean=True,
            expected_analyzer_timeout=900,
            kernel_log=args.kernel_log,
        )
    except (ValueError, KeyError, TypeError, IndexError, OSError, ImportError) as error:
        print(json.dumps({
            "passed": False,
            "error_type": type(error).__name__,
            "failure_label": str(error)[:240],
            "submission": False,
            "quota_spent": 0,
        }, sort_keys=True))
        return 1

    print(json.dumps({
        "passed": bool(result.get("passed")),
        "mode": result.get("mode"),
        "kernel_log": result.get("kernel_log"),
        "game_count": result.get("game_count"),
        "offline_mean": result.get("offline_mean"),
        "total_actions": result.get("total_actions"),
        "upstream_sha256": UPSTREAM_SHA256,
        "adapted_sha256": adapted_sha256,
        "output_artifacts_mutated": False,
        "submission": False,
        "quota_spent": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
