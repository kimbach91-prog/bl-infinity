#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314

RUNG=315; GAME="dc22-fdcac232"; MODE="phase"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit("exact p0-p9 required")
    train=[r302.augment_trace(p) for p in ps[:5]]
    replay=[r302.augment_trace(p) for p in ps[5:]]
    prepared_train=[r314._prepare_trace(t,MODE) for t in train]
    prepared_replay=[x for t in replay for x in r314._prepare_trace(t,MODE)]
    rules,fit=r314._fit_rules(prepared_train)
    val=r314._evaluate(prepared_replay,rules)
    gate=bool(val.get("predicted_changes",0)>0 and val.get("false_changes",0)==0 and val.get("pixel_gain",0)>0 and val.get("exact_frame_gain",0)>=0)
    verdict="SOURCE_ASSISTED_ZERO_FALSE_STABILITY_SIGNAL" if gate else "NO_PROMOTION"
    out={"schema":"deus/arc3-r315-dc22-phase-frozen-replay/1","rung":RUNG,"game":GAME,"mode":MODE,
      "lineage":{"r314_run":35829948269,"r314_job":107079978802,"selector_frozen_before_p5_p9":True,
                 "r314_loto":{"predicted_changes":547,"true_changed_correct":547,"false_changes":0,"pixel_gain":547,"exact_frame_gain":32}},
      "protocol":{"fit":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"p5_p9_updates_selector":False,"p5_p9_updates_model":False},
      "fit":fit,"source_assisted_p5_p9":val,"gate_pass":gate,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"gate_pass":gate,"replay":val},sort_keys=True))
if __name__=="__main__": main()
