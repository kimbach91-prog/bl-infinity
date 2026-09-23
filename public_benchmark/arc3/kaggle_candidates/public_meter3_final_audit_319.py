#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_meter4_frozen_replay_308 as r308
RUNG=319; GAMES={"ls20-9607627b","sb26-7fbdac44","sp80-589a99af"}
def main():
  ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
  by=defaultdict(list)
  for p in a.input: by[r246.game_id(p)].append(p)
  if set(by)!=GAMES: raise SystemExit(f"exact games required {sorted(GAMES)}")
  games={}; pass_games=[]
  for g in sorted(GAMES):
    ps=sorted(by[g],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)): raise SystemExit(f"{g}: exact p0-p19 required")
    fit=[r for p in ps[:10] for r in r251.prepare_rows([p])]
    hold=[r for p in ps[10:] for r in r251.prepare_rows([p])]
    exact=r308.fit_exact(fit); tab,meta=r308.fit_meter(fit); val=r308.evaluate(hold,exact,tab)
    gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
    if gate: pass_games.append(g)
    games[g]={"fit":meta,"public_p10_p19":val,"gate_pass":gate}
  verdict="FINAL_PUBLIC_METER_AUDIT_SIGNAL" if pass_games else "FINAL_PUBLIC_AUDIT_NO_PROMOTION"
  out={"schema":"deus/arc3-r319-meter3-final-audit/1","rung":RUNG,"games":games,"pass_games":pass_games,"verdict":verdict,
       "lineage":{"r307_run":35827692947,"r308_run":35827840654,"selector_frozen_before_p5_p9":True},
       "protocol":{"frozen_mode":"meter","refit":"p0-p9 after selector freeze","final_eval":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_model":False},
       "truth":{"public_trace_only":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
  a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"pass_games":pass_games,"games":games},sort_keys=True))
if __name__=="__main__": main()
