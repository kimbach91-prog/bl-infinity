#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314

RUNG=316
FROZEN={"tr87-cd924810":"delta","wa30-ee6fef47":"spatial"}
MIN_NESTED_PRED=2

def key_stats(rows,rules):
    stats=defaultdict(Counter)
    for row in rows:
        b=row["b"]; a=row["a"]; keys=row["keys"]; h=len(b); w=len(b[0]) if h else 0
        for rr in range(h):
            for cc in range(w):
                k=keys[rr][cc]
                if k not in rules: continue
                pred=int(rules[k]); before=int(b[rr][cc]); actual=int(a[rr][cc])
                if pred==before: continue
                stats[k]["predictions"]+=1
                if pred==actual and before!=actual: stats[k]["correct"]+=1
                else: stats[k]["wrong"]+=1
    return stats

def nested_trust(train_traces):
    stats=defaultdict(Counter)
    for held in range(len(train_traces)):
        sub=[train_traces[i] for i in range(len(train_traces)) if i!=held]
        rules,_=r314._fit_rules(sub)
        st=key_stats(train_traces[held],rules)
        for k,c in st.items():
            stats[k].update(c)
    trusted={k for k,c in stats.items() if c["predictions"]>=MIN_NESTED_PRED and c["wrong"]==0}
    return trusted,stats

def run_game(ps,mode):
    raw=[r302.augment_trace(p) for p in ps]
    prepared=[r314._prepare_trace(t,mode) for t in raw]
    total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        trusted,nstats=nested_trust(train)
        rules,fit=r314._fit_rules(train)
        rules={k:v for k,v in rules.items() if k in trusted}
        ev=r314._evaluate(prepared[held],rules)
        folds.append({"held_trace":held,"trusted_keys":len(trusted),"fit":fit,
                      "nested_predictions":sum(c["predictions"] for c in nstats.values()),
                      "nested_wrong":sum(c["wrong"] for c in nstats.values()),"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--game",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    if a.game not in FROZEN: raise SystemExit("game not frozen")
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=a.game for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    mode=FROZEN[a.game]; total,folds=run_game(ps,mode)
    signal=bool(total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0 and total.get("exact_frame_gain",0)>=0)
    verdict="NESTED_ZERO_FALSE_LOTO_SIGNAL" if signal else ("NESTED_GAIN_WITH_FALSE_CHANGE" if total.get("pixel_gain",0)>0 else "NO_SIGNAL")
    out={"schema":"deus/arc3-r316-tr87-wa30-nested-verifier/1","rung":RUNG,"game":a.game,"mode":mode,
      "lineage":{"r314_run":35829948269,"selector_fixed_from_r314_p0_p4_loto":True},
      "protocol":{"data":"p0-p4 only","outer":"5-fold LOTO","inner":"nested training-only per-key zero-wrong verifier","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "loto":total,"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"mode":mode,"verdict":verdict,"loto":total},sort_keys=True))
if __name__=="__main__": main()
