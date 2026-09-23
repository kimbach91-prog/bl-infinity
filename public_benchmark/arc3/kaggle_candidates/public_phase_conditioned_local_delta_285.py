#!/usr/bin/env python3
"""R285: source-free phase/history-conditioned repair for R284 re86 mismatches.

Delta-first repair: R284 showed translation-invariant local deltas alone are
insufficient on re86 (22/31 diagnostic predictions wrong). R285 does not relax
support or accuracy thresholds. It changes the state representation by adding
causal history/phase features available before the current action.

Protocol:
* game: re86 only (exact failing family)
* public traces only; no game source
* candidate representation chosen ONLY by leave-one-trace-out CV on p0-p4
* frozen diagnostic on p5-p9 after selection
* p10-p19 are not staged/read
* exact full-frame scoring; any diagnostic mismatch rejects the repair
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_relational_local_delta_284 as r284

RUNG=285
MODES=("prev_action","prev_action_streak","prev_shape","neighbor_phase")


def coarse_prev_shape(prev: dict[str,Any] | None) -> tuple[Any,...]:
    if prev is None:
        return ("START",)
    ds=r284.diff_cells(prev["before"],prev["after"])
    if not ds:
        return (0,0,0,())
    ys=[y for y,_,_,_ in ds]; xs=[x for _,x,_,_ in ds]
    pairs=Counter((bv,av) for _,_,bv,av in ds)
    # translation-invariant coarse transition shape, deliberately not absolute coords
    return (len(ds),max(ys)-min(ys)+1,max(xs)-min(xs)+1,tuple(sorted(pairs.items())))


def neighbor_topology(board:list[list[int]], c:dict[str,Any]) -> tuple[Any,...]:
    ay,ax=c["anchor"]
    rel=[]
    for o in r284.components(board):
        if o["anchor"]==c["anchor"] and o["sig"]==c["sig"]:
            continue
        oy,ox=o["anchor"]
        rel.append((oy-ay,ox-ax,o["sig"][0],o["sig"][1],o["sig"][2]))
    rel.sort(key=lambda z:(abs(z[0])+abs(z[1]),z))
    return tuple(rel[:3])


def annotate(rows:list[dict[str,Any]]) -> list[dict[str,Any]]:
    by:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for r in rows: by[r["trace"]].append(r)
    out=[]
    for trace,seq in by.items():
        prev=None; prev_action=None; streak=0
        for row in seq:
            if prev_action==row["action"]: streak+=1
            else: streak=0
            x=dict(row)
            x["ctx_prev_action"]=prev_action or "START"
            x["ctx_streak_bucket"]=min(streak,3)
            x["ctx_prev_shape"]=coarse_prev_shape(prev)
            out.append(x)
            prev=row; prev_action=row["action"]
    return out


def key_for(row:dict[str,Any], c:dict[str,Any], mode:str) -> tuple[Any,...]:
    base=(row["action"],c["sig"])
    if mode=="prev_action":
        return base+(row["ctx_prev_action"],)
    if mode=="prev_action_streak":
        return base+(row["ctx_prev_action"],row["ctx_streak_bucket"])
    if mode=="prev_shape":
        return base+(row["ctx_prev_action"],row["ctx_prev_shape"])
    if mode=="neighbor_phase":
        return base+(row["ctx_prev_action"],row["ctx_streak_bucket"],neighbor_topology(row["before"],c))
    raise ValueError(mode)


def observation(row:dict[str,Any],mode:str):
    ds=r284.diff_cells(row["before"],row["after"])
    if not ds or len(ds)>r284.MAX_DIFF: return None
    c=r284.choose_anchor(row["before"],ds)
    if c is None: return None
    ay,ax=c["anchor"]
    delta=tuple(sorted((y-ay,x-ax,bv,av) for y,x,bv,av in ds))
    return key_for(row,c,mode),delta,(ay,ax)


def fit(rows:list[dict[str,Any]],mode:str):
    obs:dict[Any,Counter]=defaultdict(Counter); anchors:dict[tuple[Any,Any],set]=defaultdict(set)
    usable=0
    for row in rows:
        o=observation(row,mode)
        if o is None: continue
        usable+=1; key,delta,anchor=o
        obs[key][delta]+=1; anchors[(key,delta)].add(anchor)
    rules={}
    for key,ctr in obs.items():
        if len(ctr)!=1: continue
        delta,support=ctr.most_common(1)[0]
        if support<r284.MIN_SUPPORT or len(anchors[(key,delta)])<2: continue
        rules[key]=delta
    return rules,{"usable":usable,"rules":len(rules)}


def predict(row:dict[str,Any],rules:dict[Any,Any],mode:str):
    matches=[]
    for c in r284.components(row["before"]):
        key=key_for(row,c,mode)
        if key in rules: matches.append((c,rules[key]))
    if len(matches)!=1: return None
    c,delta=matches[0]; ay,ax=c["anchor"]; b=row["before"]; h,w=len(b),len(b[0]); out=[list(z) for z in b]
    for dy,dx,bv,av in delta:
        y,x=ay+dy,ax+dx
        if not(0<=y<h and 0<=x<w) or int(out[y][x])!=int(bv): return None
    for dy,dx,bv,av in delta: out[ay+dy][ax+dx]=int(av)
    return out


def score(rows,rules,mode):
    s=Counter(); examples=[]
    for row in rows:
        s["transitions"]+=1; p=predict(row,rules,mode)
        if p is None: s["abstain"]+=1; continue
        s["predictions"]+=1; ok=p==row["after"]; s["correct" if ok else "wrong"]+=1
        if len(examples)<30: examples.append({"trace":row["trace"],"action":row["action"],"correct":ok,"prev_action":row["ctx_prev_action"],"streak":row["ctx_streak_bucket"]})
    return {**dict(s),"accuracy":round(s["correct"]/s["predictions"],6) if s["predictions"] else None,"examples":examples}


def select_mode(train_by_trace:dict[str,list[dict[str,Any]]]):
    reports={}
    for mode in MODES:
        agg=Counter(); folds=[]
        traces=sorted(train_by_trace)
        for hold in traces:
            fitrows=[r for t in traces if t!=hold for r in train_by_trace[t]]
            rules,_=fit(fitrows,mode); sc=score(train_by_trace[hold],rules,mode)
            for k in ("transitions","predictions","correct","wrong","abstain"): agg[k]+=int(sc.get(k,0) or 0)
            folds.append({"holdout":hold,"predictions":sc.get("predictions",0),"correct":sc.get("correct",0),"wrong":sc.get("wrong",0)})
        reports[mode]={"aggregate":dict(agg),"folds":folds}
    eligible=[m for m,r in reports.items() if r["aggregate"].get("predictions",0)>0 and r["aggregate"].get("wrong",0)==0]
    chosen=max(eligible,key=lambda m:(reports[m]["aggregate"].get("correct",0),-MODES.index(m))) if eligible else None
    return chosen,reports


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f"exact p0..p9 required: {nums}")
    train=annotate([r for p in ps[:5] for r in r251.prepare_rows([p])]); diag=annotate([r for p in ps[5:] for r in r251.prepare_rows([p])])
    by=defaultdict(list)
    for r in train: by[r["trace"]].append(r)
    chosen,cv=select_mode(by)
    if chosen is None:
        result={"verdict":"NO_STABLE_PHASE_REPAIR","chosen":None,"cv":cv,"diagnostic":None}
    else:
        rules,fitmeta=fit(train,chosen); sc=score(diag,rules,chosen)
        verdict="PASS_ZERO_WRONG_SIGNAL" if sc.get("predictions",0)>0 and sc.get("wrong",0)==0 else ("NO_SIGNAL" if sc.get("predictions",0)==0 else "REJECT_MISMATCH")
        result={"verdict":verdict,"chosen":chosen,"cv":cv,"fit":fitmeta,"diagnostic":sc}
    out={"schema":"deus/arc3-r285-phase-conditioned-local-delta/1","rung":RUNG,
         "protocol":{"game":"re86-8af5384d","selection":"leave-one-trace-out p0-p4 only","diagnostic":"p5-p9 only","p10_p19_staged":False,"candidate_modes":MODES,"support_threshold_unchanged":r284.MIN_SUPPORT,"exact_full_frame_scoring":True},
         "result":result,"truth":{"public_trace_only":True,"source_free":True,"game_source_read":False,"p10_p19_read":False,"kaggle_execution":False,"competition_submission":False,"owner_score_claim":False,"submission_quota_spent":False}}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"chosen":result.get("chosen"),"verdict":result["verdict"],"diagnostic":result.get("diagnostic") and {k:result["diagnostic"].get(k) for k in ("transitions","predictions","correct","wrong","abstain","accuracy")}},sort_keys=True))
if __name__=="__main__": main()
