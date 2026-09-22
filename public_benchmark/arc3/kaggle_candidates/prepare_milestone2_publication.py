#!/usr/bin/env python3
"""Prepare and statically audit an ARC-AGI-3 Milestone-2 publication bundle.

This tool does NOT publish to Kaggle and does NOT select a Kaggle license.
It converts an already-built private evaluation package into a public-intent
candidate, preserves MIT provenance, proves the configured runtime ceiling is
below the 9-hour competition limit, and emits a fail-closed receipt.

Provider truth remains separate:
PUBLICATION_READY_STATIC != KAGGLE_PUBLIC != LICENSE_SELECTED != PRIZE_ELIGIBLE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

# Trigger revision: workflow is now present on this branch.\nSCHEMA="deus/arc3-milestone2-publication-gate/1"
COMPETITION="arc-prize-2026-arc-agi-3"
MACHINE="NvidiaRtxPro6000"
LIMIT_SECONDS=9*60*60

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def semantic_notebook_sha(p:Path)->str:
    nb=json.loads(p.read_text(encoding="utf-8"))
    semantic=[
        {"cell_type":c.get("cell_type"),"source":"".join(c.get("source",[]))}
        for c in nb.get("cells",[])
    ]
    payload=json.dumps(semantic,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(payload).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--built-package",type=Path,required=True)
    ap.add_argument("--source-root",type=Path,required=True)
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--receipt",type=Path,required=True)
    ap.add_argument("--concurrency",type=int,default=8)
    ap.add_argument("--games",type=int,default=25)
    ap.add_argument("--runtime-seconds",type=int,default=7200)
    ap.add_argument("--analyzer-timeout",type=int,default=900)
    args=ap.parse_args()

    src=args.built_package.resolve()
    out=args.output_dir.resolve()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src,out)

    nbs=sorted(out.glob("*.ipynb"))
    if len(nbs)!=1:
        raise SystemExit(f"expected exactly one notebook, got {len(nbs)}")
    nb=nbs[0]
    meta_path=out/"kernel-metadata.json"
    meta=json.loads(meta_path.read_text(encoding="utf-8"))

    # Public-intent artifact only. No provider mutation occurs here.
    meta["is_private"]=False
    meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    upstream_license=args.source_root/"UPSTREAM_LICENSE.txt"
    deus_license=args.repo_root/"LICENSE-CODE"
    manifest=args.source_root/"DEUS_MANIFEST.md"

    waves=math.ceil(args.games/args.concurrency)
    configured_upper_bound=waves*args.runtime_seconds+args.analyzer_timeout

    checks={
        "exact_one_notebook":len(nbs)==1,
        "competition_source":COMPETITION in (meta.get("competition_sources") or []),
        "gpu_enabled":meta.get("enable_gpu") is True,
        "internet_disabled":meta.get("enable_internet") is False,
        "machine_shape_exact":meta.get("machine_shape")==MACHINE,
        "public_intent_metadata":meta.get("is_private") is False,
        "runtime_positive":args.runtime_seconds>0 and args.concurrency>0 and args.games>0,
        "runtime_ceiling_lt_9h":configured_upper_bound < LIMIT_SECONDS,
        "upstream_license_present":upstream_license.is_file(),
        "deus_code_license_present":deus_license.is_file(),
        "provenance_manifest_present":manifest.is_file(),
    }
    if upstream_license.is_file():
        checks["upstream_license_mit"]="MIT License" in upstream_license.read_text(encoding="utf-8",errors="replace")
    if deus_license.is_file():
        checks["deus_code_license_mit"]="MIT License" in deus_license.read_text(encoding="utf-8",errors="replace")

    # Preserve source licenses and attribution with the publication bundle.
    shutil.copy2(upstream_license,out/"UPSTREAM_LICENSE.txt")
    shutil.copy2(deus_license,out/"DEUS_LICENSE_CODE.txt")
    shutil.copy2(manifest,out/"DEUS_PROVENANCE_MANIFEST.md")

    publication_manifest={
        "schema":"deus/arc3-milestone2-publication-manifest/1",
        "competition":COMPETITION,
        "milestone_deadline_utc":"2026-09-30T23:59:00Z",
        "notebook_file":nb.name,
        "notebook_sha256":sha256(nb),
        "notebook_semantic_sha256":semantic_notebook_sha(nb),
        "metadata_sha256":sha256(meta_path),
        "configured_runtime":{
            "games":args.games,
            "concurrency":args.concurrency,
            "per_game_runtime_seconds":args.runtime_seconds,
            "analyzer_timeout_seconds":args.analyzer_timeout,
            "concurrency_waves":waves,
            "conservative_upper_bound_seconds":configured_upper_bound,
            "competition_limit_seconds":LIMIT_SECONDS,
        },
        "licenses":{
            "deus_authored_code":"MIT via LICENSE-CODE",
            "upstream_flash_next":"MIT via UPSTREAM_LICENSE.txt",
            "external_models_and_data":"retain their own upstream licenses; verify provider attachment/license compatibility before prize claim",
        },
        "provider_actions_required_before_milestone_claim":[
            "publish the exact prize-candidate notebook publicly on Kaggle",
            "select/confirm an open-source license on the public Kaggle notebook",
            "read back public visibility and license from the provider",
            "ensure the public notebook corresponds to the leaderboard/milestone candidate",
        ],
        "truth":{
            "kaggle_authenticated":False,
            "kaggle_publication_executed":False,
            "kaggle_public_visibility_readback":False,
            "kaggle_license_selected":False,
            "kaggle_license_readback":False,
            "competition_submission_attempted":False,
            "submission_quota_spent":False,
            "milestone_prize_eligibility_claim":False,
        },
    }
    (out/"PUBLICATION_MANIFEST.json").write_text(json.dumps(publication_manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    gate="PUBLICATION_READY_STATIC_REQUIRES_KAGGLE_PUBLIC_LICENSE_READBACK" if all(checks.values()) else "HOLD"
    receipt={
        "schema":SCHEMA,
        "gate":gate,
        "checks":checks,
        "publication_manifest":publication_manifest,
        "bundle_files":sorted(p.name for p in out.iterdir() if p.is_file()),
        "truth":publication_manifest["truth"],
    }
    args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "gate":gate,
        "notebook_sha256":publication_manifest["notebook_sha256"],
        "runtime_upper_bound_seconds":configured_upper_bound,
        "runtime_upper_bound_hours":round(configured_upper_bound/3600,4),
        "checks":checks,
        "truth":receipt["truth"],
    },sort_keys=True))
    return 0 if gate.startswith("PUBLICATION_READY_STATIC") else 2

if __name__=="__main__":
    raise SystemExit(main())
