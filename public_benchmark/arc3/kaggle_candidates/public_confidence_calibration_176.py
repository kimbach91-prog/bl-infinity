#!/usr/bin/env python3
"""R176: calibrate an abstaining confidence gate on p11, then evaluate frozen gate on p0+p10.

Purpose: R175's patch_recent1_s2 renderer reached 77/197 raw exact frames but
failed strict zero-error qualification. R176 is the easiest remaining test:
do not change the renderer; only test whether PRIOR-ONLY confidence signals can
identify a safe subset. Hyperparameters are selected on p11 only, then frozen
and evaluated on p0 and p10 without using their outcomes for gate selection.

This remains source-assisted public replay, not independent generalization and
not a Kaggle score/submission.
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

RUNG=176
Grid=list[list[int]]

MIN_PRIOR_OK=(0,1,2,3,4)
MIN_PATCH_COVERAGE=(0.0,0.1,0.2,0.4,0.6,0.8)
MIN_RECENT_JACCARD=(0.0,0.25,0.5,0.75,0.9)
MIN_PATCH_RECENT_AGREEMENT=(0.0,0.5,0.75,0.9,0.98)

def jaccard(a:set[tuple[int,int]],b:set[tuple[int,int]])->float:
    if not a and not b:return 1.0
    u=len(a|b)
    return len(a&b)/u if u else 1.0

def meta_features(before:Grid,shift,action,recent_masks,labels)->dict[str,float]:
    dr,dc=shift; h,w=len(before),len(before[0]); comps=r175.component_descriptors(before)
    eligible=known=agree=known_with_recent=0
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w): continue
        fixed,world=before[r][c],before[sr][sc]
        if fixed==world: continue
        eligible+=1
        key=r175.morph_feature("patch",action,before,r,c,sr,sc,comps)
        lab=r175.unique(labels["patch"][key],2)
        if lab is not None:
          known+=1
          if recent_masks[action]:
            known_with_recent+=1
            recent_lab="fixed" if (r,c) in recent_masks[action][-1] else "world"
            if recent_lab==lab: agree+=1
    cov=known/eligible if eligible else 0.0
    agr=agree/known_with_recent if known_with_recent else 0.0
    sim=jaccard(recent_masks[action][-1],recent_masks[action][-2]) if len(recent_masks[action])>=2 else 0.0
    return {"patch_coverage":cov,"recent_jaccard":sim,"patch_recent_agreement":agr}

def gate_tuple(g):
    return (g["min_prior_ok"],g["min_patch_coverage"],g["min_recent_jaccard"],g["min_patch_recent_agreement"])

def enumerate_gates():
    for ok in MIN_PRIOR_OK:
      for cov in MIN_PATCH_COVERAGE:
       for jac in MIN_RECENT_JACCARD:
        for agr in MIN_PATCH_RECENT_AGREEMENT:
          yield {"min_prior_ok":ok,"min_patch_coverage":cov,"min_recent_jaccard":jac,"min_patch_recent_agreement":agr}

def gate_pass(g,m,prior_ok,prior_wrong):
    return (
      prior_wrong==0 and
      prior_ok>=g["min_prior_ok"] and
      m["patch_coverage"]>=g["min_patch_coverage"] and
      m["recent_jaccard"]>=g["min_recent_jaccard"] and
      m["patch_recent_agreement"]>=g["min_patch_recent_agreement"]
    )

def collect(events:list[dict[str,Any]])->list[dict[str,Any]]:
    exact=defaultdict(Counter); shifts=defaultdict(Counter)
    recent_masks=defaultdict(list)
    labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    shadow=defaultdict(Counter)
    rows=[]; pre=events[0]
    for e in events[1:]:
      if e.get("type")!="action": pre=e; continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
      ek=r160.context_exact(before,action); prog=r175.exact_prog(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog is not None else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
      if pred_exact is None and sh is not None:
        comps=r175.component_descriptors(before)
        pred=r175.render_candidate(before,sh,action,"patch_recent1_s2",recent_masks,labels,comps)
        err=r175.score_frame(pred,after)
        m=meta_features(before,sh,action,recent_masks,labels)
        rows.append({
          "action":action,
          "correct":err==0,
          "cell_errors":err,
          "prior_ok":int(shadow[action]["ok"]),
          "prior_wrong":int(shadow[action]["wrong"]),
          **m,
        })
        shadow[action]["ok" if err==0 else "wrong"]+=1
      # post-outcome learning only
      exact[ek][r160.program(before,after)]+=1
      if action in r172.CAMERA_ACTIONS:
        changed=sum(before[r][c]!=after[r][c] for r in range(len(before)) for c in range(len(before[0])))
        if changed:
          b=r167.best_nonzero_shift(before,after)
          if float(b["valid_match_fraction"])>=r172.MIN_TRANSITION_FIT:
            obs=(int(b["dr"]),int(b["dc"])); shifts[action][obs]+=1
            comps=r175.component_descriptors(before)
            r175.learn_morph(before,after,obs,action,labels,comps)
            recent_masks[action].append(r175.fixed_mask_from_transition(before,after,obs))
            if len(recent_masks[action])>3: recent_masks[action]=recent_masks[action][-3:]
    return rows

def score_gate(rows,g):
    sel=[x for x in rows if gate_pass(g,x,x["prior_ok"],x["prior_wrong"])]
    cor=sum(x["correct"] for x in sel); wrong=len(sel)-cor
    return {"selected":len(sel),"correct":cor,"wrong":wrong,"accuracy":round(cor/len(sel),6) if sel else None}

def choose_gate(cal_rows):
    scored=[]
    for g in enumerate_gates():
      s=score_gate(cal_rows,g)
      if s["selected"] and s["wrong"]==0:
        # Prefer more zero-error predictions, then simpler/lower thresholds.
        scored.append((s["selected"], -g["min_prior_ok"], -g["min_patch_coverage"], -g["min_recent_jaccard"], -g["min_patch_recent_agreement"], g, s))
    if not scored:return None,None
    scored.sort(reverse=True,key=lambda x:x[:5])
    return scored[0][5],scored[0][6]

def run(cal_path:Path, eval_paths:list[Path]):
    cal_rows=collect(base.load_events(cal_path))
    gate,cal_score=choose_gate(cal_rows)
    eval_parts=[]
    if gate:
      for p in eval_paths:
        rows=collect(base.load_events(p))
        eval_parts.append({"path":p.name,"score":score_gate(rows,gate),"raw_rows":len(rows)})
    strict=bool(
      gate and len(eval_parts)>=2 and
      all(x["score"]["selected"]>0 and x["score"]["wrong"]==0 for x in eval_parts[:2])
    )
    return {
      "schema":"deus/arc3-public-confidence-calibration/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_P11_CALIBRATION_P0P10_FROZEN_GATE_EVAL",
      "representation_change_from_rung175":{"changed":False,"change":"renderer frozen at patch_recent1_s2; calibrate abstention/confidence only"},
      "calibration":{"trace":cal_path.name,"rows":len(cal_rows),"chosen_gate":gate,"score":cal_score},
      "evaluation":eval_parts,
      "diagnostic_gate":"FROZEN_GATE_ZERO_ERROR_NONZERO_P0_P10" if strict else "FROZEN_GATE_FAILS_STRICT_P0_P10",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{
        "public_trace_only":True,"source_assisted_sequence_replay":True,
        "gate_selected_on_p11_only":True,"p0_p10_not_used_for_gate_selection":True,
        "current_prediction_uses_preaction_and_prior_history_only":True,
        "current_outcome_used_only_for_scoring_and_post_prediction_learning":True,
        "independent_generalization_claim":False,"kaggle_execution":False,
        "submission_quota_spent":False,"owner_score_claim":False
      }
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--calibration",type=Path,required=True)
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    d=run(a.calibration,a.eval)
    s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
