#!/usr/bin/env python3
"""R303: p0-p4-only exact-topology LOTO diagnostic for cd82/cn04/m0r0/sk48.

The current parent job marks these games as a separate residual subset where the
static UI-mask representation itself was insufficient. R303 does not reuse
p5-p19. It tests whether preserving exact component shape/topology, optionally
with causal phase, resolves coarse-state aliasing.

All modes are action-canonical and static-UI-masked. The baseline is coarse
component nodes. Candidates are exact component nodes, exact relational graph,
and exact nodes + past-only phase_before. Five-fold leave-one-trace-out is used
inside p0-p4 only.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274

RUNG=303
ALLOWED_PREFIXES=("cd82","cn04","m0r0","sk48")
MIN_TRACE_SUPPORT=2
MODES=("nodes_coarse","nodes_exact","graph_exact","nodes_exact_phase")


def canon(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def phase(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)


def state(row,which,mode):
    board=canon(row[which],row["action"])
    base=mode.replace("_phase","")
    if base=="nodes_coarse": d=r274.desc(board,"nodes_coarse")
    elif base=="nodes_exact": d=r274.desc(board,"nodes_exact")
    elif base=="graph_exact": d=r274.desc(board,"graph_exact")
    else: raise KeyError(mode)
    if mode.endswith("_phase") and which=="before":
        return (d,phase(row))
    if mode.endswith("_phase") and which=="after":
        # phase_after is causal after current action; if absent use SAME/run1
        p=row.get("phase_after",("SAME",1))
        if isinstance(p,list): p=tuple(p)
        return (d,tuple(p) if isinstance(p,tuple) else (str(p),1))
    return d


def fit(traces,mode):
    obs=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(traces):
        for row in tr:
            k=(r274.dig(state(row,"before",mode)),r275.action_class(row["action"]))
            n=r274.dig(state(row,"after",mode))
            obs[k][n]+=1; support[k].add(ti)
    tab={}
    for k,c in obs.items():
        if len(c)==1 and len(support[k])>=MIN_TRACE_SUPPORT:
            tab[k]=next(iter(c))
    return tab,{"keys":len(obs),"deterministic_supported":len(tab),"ambiguous":sum(len(c)>1 for c in obs.values())}


def evaluate(rows,tab,mode):
    s=Counter()
    for row in rows:
        s["transitions"]+=1
        k=(r274.dig(state(row,"before",mode)),r275.action_class(row["action"]))
        pred=tab.get(k)
        if pred is None:
            s["abstain"]+=1; continue
        s["predictions"]+=1
        actual=r274.dig(state(row,"after",mode))
        s["correct" if pred==actual else "wrong"]+=1
    p=s["predictions"]
    s["accuracy"]=round(s["correct"]/p,6) if p else None
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
    base=modes["nodes_coarse"]
    candidates=[]
    for m in MODES[1:]:
        v=modes[m]
        if v.get("predictions",0)>0 and v.get("wrong",0)==0 and v.get("correct",0)>base.get("correct",0):
            candidates.append(m)
    best=max(candidates,key=lambda m:(modes[m].get("correct",0),modes[m].get("predictions",0))) if candidates else None
    verdict="EXACT_TOPOLOGY_LOTO_SIGNAL" if best else "NO_SIGNAL"
    out={
      "schema":"deus/arc3-r303-subset4-exact-topology-loto/1","rung":RUNG,"game":game,"prefix":prefix,
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r303":False},
      "baseline":"nodes_coarse","modes":modes,"folds":folds,"candidate_modes":candidates,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r303":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":game,"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
