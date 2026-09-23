#!/usr/bin/env python3
"""R301O: p0-p4-only object-relative residual LOTO diagnostic for lp85.

This tests a materially different unit of computation from R300's seeded pixels:
connected foreground objects on the action-canonical UI-masked world. A rule maps
an object's translation-invariant before descriptor plus a coarse local ring
histogram to a deterministic multi-pixel residual template in a fixed bbox+2
neighborhood. Templates require support from >=2 distinct training traces.

Five-fold leave-one-trace-out is performed entirely on p0-p4. p5-p19 are never
staged/read. PUBLIC_OFFLINE diagnostic only.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict,deque
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG=301
TARGET_GAME="lp85-305b61c3"
MARGIN=2
MIN_TRACE_SUPPORT=2


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def components(board):
    h=len(board); w=len(board[0]) if h else 0
    cnt=Counter(int(v) for row in board for v in row)
    bg=min(cnt,key=lambda k:(-cnt[k],k)) if cnt else 0
    seen=set(); out=[]
    for r in range(h):
        for c in range(w):
            color=int(board[r][c])
            if color==bg or (r,c) in seen: continue
            q=deque([(r,c)]); seen.add((r,c)); pts=[]
            while q:
                rr,cc=q.popleft(); pts.append((rr,cc))
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and int(board[nr][nc])==color:
                        seen.add((nr,nc)); q.append((nr,nc))
            rs=[x for x,y in pts]; cs=[y for x,y in pts]
            r0,c0,r1,c1=min(rs),min(cs),max(rs),max(cs)
            local=tuple(sorted((rr-r0,cc-c0) for rr,cc in pts))
            out.append({"color":color,"pts":pts,"r0":r0,"c0":c0,"r1":r1,"c1":c1,
                        "h":r1-r0+1,"w":c1-c0+1,"shape":r246.digest(local),"bg":bg})
    return out


def ring_hist(board,obj):
    h=len(board); w=len(board[0]) if h else 0
    r0=max(0,obj["r0"]-MARGIN); c0=max(0,obj["c0"]-MARGIN)
    r1=min(h-1,obj["r1"]+MARGIN); c1=min(w-1,obj["c1"]+MARGIN)
    inside=set(obj["pts"]); cnt=Counter()
    for r in range(r0,r1+1):
        for c in range(c0,c1+1):
            if (r,c) in inside: continue
            cnt[int(board[r][c])]+=1
    # coarse capped counts reduce brittle absolute-position dependence
    return tuple(sorted((col,min(n,15)) for col,n in cnt.items()))


def obj_key(board,obj,action):
    return (r275.action_class(action),obj["color"],len(obj["pts"]),obj["h"],obj["w"],obj["shape"],ring_hist(board,obj))


def template_for(before,after,obj):
    h=len(before); w=len(before[0]) if h else 0
    r0=max(0,obj["r0"]-MARGIN); c0=max(0,obj["c0"]-MARGIN)
    r1=min(h-1,obj["r1"]+MARGIN); c1=min(w-1,obj["c1"]+MARGIN)
    rel=[]
    for r in range(r0,r1+1):
        for c in range(c0,c1+1):
            bv=int(before[r][c]); av=int(after[r][c])
            if bv!=av: rel.append((r-obj["r0"],c-obj["c0"],bv,av))
    return tuple(sorted(rel))


def fit_rules(trace_rows):
    obs=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(trace_rows):
        for row in tr:
            b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
            for obj in components(b):
                t=template_for(b,a,obj)
                if not t: continue
                k=obj_key(b,obj,row["action"]); obs[k][t]+=1; support[k].add(ti)
    rules={}
    for k,cnt in obs.items():
        if len(cnt)==1 and len(support[k])>=MIN_TRACE_SUPPORT:
            rules[k]=next(iter(cnt))
    return rules,{"keys_with_change":len(obs),"accepted_templates":len(rules),"trace_supported_keys":sum(len(support[k])>=MIN_TRACE_SUPPORT for k in obs)}


def evaluate(rows,rules):
    m=Counter()
    for row in rows:
        b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
        h=len(b); w=len(b[0]) if h else 0
        proposals=defaultdict(set)
        for obj in components(b):
            k=obj_key(b,obj,row["action"]); t=rules.get(k)
            if t is None: continue
            ok=True
            for dr,dc,bv,av in t:
                rr=obj["r0"]+dr; cc=obj["c0"]+dc
                if not (0<=rr<h and 0<=cc<w and int(b[rr][cc])==int(bv)):
                    ok=False; break
            if not ok: continue
            m["template_firings"]+=1
            for dr,dc,bv,av in t:
                rr=obj["r0"]+dr; cc=obj["c0"]+dc
                proposals[(rr,cc)].add(int(av))
        pred=[list(map(int,x)) for x in b]
        for (r,c),vals in proposals.items():
            if len(vals)==1: pred[r][c]=next(iter(vals))
            else: m["conflicting_cells"]+=1
        id_err=cand_err=0
        for r in range(h):
            for c in range(w):
                bv=int(b[r][c]); av=int(a[r][c]); pv=int(pred[r][c])
                id_err += bv!=av; cand_err += pv!=av
                if pv!=bv:
                    m["predicted_changes"]+=1
                    if pv==av and bv!=av: m["true_changed_correct"]+=1
                    elif pv!=av: m["false_changes"]+=1
        m["frames"]+=1; m["pixels"]+=h*w; m["identity_errors"]+=id_err; m["candidate_errors"]+=cand_err
        m["identity_exact_frames"]+=id_err==0; m["candidate_exact_frames"]+=cand_err==0
    m["pixel_gain"]=m["identity_errors"]-m["candidate_errors"]
    m["exact_frame_gain"]=m["candidate_exact_frames"]-m["identity_exact_frames"]
    return dict(m)


def run_loto(traces):
    total=Counter(); folds=[]
    for held in range(len(traces)):
        train=[traces[i] for i in range(len(traces)) if i!=held]
        rules,fit=fit_rules(train); ev=evaluate(traces[held],rules)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f"exact target required, got {sorted(by)}")
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f"exact p0-p4 required, got {nums}")
    traces=[r278.annotated_rows([p]) for p in ps]
    loto,folds=run_loto(traces)
    if loto.get("predicted_changes",0)>0 and loto.get("false_changes",0)==0 and loto.get("pixel_gain",0)>0:
        verdict="OBJECT_RESIDUAL_ZERO_FALSE_LOTO_GAIN"
    elif loto.get("pixel_gain",0)>0:
        verdict="OBJECT_RESIDUAL_LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="OBJECT_RESIDUAL_NO_SIGNAL"
    out={
      "schema":"deus/arc3-r301o-lp85-object-residual-loto/1","rung":RUNG,"game":TARGET_GAME,
      "lineage":{"r300":"seeded local structural residual zero-false source-assisted signal, exact-frame delta0"},
      "mechanism":{"unit":"connected foreground object","key":"action class + color/size/bbox/exact shape + capped bbox+2 ring histogram","output":"deterministic multi-pixel bbox+2 residual template","support":f">={MIN_TRACE_SUPPORT} distinct training traces","precondition":"template before-values must match","conflict_policy":"discard conflicting cells","fallback":"identity"},
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r301o":False},
      "loto":loto,"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r301o":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"loto":loto},sort_keys=True))

if __name__=="__main__": main()
