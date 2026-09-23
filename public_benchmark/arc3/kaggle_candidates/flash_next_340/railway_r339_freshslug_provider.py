#!/usr/bin/env python3
"""R335 recovery v2: fresh-slug, single-writer matched provider A/B.

The broken candidate slug accumulated ambiguous/failed history. This recovery
creates exactly one fresh private candidate slug after compiling the current
R335 patch against the exact completed baseline stage-1 source. It reuses the
completed baseline and never calls a competition submission endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import railway_r335_flash_provider as p
import upstream_flash_r335_structured_state_package_patch as pkg

BASE_REF="lmkimbch/deus-arc3-r338-base-tr87"
CAND_REF="lmkimbch/deus-arc3-r339-r335-repaired-tr87"
EXPECTED_BASE_NOTEBOOK_SHA="2fe65f106a7ef34e44d5e12f3133fa471669e78ffeac1e67a558a20c118aca1c"
EXPECTED_STAGE1_SHA="978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
EXPECTED_REPAIRED_OVERLAY_SHA="f2adf9b64107dbfa78e2d693e19919889f31debf0fe98f9c5061b28948910388"

def list_mine(search: str):
    q=p.run([
        "kaggle","kernels","list","--mine","--search",search,
        "--format","json","--sort-by","dateRun","--page-size","50"
    ],timeout=90)
    try:
        rows=json.loads(q.stdout or "[]")
    except Exception as exc:
        raise RuntimeError(f"kernel_list_json_parse:{type(exc).__name__}")
    return [r for r in rows if isinstance(r,dict)]

def exact_row(ref: str):
    rows=list_mine(ref.split("/",1)[1])
    return next((r for r in rows if r.get("ref")==ref),None)

def exact_source_selftest():
    root=p.WORK/"r339-exact-source-selftest"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    p.run(["kaggle","kernels","output",BASE_REF,"-p",str(root)],timeout=240)
    src=root/"flash_agent_overlay/inference/agent/tool_agent.py"
    if not src.is_file(): raise RuntimeError("baseline_stage1_tool_agent_missing")
    raw=src.read_bytes()
    h=hashlib.sha256(raw).hexdigest()
    if h!=EXPECTED_STAGE1_SHA:
        raise RuntimeError(f"stage1_sha_mismatch:{h}")
    ns={"hashlib":hashlib}
    exec(pkg.PATCH_SOURCE,ns)
    patched=ns["patch_tool_agent_r335"](raw)
    compile(patched,"flash_tool_agent_r335_r339_selftest.py","exec")
    ph=hashlib.sha256(patched.encode("utf-8")).hexdigest()
    if ph!=EXPECTED_REPAIRED_OVERLAY_SHA:
        raise RuntimeError(f"repaired_overlay_sha_mismatch:{ph}")
    p.emit("DEUS_R339_EXACT_SOURCE_SELFTEST",{
        "base_ref":BASE_REF,"stage1_sha256":h,
        "repaired_overlay_sha256":ph,"compile_pass":True,
        "kernel_push":False,"competition_submission":False,
    })

def build_candidate():
    old_state=p.STATE_REF
    try:
        p.STATE_REF=CAND_REF
        base,state,bh,sh=p.stage_packages()
    finally:
        p.STATE_REF=old_state
    if bh!=EXPECTED_BASE_NOTEBOOK_SHA:
        raise RuntimeError(f"baseline_notebook_sha_changed:{bh}")
    return base,state,bh,sh

def push_fresh(state_dir: Path):
    before=exact_row(CAND_REF)
    if before is not None:
        raise RuntimeError(
            "fresh_candidate_slug_already_exists:"
            + json.dumps({k:before.get(k) for k in ("ref","lastRunTime","title")},sort_keys=True)
        )
    q=subprocess.run(
        ["kaggle","kernels","push","-p",str(state_dir),"-t","30000"],
        text=True,capture_output=True,timeout=240
    )
    raw=(q.stdout or "")+"\n"+(q.stderr or "")
    p.emit("DEUS_R339_PUSH_RAW",{
        "returncode":q.returncode,
        "stdout":(q.stdout or "")[-1600:],
        "stderr":(q.stderr or "")[-1600:],
        "competition_submission":False,
    })
    if q.returncode!=0:
        raise RuntimeError(f"kaggle_push_rc{q.returncode}")
    m=re.search(r"Kernel version\s+(\d+)\s+successfully pushed",raw,re.I)
    parsed_version=int(m.group(1)) if m else None

    deadline=time.time()+180
    row=None
    while time.time()<deadline:
        row=exact_row(CAND_REF)
        if row is not None and row.get("lastRunTime"):
            break
        time.sleep(4)
    if row is None:
        raise RuntimeError("fresh_candidate_not_visible_after_push")
    p.emit("DEUS_R339_PROVIDER_LAUNCH",{
        "candidate_ref":CAND_REF,
        "parsed_version":parsed_version,
        "provider_lastRunTime":row.get("lastRunTime"),
        "provider_title":row.get("title"),
        "single_writer":True,
        "competition_submission":False,
        "submission_quota_spent":False,
    })
    return row,parsed_version

def wait_terminal(ref: str, deadline: float):
    last=""
    while time.time()<deadline:
        q=p.run(["kaggle","kernels","status",ref],check=False,timeout=60)
        last=((q.stdout or "")+"\n"+(q.stderr or "")).strip()
        low=last.lower()
        p.emit("DEUS_R339_PROVIDER_STATUS",{"ref":ref,"status":last[:300]})
        if q.returncode==0 and ("complete" in low or "completed" in low):
            return "COMPLETE",last
        if any(x in low for x in ("error","failed","cancelled")) and "complete" not in low:
            return "ERROR",last
        time.sleep(30)
    return "TIMEOUT",last

def pull_diagnostics(ref: str):
    out=p.WORK/"r339-error-output"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    q=p.run(["kaggle","kernels","output",ref,"-p",str(out)],check=False,timeout=240)
    files=[{"path":str(x.relative_to(out)),"bytes":x.stat().st_size} for x in out.rglob("*") if x.is_file()]
    hits=[]
    pattern=re.compile(r"(Traceback|SyntaxError|RuntimeError|ValueError|ERROR|Exception encountered|FLASH_R335|FLASH_AGENT)",re.I)
    for x in out.rglob("*"):
        if not x.is_file() or x.stat().st_size>25_000_000: continue
        try: txt=x.read_text(errors="replace")
        except Exception: continue
        for line in txt.splitlines():
            if pattern.search(line):
                hits.append({"file":str(x.relative_to(out)),"line":line[:900]})
                if len(hits)>=80: break
        if len(hits)>=80: break
    p.emit("DEUS_R339_PROVIDER_DIAGNOSTIC",{
        "ref":ref,"output_rc":q.returncode,"files":files[:80],"hits":hits
    })

def main():
    threading.Thread(target=p.health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        p.emit("DEUS_R339_RECOVERY_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","competition_submission":False})
        threading.Event().wait(); return

    try:
        p.run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
        exact_source_selftest()
        base,state,bh,sh=build_candidate()
        row,parsed_version=push_fresh(state)
        state_status,state_text=wait_terminal(CAND_REF,time.time()+4200)
        if state_status!="COMPLETE":
            pull_diagnostics(CAND_REF)
            p.emit("DEUS_R339_RECOVERY_HOLD",{
                "code":"CANDIDATE_PROVIDER_"+state_status,
                "candidate_ref":CAND_REF,
                "provider_status":state_text[:400],
                "candidate_notebook_sha256":sh,
                "competition_submission":False,
                "submission_quota_spent":False,
            })
            threading.Event().wait(); return

        base_status,_=wait_terminal(BASE_REF,time.time()+180)
        if base_status!="COMPLETE":
            raise RuntimeError(f"baseline_not_complete:{base_status}")

        ba=p.download_and_audit(BASE_REF,p.WORK/"r339-base-audit",False)
        sa=p.download_and_audit(CAND_REF,p.WORK/"r339-state-audit",True)
        bm=float(ba.get("offline_mean",0)); sm=float(sa.get("offline_mean",0))
        bact=int(ba.get("total_actions",0)); sact=int(sa.get("total_actions",0))
        if sm>bm:
            verdict="PROMOTE_TO_WIDER_PROVIDER_TEST"
        elif sm==bm and sact<bact:
            verdict="PROMOTE_EFFICIENCY_ONLY"
        else:
            verdict="RETAIN_BASE"
        p.emit("DEUS_R339_MATCHED_AUDIT_FINAL",{
            "status":"MATCHED_AUDIT_COMPLETE",
            "verdict":verdict,
            "base_ref":BASE_REF,
            "candidate_ref":CAND_REF,
            "candidate_provider_lastRunTime":row.get("lastRunTime"),
            "candidate_parsed_version":parsed_version,
            "base_notebook_sha256":bh,
            "candidate_notebook_sha256":sh,
            "base_offline_mean":bm,
            "candidate_offline_mean":sm,
            "base_actions":bact,
            "candidate_actions":sact,
            "base_audit_passed":True,
            "candidate_audit_passed":True,
            "competition_submission":False,
            "submission_quota_spent":False,
            "candidate_promoted":False,
        })
    except Exception as exc:
        p.emit("DEUS_R339_RECOVERY_HOLD",{
            "code":type(exc).__name__,
            "detail":str(exc)[:1200],
            "competition_submission":False,
            "submission_quota_spent":False,
        })
    threading.Event().wait()

if __name__=="__main__":
    main()
