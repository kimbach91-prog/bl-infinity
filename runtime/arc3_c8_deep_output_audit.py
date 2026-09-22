#!/usr/bin/env python3
"""Receipt-safe read-only diagnostic for the completed ARC3 C8 Kaggle output.

Downloads a completed owner kernel output, runs the pinned immutable auditor
in-process so the first static assertion label is observable, and emits only
sanitized structural metrics.  It never submits to a competition and never
prints credentials or arbitrary artifact/log content.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

KERNEL = "lmkimbch/deus-arc-agi3-flash-next-mtp-c8-full-r2/2"
KAGGLE = os.environ.get("KAGGLE_BIN", "/tmp/kvenv/bin/kaggle")
OUT = Path("/tmp/c8-output")
AUDIT_PATH = Path("/tmp/upstream_audit_flash_output.py")
STATUS = Path("/tmp/deep-audit-status.json")
PORT = int(os.environ.get("PORT", "8080"))


def emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, sort_keys=True), flush=True)


def save(data: dict) -> None:
    STATUS.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_json(name: str) -> dict | None:
    p = OUT / name
    if not p.is_file() or p.is_symlink() or p.stat().st_size > 128 * 1024 * 1024:
        return None
    try:
        value = json.loads(p.read_text())
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def structural_summary() -> dict:
    out: dict[str, Any] = {}
    score = safe_json("score.json")
    if score:
        metadata = score.get("metadata") if isinstance(score.get("metadata"), dict) else {}
        games = score.get("games") if isinstance(score.get("games"), dict) else {}
        out["score"] = score.get("score") if finite_number(score.get("score")) else None
        out["score_game_count"] = metadata.get("game_count") if type(metadata.get("game_count")) is int else len(games)
        out["scoring_version"] = metadata.get("scoring_version") if isinstance(metadata.get("scoring_version"), str) else None
    bm = safe_json("benchmark.json")
    if bm:
        runs = bm.get("game_runs") if isinstance(bm.get("game_runs"), list) else []
        states = Counter(str(r.get("state")) for r in runs if isinstance(r, dict))
        scores = [r.get("final_score") for r in runs if isinstance(r, dict) and finite_number(r.get("final_score"))]
        histories = [r.get("history") for r in runs if isinstance(r, dict) and isinstance(r.get("history"), list)]
        out["benchmark_n_passes"] = bm.get("n_passes")
        out["benchmark_game_count"] = len(runs)
        out["benchmark_states"] = dict(sorted(states.items()))
        out["benchmark_mean"] = round(sum(scores) / len(scores), 9) if scores else None
        out["benchmark_total_actions"] = sum(len(h) for h in histories)
        out["benchmark_has_end_time"] = isinstance(bm.get("end_time"), str)
    td = safe_json("vllm-server-teardown.json")
    if td:
        keys = (
            "shutdown_ok", "identity_valid", "working_dir_validated", "port_closed",
            "final_metrics_preserved", "required_artifacts_preserved", "gpu_query_error_after",
        )
        out["teardown_flags"] = {k: td.get(k) for k in keys}
    prov = safe_json("vllm-setup-provenance.json")
    if prov:
        out["provenance"] = {
            "model_hf_repo": prov.get("model_hf_repo"),
            "model_hf_revision": prov.get("model_hf_revision"),
            "vllm_version": prov.get("vllm_version"),
            "source_identity_sha256": prov.get("source_identity_sha256"),
        }
    return out


def load_auditor():
    spec = importlib.util.spec_from_file_location("flash_auditor", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("AUDITOR_IMPORT_SPEC")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> dict:
    status = {
        "service": "deus-cpu-executor-a",
        "kernel": KERNEL,
        "state": "STARTING",
        "output_downloaded": False,
        "audit_passed": False,
        "submission": False,
        "quota_spent": 0,
    }
    save(status)

    st = subprocess.run([KAGGLE, "kernels", "status", KERNEL], capture_output=True, text=True, timeout=90)
    status["kernel_complete"] = bool(st.returncode == 0 and "COMPLETE" in (st.stdout or "").upper())
    if not status["kernel_complete"]:
        status["state"] = "KERNEL_NOT_COMPLETE"
        save(status)
        return status

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    dl = subprocess.run([KAGGLE, "kernels", "output", KERNEL, "-p", str(OUT)], capture_output=True, text=True, timeout=1200)
    if dl.returncode:
        status["state"] = "OUTPUT_DOWNLOAD_FAIL"
        status["download_error_type"] = "KaggleCLIOutputError"
        save(status)
        return status

    files = [p for p in sorted(OUT.rglob("*")) if p.is_file() and not p.is_symlink()]
    manifest = [{"path": str(p.relative_to(OUT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]
    status.update({
        "output_downloaded": True,
        "file_count": len(files),
        "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "structural": structural_summary(),
    })

    mod = load_auditor()
    try:
        report = mod.audit(
            OUT,
            "full-offline",
            expected_games=25,
            expected_concurrency=8,
            expected_runtime_seconds=7200,
            require_clean=True,
            expected_analyzer_timeout=900,
        )
        status["audit_passed"] = True
        status["state"] = "FULL_AUDIT_PASS"
        status["audit_report_summary"] = {
            k: report.get(k) for k in ("passed", "offline_mean", "game_count", "total_actions")
            if isinstance(report, dict) and k in report
        }
    except (ValueError, KeyError, TypeError, IndexError, OSError, ImportError) as exc:
        # The immutable auditor raises only static validation labels here.  Do not
        # print arbitrary artifact content.
        status["state"] = "FULL_AUDIT_FAIL_DIAGNOSED"
        status["audit_error_type"] = type(exc).__name__
        status["audit_failure_label"] = str(exc)[:300]

    save(status)
    return status


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/audit-status"):
            self.send_response(404); self.end_headers(); return
        try:
            data = json.loads(STATUS.read_text())
        except Exception:
            data = {"service": "deus-cpu-executor-a", "state": "BOOTING"}
        body = json.dumps(data, sort_keys=True).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    try:
        result = main()
        emit("arc3_c8_deep_output_audit", receipt=result)
    except Exception as exc:
        result = {
            "service": "deus-cpu-executor-a", "kernel": KERNEL,
            "state": "DIAGNOSTIC_RUNTIME_ERROR", "error_type": type(exc).__name__,
            "output_downloaded": False, "audit_passed": False,
            "submission": False, "quota_spent": 0,
        }
        save(result); emit("arc3_c8_deep_output_audit", receipt=result)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
