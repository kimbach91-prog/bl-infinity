#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304
RUNG=320; GAME="cn04-2fe56bfb"; MODE="exact_graph_to_coarse"
def main():
  ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
  by=defaultdict(list)
  for p in a.input: by[r246.game_id(p)].append(p)
  if set(by)!={GAME}: raise SystemExit("exact cn04 required")
  ps=sorted(by[GAME],key=r246.pnum)
  if [r246.pnum(p) for p in ps]!=list(range(20)): raise SystemExit("exact p0-p19 required")
  train_traces=[r278.annotated_rows([p]) for p in ps[:10]]
  hold=[r for p in ps[10:] for r in r278.annotated_rows([p])]
  tab,fit=r304.fit(train_traces,MODE); val=r304.evaluate(hold,tab,MODE)
  gate=bool(val.get("predictions",0)>0 and val.get("wrong",0)==0 and val.get("correct",0)>0)
  verdict="FINAL_PUBLIC_GRAPH_AUDIT_ZERO_WRONG_PASS" if gate else "FINAL_PUBLIC_AUDIT_NO_PROMOTION"
  out={"schema":"deus/arc3-r320-cn04-graph-final-audit/1","rung":RUNG,"game":GAME,"mode":MODE,
       "lineage":{"r303_run":35826664764,"r305_repaired_run":35827733140,"selector_frozen_before_p5_p9":True},
       "protocol":{"refit":"p0-p9 after selector freeze","final_eval":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_model":False},
       "fit":fit,"public_p10_p19":val,"gate_pass":gate,"verdict":verdict,
       "truth":{"public_trace_only":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
  a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"gate_pass":gate,"p10p19":val},sort_keys=True))
if __name__=="__main__": main()
