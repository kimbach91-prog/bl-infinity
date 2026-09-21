#!/usr/bin/env python3
"""Fail-closed Kaggle ARC-AGI-3 submission/readback actuator.

Default behavior is DRY_RUN. It never submits unless:
- candidate manifest validates,
- promotion_gate == PASS,
- audit_passed == true,
- non_dominated == true,
- an exact notebook ref/version is pinned,
- ARM_SUBMIT=true is present in the runtime,
- caller passes --execute-submit.

Raw credentials are never printed.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path

COMPETITION="arc-prize-2026-arc-agi-3"
HEX64=re.compile(r"^[0-9a-f]{64}$")
REF_RE=re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")

def auth_presence():
    return {
        "token": bool(os.getenv("KAGGLE_API_TOKEN") or os.getenv("KAGGLE_TOKEN")),
        "classic_pair": bool(os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")),
        "json_file": Path(os.path.expanduser("~/.kaggle/kaggle.json")).is_file(),
    }

def load_manifest(path: Path):
    obj=json.loads(path.read_text())
    if not isinstance(obj,dict):
        raise ValueError("manifest_not_object")
    return obj

def validate_manifest(m):
    errs=[]
    if m.get("competition")!=COMPETITION: errs.append("competition")
    ref=m.get("notebook_ref")
    if not isinstance(ref,str) or not REF_RE.fullmatch(ref): errs.append("notebook_ref")
    ver=m.get("exact_notebook_version")
    if type(ver) is not int or ver<1: errs.append("exact_notebook_version")
    sha=m.get("candidate_sha256")
    if not isinstance(sha,str) or not HEX64.fullmatch(sha): errs.append("candidate_sha256")
    if m.get("submission_file")!="submission.parquet": errs.append("submission_file")
    if m.get("audit_passed") is not True: errs.append("audit_passed")
    if m.get("non_dominated") is not True: errs.append("non_dominated")
    if m.get("incumbent_protection_ack") is not True: errs.append("incumbent_protection_ack")
    if m.get("promotion_gate")!="PASS": errs.append("promotion_gate")
    if errs: raise ValueError("manifest_gate_fail:"+",".join(errs))
    return True

def run(cmd):
    return subprocess.run(cmd,check=True,text=True,capture_output=True)

def safe_hash(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def read_submissions():
    r=run(["kaggle","competitions","submissions",COMPETITION])
    # Output is provider text; keep it as readback evidence but never parse a winner claim here.
    return r.stdout

def submit(m):
    return run([
        "kaggle","competitions","submit",COMPETITION,
        "-k",m["notebook_ref"],"-v",str(m["exact_notebook_version"]),
        "-f","submission.parquet",
        "-m",str(m.get("message","DEUS audited ARC-AGI-3 candidate"))[:120],
    ]).stdout

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path)
    p.add_argument("--readback",action="store_true")
    p.add_argument("--execute-submit",action="store_true")
    a=p.parse_args()
    present=auth_presence()
    out={"schema":"deus/kaggle-actuator/1","competition":COMPETITION,"auth_present":present,"submitted":False}
    if a.manifest:
        m=load_manifest(a.manifest)
        try:
            validate_manifest(m)
            out["manifest_gate"]="PASS"
        except Exception as e:
            out["manifest_gate"]="HOLD"
            out["hold_reason"]=str(e)
            print(json.dumps(out,sort_keys=True))
            return 2
    else:
        m=None
        out["manifest_gate"]="NO_MANIFEST"
    if a.readback:
        if not any(present.values()):
            out["readback"]="HOLD_NO_KAGGLE_AUTH"
        else:
            txt=read_submissions()
            out["readback"]="PASS"
            out["submission_output_lines"]=len([x for x in txt.splitlines() if x.strip()])
    if a.execute_submit:
        if m is None:
            raise SystemExit("submit_requires_manifest")
        if os.getenv("ARM_SUBMIT","").lower()!="true":
            out["submission_gate"]="HOLD_ARM_SUBMIT_FALSE"
        elif not any(present.values()):
            out["submission_gate"]="HOLD_NO_KAGGLE_AUTH"
        else:
            out["provider_submit_response"]=submit(m)[:1000]
            out["submitted"]=True
            out["submission_gate"]="EXECUTED"
    else:
        out["submission_gate"]="DRY_RUN"
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
