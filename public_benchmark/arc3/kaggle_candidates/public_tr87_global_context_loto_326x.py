#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
import public_tr87_wa30_region_context_loto_321 as r321
import public_relational_topology_diag_274 as r274
RUNG="326X"; GAME="tr87-cd924810"; BASE="delta"; GRID=8; MODES=("global_regions","global_nodes","global_palette")

def prep(trace,mode):
    out=r321.prep(trace,BASE,GRID)
    for row in out:
        b=row["b"]
        if mode=="global_regions": ctx=("regions",r246.regions(b,G=8))
        elif mode=="global_nodes": ctx=("nodes",r274.desc(b,"nodes_coarse"))
        elif mode=="global_palette": ctx=("palette",r246.palette(b))
        else: raise KeyError(mode)
        d=r246.digest(ctx)
        for r in range(len(row["keys"])):
            for c in range(len(row["keys"][r])): row["keys"][r][c]=row["keys"][r][c]+(("global",mode,d),)
    return out

def run(traces,mode):
    p=[prep(t,mode) for t in traces]; total=Counter()
    for held in range(5):
        train=[p[i] for i in range(5) if i!=held]; rules,_=r314._fit_rules(train); ev=r314._evaluate(p[held],rules)
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]; total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact tr87 p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]; modes={m:run(traces,m) for m in MODES}
    cand=[m for m,v in modes.items() if v.get("predicted_changes",0)>0 and v.get("false_changes",0)==0 and v.get("pixel_gain",0)>0 and v.get("exact_frame_gain",0)>=0]
    best=max(cand,key=lambda m:(modes[m].get("exact_frame_gain",0),modes[m].get("pixel_gain",0))) if cand else None
    verdict="GLOBAL_CONTEXT_ZERO_FALSE_LOTO_SIGNAL" if best else ("GLOBAL_CONTEXT_GAIN_WITH_FALSE_CHANGE" if any(v.get("pixel_gain",0)>0 for v in modes.values()) else "NO_SIGNAL")
    out={"schema":"deus/arc3-r326x-tr87-global-context-loto/1","rung":RUNG,"game":GAME,"base":"delta+region8","modes":modes,"best_mode":best,"verdict":verdict,
         "protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
         "truth":{"public_trace_only":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__":main()
