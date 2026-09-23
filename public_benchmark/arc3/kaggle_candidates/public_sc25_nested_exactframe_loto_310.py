#!/usr/bin/env python3
"""R310: nested reliability-gated exact-frame LOTO for sc25 using p0-p4 only.

R307 found near-signals on p0-p4 LOTO:
  regions: 7 correct / 1 wrong
  meter:   1 correct / 1 wrong
R310 does not retune thresholds on those outer errors. Instead each OUTER fold
builds a training-only nested reliability gate per abstract key:
  - exact visible-state/action baseline has precedence;
  - candidate abstract rule maps to ONE exact next frame;
  - support spans >=2 exact prestates and >=2 training traces;
  - within outer training traces, the key must make >=2 nested added predictions
    with zero nested wrong.
The outer held trace is then evaluated. p5-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG=310
GAME="sc25-635fd71a"
MODES=("regions","meter")
MIN_PRESTATES=2
MIN_TRACES=2
MIN_NESTED_PRED=2


def exact_key(r): return r246.digest({"b":r["before"],"a":r["action"]})
def abs_key(r,mode): return r246.stable((r["before_features"][mode],r["action"]))


def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r["after_digest"]; obs[k][d]+=1; frame[(k,d)]=r["after"]
    return {k:frame[(k,next(iter(c)))] for k,c in obs.items() if len(c)==1}


def fit_abs(rows,mode):
    obs=defaultdict(Counter); prestates=defaultdict(set); traces=defaultdict(set); frame={}
    for r in rows:
        k=abs_key(r,mode); d=r["after_digest"]
        obs[k][d]+=1; prestates[k].add(r["before_digest"]); traces[k].add(r["trace"]); frame[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<MIN_PRESTATES or len(traces[k])<MIN_TRACES: continue
        d=next(iter(c)); tab[k]=frame[(k,d)]
    return tab


def nested_trusted(train_traces,mode):
    stats=defaultdict(Counter)
    for held in range(len(train_traces)):
        train=[r for i,tr in enumerate(train_traces) if i!=held for r in tr]
        val=train_traces[held]
        exact=fit_exact(train); tab=fit_abs(train,mode)
        for r in val:
            if exact_key(r) in exact: continue
            k=abs_key(r,mode); pred=tab.get(k)
            if pred is None: continue
            stats[k]["predictions"]+=1
            stats[k]["correct" if pred==r["after"] else "wrong"]+=1
    trusted={k for k,s in stats.items() if s["predictions"]>=MIN_NESTED_PRED and s["wrong"]==0}
    return trusted,stats


def evaluate(rows,exact,tab,trusted,mode):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        k=abs_key(r,mode)
        if k not in trusted:
            s["candidate_abstain"]+=1; continue
        pred=tab.get(k)
        if pred is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        s["candidate_correct" if pred==r["after"] else "candidate_wrong"]+=1
    p=s["candidate_predictions"]
    s["accuracy"]=round(s["candidate_correct"]/p,6) if p else None
    return dict(s)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if not ps or any(r246.game_id(p)!=GAME for p in ps): raise SystemExit("exact sc25 traces required")
    if [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    traces=[r251.prepare_rows([p]) for p in ps]

    totals={m:Counter() for m in MODES}; folds=[]
    for held in range(5):
        train_traces=[traces[i] for i in range(5) if i!=held]
        train=[r for tr in train_traces for r in tr]
        val=traces[held]; exact=fit_exact(train)
        fm={"held_trace":held,"modes":{}}
        for m in MODES:
            trusted,nested=nested_trusted(train_traces,m)
            tab=fit_abs(train,m)
            ev=evaluate(val,exact,tab,trusted,m)
            fm["modes"][m]={"trusted_keys":len(trusted),
                            "nested_predictions":sum(v["predictions"] for v in nested.values()),
                            "nested_wrong":sum(v["wrong"] for v in nested.values()),
                            "eval":ev}
            for k,v in ev.items():
                if isinstance(v,int): totals[m][k]+=v
        folds.append(fm)

    modes={}; candidates=[]
    for m in MODES:
        s=totals[m]; p=s["candidate_predictions"]
        modes[m]={**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None}
        if p>0 and s["candidate_wrong"]==0 and s["candidate_correct"]>0: candidates.append(m)
    best=max(candidates,key=lambda m:(modes[m]["candidate_correct"],modes[m]["candidate_predictions"])) if candidates else None
    verdict="NESTED_ZERO_WRONG_EXACTFRAME_SIGNAL" if best else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r310-sc25-nested-exactframe-loto/1","rung":RUNG,"game":GAME,
      "lineage":{"r307_run":35827692947,"r307_sc25":"regions 7 correct/1 wrong; meter1/1 on p0-p4 LOTO"},
      "protocol":{"data":"p0-p4 only","outer":"5-fold leave-one-trace-out","inner":"nested training-only per-key reliability gate","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r310":False},
      "modes":modes,"candidate_modes":candidates,"best_mode":best,"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r310":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
