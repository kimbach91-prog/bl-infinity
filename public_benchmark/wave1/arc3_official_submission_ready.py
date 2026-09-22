#!/usr/bin/env python3
import json, os, pathlib, sys, hashlib

proj_path=pathlib.Path("public_benchmark/wave1/arc3_open_source_projection.json")
proj=json.loads(proj_path.read_text())

state={
  "schema":"DEUS_ARC3_OFFICIAL_SUBMISSION_READY_V1",
  "projection_digest":hashlib.sha256(proj_path.read_bytes()).hexdigest(),
  "projection_scope":proj.get("projection_scope"),
  "protected_core_included":proj.get("protected_core_included"),
  "arc_api_key_present":bool(os.environ.get("ARC_API_KEY","")),
  "kaggle_join_receipt":os.environ.get("KAGGLE_JOIN_RECEIPT","").strip(),
  "kaggle_rules_accepted":os.environ.get("KAGGLE_RULES_ACCEPTED","").lower()=="true",
  "official_submission_receipt":os.environ.get("KAGGLE_SUBMISSION_RECEIPT","").strip(),
  "state":"HOLD"
}
missing=[]
if state["protected_core_included"] is not False: missing.append("PUBLIC_SAFE_PROJECTION")
if not state["arc_api_key_present"]: missing.append("ARC_API_KEY")
if not state["kaggle_join_receipt"]: missing.append("KAGGLE_JOIN_RECEIPT")
if not state["kaggle_rules_accepted"]: missing.append("KAGGLE_RULES_ACCEPTED")
if missing:
    state["hold_reason"]=",".join(missing)
else:
    state["state"]="READY_FOR_OFFICIAL_PROVIDER_SUBMISSION"
    state["hold_reason"]=None

pathlib.Path("arc3-official-submission-ready-receipt.json").write_text(json.dumps(state,indent=2)+"\n")
print(json.dumps(state,sort_keys=True))
sys.exit(0 if state["state"]=="READY_FOR_OFFICIAL_PROVIDER_SUBMISSION" else 3)
