#!/usr/bin/env python3
"""Launch the strongest current R335 full 25-game Kaggle candidate.

Builds from the same Flash/C8 stack, adds stage-1 state patch plus the current
R335 structured-state patch, enforces the C8 full-run contract, and pushes one
private Kaggle kernel in a fresh namespace. This script does NOT submit a
competition entry; submission is a later verified gate.
"""
from __future__ import annotations
import hashlib, http.server, json, os, re, shutil, socketserver, subprocess, sys, threading
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORK=Path("/tmp/deus-r335-full-launch")
KERNEL_REF="lmkimbch/deus-arc-agi3-flash-next-mtp-r335-full-r1"
EXPECTED_STAGE1_SHA="978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
EXPECTED_R335_OVERLAY_SHA="f2adf9b64107dbfa78e2d693e19919889f31debf0fe98f9c5061b28948910388"

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"ok\n"; self.send_response(200); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

def health():
    socketserver.TCPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),H).serve_forever()

def emit(ev,d):
    print(ev+" "+json.dumps(d,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,timeout=300,check=True):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"{Path(cmd[0]).name}:rc{p.returncode}:{(p.stderr or '')[-700:]}")
    return p

def status(exact):
    p=run(["kaggle","kernels","status",exact],timeout=60,check=False)
    return p.returncode,(p.stdout+"\n"+p.stderr).strip()

def main():
    threading.Thread(target=health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        emit("DEUS_R335_FULL_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","competition_submission":False})
        threading.Event().wait(); return
    try:
        run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
        rc,txt=status(KERNEL_REF+"/1")
        if rc==0 and "not found" not in txt.lower():
            raise RuntimeError(f"fresh_full_namespace_not_empty:{txt[:180]}")
        if WORK.exists(): shutil.rmtree(WORK)
        stage=WORK/"stage"; scripts=stage/"scripts"; scripts.mkdir(parents=True)
        for src,dst in [
            ("arc-agi-flash-next-mtp.ipynb","arc-agi-flash-next-mtp.ipynb"),
            ("upstream_build_flash_next_package.py","scripts/build_flash_next_package.py"),
            ("upstream_flash_teardown_patch.py","scripts/flash_teardown_patch.py"),
            ("upstream_flash_agent_state_patch.py","scripts/flash_agent_state_patch.py"),
        ]:
            shutil.copy2(ROOT/src,stage/dst)
        out=stage/"build"/"full"
        run([
            sys.executable,str(scripts/"build_flash_next_package.py"),
            "--kernel-id",KERNEL_REF,
            "--mode","full",
            "--concurrency","8",
            "--full-runtime-seconds","7200",
            "--analyzer-timeout","900",
            "--agent-state-patch",
            "--output-dir",str(out),
        ],timeout=300)
        nbs=list(out.glob("*.ipynb"))
        if len(nbs)!=1: raise RuntimeError("full_notebook_count")
        before=hashlib.sha256(nbs[0].read_bytes()).hexdigest()
        run([
            sys.executable,str(ROOT/"upstream_flash_r335_structured_state_package_patch.py"),
            "--package-dir",str(out),
            "--receipt",str(WORK/"r335-full-package-patch.json"),
        ],timeout=120)
        after=hashlib.sha256(nbs[0].read_bytes()).hexdigest()
        if before==after: raise RuntimeError("r335_full_patch_no_delta")
        meta=json.loads((out/"kernel-metadata.json").read_text())
        assert meta["id"]==KERNEL_REF
        assert meta["machine_shape"]=="NvidiaRtxPro6000"
        assert meta["enable_internet"] is False
        q=run(["kaggle","kernels","push","-p",str(out),"-t","30000"],timeout=180)
        text=q.stdout+"\n"+q.stderr
        m=re.search(r"Kernel version\s+(\d+)\s+successfully pushed",text,re.I)
        if m:
            ver=int(m.group(1))
        else:
            rc2,txt2=status(KERNEL_REF+"/1")
            if rc2!=0: raise RuntimeError("full_push_exact_version_absent")
            ver=1
        if ver!=1: raise RuntimeError(f"full_namespace_version_race:{ver}")
        rc3,txt3=status(KERNEL_REF+"/1")
        if rc3!=0: raise RuntimeError("full_v1_not_readable_after_push")
        emit("DEUS_R335_FULL_PROVIDER_LAUNCH",{
            "kernel_exact":KERNEL_REF+"/1",
            "notebook_sha256":after,
            "baseline_full_contract":{"games":25,"concurrency":8,"per_game_runtime_seconds":7200,"analyzer_timeout_seconds":900},
            "machine_shape":"NvidiaRtxPro6000",
            "internet":False,
            "stage1_expected_sha256":EXPECTED_STAGE1_SHA,
            "r335_expected_overlay_sha256":EXPECTED_R335_OVERLAY_SHA,
            "status":txt3[:240],
            "competition_submission":False,
            "submission_quota_spent":False,
        })
    except Exception as e:
        emit("DEUS_R335_FULL_HOLD",{"code":type(e).__name__,"detail":str(e)[:500],"competition_submission":False,"submission_quota_spent":False})
    threading.Event().wait()

if __name__=="__main__": main()
