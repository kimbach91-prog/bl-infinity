#!/usr/bin/env python3
"""Exact-runtime-source self-test for the repaired R335 Flash prompt patch.

Read-only against the completed baseline kernel. Downloads baseline output,
extracts the exact stage-1 tool_agent.py, applies the current PATCH_SOURCE in
memory, compiles the result, and emits a bounded receipt. No kernel push/run or
competition submission is performed.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import threading
from pathlib import Path

import upstream_flash_r335_structured_state_package_patch as pkg

BASE_EXACT="lmkimbch/deus-arc3-r338-base-tr87/1"
EXPECTED_STAGE1_SHA="978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
ROOT=Path("/tmp/r335-exact-selftest")

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"ok\n"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

def health():
    socketserver.TCPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),H).serve_forever()

def emit(ev,d):
    print(ev+" "+json.dumps(d,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,timeout=180):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{Path(cmd[0]).name}:rc{p.returncode}:{p.stderr[-240:]}")
    return p

def main():
    threading.Thread(target=health,daemon=True).start()
    if ROOT.exists(): shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        emit("DEUS_R335_EXACT_SELFTEST_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT"})
        threading.Event().wait(); return
    try:
        run(["kaggle","kernels","output",BASE_EXACT,"-p",str(ROOT)])
        src=ROOT/"flash_agent_overlay/inference/agent/tool_agent.py"
        if not src.is_file():
            raise RuntimeError("baseline_stage1_tool_agent_missing")
        raw=src.read_bytes()
        h=hashlib.sha256(raw).hexdigest()
        if h!=EXPECTED_STAGE1_SHA:
            raise RuntimeError(f"stage1_sha_mismatch:{h}")
        ns={"hashlib":hashlib}
        exec(pkg.PATCH_SOURCE,ns)
        patched=ns["patch_tool_agent_r335"](raw)
        compile(patched,"flash_tool_agent_r335_exact_selftest.py","exec")
        marker_count=patched.count(pkg.SCHEMA_MARKER)
        anchor_count=raw.decode("utf-8").count(ns["R335_WORLD_MODEL_ANCHOR"])
        receipt={
            "schema":"deus/arc3-r335-exact-runtime-source-selftest/1",
            "base_exact":BASE_EXACT,
            "stage1_sha256":h,
            "patched_sha256":hashlib.sha256(patched.encode("utf-8")).hexdigest(),
            "anchor_count":anchor_count,
            "marker_count":marker_count,
            "compile_pass":True,
            "single_line_extension":("\n" not in ns["R335_WORLD_MODEL_EXTENSION"] and "\r" not in ns["R335_WORLD_MODEL_EXTENSION"]),
            "kernel_push":False,
            "competition_submission":False,
            "submission_quota_spent":False,
        }
        if anchor_count!=1 or marker_count!=1 or not receipt["single_line_extension"]:
            raise RuntimeError("selftest_invariant_failed")
        emit("DEUS_R335_EXACT_SELFTEST_PASS",receipt)
    except Exception as exc:
        emit("DEUS_R335_EXACT_SELFTEST_HOLD",{
            "code":type(exc).__name__,
            "detail":str(exc)[:240],
            "kernel_push":False,
            "competition_submission":False,
        })
    threading.Event().wait()

if __name__=="__main__":
    main()
