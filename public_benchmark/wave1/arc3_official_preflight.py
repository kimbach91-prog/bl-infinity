#!/usr/bin/env python3
import json, os, pathlib, sys, hashlib
state={
  "schema":"DEUS_ARC3_OFFICIAL_PREFLIGHT_V1",
  "arc_api_key_present":bool(os.environ.get("ARC_API_KEY","")),
  "kaggle_rules_accepted":os.environ.get("KAGGLE_RULES_ACCEPTED","").lower()=="true",
  "submission_source_ref":"public_benchmark/wave1/arc3_submission_package.json",
  "execution_state":"HOLD"
}
pkg=json.loads(pathlib.Path(state["submission_source_ref"]).read_text())
state["package_digest"]=hashlib.sha256(pathlib.Path(state["submission_source_ref"]).read_bytes()).hexdigest()
state["package_open_source_projection"]=pkg.get("open_source_projection",False)
if not state["arc_api_key_present"]:
    state["hold_reason"]="ARC_API_KEY_NOT_MACHINE_BOUND"
elif not state["kaggle_rules_accepted"]:
    state["hold_reason"]="KAGGLE_RULE_ACCEPTANCE_NOT_ATTESTED"
elif not state["package_open_source_projection"]:
    state["hold_reason"]="OPEN_SOURCE_PROJECTION_NOT_APPROVED"
else:
    state["execution_state"]="READY_FOR_OFFICIAL_SUBMISSION_ROUTE"
    state["hold_reason"]=None
print(json.dumps(state,sort_keys=True))
pathlib.Path("arc3-official-preflight-receipt.json").write_text(json.dumps(state,indent=2)+"\n")
sys.exit(0 if state["execution_state"]=="READY_FOR_OFFICIAL_SUBMISSION_ROUTE" else 3)
