#!/usr/bin/env python3
"""R302: p0-p4-only local/phase/causal-delta LOTO sweep for four residual ARC3 games.

Games are frozen from the parent ARC job:
  dc22-fdcac232, ft09-0d8bbf25, tr87-cd924810, wa30-ee6fef47

Each game runs three materially bounded local representations entirely within
p0-p4 five-fold leave-one-trace-out:
  spatial: 3x3+5x5 action-canonical UI-masked context
  phase:   spatial + past-only phase_before token
  delta:   spatial + 3x3 binary activity field from the previous transition

Only deterministic non-identity next-center rules with support from >=2 distinct
training traces may fire. Identity is the fallback. p5-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298

RUNG=302
ALLOWED={
 "dc22-fdcac232","ft09-0d8bbf25","tr87-cd924810","wa30-ee6fef47"
}
MIN_TRACE_SUPPORT=2
PAD=-1


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def augment_trace(path):
    rows=r278.annotated_rows([path]); prev=None; out=[]
    for row in rows:
        rr=dict(row)
        rr["_prev_before"]=None if prev is None else prev["before"]
        rr["_prev_after"]=None if prev is None else prev["after"]
        out.append(rr); prev=row
    return out


def phase_token(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)


def prev_delta_patch(row,r,c):
    if row.get("_prev_before") is None: return (0,)*9
    pb=world(row["_prev_before"],row["action"]); pa=world(row["_prev_after"],row["action"])
    h=len(pb); w=len(pb[0]) if h else 0; vals=[]
    for dr in (-1,0,1):
        rr=r+dr
        for dc in (-1,0,1):
            cc=c+dc
            vals.append(int(int(pb[rr][cc])!=int(pa[rr][cc])) if 0<=rr<h and 0<=cc<w else PAD)
    return tuple(vals)


def key_for(row,r,c,mode):
    b=world(row["before"],row["action"])
    base=(r298.patch(b,r,c,1),r298.patch(b,r,c,2),r275.action_class(row["action"]))
    if mode=="spatial": return base
    if mode=="phase": return base+(phase_token(row),)
    if mode=="delta": return base+(prev_delta_patch(row,r,c),)
    raise KeyError(mode)


def fit_rules(traces,mode):
    outcomes=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(traces):
        for row in tr:
            b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    k=key_for(row,r,c,mode); outcomes[k][int(a[r][c])]+=1; support[k].add(ti)
    rules={}
    for k,out in outcomes.items():
        if len(out)!=1 or len(support[k])<MIN_TRACE_SUPPORT: continue
        pred=int(next(iter(out))); center=int(k[0][len(k[0])//2])
        if pred!=center: rules[k]=pred
    return rules,{"keys":len(outcomes),"change_rules":len(rules),"trace_supported_keys":sum(len(support[k])>=MIN_TRACE_SUPPORT for k in outcomes)}


def evaluate(rows,rules,mode):
    m=Counter()
    for row in rows:
        b=world(row["before"],row["action"]); a=world(row["after"],row["action"]); pred=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=key_for(row,r,c,mode)
                if k in rules: pred[r][c]=int(rules[k])
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


def run_loto(traces,mode):
    total=Counter(); folds=[]
    for held in range(len(traces)):
        train=[traces[i] for i in range(len(traces)) if i!=held]
        rules,fit=fit_rules(train,mode); ev=evaluate(traces[held],rules,mode)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--game",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    if a.game not in ALLOWED: raise SystemExit(f"game not allowed: {a.game}")
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={a.game}: raise SystemExit(f"exact game required, got {sorted(by)}")
    ps=sorted(by[a.game],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f"exact p0-p4 required, got {nums}")
    traces=[augment_trace(p) for p in ps]
    modes={}; folds={}
    for mode in ("spatial","phase","delta"):
        modes[mode],folds[mode]=run_loto(traces,mode)
    zero=[m for m,v in modes.items() if v.get("predicted_changes",0)>0 and v.get("false_changes",0)==0 and v.get("pixel_gain",0)>0]
    positive=[m for m,v in modes.items() if v.get("pixel_gain",0)>0]
    if zero:
        best=max(zero,key=lambda m:(modes[m].get("true_changed_correct",0),modes[m].get("pixel_gain",0)))
        verdict="ZERO_FALSE_LOTO_SIGNAL"
    elif positive:
        best=max(positive,key=lambda m:(modes[m].get("pixel_gain",0),-modes[m].get("false_changes",0)))
        verdict="LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        best=None; verdict="NO_SIGNAL"
    out={
      "schema":"deus/arc3-r302-residual4-local-causal-loto/1","rung":RUNG,"game":a.game,
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r302":False},
      "modes":modes,"folds":folds,"best_mode":best,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r302":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"verdict":verdict,"best_mode":best,"modes":modes},sort_keys=True))

if __name__=="__main__": main()
