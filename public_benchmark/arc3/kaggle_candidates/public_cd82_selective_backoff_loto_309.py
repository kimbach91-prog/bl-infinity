#!/usr/bin/env python3
"""R309: nested reliability-gated backoff for cd82 using p0-p4 only.

R304: exact_nodes_to_coarse is zero-wrong in p0-p4 LOTO (139/139) while
coarse_to_coarse has greater coverage but 9 wrong. R305 source-assisted p5-p9
showed both routes zero-wrong there, with coarse covering more. R309 does NOT
use p5-p9. It asks whether nested training-only reliability can safely recover
some of the coarse coverage:
  exact_nodes_to_coarse first;
  coarse backoff only for keys with >=2 nested predictions and zero nested wrong.
Five-fold outer LOTO stays entirely in p0-p4.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=309
GAME="cd82-fb555c5d"
EXACT="exact_nodes_to_coarse"
COARSE="coarse_to_coarse"
MIN_NESTED_PRED=2


def fit_raw(rows,mode):
    return r304.fit([rows],mode)


def nested_trust(train_traces):
    stats=defaultdict(Counter)
    for held in range(len(train_traces)):
        sub=[r for i,tr in enumerate(train_traces) if i!=held for r in tr]
        val=train_traces[held]
        tab,_=fit_raw(sub,COARSE)
        for row in val:
            k=r304.before_key(row,COARSE); pred=tab.get(k)
            if pred is None: continue
            stats[k]["predictions"]+=1
            stats[k]["correct" if pred==r304.target(row) else "wrong"]+=1
    trusted={k for k,s in stats.items() if s["predictions"]>=MIN_NESTED_PRED and s["wrong"]==0}
    return trusted,stats


def eval_outer(rows,exact_tab,coarse_tab,trusted):
    ex=Counter(); ens=Counter()
    for row in rows:
        tgt=r304.target(row); ek=r304.before_key(row,EXACT); ck=r304.before_key(row,COARSE)
        ep=exact_tab.get(ek)
        ex["transitions"]+=1
        if ep is None: ex["abstain"]+=1
        else:
            ex["predictions"]+=1; ex["correct" if ep==tgt else "wrong"]+=1
        ens["transitions"]+=1
        if ep is not None:
            pred=ep; ens["exact_route"]+=1
        elif ck in trusted and ck in coarse_tab:
            pred=coarse_tab[ck]; ens["trusted_coarse_route"]+=1
        else:
            ens["abstain"]+=1; continue
        ens["predictions"]+=1; ens["correct" if pred==tgt else "wrong"]+=1
    for s in (ex,ens):
        p=s["predictions"]; s["accuracy"]=round(s["correct"]/p,6) if p else None
    return dict(ex),dict(ens)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(5)): raise SystemExit("exact p0-p4 required")
    traces=[r278.annotated_rows([p]) for p in ps]

    tex=Counter(); tens=Counter(); folds=[]
    for held in range(5):
        train_traces=[traces[i] for i in range(5) if i!=held]
        train=[r for tr in train_traces for r in tr]
        trusted,nested=nested_trust(train_traces)
        etab,efit=fit_raw(train,EXACT); ctab,cfit=fit_raw(train,COARSE)
        ex,ens=eval_outer(traces[held],etab,ctab,trusted)
        folds.append({"held_trace":held,"trusted_coarse_keys":len(trusted),
                      "nested_predictions":sum(v["predictions"] for v in nested.values()),
                      "nested_wrong":sum(v["wrong"] for v in nested.values()),
                      "exact_fit":efit,"coarse_fit":cfit,"exact_only":ex,"ensemble":ens})
        for k,v in ex.items():
            if isinstance(v,int): tex[k]+=v
        for k,v in ens.items():
            if isinstance(v,int): tens[k]+=v
    for s in (tex,tens):
        p=s["predictions"]; s["accuracy"]=round(s["correct"]/p,6) if p else None
    signal=bool(tens["predictions"]>tex["predictions"] and tens["wrong"]==0 and tens["correct"]>tex["correct"])
    verdict="SELECTIVE_BACKOFF_ZERO_WRONG_LOTO_GAIN" if signal else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r309-cd82-selective-backoff-loto/1","rung":RUNG,"game":GAME,
      "lineage":{"r304":"exact_nodes_to_coarse 139/139 zero-wrong p0-p4 LOTO; coarse had 9 wrong","r305":"source-assisted p5-p9 candidate247/247 vs coarse255/255; not used for R309 selection"},
      "protocol":{"data":"p0-p4 only","outer":"5-fold leave-one-trace-out","inner":"nested training-only coarse-key reliability","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r309":False},
      "exact_only":dict(tex),"ensemble":dict(tens),"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r309":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"exact_only":out["exact_only"],"ensemble":out["ensemble"]},sort_keys=True))

if __name__=="__main__": main()
