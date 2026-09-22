#!/usr/bin/env python3
"""R179: p11-calibrated confidence gate for the R178 local_s1 residual renderer.

R178 raised raw exact full-frame prediction to 123/197. R179 freezes that
renderer and asks whether prior-only risk signals can select a nonempty safe
subset. Gate parameters are selected on p11 only and frozen before p0/p10
evaluation.

Signals available before the current outcome:
- consecutive exact streak for this action,
- residual-cache coverage,
- fraction of known cache labels that request SET rather than KEEP,
- recent fixed-mask stability (Jaccard).

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
import public_residual_correction_178 as r178

RUNG=179
Grid=list[list[int]]

MIN_STREAK=(0,1,2,3,4,5)
MIN_COVERAGE=(0.0,0.05,0.1,0.2,0.4,0.6,0.8)
MAX_SET_FRAC=(1.0,0.75,0.5,0.25,0.1,0.05)
MIN_JACCARD=(0.0,0.25,0.5,0.75,0.9,0.98)

def jaccard(a:set[tuple[int,int]],b:set[tuple[int,int]])->float:
    if not a and not b:return 1.0
    u=len(a|b); return len(a&b)/u if u else 1.0

def residual_meta(before:Grid,base_pred:Grid,action,shift,caches,prev_action,action_index,prior_same_run,recent_masks):
    cb=r175.component_descriptors(before); cp=r175.component_descriptors(base_pred)
    known=setn=0; total=len(before)*len(before[0])
    for r in range(len(before)):
      for c in range(len(before[0])):
        key=r178.fkey("local",action,before,base_pred,r,c,shift,cb,cp,prev_action,action_index,prior_same_run)
        lab=r178.uniq(caches["local"][key],1)
        if lab is not None:
          known+=1
          if lab!="KEEP": setn+=1
    coverage=known/total if total else 0.0
    setfrac=setn/known if known else 0.0
    jac=jaccard(recent_masks[action][-1],recent_masks[action][-2]) if len(recent_masks[action])>=2 else 0.0
    return {"cache_coverage":coverage,"set_fraction":setfrac,"recent_jaccard":jac}

def collect(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    caches={f:defaultdict(Counter) for f in r178.FAMILIES}
    streak=Counter()
    rows=[]; pre=events[0]; prev_action="START"; prior_same_run=0; action_index=0

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
        m=residual_meta(before,base_pred,action,sh,caches,prev_action,action_index,run_before,recent_masks)
        pred=r178.correct_frame(before,base_pred,action,sh,"local_s1",caches,prev_action,action_index,run_before)
        err=r175.score_frame(pred,after)
        rows.append({"action":action,"correct":err==0,"cell_errors":err,"prior_streak":int(streak[action]),**m})
        streak[action]=streak[action]+1 if err==0 else 0

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
              r178.learn_caches(before,base_pred,after,action,obs,caches,prev_action,action_index,run_before)

      if action==prev_action: prior_same_run=run_before+1
      else: prior_same_run=1
      prev_action=action; action_index+=1
    return rows

def gates():
    for st in MIN_STREAK:
      for cov in MIN_COVERAGE:
       for sf in MAX_SET_FRAC:
        for jac in MIN_JACCARD:
          yield {"min_streak":st,"min_cache_coverage":cov,"max_set_fraction":sf,"min_recent_jaccard":jac}

def pass_gate(g,x):
    return x["prior_streak"]>=g["min_streak"] and x["cache_coverage"]>=g["min_cache_coverage"] and x["set_fraction"]<=g["max_set_fraction"] and x["recent_jaccard"]>=g["min_recent_jaccard"]

def score(rows,g):
    s=[x for x in rows if pass_gate(g,x)]
    c=sum(x["correct"] for x in s); w=len(s)-c
    return {"selected":len(s),"correct":c,"wrong":w,"accuracy":round(c/len(s),6) if s else None}

def choose(cal):
    zs=[]
    for g in gates():
      s=score(cal,g)
      if s["selected"] and s["wrong"]==0:
        # max predictions, then simpler gate: lower required streak/coverage/jaccard, higher allowed set fraction
        zs.append((s["selected"],-g["min_streak"],-g["min_cache_coverage"],g["max_set_fraction"],-g["min_recent_jaccard"],g,s))
    if not zs:return None,None
    zs.sort(reverse=True,key=lambda x:x[:5])
    return zs[0][5],zs[0][6]

def run(cal_path:Path,eval_paths:list[Path]):
    cal=collect(base.load_events(cal_path)); g,cs=choose(cal)
    ev=[]
    if g:
      for p in eval_paths:
        rows=collect(base.load_events(p)); ev.append({"path":p.name,"rows":len(rows),"score":score(rows,g)})
    strict=bool(g and len(ev)>=2 and all(x["score"]["selected"]>0 and x["score"]["wrong"]==0 for x in ev[:2]))
    return {
      "schema":"deus/arc3-public-r178-confidence-gate/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_P11_CALIBRATION_P0P10_FROZEN_R178_GATE",
      "representation_change_from_rung178":{"changed":False,"change":"freeze local_s1 residual renderer; calibrate abstention only"},
      "calibration":{"trace":cal_path.name,"rows":len(cal),"chosen_gate":g,"score":cs},
      "evaluation":ev,
      "diagnostic_gate":"FROZEN_R178_GATE_ZERO_ERROR_NONZERO_P0_P10" if strict else "FROZEN_R178_GATE_FAILS_STRICT_P0_P10",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"gate_selected_on_p11_only":True,"p0_p10_not_used_for_gate_selection":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"r178_renderer_frozen":True,"independent_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--calibration",type=Path,required=True); ap.add_argument("--eval",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    d=run(a.calibration,a.eval); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
