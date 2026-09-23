#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268

RUNG=317; GAME="ft09-0d8bbf25"
MODES=("palette","meter","symmetry","regions","objects","composite","ui_mask")
MIN_PRESTATES=2; MIN_TRACES=2

def exact_key(r): return r246.digest({"b":r["before"],"a":r["action"]})
def abs_key(r,m):
    rep=r268.masked(r["before"]) if m=="ui_mask" else r["before_features"][m]
    return r246.stable((rep,r["action"]))

def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r["after_digest"]; obs[k][d]+=1; frame[(k,d)]=r["after"]
    return {k:frame[(k,next(iter(c)))] for k,c in obs.items() if len(c)==1}

def fit_abs(rows,m):
    obs=defaultdict(Counter); pre=defaultdict(set); trs=defaultdict(set); frame={}
    for r in rows:
        k=abs_key(r,m); d=r["after_digest"]; obs[k][d]+=1; pre[k].add(r["before_digest"]); trs[k].add(r["trace"]); frame[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(pre[k])<MIN_PRESTATES or len(trs[k])<MIN_TRACES: continue
        d=next(iter(c)); tab[k]=frame[(k,d)]
    return tab

def ev(rows,exact,tab,m):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact: s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1; pred=tab.get(abs_key(r,m))
        if pred is None: s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        s["candidate_correct" if pred==r["after"] else "candidate_wrong"]+=1
    p=s["candidate_predictions"]; s["accuracy"]=round(s["candidate_correct"]/p,6) if p else None
    return dict(s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact ft09 p0-p4 required")
    traces=[r251.prepare_rows([p]) for p in ps]
    totals={m:Counter() for m in MODES}
    for held in range(5):
        train=[r for i,tr in enumerate(traces) if i!=held for r in tr]; val=traces[held]; exact=fit_exact(train)
        for m in MODES:
            met=ev(val,exact,fit_abs(train,m),m)
            for k,v in met.items():
                if isinstance(v,int): totals[m][k]+=v
    modes={}; cand=[]
    for m,s in totals.items():
        p=s["candidate_predictions"]; modes[m]={**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None}
        if p>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0: cand.append(m)
    best=max(cand,key=lambda m:(modes[m]["candidate_correct"],modes[m]["candidate_predictions"])) if cand else None
    verdict="ZERO_WRONG_EXACTFRAME_LOTO_SIGNAL" if best else "NO_SIGNAL"
    out={"schema":"deus/arc3-r317-ft09-exactframe-loto/1","rung":RUNG,"game":GAME,
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold LOTO","exact_baseline_precedence":True,"p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False},
      "modes":modes,"candidate_modes":cand,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))
if __name__=="__main__": main()
