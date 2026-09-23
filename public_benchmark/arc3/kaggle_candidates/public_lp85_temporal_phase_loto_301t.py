#!/usr/bin/env python3
"""R301T: p0-p4-only temporal-phase LOTO diagnostic for lp85.

R300 established zero-false structural residual templates on source-assisted p5-p9
but did not increase exact-frame count. This diagnostic does NOT read p5-p19.
It asks whether a causal phase token, derived only from actions already observed
before the current transition, can safely unlock additional local changes.

For each p0-p4 leave-one-trace-out fold:
- canonicalize the visible board to the current directional action and apply the
  frozen static UI mask;
- fit deterministic 3x3+5x5 next-center rules on the other four traces;
- compare a spatial key against the same key augmented with causal phase_before;
- require support from >=2 distinct training traces and apply change rules only;
- evaluate on the held trace, with identity fallback.

This is PUBLIC_OFFLINE internal cross-validation only. No p5-p19, Kaggle, score,
or solver-promotion claim is permitted.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_hierarchical_sparse_delta_gate_298 as r298

RUNG=301
TARGET_GAME="lp85-305b61c3"
MIN_TRACE_SUPPORT=2


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def phase(row:dict[str,Any]):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)


def key_for(row,r,c,use_phase:bool):
    b=world(row["before"],row["action"])
    base=(r298.patch(b,r,c,1),r298.patch(b,r,c,2),r275.action_class(row["action"]))
    return base+(phase(row),) if use_phase else base


def fit_rules(trace_rows,use_phase:bool):
    outcomes=defaultdict(Counter)
    trace_support=defaultdict(set)
    for ti,tr in enumerate(trace_rows):
        for row in tr:
            b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    k=key_for(row,r,c,use_phase)
                    outcomes[k][int(a[r][c])]+=1
                    trace_support[k].add(ti)
    rules={}
    for k,out in outcomes.items():
        if len(out)!=1 or len(trace_support[k])<MIN_TRACE_SUPPORT:
            continue
        pred=int(next(iter(out)))
        p3=k[0]; center=int(p3[len(p3)//2])
        if pred!=center:
            rules[k]=pred
    return rules,{
        "deterministic_change_rules":len(rules),
        "all_keys":len(outcomes),
        "trace_supported_keys":sum(len(trace_support[k])>=MIN_TRACE_SUPPORT for k in outcomes),
    }


def eval_rows(rows,rules,use_phase:bool):
    m=Counter()
    for row in rows:
        b=world(row["before"],row["action"]); a=world(row["after"],row["action"])
        pred=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=key_for(row,r,c,use_phase)
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
        m["frames"]+=1; m["pixels"]+=h*w
        m["identity_errors"]+=id_err; m["candidate_errors"]+=cand_err
        m["identity_exact_frames"]+=id_err==0; m["candidate_exact_frames"]+=cand_err==0
    m["pixel_gain"]=m["identity_errors"]-m["candidate_errors"]
    m["exact_frame_gain"]=m["candidate_exact_frames"]-m["identity_exact_frames"]
    return dict(m)


def run_loto(traces,use_phase:bool):
    total=Counter(); folds=[]
    for held in range(len(traces)):
        train=[traces[i] for i in range(len(traces)) if i!=held]
        rules,fit=fit_rules(train,use_phase)
        ev=eval_rows(traces[held],rules,use_phase)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f"exact target required, got {sorted(by)}")
    ps=sorted(by[TARGET_GAME],key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f"exact p0-p4 required, got {nums}")

    traces=[r278.annotated_rows([p]) for p in ps]
    spatial,spatial_folds=run_loto(traces,False)
    temporal,temporal_folds=run_loto(traces,True)

    zero_false=temporal.get("predicted_changes",0)>0 and temporal.get("false_changes",0)==0
    safer=temporal.get("false_changes",0)<spatial.get("false_changes",0)
    more_true=temporal.get("true_changed_correct",0)>spatial.get("true_changed_correct",0)
    gain=temporal.get("pixel_gain",0)>0
    if zero_false and gain and (more_true or safer):
        verdict="TEMPORAL_PHASE_ZERO_FALSE_LOTO_GAIN"
    elif gain and (more_true or safer):
        verdict="TEMPORAL_PHASE_LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="TEMPORAL_PHASE_NO_SIGNAL"

    out={
      "schema":"deus/arc3-r301t-lp85-temporal-phase-loto/1",
      "rung":RUNG,
      "game":TARGET_GAME,
      "lineage":{"r300":"zero-false source-assisted structural residual signal; exact-frame delta 0"},
      "mechanism":{
        "world":"action-canonical static-UI-masked board",
        "spatial_key":"3x3 + 5x5 local context + action class",
        "temporal_delta":"add phase_before = prior-action relation + capped prior-action run length",
        "support":f">={MIN_TRACE_SUPPORT} distinct training traces",
        "fallback":"identity",
      },
      "protocol":{
        "data":"p0-p4 only",
        "evaluation":"5-fold leave-one-trace-out",
        "p5_p9_staged_or_read":False,
        "p10_p19_staged_or_read":False,
        "threshold_sweep":False,
        "promotion_in_r301t":False,
      },
      "spatial_loto":spatial,
      "temporal_loto":temporal,
      "spatial_folds":spatial_folds,
      "temporal_folds":temporal_folds,
      "delta":{
        "true_changed_correct":temporal.get("true_changed_correct",0)-spatial.get("true_changed_correct",0),
        "false_changes":temporal.get("false_changes",0)-spatial.get("false_changes",0),
        "pixel_gain":temporal.get("pixel_gain",0)-spatial.get("pixel_gain",0),
        "exact_frame_gain":temporal.get("exact_frame_gain",0)-spatial.get("exact_frame_gain",0),
      },
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_read":False,
        "p10_p19_read":False,
        "internal_cross_validation_only":True,
        "independent_hidden_generalization_claim":False,
        "solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
        "submission_quota_spent_by_r301t":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"spatial":spatial,"temporal":temporal,"delta":out["delta"]},sort_keys=True))

if __name__=="__main__": main()
