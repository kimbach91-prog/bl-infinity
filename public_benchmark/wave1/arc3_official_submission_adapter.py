#!/usr/bin/env python3
import json, os, pathlib, sys, hashlib
pkg=json.loads(pathlib.Path("public_benchmark/wave1/arc3_submission_package.json").read_text())
state={
  "schema":"DEUS_ARC3_OFFICIAL_SUBMISSION_ADAPTER_V1",
  "package_digest":hashlib.sha256(pathlib.Path("public_benchmark/wave1/arc3_submission_package.json").read_bytes()).hexdigest(),
  "arc_api_key_present":bool(os.environ.get("ARC_API_KEY","")),
  "kaggle_rules_accepted":os.environ.get("KAGGLE_RULES_ACCEPTED","").lower()=="true",
  "official_account_bound":os.environ.get("ARC_OFFICIAL_ACCOUNT_BOUND","").lower()=="true",
  "open_source_projection":bool(pkg.get("open_source_projection",False)),
  "submission_state":"HOLD"
}
missing=[]
if not state["arc_api_key_present"]: missing.append("ARC_API_KEY")
if not state["kaggle_rules_accepted"]: missing.append("KAGGLE_RULES_ACCEPTED")
if not state["official_account_bound"]: missing.append("ARC_OFFICIAL_ACCOUNT_BOUND")
if not state["open_source_projection"]: missing.append("OPEN_SOURCE_PROJECTION_APPROVAL")
if not missing:
    state["submission_state"]="READY_FOR_PROVIDER_SUBMISSION"
state["missing"]=missing
pathlib.Path("arc3-official-submission-adapter-receipt.json").write_text(json.dumps(state,indent=2)+"\n")
print(json.dumps(state,sort_keys=True))
sys.exit(0 if not missing else 3)
