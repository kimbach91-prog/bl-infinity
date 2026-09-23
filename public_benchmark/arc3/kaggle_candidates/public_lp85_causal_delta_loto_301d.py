#!/usr/bin/env python3
"""R301D: p0-p4-only causal local-delta LOTO diagnostic for lp85.

R300's static structural templates are zero-false on source-assisted p5-p9 but
leave most frame errors untouched. R301D tests whether the immediately previous
observed transition supplies missing causal state.

The candidate key is current action-canonical UI-masked 3x3+5x5 context plus a
3x3 binary activity patch from the PREVIOUS transition, rotated into the current
action frame. Only past observations are used. Five-fold leave-one-trace-out is
performed entirely inside p0-p4. p5-p19 are never staged or read.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298

RUNG=301
TARGET_GAME="lp85-305b61c3"
MIN_TRACE_SUPPORT=2
PAD=-1


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def augment_trace(path:Path):
    rows=r278.annotated_rows([path])
    prev=None
    out=[]
    for row in rows:
        rr=dict(row)
        if prev is None:
            rr["_prev_before"]=None; rr["_prev_after"]=None
        else:
            rr["_prev_before"]=prev["before"]; rr["_prev_after"]=prev["after"]
        out.append(rr)
        prev=row
    return out


def binary_delta_patch(row,r,c):
    if row.get("_prev_before") is None:
        return (0,)*9
    action=row["action"]
    pb=world(row["_prev_before"],action); pa=world(row["_prev_after"],action)
    h=len(pb); w=len(pb[0]) if h else 0; vals=[]
    for dr in (-1,0,1):
        rr=r+dr
        for dc in (-1,0,1):
            cc=c+dc
            if 0<=rr<h and 0<=cc<w:
                vals.append(int(int(pb[rr][cc])!=int(pa[rr][cc])))
            else:
                vals.append(PAD)
    return tuple(vals)


def key_for(row,r,c,use_delta):
    b=world(row["before"],row["action"])
    base=(r298.patch(b,r,c,1),r298.patch(b,r,c,2),r275.action_class(row["action"]))
    return base+(binary_delta_patch(row,r,c),) if use_delta else base


def fit_rules(trace_rows,use_delta):
    outcomes=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(trace_rows):
        for row in tr:
            b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    k=key_for(row,r,c,use_delta); outcomes[k][int(a[r][c])]+=1; support[k].add(ti)
    rules={}
    for k,out in outcomes.items():
        if len(out)!=1 or len(support[k])<MIN_TRACE_SUPPORT: continue
        pred=int(next(iter(out))); center=int(k[0][len(k[0])//2])
        if pred!=center: rules[k]=pred
    return rules,{"keys":len(outcomes),"change_rules":len(rules),"trace_supported_keys":sum(len(support[k])>=MIN_TRACE_SUPPORT for k in outcomes)}


def evaluate(rows,rules,use_delta):
    m=Counter()
    for row in rows:
        b=world(row["before"],row["action"]); a=world(row["after"],row["action"]); pred=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=key_for(row,r,c,use_delta)
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


def run_loto(traces,use_delta):
    total=Counter(); folds=[]
    for held in range(len(traces)):
        train=[traces[i] for i in range(len(traces)) if i!=held]
        rules,fit=fit_rules(train,use_delta); ev=evaluate(traces[held],rules,use_delta)
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
    traces=[augment_trace(p) for p in ps]
    spatial,spatial_folds=run_loto(traces,False)
    causal,causal_folds=run_loto(traces,True)

    gain=causal.get("pixel_gain",0)>0
    better_true=causal.get("true_changed_correct",0)>spatial.get("true_changed_correct",0)
    safer=causal.get("false_changes",0)<spatial.get("false_changes",0)
    zero_false=causal.get("predicted_changes",0)>0 and causal.get("false_changes",0)==0
    if zero_false and gain and (better_true or safer):
        verdict="CAUSAL_DELTA_ZERO_FALSE_LOTO_GAIN"
    elif gain and (better_true or safer):
        verdict="CAUSAL_DELTA_LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="CAUSAL_DELTA_NO_SIGNAL"

    out={
      "schema":"deus/arc3-r301d-lp85-causal-delta-loto/1","rung":RUNG,"game":TARGET_GAME,
      "lineage":{"r300":"zero-false structural residual source-assisted signal; exact-frame delta0"},
      "mechanism":{
        "current_state":"action-canonical UI-masked 3x3+5x5 context",
        "causal_memory":"3x3 binary changed/not-changed field from immediately previous transition, rotated into current action frame",
        "support":f">={MIN_TRACE_SUPPORT} distinct training traces",
        "fallback":"identity",
      },
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r301d":False},
      "spatial_loto":spatial,"causal_loto":causal,"spatial_folds":spatial_folds,"causal_folds":causal_folds,
      "delta":{"true_changed_correct":causal.get("true_changed_correct",0)-spatial.get("true_changed_correct",0),"false_changes":causal.get("false_changes",0)-spatial.get("false_changes",0),"pixel_gain":causal.get("pixel_gain",0)-spatial.get("pixel_gain",0),"exact_frame_gain":causal.get("exact_frame_gain",0)-spatial.get("exact_frame_gain",0)},
      "verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"past_only_memory":True,"p5_p9_read":False,"p10_p19_read":False,"internal_cross_validation_only":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r301d":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"spatial":spatial,"causal":causal,"delta":out["delta"]},sort_keys=True))

if __name__=="__main__": main()
