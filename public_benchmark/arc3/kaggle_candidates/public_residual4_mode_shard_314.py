#!/usr/bin/env python3
"""R314: sharded execution wrapper for R302 residual4 p0-p4 LOTO modes.

This preserves R302 solver/evaluation semantics while removing redundant
canonicalization from the execution representation. Each row's action-canonical
before/after worlds and each cell key are prepared once and reused across the
five LOTO folds. The purpose is runtime resilience, not a new solver.

No p5-p19 traces are staged/read.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302

RUNG=314
ALLOWED=r302.ALLOWED
MODES=("spatial","phase","delta")


def _prepare_trace(trace,mode):
    """Cache exactly the worlds/keys that R302.key_for would recompute per cell/fold."""
    out=[]
    for row in trace:
        action=row["action"]
        b=r302.world(row["before"],action)
        a=r302.world(row["after"],action)
        ac=r302.r275.action_class(action)
        phase=r302.phase_token(row) if mode=="phase" else None
        if mode=="delta" and row.get("_prev_before") is not None:
            pb=r302.world(row["_prev_before"],action)
            pa=r302.world(row["_prev_after"],action)
        else:
            pb=pa=None
        h=len(b); w=len(b[0]) if h else 0
        keys=[]
        for rr in range(h):
            kr=[]
            for cc in range(w):
                base=(r302.r298.patch(b,rr,cc,1),r302.r298.patch(b,rr,cc,2),ac)
                if mode=="spatial":
                    k=base
                elif mode=="phase":
                    k=base+(phase,)
                elif mode=="delta":
                    if pb is None:
                        dp=(0,)*9
                    else:
                        vals=[]; ph=len(pb); pw=len(pb[0]) if ph else 0
                        for dr in (-1,0,1):
                            rrr=rr+dr
                            for dc in (-1,0,1):
                                ccc=cc+dc
                                vals.append(int(int(pb[rrr][ccc])!=int(pa[rrr][ccc])) if 0<=rrr<ph and 0<=ccc<pw else r302.PAD)
                        dp=tuple(vals)
                    k=base+(dp,)
                else:
                    raise KeyError(mode)
                kr.append(k)
            keys.append(kr)
        out.append({"b":b,"a":a,"keys":keys})
    return out


def _fit_rules(prepared_traces):
    outcomes=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(prepared_traces):
        for row in tr:
            b=row["b"]; a=row["a"]; keys=row["keys"]
            h=len(b); w=len(b[0]) if h else 0
            for rr in range(h):
                for cc in range(w):
                    k=keys[rr][cc]
                    outcomes[k][int(a[rr][cc])]+=1
                    support[k].add(ti)
    rules={}
    for k,out in outcomes.items():
        if len(out)!=1 or len(support[k])<r302.MIN_TRACE_SUPPORT:
            continue
        pred=int(next(iter(out)))
        center=int(k[0][len(k[0])//2])
        if pred!=center:
            rules[k]=pred
    return rules,{"keys":len(outcomes),"change_rules":len(rules),"trace_supported_keys":sum(len(support[k])>=r302.MIN_TRACE_SUPPORT for k in outcomes)}


def _evaluate(prepared_rows,rules):
    m=Counter()
    for row in prepared_rows:
        b=row["b"]; a=row["a"]; keys=row["keys"]
        pred=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        for rr in range(h):
            for cc in range(w):
                k=keys[rr][cc]
                if k in rules:
                    pred[rr][cc]=int(rules[k])
        id_err=cand_err=0
        for rr in range(h):
            for cc in range(w):
                bv=int(b[rr][cc]); av=int(a[rr][cc]); pv=int(pred[rr][cc])
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


def _run_loto_cached(traces,mode):
    prepared=[_prepare_trace(tr,mode) for tr in traces]
    total=Counter(); folds=[]
    for held in range(len(prepared)):
        train=[prepared[i] for i in range(len(prepared)) if i!=held]
        rules,fit=_fit_rules(train)
        ev=_evaluate(prepared[held],rules)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--game",required=True)
    ap.add_argument("--mode",choices=MODES,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.game not in ALLOWED: raise SystemExit(f"game not allowed: {a.game}")
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={a.game}: raise SystemExit(f"exact game required, got {sorted(by)}")
    ps=sorted(by[a.game],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]
    total,folds=_run_loto_cached(traces,a.mode)
    if total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0:
        verdict="ZERO_FALSE_LOTO_SIGNAL"
    elif total.get("pixel_gain",0)>0:
        verdict="LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="NO_SIGNAL"
    out={
      "schema":"deus/arc3-r314-residual4-mode-shard/1",
      "rung":RUNG,"game":a.game,"mode":a.mode,
      "lineage":{"r302":"semantic-identical single-mode shard; row-world/key cache execution repair only","representation_repair":"row_world_key_cache_v2"},
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r314":False},
      "loto":total,"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"runtime_shard_only":True,"p5_p9_read":False,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r314":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"mode":a.mode,"verdict":verdict,"loto":total},sort_keys=True))
if __name__=="__main__": main()
