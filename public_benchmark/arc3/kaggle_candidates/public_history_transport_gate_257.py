#!/usr/bin/env python3
"""R257: source-free history-conditioned moving-region transport gate for re86.

R252 falsified local cellular operators. R255 falsified global viewport shifts.
R256 then found that directional transitions have a highly stable 3-cell
foreground transport and that the previous observed change mask tracks the next
change region strongly. R257 turns exactly that falsifier into a conservative
online mechanism: use only *previously observed* transition history to localize
the moving region, transport that region under an action-conditioned shift, and
leave the rest of the screen fixed.

Selection protocol:
  p0-p4: fit action shift from observed history/change masks
  p5-p9: select per-action variant only if it adds >0 full-frame predictions
         with ZERO wrong beyond exact visible-state/action lookup
  p0-p9: refit selected action shifts
  p10-p19: frozen reused public-development evaluation; no model update

This is public offline development evidence, not independent generalization and
not a Kaggle score/submission.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG=257
RADIUS=4
CONDITIONS=("same","same_run3","same_run4","same_nonedge","any","any_nonedge")
MODES=("shiftmask","union")
VARIANTS=tuple(f"{m}:{c}" for m in MODES for c in CONDITIONS)

def delta_mask(before,after):
    return {(r,c) for r,row in enumerate(before) for c,v in enumerate(row) if int(v)!=int(after[r][c])}

def shift_mask(mask,dr,dc,h,w):
    return {(r+dr,c+dc) for r,c in mask if 0<=r+dr<h and 0<=c+dc<w}

def iou(a,b):
    if not a and not b: return 1.0
    u=len(a|b); return len(a&b)/u if u else 0.0

def touches_edge(mask,h,w):
    return any(r in (0,h-1) or c in (0,w-1) for r,c in mask)

def prepare_trace(path:Path)->list[dict[str,Any]]:
    ev=r246.load_events(path); pre=ev[0]; out=[]
    prev_mask=None; prev_action="START"; runlen=0; step=0
    for e in ev[1:]:
        if e.get("type")!="action": pre=e; continue
        b=[[int(v) for v in row] for row in pre["board"]]
        a=[[int(v) for v in row] for row in e["board"]]
        action=r246.action_name(e)
        runlen=runlen+1 if action==prev_action else 1
        if len(b)==len(a) and len(b[0])==len(a[0]):
            out.append({
                "trace":path.name,"step":step,"action":action,"prev_action":prev_action,
                "action_run_length":runlen,"before":b,"after":a,
                "before_digest":r246.digest(b),"after_digest":r246.digest(a),
                "exact_key":r246.digest({"b":b,"a":action}),
                "prev_mask":None if prev_mask is None else set(prev_mask),
                "current_mask":delta_mask(b,a),
            })
            prev_mask=delta_mask(b,a)
        prev_action=action; pre=e; step+=1
    return out

def prepare(paths): return [prepare_trace(p) for p in sorted(paths,key=r246.pnum)]

def best_track_shift(row):
    pm=row["prev_mask"]; cm=row["current_mask"]
    if not pm or not cm: return None
    h=len(row["before"]); w=len(row["before"][0]); best=None
    for dr in range(-RADIUS,RADIUS+1):
        for dc in range(-RADIUS,RADIUS+1):
            if dr==0 and dc==0: continue
            s=iou(shift_mask(pm,dr,dc,h,w),cm)
            key=(s,-abs(dr)-abs(dc),-abs(dr),-abs(dc),-dr,-dc)
            if best is None or key>best[0]: best=(key,(dr,dc))
    return best[1]

def fit_shifts(rows):
    obs=defaultdict(Counter)
    for r in rows:
        s=best_track_shift(r)
        if s is not None: obs[r["action"]][s]+=1
    return {a:c.most_common(1)[0][0] for a,c in obs.items() if c}

def condition_ok(row,cond,predmask):
    b=row["before"]; h=len(b); w=len(b[0])
    if cond.startswith("same") and row["action"]!=row["prev_action"]: return False
    if cond=="same_run3" and row["action_run_length"]<3: return False
    if cond=="same_run4" and row["action_run_length"]<4: return False
    if cond.endswith("nonedge") and touches_edge(predmask,h,w): return False
    return True

def predict(row,shift,variant):
    pm=row["prev_mask"]
    if not pm: return None
    dr,dc=shift; b=row["before"]; h=len(b); w=len(b[0]); bg=r246.bg(b)
    predmask=shift_mask(pm,dr,dc,h,w)
    mode,cond=variant.split(":",1)
    if not predmask or not condition_ok(row,cond,predmask): return None
    target=set(predmask) if mode=="shiftmask" else (set(pm)|set(predmask))
    out=[list(map(int,rowx)) for rowx in b]
    for r,c in target:
        sr=r-dr; sc=c-dc
        out[r][c]=int(b[sr][sc]) if 0<=sr<h and 0<=sc<w else int(bg)
    return out

def fit_exact(rows): return r251.fit_exact(rows)

def evaluate(rows,exact,shifts,variant_by_action):
    s=Counter(); bya=defaultdict(Counter); examples=[]
    for r in rows:
        s["transitions"]+=1
        if r["exact_key"] in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        var=variant_by_action.get(r["action"]); sh=shifts.get(r["action"])
        if var is None or sh is None:
            s["candidate_abstain"]+=1; continue
        p=predict(r,sh,var)
        if p is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1; bya[r["action"]]["predictions"]+=1
        ok=p==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        bya[r["action"]]["correct" if ok else "wrong"]+=1
        if len(examples)<30:
            examples.append({"trace":r["trace"],"step":r["step"],"action":r["action"],"prev_action":r["prev_action"],"variant":var,"shift":list(sh),"correct":ok})
    p=s["candidate_predictions"]; opp=s["baseline_abstain"]
    return {**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None,
            "coverage_of_baseline_abstain":round(p/opp,6) if opp else 0.0,
            "by_action":{a:dict(v) for a,v in bya.items()},"examples":examples}

def select(train,val):
    exact=fit_exact(train); shifts=fit_shifts(train); selected={}; diag={}
    actions=sorted(set(r["action"] for r in train+val))
    for a in actions:
        vr=[r for r in val if r["action"]==a]; cand={}
        for v in VARIANTS:
            met=evaluate(vr,exact,shifts,{a:v})
            cand[v]=met
        zero=[v for v in VARIANTS if cand[v].get("candidate_predictions",0)>0 and cand[v].get("candidate_wrong",0)==0]
        if zero:
            zero.sort(key=lambda v:(-cand[v].get("candidate_correct",0),-cand[v].get("candidate_predictions",0),VARIANTS.index(v)))
            selected[a]=zero[0]
        diag[a]=cand
    return selected,shifts,diag

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f"exact p0..p19 required, got {nums}")
    parts=prepare(ps)
    tr=[r for part in parts[:5] for r in part]; va=[r for part in parts[5:10] for r in part]
    fit=[r for part in parts[:10] for r in part]; ho=[r for part in parts[10:] for r in part]
    selected,train_shifts,diag=select(tr,va)
    refit_shifts=fit_shifts(fit); exact_fit=fit_exact(fit)
    held=evaluate(ho,exact_fit,refit_shifts,selected)
    p=held.get("candidate_predictions",0); c=held.get("candidate_correct",0); w=held.get("candidate_wrong",0)
    nondom=bool(p>0 and c>0 and w==0)
    out={
      "schema":"deus/arc3-r257-history-transport-gate/1","rung":RUNG,
      "lineage":{"r252":"NO_PROMOTION local-cell","r255":"NO_PROMOTION global-shift","r256":"DYNAMIC_COMPONENT_SUPPORTED run35799485185 artifact10725471302"},
      "protocol":{"select":"p0-p4 fit shifts / p5-p9 per-action zero-wrong variant selection","refit":"p0-p9 shifts","frozen_eval":"p10-p19 reused public development","history":"previous observed transition delta mask only","exact_baseline_precedence":True,"variants":list(VARIANTS)},
      "train_shifts":{k:list(v) for k,v in train_shifts.items()},"selected_by_action":selected,
      "selection_diagnostic":diag,"refit_shifts":{k:list(v) for k,v in refit_shifts.items()},"heldout":held,
      "non_dominated_source_side_gain":nondom,
      "promotion":{"integration_candidate":nondom,"solver_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"game_source_read":False,"selection_uses_p0_p9_only":True,"p10_p19_never_updates_selection_or_model":True,"p10_p19_status":"PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT","independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent":False,"owner_score_claim":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"train_shifts":out["train_shifts"],"selected_by_action":selected,"refit_shifts":out["refit_shifts"],"heldout":held,"non_dominated_source_side_gain":nondom},sort_keys=True))
if __name__=="__main__": main()
