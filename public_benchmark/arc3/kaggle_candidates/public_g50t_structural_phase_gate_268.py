#!/usr/bin/env python3
"""R268: source-free structural phase reliability gate for g50t.

R262 showed coarse current-state descriptors did not beat action-only modal
delta correct coverage. R268 changes the question: instead of replacing the
action model, learn *where it is trustworthy* using richer relational structure.

Protocol:
  p0-p4 fit action-conditioned modal normalized delta signature
  p5-p9 select structural reliability keys with support>=2, correct>0, wrong=0
  freeze selected feature family per action
  p0-p9 refit deterministic key->delta only when all observed deltas agree
  p10-p19 frozen reused public-development evaluation

Diagnostic predicts normalized delta signatures only. No game source, hidden
state, Kaggle execution/score, leaderboard data, or submission.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=268\n# R268_RETRY2_MARKER: self-contained compile path verified before runtime.

def delta_sig(before,after):
    ch=[]
    for r in range(len(before)):
        for cc in range(len(before[0])):
            b=int(before[r][cc]); a=int(after[r][cc])
            if b!=a: ch.append((r,cc,b,a))
    if not ch:return "IDENTITY",0
    r0=min(x[0] for x in ch); c0=min(x[1] for x in ch)
    r1=max(x[0] for x in ch); c1=max(x[1] for x in ch)
    norm=tuple(sorted((r-r0,cc-c0,b,a) for r,cc,b,a in ch))
    return stable(((r1-r0+1,c1-c0+1),norm)),len(ch)

FEATURE_MODES=(
    "rel_basic",
    "rel_edge",
    "rel_pairwise",
    "rel_palettefree",
    "rel_full",
)
MIN_KEY_TRACE_SUPPORT=2


def stable(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]


def extract(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        ev=r246.load_events(p); pre=ev[0]
        for step,e in enumerate(ev[1:]):
            if e.get("type")!="action":
                pre=e; continue
            b=[[int(v) for v in row] for row in pre["board"]]
            a=[[int(v) for v in row] for row in e["board"]]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                ds,n=delta_sig(b,a)
                out.append({"trace":p.name,"step":step,"action":r246.action_name(e),"board":b,"delta_sig":ds,"changed":n})
            pre=e
    return out


def bg(board):
    c=Counter(v for row in board for v in row)
    return min(c,key=lambda k:(-c[k],k))


def comps(board):
    h=len(board); w=len(board[0]); b=bg(board); seen=set(); out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen or board[r][c]==b: continue
            col=int(board[r][c]); q=deque([(r,c)]); seen.add((r,c)); pts=[]
            while q:
                rr,cc=q.popleft(); pts.append((rr,cc))
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and int(board[nr][nc])==col:
                        seen.add((nr,nc)); q.append((nr,nc))
            r0=min(x for x,_ in pts); r1=max(x for x,_ in pts); c0=min(y for _,y in pts); c1=max(y for _,y in pts)
            norm=tuple(sorted((rr-r0,cc-c0) for rr,cc in pts))
            out.append({
                "color":col,
                "area":len(pts),
                "bbox":(r0,c0,r1,c1),
                "shape":stable(norm),
                "center2":(r0+r1,c0+c1),
                "edge":(r0==0,c0==0,r1==h-1,c1==w-1),
            })
    return sorted(out,key=lambda x:(x["area"],x["color"],x["bbox"],x["shape"]))


def binv(x,cuts):
    for i,c in enumerate(cuts):
        if x<=c:return i
    return len(cuts)


def structural(board,mode):
    h=len(board); w=len(board[0]); b=bg(board); cs=comps(board)
    n=len(cs); areas=sorted(c["area"] for c in cs)
    total=sum(areas)
    largest=max(areas) if areas else 0
    edge_count=sum(any(c["edge"]) for c in cs)
    shape_mult=Counter(c["shape"] for c in cs)
    repeated_shapes=sum(v>=2 for v in shape_mult.values())
    if cs:
        r0=min(c["bbox"][0] for c in cs); c0=min(c["bbox"][1] for c in cs)
        r1=max(c["bbox"][2] for c in cs); c1=max(c["bbox"][3] for c in cs)
        span=(binv(r1-r0+1,[4,8,16,32]),binv(c1-c0+1,[4,8,16,32]))
    else:
        span=(0,0)
    base=(
        binv(n,[1,2,4,8,16]),
        binv(total,[4,12,32,64,128,256]),
        binv(largest,[1,2,4,8,16,32,64]),
        binv(edge_count,[0,1,2,4,8]),
        binv(repeated_shapes,[0,1,2,4]),
        span,
    )
    if mode=="rel_basic":
        return base
    # pairwise center relation histogram, color-blind
    rel=Counter()
    for i,a in enumerate(cs):
        ar,ac=a["center2"]
        for j,bb in enumerate(cs):
            if i>=j: continue
            br,bc=bb["center2"]
            dr=br-ar; dc=bc-ac
            orient=("S" if dr>0 else "N" if dr<0 else "C", "E" if dc>0 else "W" if dc<0 else "C")
            dist=binv(abs(dr)+abs(dc),[2,4,8,16,32])
            rel[(orient,dist)]+=1
    relsig=tuple(sorted((k[0],k[1],binv(v,[1,2,4,8])) for k,v in rel.items()))
    if mode=="rel_pairwise":
        return base+(relsig,)
    edge_sig=tuple(sorted((binv(c["area"],[1,2,4,8,16,32]),c["edge"]) for c in cs))
    if mode=="rel_edge":
        return base+(edge_sig,)
    geom=tuple(sorted((binv(c["area"],[1,2,4,8,16,32]),
                       binv(c["bbox"][2]-c["bbox"][0]+1,[1,2,4,8,16]),
                       binv(c["bbox"][3]-c["bbox"][1]+1,[1,2,4,8,16]),
                       c["shape"]) for c in cs))
    if mode=="rel_palettefree":
        return base+(relsig,geom)
    palette=tuple(sorted((int(k),binv(v,[1,2,4,8,16,32,64])) for k,v in Counter(x for row in board for x in row).items() if k!=b))
    if mode=="rel_full":
        return base+(relsig,geom,palette)
    raise KeyError(mode)


def fit_action_modal(rows):
    obs=defaultdict(Counter); trace_support=defaultdict(lambda:defaultdict(set))
    for r in rows:
        if r["changed"]==0: continue
        obs[r["action"]][r["delta_sig"]]+=1
        trace_support[r["action"]][r["delta_sig"]].add(r["trace"])
    model={}
    for a,c in obs.items():
        ranked=sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))
        if ranked:
            model[a]=ranked[0][0]
    return model


def select_reliability(train,val):
    action_model=fit_action_modal(train)
    selected={}; diagnostics={}
    for action in sorted(set(r["action"] for r in train+val)):
        target=action_model.get(action)
        cand={}
        for mode in FEATURE_MODES:
            key_stats=defaultdict(Counter); key_traces=defaultdict(set)
            for r in val:
                if r["action"]!=action or r["changed"]==0 or target is None: continue
                k=stable(structural(r["board"],mode))
                ok=(r["delta_sig"]==target)
                key_stats[k]["correct" if ok else "wrong"]+=1
                key_stats[k]["n"]+=1; key_traces[k].add(r["trace"])
            accepted={k for k,s in key_stats.items() if s["correct"]>0 and s["wrong"]==0 and len(key_traces[k])>=MIN_KEY_TRACE_SUPPORT}
            met=Counter()
            for r in val:
                if r["action"]!=action or r["changed"]==0 or target is None: continue
                k=stable(structural(r["board"],mode))
                if k not in accepted:
                    met["abstain"]+=1; continue
                met["predictions"]+=1
                if r["delta_sig"]==target: met["correct"]+=1
                else: met["wrong"]+=1
            cand[mode]={
                "target_delta":target,
                "accepted_keys":sorted(accepted),
                "accepted_key_count":len(accepted),
                "validation":dict(met),
            }
        viable=[m for m,v in cand.items() if v["validation"].get("correct",0)>0 and v["validation"].get("wrong",0)==0]
        if viable:
            viable.sort(key=lambda m:(-cand[m]["validation"].get("correct",0),
                                      -cand[m]["validation"].get("predictions",0),
                                      cand[m]["accepted_key_count"],m))
            selected[action]=viable[0]
        diagnostics[action]=cand
    return action_model,selected,diagnostics


def refit_mapping(rows,selected,diagnostics):
    out={}
    for action,mode in selected.items():
        allowed=set(diagnostics[action][mode]["accepted_keys"])
        obs=defaultdict(Counter); traces=defaultdict(lambda:defaultdict(set))
        for r in rows:
            if r["action"]!=action or r["changed"]==0: continue
            k=stable(structural(r["board"],mode))
            if k not in allowed: continue
            obs[k][r["delta_sig"]]+=1; traces[k][r["delta_sig"]].add(r["trace"])
        mapping={}
        for k,c in obs.items():
            if len(c)!=1: continue
            sig=next(iter(c))
            if len(traces[k][sig])>=MIN_KEY_TRACE_SUPPORT: mapping[k]=sig
        out[action]={"mode":mode,"mapping":mapping}
    return out


def evaluate(rows,refit):
    s=Counter(); by=defaultdict(Counter); examples=[]
    for r in rows:
        if r["changed"]==0:
            s["identity_skipped"]+=1; continue
        s["nonidentity"]+=1; by[r["action"]]["nonidentity"]+=1
        pack=refit.get(r["action"])
        if not pack:
            s["abstain"]+=1; by[r["action"]]["abstain"]+=1; continue
        k=stable(structural(r["board"],pack["mode"]))
        pred=pack["mapping"].get(k)
        if pred is None:
            s["abstain"]+=1; by[r["action"]]["abstain"]+=1; continue
        s["predictions"]+=1; by[r["action"]]["predictions"]+=1
        ok=(pred==r["delta_sig"])
        s["correct" if ok else "wrong"]+=1; by[r["action"]]["correct" if ok else "wrong"]+=1
        if len(examples)<30: examples.append({"trace":r["trace"],"action":r["action"],"mode":pack["mode"],"correct":ok})
    n=s["predictions"]; opp=s["nonidentity"]
    return {**dict(s),"accuracy":round(s["correct"]/n,6) if n else None,
            "coverage":round(n/opp,6) if opp else 0.0,
            "correct_coverage":round(s["correct"]/opp,6) if opp else 0.0,
            "by_action":{a:dict(v) for a,v in sorted(by.items())},"examples":examples}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)): raise ValueError("exact p0..p19 required")
    parts=[extract([p]) for p in ps]
    tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:10] for r in x]
    fit=[r for x in parts[:10] for r in x]; ho=[r for x in parts[10:] for r in x]
    action_model,selected,diag=select_reliability(tr,va)
    refit=refit_mapping(fit,selected,diag)
    held=evaluate(ho,refit)
    gain=bool(held.get("predictions",0)>0 and held.get("wrong",0)==0 and held.get("correct",0)>0)
    out={
      "schema":"deus/arc3-r268-g50t-structural-phase-gate/1",
      "rung":RUNG,
      "lineage":{"r262":"coarse descriptors no promotion","repair":"structural relation used as zero-wrong reliability gate, not replacement predictor"},
      "protocol":{"fit":"p0-p4 action modal","select":"p5-p9 zero-wrong structural reliability keys",
                  "refit":"p0-p9 deterministic selected key->delta","frozen_eval":"p10-p19"},
      "action_model":action_model,"selected_by_action":selected,"selection_diagnostic":diag,
      "heldout":held,"non_dominated_source_side_gain":gain,
      "promotion":{"integration_candidate":gain,"solver_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,
               "p10_p19_never_updates_selection_or_model":True,
               "p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
               "independent_generalization_claim":False,"kaggle_execution":False,
               "competition_submission":False,"submission_quota_spent":False,"owner_score_claim":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"selected":selected,"heldout":held,"gain":gain},sort_keys=True))

if __name__=="__main__": main()
