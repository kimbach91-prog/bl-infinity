#!/usr/bin/env python3
"""One-shot Railway executor for matched private Flash R335 A/B.

Uses the service's already-bound Kaggle machine credential. It launches two
private Kaggle preflight kernels only, polls exact versions, downloads outputs,
runs strict audits, and never calls any competition-submission endpoint.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORK=Path("/tmp/deus-r335-flash-provider")
GAME="tr87-cd924810"
RUNTIME=1200
GRACE=120
CONCURRENCY=1
ANALYZER=900
BASE_REF="lmkimbch/deus-arc3-r338-base-tr87"
STATE_REF="lmkimbch/deus-arc3-r338-state-tr87"
EVENT_FINAL="DEUS_R335_FLASH_PROVIDER_FINAL"
EVENT_LAUNCH="DEUS_R335_FLASH_PROVIDER_LAUNCH"
EVENT_HOLD="DEUS_R335_FLASH_PROVIDER_HOLD"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b"ok\n"
        self.send_response(200); self.send_header("Content-Type","text/plain")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args):
        pass

def health():
    port=int(os.environ.get("PORT","8080"))
    server=socketserver.TCPServer(("0.0.0.0",port),Handler)
    server.serve_forever()

def emit(event,payload):
    print(event+" "+json.dumps(payload,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,*,cwd=None,timeout=None,check=True):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"command_failed:{Path(cmd[0]).name}:rc{p.returncode}")
    return p

def one_nb(root):
    xs=list(Path(root).glob("*.ipynb"))
    if len(xs)!=1: raise RuntimeError("package_notebook_count")
    return xs[0]

def stage_packages():
    if WORK.exists(): shutil.rmtree(WORK)
    stage=WORK/"stage"; scripts=stage/"scripts"; scripts.mkdir(parents=True)
    shutil.copy2(ROOT/"arc-agi-flash-next-mtp.ipynb",stage/"arc-agi-flash-next-mtp.ipynb")
    shutil.copy2(ROOT/"upstream_build_flash_next_package.py",scripts/"build_flash_next_package.py")
    shutil.copy2(ROOT/"upstream_flash_teardown_patch.py",scripts/"flash_teardown_patch.py")
    shutil.copy2(ROOT/"upstream_flash_agent_state_patch.py",scripts/"flash_agent_state_patch.py")
    base=stage/"build"/"base"; state=stage/"build"/"state"
    common=[
        "--mode","preflight","--max-games","1","--game-id",GAME,
        "--concurrency",str(CONCURRENCY),"--runtime-seconds",str(RUNTIME),
        "--terminal-grace-seconds",str(GRACE),"--analyzer-timeout",str(ANALYZER),
        "--agent-state-patch",
    ]
    run([sys.executable,str(scripts/"build_flash_next_package.py"),"--kernel-id",BASE_REF,*common,"--output-dir",str(base)])
    run([sys.executable,str(scripts/"build_flash_next_package.py"),"--kernel-id",STATE_REF,*common,"--output-dir",str(state)])
    bh=hashlib.sha256(one_nb(base).read_bytes()).hexdigest()
    sh=hashlib.sha256(one_nb(state).read_bytes()).hexdigest()
    if bh!=sh: raise RuntimeError("prepatch_packages_not_identical")
    run([sys.executable,str(ROOT/"upstream_flash_r335_structured_state_package_patch.py"),
         "--package-dir",str(state),"--receipt",str(WORK/"r335-package-patch.json")])
    fh=hashlib.sha256(one_nb(state).read_bytes()).hexdigest()
    if fh==bh: raise RuntimeError("r335_patch_no_delta")
    return base,state,bh,fh

def push(root):
    p=run(["kaggle","kernels","push","-p",str(root),"-t","30000"],timeout=120)
    txt=p.stdout+"\n"+p.stderr
    m=re.search(r"Kernel version\s+(\d+)\s+successfully pushed",txt,re.I)
    if not m: raise RuntimeError("provider_exact_version_absent")
    return int(m.group(1))

def wait_complete(exact,deadline):
    last=""
    while time.time()<deadline:
        p=run(["kaggle","kernels","status",exact],check=False,timeout=60)
        last=(p.stdout+"\n"+p.stderr).strip()
        low=last.lower()
        if p.returncode==0 and ("complete" in low or "completed" in low):
            return True
        if any(x in low for x in ("error","failed","cancelled")) and "complete" not in low:
            raise RuntimeError("provider_terminal_failure")
        time.sleep(25)
    return False

def download_and_audit(exact,out,r335):
    out.mkdir(parents=True,exist_ok=True)
    run(["kaggle","kernels","output",exact,"-p",str(out)],timeout=180)
    logs=sorted(p.name for p in out.glob("arc-agi3-flash-next-mtp-*.log"))
    if len(logs)!=1: raise RuntimeError("kernel_log_count")
    auditor=ROOT/("upstream_audit_flash_r335_output.py" if r335 else "upstream_audit_flash_output.py")
    cmd=[
        sys.executable,str(auditor),"--mode","preflight","--expected-games","1",
        "--expected-concurrency",str(CONCURRENCY),"--expected-game-id",GAME,
        "--expected-runtime-seconds",str(RUNTIME),"--expected-gameplay-budget-seconds",str(RUNTIME),
        "--require-runtime-from-ready","--expected-terminal-grace-seconds",str(GRACE),
        "--expected-analyzer-timeout",str(ANALYZER),"--require-clean","--kernel-log",logs[0],
    ]
    if not r335: cmd.append("--require-agent-state-patch")
    cmd.append(str(out))
    p=run(cmd,timeout=180)
    report=json.loads(p.stdout)
    if report.get("passed") is not True: raise RuntimeError("strict_audit_failed")
    return report

def main():
    threading.Thread(target=health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        emit(EVENT_HOLD,{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","competition_submission":False})
        threading.Event().wait()
        return
    run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
    try:
        base,state,bh,sh=stage_packages()
        bv=push(base); sv=push(state)
        launch={
            "base_exact":f"{BASE_REF}/{bv}","state_exact":f"{STATE_REF}/{sv}",
            "base_notebook_sha256":bh,"state_notebook_sha256":sh,
            "game_id":GAME,"runtime_seconds":RUNTIME,"competition_submission":False,
            "submission_quota_spent":False,
        }
        emit(EVENT_LAUNCH,launch)
        deadline=time.time()+3900
        bc=wait_complete(launch["base_exact"],deadline)
        sc=wait_complete(launch["state_exact"],deadline)
        if not (bc and sc):
            emit(EVENT_HOLD,{**launch,"code":"PROVIDER_TIMEOUT","base_complete":bc,"state_complete":sc})
            threading.Event().wait(); return
        ba=download_and_audit(launch["base_exact"],WORK/"base-output",False)
        sa=download_and_audit(launch["state_exact"],WORK/"state-output",True)
        bm=float(ba.get("offline_mean",0)); sm=float(sa.get("offline_mean",0))
        bact=int(ba.get("total_actions",0)); sact=int(sa.get("total_actions",0))
        if sm>bm: verdict="PROMOTE_TO_WIDER_PROVIDER_TEST"
        elif sm==bm and sact<bact: verdict="PROMOTE_EFFICIENCY_ONLY"
        else: verdict="RETAIN_BASE"
        final={
            **launch,
            "status":"MATCHED_AUDIT_COMPLETE","verdict":verdict,
            "base_offline_mean":bm,"state_offline_mean":sm,
            "base_actions":bact,"state_actions":sact,
            "base_audit_passed":True,"state_audit_passed":True,
            "competition_submission":False,"submission_quota_spent":False,
            "leaderboard_score_observed":False,"candidate_promoted":False,
        }
        emit(EVENT_FINAL,final)
    except Exception as e:
        emit(EVENT_HOLD,{"code":type(e).__name__,"detail":str(e)[:160],
                         "competition_submission":False,"submission_quota_spent":False})
    threading.Event().wait()

if __name__=="__main__":
    main()
