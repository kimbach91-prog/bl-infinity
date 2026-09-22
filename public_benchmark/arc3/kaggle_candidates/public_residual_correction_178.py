#!/usr/bin/env python3
"""R178: prior-only residual correction sweep over the R175 base renderer.

The R175/R177 renderer is often exact or within only a few cells. Instead of
rebuilding the whole frame again, R178 learns a second-stage correction cache
from PRIOR prediction residuals. Each family predicts KEEP vs SET(value) for a
base-rendered cell using only pre-action features.

Families progress from simple screen-coordinate residuals to local morphology,
connected-component morphology, and temporal variants. Current outcomes are
used only after prediction for scoring and cache updates.

Public source-assisted replay only; no independent-generalization or Kaggle
score/submission claim.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175

RUNG=178
SUPPORTS=(1,2,3)
FAMILIES=("coord","coord_prev","coord_phase2","coord_phase3","local","local_prev","component","component_prev")
MIN_PRIOR_FRAME_OK=2
Grid=list[list[int]]

def run_bucket(n:int)->int:
    return 0 if n<=0 else 1 if n==1 else 2 if n==2 else 3

def label_for(pred:int,actual:int)->str:
    return "KEEP" if pred==actual else f"SET:{actual}"

def apply_label(pred:int,lab:str|None)->int:
    if lab is None or lab=="KEEP": return pred
    if lab.startswith("SET:"): return int(lab.split(":",1)[1])
    return pred

def uniq(c:Counter[str],support:int)->str|None:
    if len(c)!=1:return None
    k,n=next(iter(c.items()))
    return k if n>=support else None

def fkey(fam:str,action:str,before:Grid,pred:Grid,r:int,c:int,shift,comps_before,comps_pred,prev_action:str,action_index:int,prior_same_run:int):
    h,w=len(before),len(before[0]); dr,dc=shift; sr,sc=r-dr,c-dc
    world=before[sr][sc] if 0<=sr<h and 0<=sc<w else -1
    core=(action,pred[r][c],before[r][c],world)
    if fam=="coord": return core+(r,c)
    if fam=="coord_prev": return core+(r,c,prev_action,run_bucket(prior_same_run))
    if fam=="coord_phase2": return core+(r,c,action_index%2)
    if fam=="coord_phase3": return core+(r,c,action_index%3)
    if fam=="local":
        return core+(r175.local_eq_signature(before,r,c),r175.local_eq_signature(pred,r,c),r175.band(r,h),r175.band(c,w))
    if fam=="local_prev":
        return core+(r175.local_eq_signature(before,r,c),r175.local_eq_signature(pred,r,c),prev_action,run_bucket(prior_same_run),r175.band(r,h),r175.band(c,w))
    if fam=="component":
        return core+(comps_before[(r,c)],comps_pred[(r,c)],r175.band(r,h),r175.band(c,w))
    if fam=="component_prev":
        return core+(comps_before[(r,c)],comps_pred[(r,c)],prev_action,run_bucket(prior_same_run),r175.band(r,h),r175.band(c,w))
    raise ValueError(fam)

def names():
    return [f"{f}_s{s}" for f in FAMILIES for s in SUPPORTS]

def correct_frame(before:Grid,base_pred:Grid,action:str,shift,name:str,caches,prev_action,action_index,prior_same_run)->Grid:
    fam,s=name.rsplit("_s",1); support=int(s)
    out=[row[:] for row in base_pred]
    cb=r175.component_descriptors(before)
    cp=r175.component_descriptors(base_pred)
    for r in range(len(before)):
      for c in range(len(before[0])):
        key=fkey(fam,action,before,base_pred,r,c,shift,cb,cp,prev_action,action_index,prior_same_run)
        out[r][c]=apply_label(base_pred[r][c],uniq(caches[fam][key],support))
    return out

def learn_caches(before:Grid,base_pred:Grid,after:Grid,action:str,shift,caches,prev_action,action_index,prior_same_run):
    cb=r175.component_descriptors(before); cp=r175.component_descriptors(base_pred)
    for r in range(len(before)):
      for c in range(len(before[0])):
        lab=label_for(base_pred[r][c],after[r][c])
        for fam in FAMILIES:
          key=fkey(fam,action,before,base_pred,r,c,shift,cb,cp,prev_action,action_index,prior_same_run)
          caches[fam][key][lab]+=1

def audit_trace(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    caches={f:defaultdict(Counter) for f in FAMILIES}
    shadow=defaultdict(Counter); stats=defaultdict(Counter)
    base_stats=Counter()
    pre=events[0]; prev_action="START"; prior_same_run=0; action_index=0

    for e in events[1:]:
      if e.get("type")!="action": pre=e; continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
      run_before=prior_same_run if action==prev_action else 0
      ek=r160.context_exact(before,action); prog=r175.exact_prog(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog is not None else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None

      base_pred=None
      if pred_exact is None and sh is not None:
        comps=r175.component_descriptors(before)
        base_pred=r175.render_candidate(before,sh,action,"patch_recent1_s2",recent_masks,base_labels,comps)
        berr=r175.score_frame(base_pred,after)
        base_stats["raw"]+=1; base_stats["raw_correct" if berr==0 else "raw_wrong"]+=1
        base_stats["cell_errors"]+=berr
        if berr<=4:base_stats["near4"]+=1
        if berr<=16:base_stats["near16"]+=1

        for name in names():
          pred=correct_frame(before,base_pred,action,sh,name,caches,prev_action,action_index,run_before)
          err=r175.score_frame(pred,after); c=stats[name]
          c["raw"]+=1; c["cell_errors"]+=err
          c["raw_correct" if err==0 else "raw_wrong"]+=1
          if err<=4:c["near4"]+=1
          if err<=16:c["near16"]+=1
          q=shadow[(name,action)]["ok"]>=MIN_PRIOR_FRAME_OK and shadow[(name,action)]["wrong"]==0
          if q:
            c["qualified"]+=1; c["qualified_correct" if err==0 else "qualified_wrong"]+=1
          shadow[(name,action)]["ok" if err==0 else "wrong"]+=1

      # Post-outcome learning.
      exact[ek][r160.program(before,after)]+=1
      if action in r172.CAMERA_ACTIONS:
        changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
        if changed:
          b=r167.best_nonzero_shift(before,after)
          if float(b["valid_match_fraction"])>=r172.MIN_TRANSITION_FIT:
            obs=(int(b["dr"]),int(b["dc"])); shifts[action][obs]+=1
            comps=r175.component_descriptors(before)
            r175.learn_morph(before,after,obs,action,base_labels,comps)
            recent_masks[action].append(r175.fixed_mask_from_transition(before,after,obs))
            if len(recent_masks[action])>3: recent_masks[action]=recent_masks[action][-3:]
            if base_pred is not None and obs==sh:
              learn_caches(before,base_pred,after,action,obs,caches,prev_action,action_index,run_before)

      if action==prev_action: prior_same_run=run_before+1
      else: prior_same_run=1
      prev_action=action; action_index+=1

    def pack(c):
      d={k:int(c[k]) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      return d
    return {"base":pack(base_stats),"candidates":{n:pack(stats[n]) for n in names()}}

def run(paths):
    parts=[audit_trace(base.load_events(p)) for p in paths]; agg={}
    for n in names():
      d={k:sum(p["candidates"][n][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["per_trace_raw_correct"]=[p["candidates"][n]["raw_correct"] for p in parts]
      d["per_trace_raw_wrong"]=[p["candidates"][n]["raw_wrong"] for p in parts]
      d["per_trace_qualified_correct"]=[p["candidates"][n]["qualified_correct"] for p in parts]
      d["per_trace_qualified_wrong"]=[p["candidates"][n]["qualified_wrong"] for p in parts]
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      d["strict_p0_p10_gain"]=bool(len(parts)>=2 and d["qualified_wrong"]==0 and d["per_trace_qualified_correct"][0]>0 and d["per_trace_qualified_correct"][1]>0)
      agg[n]=d
    baseagg={k:sum(p["base"][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors")}
    baseagg["raw_accuracy"]=round(baseagg["raw_correct"]/baseagg["raw"],6) if baseagg["raw"] else None
    ranked=sorted(names(),key=lambda n:(-agg[n]["raw_correct"],-agg[n]["near4"],agg[n]["cell_errors"],n))
    strict=[n for n in names() if agg[n]["strict_p0_p10_gain"]]
    best=ranked[0] if ranked else None
    return {
      "schema":"deus/arc3-public-residual-correction/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_SECOND_STAGE_RESIDUAL_CORRECTION_SWEEP",
      "representation_change_from_rung177":{"changed":True,"change":"freeze R175 base renderer and learn prior-only KEEP/SET residual corrections via coordinate, morphology, component and temporal caches"},
      "aggregate":{"base_patch_recent1_s2":baseagg,"candidates":agg,"ranking":ranked,"best_diagnostic_candidate":best,"strict_p0_p10_candidates":strict,"per_trace":parts},
      "diagnostic_gate":"ZERO_ERROR_P0_P10_RESIDUAL_CORRECTION_GAIN" if strict else "NO_STRICT_PREQUENTIAL_RESIDUAL_CORRECTION_GAIN",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"second_stage_base_renderer_frozen":True,"independent_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
