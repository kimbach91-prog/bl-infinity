#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
RUNG=321
BASE={"tr87-cd924810":"delta","wa30-ee6fef47":"spatial"}
GRIDS=(4,8)

def prep(trace,base_mode,G):
    out=r314._prepare_trace(trace,base_mode)
    for row in out:
        h=len(row["b"]); w=len(row["b"][0]) if h else 0
        for r in range(h):
            for c in range(w):
                rb=min(G-1,(r*G)//max(1,h)); cb=min(G-1,(c*G)//max(1,w))
                row["keys"][r][c]=row["keys"][r][c]+(("region",G,rb,cb),)
    return out

def run(traces,base_mode,G):
    p=[prep(t,base_mode,G) for t in traces]; total=Counter(); folds=[]
    for held in range(5):
        train=[p[i] for i in range(5) if i!=held]
        rules,fit=r314._fit_rules(train); ev=r314._evaluate(p[held],rules)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--game",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    if a.game not in BASE: raise SystemExit("game not frozen")
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=a.game for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]; modes={}; folds={}
    for G in GRIDS:
        key=f"region{G}"; modes[key],folds[key]=run(traces,BASE[a.game],G)
    cand=[m for m,v in modes.items() if v.get("predicted_changes",0)>0 and v.get("false_changes",0)==0 and v.get("pixel_gain",0)>0 and v.get("exact_frame_gain",0)>=0]
    best=max(cand,key=lambda m:(modes[m].get("exact_frame_gain",0),modes[m].get("pixel_gain",0))) if cand else None
    verdict="REGION_CONTEXT_ZERO_FALSE_LOTO_SIGNAL" if best else ("REGION_CONTEXT_GAIN_WITH_FALSE_CHANGE" if any(v.get("pixel_gain",0)>0 for v in modes.values()) else "NO_SIGNAL")
    out={"schema":"deus/arc3-r321-tr87-wa30-region-context-loto/1","rung":RUNG,"game":a.game,"base_mode":BASE[a.game],
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","representation_delta":"append fixed action-canonical coarse region bin to local causal key","grids":[4,8],"p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "modes":modes,"folds":folds,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"game":a.game,"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__": main()
