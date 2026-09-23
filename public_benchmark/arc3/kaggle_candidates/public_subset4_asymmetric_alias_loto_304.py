#!/usr/bin/env python3
"""R304: asymmetric alias-repair LOTO for cd82/cn04/m0r0/sk48.

R303 tests symmetric state representations. R304 asks a narrower question:
can a more specific BEFORE state remove aliasing while retaining a deliberately
coarser NEXT-state target?

Modes:
- coarse_to_coarse baseline
- exact_nodes_to_coarse
- exact_graph_to_coarse
- exact_nodes_phase_to_coarse

All boards are action-canonical and static-UI-masked. Evaluation is five-fold
leave-one-trace-out inside p0-p4 only; p5-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274

RUNG=304
ALLOWED_PREFIXES=("cd82","cn04","m0r0","sk48")
MIN_TRACE_SUPPORT=2
MODES=("coarse_to_coarse","exact_nodes_to_coarse","exact_graph_to_coarse","exact_nodes_phase_to_coarse")


def canon(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def phase(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)


def coarse(board,action):
    return r274.desc(canon(board,action),"nodes_coarse")


def exact_nodes(board,action):
    return r274.desc(canon(board,action),"nodes_exact")


def exact_graph(board,action):
    return r274.desc(canon(board,action),"graph_exact")


def before_key(row,mode):
    action=row["action"]
    if mode=="coarse_to_coarse": rep=coarse(row["before"],action)
    elif mode=="exact_nodes_to_coarse": rep=exact_nodes(row["before"],action)
    elif mode=="exact_graph_to_coarse": rep=exact_graph(row["before"],action)
    elif mode=="exact_nodes_phase_to_coarse": rep=(exact_nodes(row["before"],action),phase(row))
    else: raise KeyError(mode)
    return (r274.dig(rep),r275.action_class(action))


def target(row):
    return r274.dig(coarse(row["after"],row["action"]))


def fit(traces,mode):
    obs=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(traces):
        for row in tr:
            k=before_key(row,mode); obs[k][target(row)]+=1; support[k].add(ti)
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1 and len(support[k])>=MIN_TRACE_SUPPORT}
    return tab,{"keys":len(obs),"deterministic_supported":len(tab),"ambiguous":sum(len(v)>1 for v in obs.values())}


def evaluate(rows,tab,mode):
    s=Counter()
    for row in rows:
        s["transitions"]+=1; pred=tab.get(before_key(row,mode))
        if pred is None: s["abstain"]+=1; continue
        s["predictions"]+=1
        s["correct" if pred==target(row) else "wrong"]+=1
    p=s["predictions"]; s["accuracy"]=round(s["correct"]/p,6) if p else None
    return dict(s)


def run_loto(traces,mode):
    total=Counter(); folds=[]
    for held in range(len(traces)):
        train=[traces[i] for i in range(len(traces)) if i!=held]
        tab,fs=fit(train,mode); ev=evaluate(traces[held],tab,mode)
        folds.append({"held_trace":held,"fit":fs,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    p=total["predictions"]; total["accuracy"]=round(total["correct"]/p,6) if p else None
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if len(by)!=1: raise SystemExit(f"one game required, got {sorted(by)}")
    game=next(iter(by)); prefix=game.split("-")[0]
    if prefix not in ALLOWED_PREFIXES: raise SystemExit(f"prefix not allowed: {prefix}")
    ps=sorted(by[game],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f"exact p0-p4 required, got {nums}")
    traces=[r278.annotated_rows([p]) for p in ps]
    modes={}; folds={}
    for m in MODES: modes[m],folds[m]=run_loto(traces,m)
    base=modes["coarse_to_coarse"]
    candidates=[]
    for m in MODES[1:]:
        v=modes[m]
        zero=bool(v.get("predictions",0)>0 and v.get("wrong",0)==0)
        coverage_floor=bool(v.get("correct",0)>=max(1,int(0.75*base.get("correct",0))))
        dominates_error=bool(v.get("wrong",0)<base.get("wrong",0))
        if zero and coverage_floor and dominates_error:
            candidates.append(m)
    best=max(candidates,key=lambda m:(modes[m].get("correct",0),modes[m].get("predictions",0))) if candidates else None
    verdict="ASYMMETRIC_ZERO_WRONG_ALIAS_SIGNAL" if best else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r304-subset4-asymmetric-alias-loto/1","rung":RUNG,"game":game,"prefix":prefix,
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r304":False,
                  "candidate_rule":"wrong=0; correct>=75% coarse baseline correct; fewer wrong than baseline"},
      "baseline":"coarse_to_coarse","modes":modes,"folds":folds,"candidate_modes":candidates,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r304":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":game,"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
