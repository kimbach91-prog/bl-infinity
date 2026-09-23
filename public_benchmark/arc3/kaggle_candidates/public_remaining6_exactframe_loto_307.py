#!/usr/bin/env python3
"""R307: p0-p4-only exact-frame LOTO sweep for the six remaining public ARC3 games.

Frozen game set:
  bp35-0a0ad940, g50t-5849a774, ls20-9607627b,
  sb26-7fbdac44, sc25-635fd71a, sp80-589a99af

Each outer fold trains on four complete traces and evaluates the fifth. Exact
visible-state/action prediction has precedence. Abstract candidates are fixed
public state lenses (palette, meter, symmetry, regions, objects, composite) plus
the static UI-mask representation. An abstract rule may act only when:
  - the exact baseline abstains;
  - training maps abstract state+action to ONE exact next frame;
  - support spans >=2 distinct exact pre-states AND >=2 distinct train traces.

No mode is selected using the held trace. We report every mode and nominate only
modes that are zero-wrong across all five folds with >0 incremental predictions.
p5-p19 are never staged/read. PUBLIC_OFFLINE internal CV only.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268

RUNG=307
ALLOWED={
 "bp35-0a0ad940","g50t-5849a774","ls20-9607627b",
 "sb26-7fbdac44","sc25-635fd71a","sp80-589a99af"
}
MODES=("palette","meter","symmetry","regions","objects","composite","ui_mask")
MIN_PRESTATES=2
MIN_TRACES=2


def trace_rows(path:Path):
    return r251.prepare_rows([path])


def exact_key(r):
    return r246.digest({"b":r["before"],"a":r["action"]})


def abstract_key(r,mode):
    if mode=="ui_mask":
        rep=r268.masked(r["before"])
    else:
        rep=r["before_features"][mode]
    return r246.stable((rep,r["action"]))


def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r["after_digest"]
        obs[k][d]+=1; frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=frame[(k,d)]
    return out


def fit_abs(rows,mode):
    obs=defaultdict(Counter); prestates=defaultdict(set); traces=defaultdict(set); frame={}
    for r in rows:
        k=abstract_key(r,mode); d=r["after_digest"]
        obs[k][d]+=1
        prestates[k].add(r["before_digest"])
        traces[k].add(r["trace"])
        frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<MIN_PRESTATES or len(traces[k])<MIN_TRACES:
            continue
        d=next(iter(c)); out[k]=frame[(k,d)]
    return out,{"observed_keys":len(obs),"safe_keys":len(out)}


def evaluate(rows,exact,tab,mode):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["exact_baseline"]+=1
            continue
        s["baseline_abstain"]+=1
        pred=tab.get(abstract_key(r,mode))
        if pred is None:
            s["candidate_abstain"]+=1
            continue
        s["candidate_predictions"]+=1
        ok=pred==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
    p=s["candidate_predictions"]
    s["accuracy"]=round(s["candidate_correct"]/p,6) if p else None
    return dict(s)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--game",required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.game not in ALLOWED: raise SystemExit(f"not allowed: {a.game}")
    ps=sorted(a.input,key=r246.pnum)
    if not ps or any(r246.game_id(p)!=a.game for p in ps): raise SystemExit("exact game traces required")
    if [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    traces=[trace_rows(p) for p in ps]

    totals={m:Counter() for m in MODES}
    folds=[]
    for held in range(5):
        train=[r for i,tr in enumerate(traces) if i!=held for r in tr]
        val=traces[held]
        exact=fit_exact(train)
        fm={"held_trace":held,"exact_keys":len(exact),"modes":{}}
        for m in MODES:
            tab,fit=fit_abs(train,m)
            ev=evaluate(val,exact,tab,m)
            fm["modes"][m]={"fit":fit,"eval":ev}
            for k,v in ev.items():
                if isinstance(v,int): totals[m][k]+=v
        folds.append(fm)

    modes={}
    candidates=[]
    for m in MODES:
        s=totals[m]
        p=s["candidate_predictions"]
        out={**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None}
        modes[m]=out
        if p>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0:
            candidates.append(m)
    best=max(candidates,key=lambda m:(modes[m]["candidate_correct"],modes[m]["candidate_predictions"],-MODES.index(m))) if candidates else None
    verdict="ZERO_WRONG_EXACTFRAME_LOTO_SIGNAL" if best else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r307-remaining6-exactframe-loto/1",
      "rung":RUNG,"game":a.game,
      "protocol":{
        "data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out",
        "exact_baseline_precedence":True,
        "abstract_support":f">={MIN_PRESTATES} exact prestates and >={MIN_TRACES} training traces",
        "p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,
        "promotion_in_r307":False,
      },
      "modes":modes,"candidate_modes":candidates,"best_mode":best,"folds":folds,"verdict":verdict,
      "truth":{
        "public_trace_only":True,"source_free_runtime_logic":True,
        "p5_p9_read":False,"p10_p19_read":False,
        "internal_cross_validation_only":True,
        "independent_hidden_generalization_claim":False,
        "solver_promotion":False,"kaggle_execution":False,
        "competition_submission":False,"submission_quota_spent_by_r307":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
