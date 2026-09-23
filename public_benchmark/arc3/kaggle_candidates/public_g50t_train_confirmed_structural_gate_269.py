#!/usr/bin/env python3
"""R269: g50t train-confirmed structural reliability gate.

R268 found a promising but unsafe structural phase signal: 55/63 correct on
frozen p10-p19 (87.3%) but 8 wrong, so it cannot promote under the zero-wrong
policy. R269 removes R268's validation-only key admission.

For each action/mode:
  - p0-p4 fits the action-modal delta and admits structural keys only when they
    independently support that target with zero contradiction across >=N traces.
  - p5-p9 may select a mode only by testing those already-admitted p0-p4 keys;
    it may not add new keys.
  - p0-p9 refits outcomes only for the frozen p0-p4 key whitelist.
  - p10-p19 is a frozen reused public-development gate.

No game source, hidden state, Kaggle execution/score, leaderboard data or
competition submission is read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_g50t_structural_phase_gate_268 as r268

RUNG=269
# R269_RETRY1_MARKER: repaired R268 substrate synced.
SUPPORTS=(2,3,4)


def key_stats(rows, action, mode):
    obs=defaultdict(Counter)
    traces=defaultdict(lambda:defaultdict(set))
    for r in rows:
        if r["action"]!=action or r["changed"]==0:
            continue
        k=r268.stable(r268.structural(r["board"],mode))
        sig=r["delta_sig"]
        obs[k][sig]+=1
        traces[k][sig].add(r["trace"])
    return obs,traces


def admitted_train_keys(train,action,mode,target,min_support):
    obs,traces=key_stats(train,action,mode)
    good=set()
    detail={}
    for k,c in obs.items():
        correct=int(c.get(target,0))
        wrong=sum(int(v) for sig,v in c.items() if sig!=target)
        support=len(traces[k].get(target,set()))
        detail[k]={"correct":correct,"wrong":wrong,"target_trace_support":support,"outcome_count":len(c)}
        if correct>0 and wrong==0 and support>=min_support:
            good.add(k)
    return good,detail


def validate_whitelist(rows,action,mode,target,keys):
    s=Counter()
    per_key=defaultdict(Counter)
    for r in rows:
        if r["action"]!=action or r["changed"]==0:
            continue
        k=r268.stable(r268.structural(r["board"],mode))
        if k not in keys:
            s["abstain"]+=1
            continue
        s["predictions"]+=1
        ok=(r["delta_sig"]==target)
        s["correct" if ok else "wrong"]+=1
        per_key[k]["correct" if ok else "wrong"]+=1
    return {**dict(s),"per_key":{k:dict(v) for k,v in per_key.items()}}


def select(train,val):
    action_model=r268.fit_action_modal(train)
    selected={}
    diag={}
    actions=sorted(set(r["action"] for r in train+val))
    for action in actions:
        target=action_model.get(action)
        candidates={}
        if target is None:
            diag[action]=candidates
            continue
        for mode in r268.FEATURE_MODES:
            for support in SUPPORTS:
                keys,train_detail=admitted_train_keys(train,action,mode,target,support)
                met=validate_whitelist(val,action,mode,target,keys)
                name=f"{mode}_s{support}"
                candidates[name]={
                    "mode":mode,
                    "support":support,
                    "target_delta":target,
                    "train_admitted_keys":sorted(keys),
                    "train_admitted_key_count":len(keys),
                    "train_detail":train_detail,
                    "validation":met,
                }
        viable=[
            name for name,v in candidates.items()
            if v["validation"].get("correct",0)>0
            and v["validation"].get("wrong",0)==0
        ]
        if viable:
            viable.sort(key=lambda name:(
                -candidates[name]["validation"].get("correct",0),
                -candidates[name]["validation"].get("predictions",0),
                -candidates[name]["support"],
                candidates[name]["train_admitted_key_count"],
                name,
            ))
            selected[action]=viable[0]
        diag[action]=candidates
    return action_model,selected,diag


def refit(rows,selected,diag):
    out={}
    for action,name in selected.items():
        spec=diag[action][name]
        mode=spec["mode"]
        whitelist=set(spec["train_admitted_keys"])
        obs=defaultdict(Counter)
        traces=defaultdict(lambda:defaultdict(set))
        for r in rows:
            if r["action"]!=action or r["changed"]==0:
                continue
            k=r268.stable(r268.structural(r["board"],mode))
            if k not in whitelist:
                continue
            obs[k][r["delta_sig"]]+=1
            traces[k][r["delta_sig"]].add(r["trace"])
        mapping={}
        for k,c in obs.items():
            if len(c)!=1:
                continue
            sig=next(iter(c))
            # Keep at least the train support selected; p5-p9 can confirm but
            # never introduces a new structural key.
            if len(traces[k][sig])>=spec["support"]:
                mapping[k]=sig
        out[action]={
            "mode":mode,
            "support":spec["support"],
            "whitelist":sorted(whitelist),
            "mapping":mapping,
        }
    return out


def evaluate(rows,model):
    s=Counter(); by=defaultdict(Counter); examples=[]
    for r in rows:
        if r["changed"]==0:
            s["identity_skipped"]+=1
            continue
        s["nonidentity"]+=1
        by[r["action"]]["nonidentity"]+=1
        pack=model.get(r["action"])
        if not pack:
            s["abstain"]+=1; by[r["action"]]["abstain"]+=1
            continue
        k=r268.stable(r268.structural(r["board"],pack["mode"]))
        pred=pack["mapping"].get(k)
        if pred is None:
            s["abstain"]+=1; by[r["action"]]["abstain"]+=1
            continue
        s["predictions"]+=1; by[r["action"]]["predictions"]+=1
        ok=(pred==r["delta_sig"])
        s["correct" if ok else "wrong"]+=1
        by[r["action"]]["correct" if ok else "wrong"]+=1
        if len(examples)<30:
            examples.append({"trace":r["trace"],"action":r["action"],"mode":pack["mode"],"support":pack["support"],"correct":ok})
    n=s["predictions"]; opp=s["nonidentity"]
    return {
        **dict(s),
        "accuracy":round(s["correct"]/n,6) if n else None,
        "coverage":round(n/opp,6) if opp else 0.0,
        "correct_coverage":round(s["correct"]/opp,6) if opp else 0.0,
        "by_action":{a:dict(v) for a,v in sorted(by.items())},
        "examples":examples,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(20)):
        raise ValueError("exact p0..p19 required")
    parts=[r268.extract([p]) for p in ps]
    tr=[r for x in parts[:5] for r in x]
    va=[r for x in parts[5:10] for r in x]
    fit=[r for x in parts[:10] for r in x]
    ho=[r for x in parts[10:] for r in x]
    action_model,selected,diag=select(tr,va)
    model=refit(fit,selected,diag)
    held=evaluate(ho,model)
    gain=bool(held.get("predictions",0)>0 and held.get("correct",0)>0 and held.get("wrong",0)==0)
    out={
        "schema":"deus/arc3-r269-g50t-train-confirmed-structural-reliability/1",
        "rung":RUNG,
        "lineage":{
            "r262":"coarse descriptor replacement no promotion",
            "r268":"structural gate 55/63 correct but 8 wrong on p10-p19",
            "repair":"admit structural keys on p0-p4 only; p5-p9 confirms mode but cannot add keys",
        },
        "protocol":{
            "train":"p0-p4 action-modal + zero-contradiction structural key admission",
            "select":"p5-p9 frozen-key zero-wrong mode selection",
            "refit":"p0-p9 outcome refit restricted to p0-p4 key whitelist",
            "frozen_eval":"p10-p19",
        },
        "action_model":action_model,
        "selected_by_action":selected,
        "selection_diagnostic":diag,
        "refit_summary":{a:{"mode":x["mode"],"support":x["support"],"whitelist_count":len(x["whitelist"]),"mapping_count":len(x["mapping"])} for a,x in model.items()},
        "heldout":held,
        "non_dominated_source_side_gain":gain,
        "promotion":{"integration_candidate":gain,"solver_promotion":False,"kaggle_packaging":False},
        "truth":{
            "public_trace_only":True,
            "game_source_read":False,
            "selection_uses_p0_p9_only":True,
            "p10_p19_never_updates_selection_or_model":True,
            "p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
            "independent_generalization_claim":False,
            "kaggle_execution":False,
            "competition_submission":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"selected":selected,"refit":out["refit_summary"],"heldout":held,"gain":gain},sort_keys=True))

if __name__=="__main__":
    main()
