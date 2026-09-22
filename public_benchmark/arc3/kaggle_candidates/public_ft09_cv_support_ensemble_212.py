#!/usr/bin/env python3
"""R212: ft09 CV-selected support ensemble, frozen p10-p19 gate.

R208 gives broad base-key coverage with two heldout errors. R211 gives a
radius-2 relational key with zero heldout errors but lower coverage. R212 does
NOT select policy parameters on p10-p19. It uses leave-one-trace-out CV on
p0-p9 only to select support thresholds and conflict policy, then freezes the
selected policy and evaluates p10-p19 once.

Because the mechanism lineage itself was informed by earlier public-heldout
diagnostics, this remains iterative public research rather than an independent
generalization claim. It is never a full solver or Kaggle promotion by itself.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path

import public_ft09_ring2_relational_gate_211 as r211

RUNG=212
GAME="ft09-0d8bbf25"

def pnum(p:Path)->int:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return int(m.group(1)) if m else -1

def fit(rows,key_name):
    obs=defaultdict(Counter)
    for r in rows:
        if not r["changed"]:
            continue
        key=repr(r[key_name])
        obs[key][r["target"]]+=1
    table={}
    for k,c in obs.items():
        if len(c)==1:
            pred=next(iter(c))
            table[k]={"pred":pred,"support":int(sum(c.values()))}
    return table

def predict(r,base_tab,ring_tab,base_min,ring_min,mode):
    b=base_tab.get(repr(r["base"]))
    q=ring_tab.get(repr((r["base"],r["ring2"])))
    bp=b["pred"] if b and b["support"]>=base_min else None
    qp=q["pred"] if q and q["support"]>=ring_min else None

    if mode=="ring_first":
        return qp if qp is not None else bp
    if mode=="consensus":
        if qp is not None and bp is not None:
            return qp if qp==bp else None
        return qp if qp is not None else bp
    if mode=="ring_only_conflict_abstain":
        if qp is not None:
            if bp is not None and bp!=qp:
                return None
            return qp
        return bp
    raise ValueError(mode)

def eval_rows(rows,base_tab,ring_tab,base_min,ring_min,mode,keep_examples=False):
    s=Counter(); mistakes=[]; correct_examples=[]
    for r in rows:
        s["eligible"]+=1
        pred=predict(r,base_tab,ring_tab,base_min,ring_min,mode)
        if pred is None:
            s["abstain"]+=1
            continue
        s["predictions"]+=1
        if pred==r["target"]:
            s["correct"]+=1
            if keep_examples and len(correct_examples)<12:
                correct_examples.append({
                    "trace":r["trace"],"step":r["step"],"current":r["current"],
                    "target":r["target"],"pred":pred})
        else:
            s["wrong"]+=1
            if len(mistakes)<20:
                mistakes.append({
                    "trace":r["trace"],"step":r["step"],"current":r["current"],
                    "target":r["target"],"pred":pred})
    p=s["predictions"]; e=s["eligible"]
    return {
        **dict(s),
        "accuracy":round(s["correct"]/p,6) if p else None,
        "coverage":round(p/e,6) if e else 0.0,
        "mistakes":mistakes,
        "correct_examples":correct_examples,
    }

def cv_score(trace_rows,base_min,ring_min,mode):
    total=Counter()
    folds=[]
    for hold in range(10):
        train=[r for i in range(10) if i!=hold for r in trace_rows[i]]
        test=trace_rows[hold]
        bt=fit(train,"base"); rt=fit(train,"ring2")
        m=eval_rows(test,bt,rt,base_min,ring_min,mode)
        for k in ("eligible","abstain","predictions","correct","wrong"):
            total[k]+=m.get(k,0)
        folds.append({"holdout_trace":hold,**{k:m.get(k,0) for k in ("predictions","correct","wrong")},"accuracy":m["accuracy"],"coverage":m["coverage"]})
    p=total["predictions"]; e=total["eligible"]
    return {
        **dict(total),
        "accuracy":round(total["correct"]/p,6) if p else None,
        "coverage":round(p/e,6) if e else 0.0,
        "folds":folds,
    }

def selection_key(item):
    cfg,m=item
    # Strict priority: fewer errors, then higher accuracy, then more correct,
    # then more predictions. Parameters are selected solely on p0-p9 CV.
    acc=m["accuracy"] if m["accuracy"] is not None else 0.0
    return (m.get("wrong",0),-acc,-m.get("correct",0),-m.get("predictions",0),cfg)

def run(paths):
    ps=sorted(paths,key=pnum)
    nums=[pnum(x) for x in ps]
    if nums!=list(range(20)):
        raise ValueError(f"exact p0..p19 required; got {nums}")

    trace_rows=[[r for r in r211.rows(p)] for p in ps]
    train_rows=[r for i in range(10) for r in trace_rows[i]]
    held_rows=[r for i in range(10,20) for r in trace_rows[i]]

    candidates={}
    for mode in ("ring_first","consensus","ring_only_conflict_abstain"):
        for base_min in (1,2,3,4,5,6,8):
            for ring_min in (1,2,3,4):
                cfg=f"{mode}|b{base_min}|r{ring_min}"
                candidates[cfg]=cv_score(trace_rows,base_min,ring_min,mode)

    ranking=[cfg for cfg,_ in sorted(candidates.items(),key=selection_key)]
    selected=ranking[0]
    mode,bpart,rpart=selected.split("|")
    base_min=int(bpart[1:]); ring_min=int(rpart[1:])

    base_tab=fit(train_rows,"base"); ring_tab=fit(train_rows,"ring2")
    held=eval_rows(held_rows,base_tab,ring_tab,base_min,ring_min,mode,keep_examples=True)
    cv=candidates[selected]

    # Reference anchors from verified prior rungs, encoded only for comparison.
    dominates_r211=bool(
        held.get("wrong",0)==0
        and held.get("predictions",0)>282
        and (held.get("accuracy") or 0.0)>=1.0
    )
    mechanism_gate=bool(
        cv.get("wrong",0)==0 and cv.get("predictions",0)>=100
        and held.get("wrong",0)==0 and held.get("predictions",0)>=100
    )

    return {
        "schema":"deus/arc3-ft09-cv-support-ensemble/1",
        "rung":RUNG,
        "game":GAME,
        "protocol":{
            "parameter_selection":"leave-one-trace-out CV on p0-p9 only",
            "fit":"final deterministic tables on all p0-p9 after policy freeze",
            "heldout":"single frozen evaluation on p10-p19; no policy/model updates",
            "policy":"ring2 and base deterministic tables with train-support thresholds",
        },
        "candidate_count":len(candidates),
        "selected_policy":{
            "config":selected,"mode":mode,"base_support_min":base_min,
            "ring2_support_min":ring_min,
        },
        "cv_selected":cv,
        "cv_ranking":ranking[:20],
        "heldout":held,
        "reference":{
            "r208":{"predictions":373,"correct":371,"wrong":2,"coverage":0.408096},
            "r211":{"predictions":282,"correct":282,"wrong":0,"coverage":0.308534},
            "dominates_r211_zero_error_anchor":dominates_r211,
        },
        "mechanism_gate_pass":mechanism_gate,
        "promotion":{
            "mechanism_gate":mechanism_gate,
            "solver_promotion":False,
            "kaggle_packaging":False,
            "reason":"target-color mechanism only; lineage is iterative public research and full policy/goal/HUD/reset behavior is unresolved",
        },
        "truth":{
            "public_trace_only":True,
            "policy_parameters_selected_from_p0_p9_cv_only":True,
            "p10_p19_never_select_policy":True,
            "heldout_never_updates_model":True,
            "lineage_previously_informed_by_public_heldout":True,
            "independent_generalization_claim":False,
            "full_frame_solver_claim":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    d=run(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "selected_policy":d["selected_policy"],
        "cv":{k:d["cv_selected"].get(k) for k in ("predictions","correct","wrong","accuracy","coverage")},
        "heldout":{k:d["heldout"].get(k) for k in ("predictions","correct","wrong","accuracy","coverage")},
        "reference":d["reference"],
        "mechanism_gate_pass":d["mechanism_gate_pass"],
    },sort_keys=True))

if __name__=="__main__":
    main()
