#!/usr/bin/env python3
"""Recover matched R335 provider evidence after state-v1 packaging syntax failure.

Reuses the still-running exact baseline /1 and launches only the repaired state
package as the next private kernel version. No competition submission endpoint is
called. Configuration/model/machine/runtime remain matched to the static contract.
"""
from __future__ import annotations

import json
import os
import threading
import time

import railway_r335_flash_provider as p

BASE_EXACT="lmkimbch/deus-arc3-r338-base-tr87/1"

def main():
    threading.Thread(target=p.health,daemon=True).start()
    if not os.environ.get("KAGGLE_API_TOKEN") and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        p.emit("DEUS_R335_FLASH_RECOVERY_HOLD",{"code":"KAGGLE_MACHINE_CREDENTIAL_ABSENT","competition_submission":False})
        threading.Event().wait(); return
    p.run(["kaggle","kernels","list","--mine","--page-size","1"],timeout=90)
    try:
        base,state,bh,sh=p.stage_packages()
        # Baseline /1 already launched from the same pre-patch baseline hash.
        if bh!="2fe65f106a7ef34e44d5e12f3133fa471669e78ffeac1e67a558a20c118aca1c":
            raise RuntimeError("baseline_hash_changed_from_v1")
        sv=p.push(state)
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
            "competition_submission":False,
            "submission_quota_spent":False,
        }
        p.emit("DEUS_R335_FLASH_PROVIDER_RECOVERY_LAUNCH",launch)
        deadline=time.time()+3900
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
            "detail":str(e)[:200],
            "competition_submission":False,
            "submission_quota_spent":False,
        })
    threading.Event().wait()

if __name__=="__main__":
    main()
