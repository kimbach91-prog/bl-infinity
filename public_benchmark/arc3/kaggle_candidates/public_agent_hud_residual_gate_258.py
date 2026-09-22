#!/usr/bin/env python3
"""R258: source-free agent-transport + fixed-screen/HUD residual gate for re86.

R257 proved that moving-region transport alone is not full-frame exact. R258
keeps the R256/R257 action-conditioned moving-region hypothesis but models the
remaining error as sparse deterministic screen-fixed residuals. Residual rules
are learned only from p0-p4 and selected on p5-p9 with a strict zero-wrong
full-frame gate. p10-p19 is frozen reused public-development evaluation.

No game source, hidden outcome, Kaggle runtime, score, or submission is read.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_history_transport_gate_257 as r257

RUNG=258
MIN_SUPPORT=2
BASE_VARIANTS=("shiftmask:same_run3","shiftmask:same","shiftmask:any")
RESIDUAL_REPS=("abs","abs_prev","abs_run")
SCOPES=("outside_mask","all")
VARIANTS=tuple((b,r,s) for b in BASE_VARIANTS for r in RESIDUAL_REPS for s in SCOPES)

def resid_key(row,r,c,base_val,rep):
    k=[row["action"],int(r),int(c),int(row["before"][r][c]),int(base_val)]
    if rep=="abs_prev": k.append(row["prev_action"])
    elif rep=="abs_run": k.append(min(int(row["action_run_length"]),4))
    elif rep!="abs": raise KeyError(rep)
    return r246.stable(k)

def base_prediction(row,shift,base_variant):
    pm=row["prev_mask"]
    if not pm: return None,set()
    dr,dc=shift; b=row["before"]; h=len(b); w=len(b[0])
    predmask=r257.shift_mask(pm,dr,dc,h,w)
    if not predmask or not r257.condition_ok(row,base_variant.split(":",1)[1],predmask): return None,predmask
    p=r257.predict(row,shift,base_variant)
    return p,predmask

def fit_residual(rows,shift,base_variant,rep,scope):
    obs=defaultdict(Counter); support=defaultdict(set)
    for row in rows:
        p,mask=base_prediction(row,shift,base_variant)
        if p is None: continue
        h=len(p); w=len(p[0]); tid=(row["trace"],row["step"])
        for rr in range(h):
            for cc in range(w):
                if scope=="outside_mask" and (rr,cc) in mask: continue
                if int(p[rr][cc])==int(row["after"][rr][cc]): continue
                k=resid_key(row,rr,cc,p[rr][cc],rep)
                obs[k][int(row["after"][rr][cc])]+=1; support[k].add(tid)
    rules={}
    for k,c in obs.items():
        if len(c)==1 and len(support[k])>=MIN_SUPPORT:
            rules[k]=int(next(iter(c)))
    return rules

def apply(row,shift,variant,rules):
    base_variant,rep,scope=variant
    p,mask=base_prediction(row,shift,base_variant)
    if p is None: return None
    h=len(p); w=len(p[0]); out=[list(x) for x in p]
    for rr in range(h):
        for cc in range(w):
            if scope=="outside_mask" and (rr,cc) in mask: continue
            k=resid_key(row,rr,cc,p[rr][cc],rep)
            if k in rules: out[rr][cc]=rules[k]
    return out

def eval_rows(rows,exact,shifts,chosen,rules_by_action):
    s=Counter(); bya=defaultdict(Counter); ex=[]
    for row in rows:
        s["transitions"]+=1
        if row["exact_key"] in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        v=chosen.get(row["action"]); sh=shifts.get(row["action"])
        if v is None or sh is None:
            s["candidate_abstain"]+=1; continue
        p=apply(row,sh,v,rules_by_action.get(row["action"],{}))
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1; bya[row["action"]]["predictions"]+=1
        ok=p==row["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        bya[row["action"]]["correct" if ok else "wrong"]+=1
        if len(ex)<30: ex.append({"trace":row["trace"],"step":row["step"],"action":row["action"],"variant":list(v),"correct":ok})
    p=s["candidate_predictions"]; opp=s["baseline_abstain"]
    return {**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None,
            "coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
            "by_action":{a:dict(v) for a,v in bya.items()},"examples":ex}

def select(train,val):
    shifts=r257.fit_shifts(train); exact=r251.fit_exact(train)
    selected={}; diag={}
    for action in sorted(set(r["action"] for r in train+val)):
        tr=[r for r in train if r["action"]==action]; va=[r for r in val if r["action"]==action]
        cand={}
        sh=shifts.get(action)
        if sh is None:
            diag[action]=cand; continue
        for v in VARIANTS:
            rules=fit_residual(tr,sh,*v)
            met=eval_rows(va,exact,{action:sh},{action:v},{action:rules})
            cand["|".join(v)]={"rule_count":len(rules),"validation":met}
        zero=[]
        for v in VARIANTS:
            m=cand["|".join(v)]["validation"]
            if m.get("candidate_predictions",0)>0 and m.get("candidate_wrong",0)==0:
                zero.append(v)
        if zero:
            zero.sort(key=lambda v:(-cand["|".join(v)]["validation"].get("candidate_correct",0),
                                    -cand["|".join(v)]["validation"].get("candidate_predictions",0),
                                    cand["|".join(v)]["rule_count"],VARIANTS.index(v)))
            selected[action]=zero[0]
        diag[action]=cand
    return selected,shifts,diag

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f"exact p0..p19 required, got {nums}")
    parts=r257.prepare(ps)
    tr=[r for p in parts[:5] for r in p]; va=[r for p in parts[5:10] for r in p]
    fit=[r for p in parts[:10] for r in p]; ho=[r for p in parts[10:] for r in p]
    selected,train_shifts,diag=select(tr,va)
    refit_shifts=r257.fit_shifts(fit); exact_fit=r251.fit_exact(fit); rules={}
    for action,v in selected.items():
        rows=[r for r in fit if r["action"]==action]
        rules[action]=fit_residual(rows,refit_shifts[action],*v)
    held=eval_rows(ho,exact_fit,refit_shifts,selected,rules)
    p=held.get("candidate_predictions",0); c=held.get("candidate_correct",0); w=held.get("candidate_wrong",0)
    nondom=bool(p>0 and c>0 and w==0)
    out={"schema":"deus/arc3-r258-agent-hud-residual-gate/1","rung":RUNG,
      "lineage":{"r256":"DYNAMIC_COMPONENT_SUPPORTED run35799485185/artifact10725471302","r257":"NO_PROMOTION run35799698285/artifact10725381903","repair":"agent transport plus deterministic fixed-screen/HUD residual; no threshold retry"},
      "protocol":{"select":"p0-p4 fit / p5-p9 per-action zero-wrong full-frame selection","refit":"p0-p9","frozen_eval":"p10-p19 reused public development","exact_baseline_precedence":True,"variants":[list(v) for v in VARIANTS]},
      "train_shifts":{k:list(v) for k,v in train_shifts.items()},"selected_by_action":{k:list(v) for k,v in selected.items()},
      "selection_diagnostic":diag,"refit_shifts":{k:list(v) for k,v in refit_shifts.items()},"refit_rule_counts":{k:len(v) for k,v in rules.items()},
      "heldout":held,"non_dominated_source_side_gain":nondom,
      "promotion":{"integration_candidate":nondom,"solver_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,"p10_p19_never_updates_selection_or_model":True,"p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT","independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent":False,"owner_score_claim":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"selected_by_action":out["selected_by_action"],"refit_rule_counts":out["refit_rule_counts"],"heldout":held,"non_dominated_source_side_gain":nondom},sort_keys=True))
if __name__=="__main__": main()
