#!/usr/bin/env python3
"""Read-only recovery/verification observer for exact existing R335 Flash provider refs.

Never pushes kernels and never submits a competition entry. It polls the two exact
private kernel versions launched by the matched provider run, downloads outputs
only after both are terminal, runs strict audits, and emits an attributable final
comparison receipt.
"""
from __future__ import annotations

import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WORK=Path("/tmp/deus-r335-flash-observer")
GAME="tr87-cd924810"
RUNTIME=1200
GRACE=120
CONCURRENCY=1
ANALYZER=900
BASE_EXACT="lmkimbch/deus-arc3-r338-base-tr87/1"
STATE_EXACT="lmkimbch/deus-arc3-r338-state-tr87/1"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b"ok\n"; self.send_response(200); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

def health():
    socketserver.TCPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),Handler).serve_forever()

def emit(event,payload):
    print(event+" "+json.dumps(payload,sort_keys=True,separators=(",",":")),flush=True)

def run(cmd,timeout=180,check=True):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"{Path(cmd[0]).name}:rc{p.returncode}:{p.stderr[-160:]}")
    return p

def status(exact):
    p=run(["kaggle","kernels","status",exact],timeout=60,check=False)
    return p.returncode,(p.stdout+"\n"+p.stderr).strip()

def wait_pair(deadline):
    last={}
    while time.time()<deadline:
        complete=True
        for lane,exact in (("base",BASE_EXACT),("state",STATE_EXACT)):
            rc,txt=status(exact)
            low=txt.lower()
            is_complete=rc==0 and ("complete" in low or "completed" in low)
            last[lane]={"rc":rc,"complete":is_complete}
            if not is_complete:
                complete=False
                if any(x in low for x in ("failed","error","cancelled")) and "complete" not in low:
                    raise RuntimeError(f"{lane}_terminal_failure")
        emit("DEUS_R335_FLASH_OBSERVER_STATUS",last)
        if complete:return last
        time.sleep(30)
    return last

def audit_output(exact,out,r335):
    out.mkdir(parents=True,exist_ok=True)
    run(["kaggle","kernels","output",exact,"-p",str(out)],timeout=180)
    logs=sorted(p.name for p in out.glob("arc-agi3-flash-next-mtp-*.log"))
    if len(logs)!=1: raise RuntimeError("kernel_log_count")
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    import upstream_audit_flash_output as base
    common=dict(
        check_parquet=False, expected_games=1, expected_concurrency=CONCURRENCY,
        expected_game_id=GAME, expected_runtime_seconds=RUNTIME,
        expected_gameplay_budget_seconds=RUNTIME, require_clean=True,
        require_runtime_from_ready=True, expected_terminal_grace_seconds=GRACE,
        expected_analyzer_timeout=ANALYZER, kernel_log=logs[0],
    )
    if r335:
        import upstream_audit_flash_r335_output as rr
        d=rr.audit_r335(out,"preflight",**common)
    else:
        d=base.audit(out,"preflight",require_agent_state_patch=True,**common)
    if d.get("passed") is not True: raise RuntimeError("strict_audit_failed")
    return d

def main():
    threading.Thread(target=health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        emit("DEUS_R335_FLASH_OBSERVER_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","kernel_push":False,"competition_submission":False})
        threading.Event().wait(); return
    run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
    if WORK.exists(): shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    try:
        emit("DEUS_R335_FLASH_OBSERVER_START",{
            "base_exact":BASE_EXACT,"state_exact":STATE_EXACT,
            "kernel_push":False,"competition_submission":False
        })
        last=wait_pair(time.time()+3900)
        if not all(v.get("complete") for v in last.values()):
            emit("DEUS_R335_FLASH_OBSERVER_HOLD",{"code":"PROVIDER_TIMEOUT","status":last,"kernel_push":False,"competition_submission":False})
            threading.Event().wait(); return
        b=audit_output(BASE_EXACT,WORK/"base",False)
        s=audit_output(STATE_EXACT,WORK/"state",True)
        bm=float(b.get("offline_mean",0)); sm=float(s.get("offline_mean",0))
        ba=int(b.get("total_actions",0)); sa=int(s.get("total_actions",0))
        if sm>bm: verdict="PROMOTE_TO_WIDER_PROVIDER_TEST"
        elif sm==bm and sa<ba: verdict="PROMOTE_EFFICIENCY_ONLY"
        else: verdict="RETAIN_BASE"
        emit("DEUS_R335_FLASH_OBSERVER_FINAL",{
            "base_exact":BASE_EXACT,"state_exact":STATE_EXACT,
            "base_offline_mean":bm,"state_offline_mean":sm,
            "base_actions":ba,"state_actions":sa,
            "base_audit_passed":True,"state_audit_passed":True,
            "verdict":verdict,"kernel_push":False,
            "competition_submission":False,"submission_quota_spent":False,
        })
    except Exception as e:
        emit("DEUS_R335_FLASH_OBSERVER_HOLD",{"code":type(e).__name__,"detail":str(e)[:200],
             "kernel_push":False,"competition_submission":False,"submission_quota_spent":False})
    threading.Event().wait()

if __name__=="__main__":
    main()
