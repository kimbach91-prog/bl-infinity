#!/usr/bin/env python3
"""R326: WA30 coarse-region + cross-trace-unanimity LOTO falsifier.

R321 showed useful WA30 spatial+region signal but unsafe false changes and
exact-frame regression. R326 keeps that representation fixed and changes only
the reliability mechanism, requiring each deterministic change rule to be
supported in every independent training trace of the fold. Both R321 region4
and region8 are tested because neither dominated the other on gain vs false
changes. Public p0-p4 only; p5-p19 are not staged/read.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_region8_cross_trace_unanimity_323 as r323

RUNG=326
GAME="wa30-ee6fef47"
BASE_MODE="spatial"
GRIDS=(4,8)

def run(traces,G):
    prepared=[r321.prep(t,BASE_MODE,G) for t in traces]
    total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        rules,fit=r323.fit_unanimous(train)
        ev=r314._evaluate(prepared[held],rules)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact WA30 p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]
    modes={}; folds={}
    for G in GRIDS:
        modes[f"region{G}"],folds[f"region{G}"]=run(traces,G)
    cand=[m for m,v in modes.items() if v.get("predicted_changes",0)>0 and v.get("false_changes",0)==0 and v.get("pixel_gain",0)>0 and v.get("exact_frame_gain",0)>=0]
    best=max(cand,key=lambda m:(modes[m].get("exact_frame_gain",0),modes[m].get("pixel_gain",0))) if cand else None
    verdict="WA30_UNANIMOUS_ZERO_FALSE_LOTO_SIGNAL" if best else ("WA30_UNANIMOUS_GAIN_WITH_FALSE_CHANGE" if any(v.get("pixel_gain",0)>0 for v in modes.values()) else "WA30_UNANIMOUS_NO_SIGNAL")
    out={"schema":"deus/arc3-r326-wa30-region-unanimity-loto/1","rung":RUNG,"game":GAME,"base_mode":BASE_MODE,
      "protocol":{"data":"public p0-p4 only","evaluation":"5-fold LOTO","representation":"unchanged R321 spatial+coarse-region","mechanism_delta":"deterministic change rule must be supported in every training trace per fold","grids":[4,8],"p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "modes":modes,"folds":folds,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"whole_game_solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__": main()
