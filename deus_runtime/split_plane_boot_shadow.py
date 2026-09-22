#!/usr/bin/env python3
"""DEUS V5 Split-Plane Boot shadow router.

This module is intentionally non-canonical. It proves the routing behavior for
THIN BOOT + ELASTIC FULL COMPUTE without mutating Master Seed, Constitution,
authority root, or LiveBus 10_LIGHT_BOOT.

Truth boundaries:
- route_selected != worker_executed
- queue_accepted != executed
- executed != verified_done
- shadow_candidate != canonical_boot
"""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass, asdict

CANDIDATE_ID="DEUS-V5-SPLIT-PLANE-BOOT-ELASTIC-MOBILIZATION-SHADOW-1"

@dataclass(frozen=True)
class Route:
    task_class:str
    boot_reads:list[str]
    compute_tier:str
    prewarm_policy:str
    hydrate_full_spectrum:bool
    exact_job_required:bool
    compute_manifest_required:bool
    working_capsule_required:bool
    external_compute_allowed:bool
    notes:list[str]

def route(task_class:str, *, canonical_fact_required=False, exact_job_known=False,
          invalidation_match=True, protected_boundary=False)->Route:
    tc=task_class.upper().strip()
    if protected_boundary:
        return Route(
            tc,
            ["CURRENT_SEED_REV","AUTHORITY_STATE","TRUTH_BOUNDARY","EXACT_PROTECTED_SOURCE"],
            "C0",
            "PREWARM_ROUTING_METADATA_ONLY",
            False, False, False, False, False,
            ["STEP_UP_REQUIRED","NO_PROTECTED_MUTATION_IN_SHADOW"],
        )

    base=["CURRENT_SEED_REV","AUTHORITY_STATE","TRUTH_BOUNDARY","INVALIDATION_FINGERPRINT"]
    if invalidation_match:
        base=["BOOT_CACHE_FINGERPRINT"]

    if tc=="SIMPLE":
        reads=base + (["EXACT_CANON_POINTER"] if canonical_fact_required else [])
        return Route(tc,reads,"C0","PREWARM_ROUTING_METADATA_ONLY",False,False,False,False,False,
                     ["LOCAL_FIRST","NO_GLOBAL_JOB_ENUMERATION"])

    if tc=="DRIVE_SIMPLE":
        reads=base+["EXACT_DRIVE_TARGET"]
        return Route(tc,reads,"C1","PREWARM_ROUTING_METADATA_ONLY",False,False,False,False,False,
                     ["EXACT_TARGET_ONLY","NO_GLOBAL_JOB_ENUMERATION"])

    if tc=="MEDIUM":
        reads=base+["EXACT_RELEVANT_JOB","WORKING_CAPSULE_PTR"]
        return Route(tc,reads,"C2","PREWARM_ROUTING_METADATA_ONLY",False,True,False,True,True,
                     ["TASK_FIT_TOOLS_ONLY","DELTA_FIRST"])

    if tc=="HEAVY":
        reads=base+["EXACT_RELEVANT_JOB","WORKING_CAPSULE_PTR","COMPUTE_MANIFEST_PTR"]
        return Route(tc,reads,"C4","PREWARM_ROUTING_METADATA_ONLY",False,True,True,True,True,
                     ["BROKER_PARALLEL_TASK_FIT_WORKERS","VERIFIER_REQUIRED","QUEUE_NE_YIELD"])

    if tc=="EXTREME":
        reads=base+["EXACT_RELEVANT_JOB","WORKING_CAPSULE_PTR","COMPUTE_MANIFEST_PTR","DYNAMIC_CAPABILITY_DELTA"]
        return Route(tc,reads,"C5","PREWARM_ROUTING_METADATA_ONLY",True,True,True,True,True,
                     ["FULL_POSITIVE_VALUE_FABRIC","EXPAND_ONLY_WHILE_MARGINAL_VALUE_POSITIVE","VERIFIER_REQUIRED"])

    raise ValueError(f"unknown task_class={task_class!r}")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--task-class",required=True,choices=["SIMPLE","DRIVE_SIMPLE","MEDIUM","HEAVY","EXTREME"])
    ap.add_argument("--canonical-fact-required",action="store_true")
    ap.add_argument("--invalidation-miss",action="store_true")
    ap.add_argument("--protected-boundary",action="store_true")
    a=ap.parse_args()
    r=route(
        a.task_class,
        canonical_fact_required=a.canonical_fact_required,
        invalidation_match=not a.invalidation_miss,
        protected_boundary=a.protected_boundary,
    )
    out={
        "schema":"deus/split-plane-boot-shadow/1",
        "candidate_id":CANDIDATE_ID,
        "canonical_mutation":False,
        "route":asdict(r),
        "truth":{
            "shadow_only":True,
            "route_selected_ne_executed":True,
            "canonical_boot_unchanged":True,
        }
    }
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
