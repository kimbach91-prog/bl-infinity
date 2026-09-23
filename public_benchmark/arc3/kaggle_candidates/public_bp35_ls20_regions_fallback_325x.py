#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_remaining6_exactframe_loto_307 as r307
RUNG="325X"; GAMES={"bp35-0a0ad940","ls20-9607627b"}; MODE="regions"
def main():
  ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
  by=defaultdict(list)
  for p in a.input: by[r246.game_id(p)].append(p)
  if set(by)!=GAMES: raise SystemExit(f"exact games required, got {sorted(by)}")
  games={}; passes=[]
  for g in sorted(GAMES):
    ps=sorted(by[g],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit(f"{g}: p0-p9 required")
    train=[r for p in ps[:5] for r in r251.prepare_rows([p])]; replay=[r for p in ps[5:] for r in r251.prepare_rows([p])]
    exact=r307.fit_exact(train); tab=r307.fit_abs(train,MODE); val=r307.evaluate(replay,exact,tab,MODE)
    gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
    if gate: passes.append(g)
    games[g]={"mode":MODE,"source_assisted_p5_p9":val,"gate_pass":gate}
  verdict="REGIONS_FALLBACK_SOURCE_ASSISTED_SIGNAL" if passes else "NO_PROMOTION"
  out={"schema":"deus/arc3-r325x-regions-fallback/1","rung":RUNG,"games":games,"pass_games":passes,"verdict":verdict,
       "lineage":{"r307_run":35827692947,"regions_candidate_preexisted_before_meter_final_failures":True},
       "protocol":{"fit":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"p5_p9_updates_selector":False},
       "truth":{"public_trace_only":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
  a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"pass_games":passes,"games":games},sort_keys=True))
if __name__=="__main__": main()
