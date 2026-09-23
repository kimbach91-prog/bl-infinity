#!/usr/bin/env python3
"""Recover matched R335 provider evidence after state-v1/v2 packaging failure.

Reuses exact completed baseline /1. Before any new provider push, applies the
current R335 patch in memory to the exact stage-1 tool_agent.py recovered from
baseline /1 and compiles it. Then it launches at most one repaired state version.
No competition submission endpoint is called.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import threading
import time
from pathlib import Path

import railway_r335_flash_provider as p
import upstream_flash_r335_structured_state_package_patch as pkg

BASE_EXACT="lmkimbch/deus-arc3-r338-base-tr87/1"
REPAIRED_STATE_REF="lmkimbch/deus-arc3-r335fix-f2ad-state-tr87"
p.STATE_REF=REPAIRED_STATE_REF
EXPECTED_BASE_NOTEBOOK_SHA="2fe65f106a7ef34e44d5e12f3133fa471669e78ffeac1e67a558a20c118aca1c"
EXPECTED_STAGE1_SHA="978026a51c438744c64922571b2264f09a3d4ec4259ddc75b03ccc0f3ba0b772"
EXPECTED_REPAIRED_OVERLAY_SHA="f2adf9b64107dbfa78e2d693e19919889f31debf0fe98f9c5061b28948910388"

def exact_exists(version:int):
    exact=f"{p.STATE_REF}/{version}"
    q=p.run(["kaggle","kernels","status",exact],check=False,timeout=60)
    txt=(q.stdout+"\n"+q.stderr).strip()
    low=txt.lower()
    missing = q.returncode != 0 or "not found" in low or "404" in low
    return (not missing), exact, txt

def exact_source_selftest():
    root=p.WORK/"exact-source-selftest"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    p.run(["kaggle","kernels","output",BASE_EXACT,"-p",str(root)],timeout=180)
    src=root/"flash_agent_overlay/inference/agent/tool_agent.py"
    if not src.is_file(): raise RuntimeError("baseline_stage1_tool_agent_missing")
    raw=src.read_bytes()
    stage_hash=hashlib.sha256(raw).hexdigest()
    if stage_hash!=EXPECTED_STAGE1_SHA:
        raise RuntimeError(f"stage1_sha_mismatch:{stage_hash}")
    ns={"hashlib":hashlib}
    exec(pkg.PATCH_SOURCE,ns)
    patched=ns["patch_tool_agent_r335"](raw)
    compile(patched,"flash_tool_agent_r335_exact_recovery.py","exec")
    out_hash=hashlib.sha256(patched.encode("utf-8")).hexdigest()
    if out_hash!=EXPECTED_REPAIRED_OVERLAY_SHA:
        raise RuntimeError(f"repaired_overlay_sha_mismatch:{out_hash}")
    p.emit("DEUS_R335_FLASH_RECOVERY_SELFTEST",{
        "base_exact":BASE_EXACT,
        "stage1_sha256":stage_hash,
        "repaired_overlay_sha256":out_hash,
        "compile_pass":True,
        "kernel_push":False,
        "competition_submission":False,
    })

def discover_next_state_version():
    # The historical state slug accumulated many stale ERROR versions before
    # the prompt-escaping repair. Use a fresh content-identity namespace so the
    # first provider execution of the repaired candidate is attributable.
    exists, exact, txt = exact_exists(1)
    if exists:
        raise RuntimeError(
            f"isolated_state_namespace_not_empty:{exact}:{txt[:160]}"
        )
    p.emit("DEUS_R335_FLASH_RECOVERY_NAMESPACE_FENCE",{
        "state_ref":REPAIRED_STATE_REF,
        "expected_first_version":1,
        "namespace_empty":True,
        "repaired_overlay_sha256":EXPECTED_REPAIRED_OVERLAY_SHA,
        "competition_submission":False,
    })
    return 1


def launch_or_reuse_state(state_dir):
    next_version=discover_next_state_version()
    q=p.run(["kaggle","kernels","push","-p",str(state_dir),"-t","30000"],timeout=180)
    text=q.stdout+"\n"+q.stderr
    import re
    m=re.search(r"Kernel version\s+(\d+)\s+successfully pushed",text,re.I)
    if m:
        version=int(m.group(1))
        if version!=1:
            raise RuntimeError(
                f"isolated_namespace_version_race:expected1:observed{version}"
            )
        ok,exact2,_=exact_exists(version)
        if not ok: raise RuntimeError("parsed_state_version_not_readable")
        return version,True

    ok,exact2,status2=exact_exists(1)
    if not ok:
        raise RuntimeError("provider_push_returned_success_but_isolated_v1_absent")
    p.emit("DEUS_R335_FLASH_RECOVERY_VERSION_DISCOVERED",{
        "state_exact":exact2,
        "discovery":"post-push isolated exact status probe",
        "status":status2[:240],
        "competition_submission":False,
    })
    return 1,True


def main():
    threading.Thread(target=p.health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        p.emit("DEUS_R335_FLASH_RECOVERY_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","competition_submission":False})
        threading.Event().wait(); return
    p.run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
    try:
        exact_source_selftest()
        base,state,bh,sh=p.stage_packages()
        if bh!=EXPECTED_BASE_NOTEBOOK_SHA:
            raise RuntimeError("baseline_hash_changed_from_v1")
        sv,new_push=launch_or_reuse_state(state)
        state_exact=f"{p.STATE_REF}/{sv}"
        launch={
            "base_exact":BASE_EXACT,
            "state_exact":state_exact,
            "base_notebook_sha256":bh,
            "state_notebook_sha256":sh,
            "game_id":p.GAME,
            "runtime_seconds":p.RUNTIME,
            "baseline_reused_exact_v1":True,
            "state_repair_only":True,
            "state_namespace_fenced":True,
            "state_namespace":REPAIRED_STATE_REF,
            "new_state_push":new_push,
            "exact_source_selftest_passed":True,
            "competition_submission":False,
            "submission_quota_spent":False,
        }
        p.emit("DEUS_R335_FLASH_PROVIDER_RECOVERY_LAUNCH",launch)
        deadline=time.time()+4200
        sc=p.wait_complete(state_exact,deadline)
        bc=p.wait_complete(BASE_EXACT,deadline)
        if not (bc and sc):
            p.emit("DEUS_R335_FLASH_RECOVERY_HOLD",{**launch,"code":"PROVIDER_TIMEOUT","base_complete":bc,"state_complete":sc})
            threading.Event().wait(); return
        ba=p.download_and_audit(BASE_EXACT,p.WORK/"base-output-recovery",False)
        sa=p.download_and_audit(state_exact,p.WORK/"state-output-recovery",True)
        bm=float(ba.get("offline_mean",0)); sm=float(sa.get("offline_mean",0))
        bact=int(ba.get("total_actions",0)); sact=int(sa.get("total_actions",0))
        if sm>bm: verdict="PROMOTE_TO_WIDER_PROVIDER_TEST"
        elif sm==bm and sact<bact: verdict="PROMOTE_EFFICIENCY_ONLY"
        else: verdict="RETAIN_BASE"
        p.emit("DEUS_R335_FLASH_PROVIDER_FINAL",{
            **launch,
            "status":"MATCHED_AUDIT_COMPLETE",
            "verdict":verdict,
            "base_offline_mean":bm,
            "state_offline_mean":sm,
            "base_actions":bact,
            "state_actions":sact,
            "base_audit_passed":True,
            "state_audit_passed":True,
            "leaderboard_score_observed":False,
            "candidate_promoted":False,
        })
    except Exception as e:
        p.emit("DEUS_R335_FLASH_RECOVERY_HOLD",{
            "code":type(e).__name__,
            "detail":str(e)[:240],
            "competition_submission":False,
            "submission_quota_spent":False,
        })
    threading.Event().wait()

if __name__=="__main__":
    main()
