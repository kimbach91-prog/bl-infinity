#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
RUNG=318; GAME="dc22-fdcac232"; MODE="phase"
def main():
  ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
  by=defaultdict(list)
  for p in a.input: by[r246.game_id(p)].append(p)
  if set(by)!={GAME}: raise SystemExit("exact dc22 required")
  ps=sorted(by[GAME],key=r246.pnum)
  if [r246.pnum(p) for p in ps]!=list(range(20)): raise SystemExit("exact p0-p19 required")
  fit=[r314._prepare_trace(r302.augment_trace(p),MODE) for p in ps[:10]]
  hold=[x for p in ps[10:] for x in r314._prepare_trace(r302.augment_trace(p),MODE)]
  rules,meta=r314._fit_rules(fit); val=r314._evaluate(hold,rules)
  gate=bool(val.get("predicted_changes",0)>0 and val.get("false_changes",0)==0 and val.get("pixel_gain",0)>0 and val.get("exact_frame_gain",0)>=0)
  verdict="FINAL_PUBLIC_AUDIT_ZERO_FALSE_PASS" if gate else "FINAL_PUBLIC_AUDIT_NO_PROMOTION"
  out={"schema":"deus/arc3-r318-dc22-phase-final-audit/1","rung":RUNG,"game":GAME,"mode":MODE,
       "lineage":{"r314_run":35829948269,"r315_run":35830312940,"selector_frozen_before_p5_p9":True,"final_audit_opened_after_barrier":True},
       "protocol":{"selector":"frozen dc22/phase","refit":"p0-p9 after selector freeze","final_eval":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_model":False},
       "fit":meta,"public_p10_p19":val,"gate_pass":gate,"verdict":verdict,
       "truth":{"public_trace_only":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
  a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"gate_pass":gate,"p10p19":val},sort_keys=True))
if __name__=="__main__": main()
