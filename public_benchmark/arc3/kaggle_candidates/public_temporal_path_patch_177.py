#!/usr/bin/env python3
"""R177: prior-only temporal/path-context patch renderer sweep.

R175 showed that local patch morphology + the most recent prior fixed mask is
far stronger than static selectors (77/197 exact), while R176 proved confidence
thresholding alone cannot isolate a safe p11 subset. R177 changes representation
with minimal complexity: keep the same world-transport renderer, but condition
the patch fixed-vs-world label on path/temporal context available BEFORE the
current outcome: previous action, same-action run length, and action-step phase.

No current target is used to form the prediction. Public source-assisted replay
only; no independent-generalization or Kaggle-score claim.
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

RUNG=177
SUPPORTS=(1,2)
FAMILIES=("prev","run","phase2","phase3","prev_run","full")
MIN_PRIOR_FRAME_OK=2

def run_bucket(n:int)->int:
    return 0 if n<=0 else 1 if n==1 else 2 if n==2 else 3

def temporal_suffix(fam:str, prev_action:str, prior_same_run:int, action_index:int):
    if fam=="prev": return (prev_action,)
    if fam=="run": return (run_bucket(prior_same_run),)
    if fam=="phase2": return (action_index%2,)
    if fam=="phase3": return (action_index%3,)
    if fam=="prev_run": return (prev_action,run_bucket(prior_same_run))
    if fam=="full": return (prev_action,run_bucket(prior_same_run),action_index%2,action_index%3)
    raise ValueError(fam)

def tfeature(fam,action,before,r,c,sr,sc,comps,prev_action,prior_same_run,action_index):
    return r175.morph_feature("patch",action,before,r,c,sr,sc,comps)+temporal_suffix(fam,prev_action,prior_same_run,action_index)

def render(before,shift,action,name,recent_masks,labels,prev_action,prior_same_run,action_index):
    fam,s=name.rsplit("_s",1); support=int(s)
    dr,dc=shift; h,w=len(before),len(before[0]); out=[x[:] for x in before]
    comps=r175.component_descriptors(before)
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w): continue
        fixed,world=before[r][c],before[sr][sc]
        if fixed==world: out[r][c]=fixed; continue
        key=tfeature(fam,action,before,r,c,sr,sc,comps,prev_action,prior_same_run,action_index)
        lab=r175.unique(labels[fam][key],support)
        if lab is None:
          lab="fixed" if (recent_masks[action] and (r,c) in recent_masks[action][-1]) else "world"
        out[r][c]=fixed if lab=="fixed" else world
    return out

def learn(before,after,shift,action,labels,prev_action,prior_same_run,action_index):
    dr,dc=shift; h,w=len(before),len(before[0]); comps=r175.component_descriptors(before)
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w): continue
        fixed,world,actual=before[r][c],before[sr][sc],after[r][c]
        if fixed==world: continue
        if actual==fixed and actual!=world: lab="fixed"
        elif actual==world and actual!=fixed: lab="world"
        else: continue
        for fam in FAMILIES:
          labels[fam][tfeature(fam,action,before,r,c,sr,sc,comps,prev_action,prior_same_run,action_index)][lab]+=1

def names():
    return [f"{f}_s{s}" for f in FAMILIES for s in SUPPORTS]

def audit_trace(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    labels={f:defaultdict(Counter) for f in FAMILIES}
    shadow=defaultdict(Counter); stats=defaultdict(Counter)
    pre=events[0]; prev_action="START"; prior_same_run=0; action_index=0
    for e in events[1:]:
      if e.get("type")!="action": pre=e; continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
      run_before=prior_same_run if action==prev_action else 0
      ek=r160.context_exact(before,action); prog=r175.exact_prog(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog is not None else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
      if pred_exact is None and sh is not None:
        for name in names():
          pred=render(before,sh,action,name,recent_masks,labels,prev_action,run_before,action_index)
          err=r175.score_frame(pred,after); c=stats[name]
          c["raw"]+=1; c["cell_errors"]+=err
          c["raw_correct" if err==0 else "raw_wrong"]+=1
          if err<=4:c["near4"]+=1
          if err<=16:c["near16"]+=1
          q=shadow[(name,action)]["ok"]>=MIN_PRIOR_FRAME_OK and shadow[(name,action)]["wrong"]==0
          if q:
            c["qualified"]+=1; c["qualified_correct" if err==0 else "qualified_wrong"]+=1
          shadow[(name,action)]["ok" if err==0 else "wrong"]+=1

      exact[ek][r160.program(before,after)]+=1
      if action in r172.CAMERA_ACTIONS:
        changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
        if changed:
          b=r167.best_nonzero_shift(before,after)
          if float(b["valid_match_fraction"])>=r172.MIN_TRANSITION_FIT:
            obs=(int(b["dr"]),int(b["dc"])); shifts[action][obs]+=1
            learn(before,after,obs,action,labels,prev_action,run_before,action_index)
            recent_masks[action].append(r175.fixed_mask_from_transition(before,after,obs))
            if len(recent_masks[action])>3: recent_masks[action]=recent_masks[action][-3:]
      if action==prev_action: prior_same_run=run_before+1
      else: prior_same_run=1
      prev_action=action; action_index+=1

    out={}
    for n in names():
      c=stats[n]; d={k:int(c[k]) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      out[n]=d
    return out

def run(paths):
    parts=[audit_trace(base.load_events(p)) for p in paths]; agg={}
    for n in names():
      d={k:sum(p[n][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["per_trace_raw_correct"]=[p[n]["raw_correct"] for p in parts]
      d["per_trace_raw_wrong"]=[p[n]["raw_wrong"] for p in parts]
      d["per_trace_qualified_correct"]=[p[n]["qualified_correct"] for p in parts]
      d["per_trace_qualified_wrong"]=[p[n]["qualified_wrong"] for p in parts]
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      d["strict_p0_p10_gain"]=bool(len(parts)>=2 and d["qualified_wrong"]==0 and d["per_trace_qualified_correct"][0]>0 and d["per_trace_qualified_correct"][1]>0)
      agg[n]=d
    ranked=sorted(names(),key=lambda n:(-agg[n]["raw_correct"],-agg[n]["near4"],agg[n]["cell_errors"],n))
    strict=[n for n in names() if agg[n]["strict_p0_p10_gain"]]
    return {
      "schema":"deus/arc3-public-temporal-path-patch/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_TEMPORAL_PATH_PATCH_SWEEP",
      "representation_change_from_rung176":{"changed":True,"change":"condition patch fixed-vs-world labels on prior-only previous-action, same-action run and phase context; renderer otherwise unchanged"},
      "aggregate":{"candidates":agg,"ranking":ranked,"best_diagnostic_candidate":ranked[0] if ranked else None,"strict_p0_p10_candidates":strict,"per_trace":parts},
      "diagnostic_gate":"ZERO_ERROR_P0_P10_TEMPORAL_PATH_GAIN" if strict else "NO_STRICT_PREQUENTIAL_TEMPORAL_PATH_GAIN",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"independent_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
