#!/usr/bin/env python3
"""R306: nested reliability-gated backoff for sk48 using p0-p4 only.

R304 showed that exact graph -> coarse next state is zero-wrong on p0-p4 LOTO
but has very low coverage, while coarse->coarse has much higher coverage and
29 wrong predictions. R306 composes them conservatively:

1) exact_graph_to_coarse has precedence;
2) back off to a coarse key only if, inside the OUTER training set, that key
   made >=2 nested leave-one-training-trace-out predictions with ZERO wrong;
3) refit the trusted coarse key on the full outer training set;
4) evaluate the outer held trace.

This is nested cross-validation entirely within p0-p4. p5-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=306
GAME="sk48-d8078629"
EXACT="exact_graph_to_coarse"
COARSE="coarse_to_coarse"
MIN_NESTED_PRED=2


def fit_raw(rows,mode):
    groups={}
    for r in rows:
        groups.setdefault(r["trace"],[]).append(r)
    return r304.fit(list(groups.values()),mode)


def nested_trust(train_traces):
    stats=defaultdict(Counter)
    for held in range(len(train_traces)):
        subtrain=[r for i,tr in enumerate(train_traces) if i!=held for r in tr]
        val=train_traces[held]
        tab,_=fit_raw(subtrain,COARSE)
        for row in val:
            k=r304.before_key(row,COARSE)
            pred=tab.get(k)
            if pred is None: continue
            stats[k]["predictions"]+=1
            stats[k]["correct" if pred==r304.target(row) else "wrong"]+=1
    trusted={k for k,s in stats.items() if s["predictions"]>=MIN_NESTED_PRED and s["wrong"]==0}
    return trusted,stats


def eval_outer(rows,exact_tab,coarse_tab,trusted):
    exact=Counter(); ensemble=Counter()
    for row in rows:
        target=r304.target(row)
        ek=r304.before_key(row,EXACT)
        ck=r304.before_key(row,COARSE)

        ep=exact_tab.get(ek)
        exact["transitions"]+=1
        if ep is None: exact["abstain"]+=1
        else:
            exact["predictions"]+=1
            exact["correct" if ep==target else "wrong"]+=1

        ensemble["transitions"]+=1
        if ep is not None:
            pred=ep; ensemble["exact_route"]+=1
        elif ck in trusted and ck in coarse_tab:
            pred=coarse_tab[ck]; ensemble["trusted_coarse_route"]+=1
        else:
            ensemble["abstain"]+=1
            continue
        ensemble["predictions"]+=1
        ensemble["correct" if pred==target else "wrong"]+=1

    for s in (exact,ensemble):
        p=s["predictions"]; s["accuracy"]=round(s["correct"]/p,6) if p else None
    return dict(exact),dict(ensemble)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f"exact p0-p4 required, got {nums}")
    traces=[r278.annotated_rows([p]) for p in ps]

    total_exact=Counter(); total_ens=Counter(); folds=[]
    for held in range(5):
        train_traces=[traces[i] for i in range(5) if i!=held]
        train=[r for tr in train_traces for r in tr]
        trusted,nested=nested_trust(train_traces)
        exact_tab,exact_fit=fit_raw(train,EXACT)
        coarse_tab,coarse_fit=fit_raw(train,COARSE)
        e,s=eval_outer(traces[held],exact_tab,coarse_tab,trusted)
        folds.append({
          "held_trace":held,
          "trusted_coarse_keys":len(trusted),
          "nested_predictions":sum(v["predictions"] for v in nested.values()),
          "nested_wrong":sum(v["wrong"] for v in nested.values()),
          "exact_fit":exact_fit,"coarse_fit":coarse_fit,
          "exact_only":e,"ensemble":s,
        })
        for k,v in e.items():
            if isinstance(v,int): total_exact[k]+=v
        for k,v in s.items():
            if isinstance(v,int): total_ens[k]+=v

    for s in (total_exact,total_ens):
        p=s["predictions"]; s["accuracy"]=round(s["correct"]/p,6) if p else None

    signal=bool(total_ens["predictions"]>total_exact["predictions"] and total_ens["wrong"]==0 and total_ens["correct"]>total_exact["correct"])
    verdict="SELECTIVE_BACKOFF_ZERO_WRONG_LOTO_GAIN" if signal else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r306-sk48-selective-backoff-loto/1","rung":RUNG,"game":GAME,
      "lineage":{"r304_run":35826885553,"r304_sk48":"exact graph zero-wrong but only 11/1142 LOTO predictions; coarse 43 correct/29 wrong"},
      "mechanism":{"precedence":"exact_graph_to_coarse","backoff":"coarse_to_coarse only for nested-LOTO zero-wrong keys","min_nested_predictions":MIN_NESTED_PRED},
      "protocol":{"data":"p0-p4 only","outer":"5-fold leave-one-trace-out","inner":"nested leave-one-training-trace-out reliability gate","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r306":False},
      "exact_only":dict(total_exact),"ensemble":dict(total_ens),"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r306":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"exact_only":out["exact_only"],"ensemble":out["ensemble"]},sort_keys=True))

if __name__=="__main__": main()
