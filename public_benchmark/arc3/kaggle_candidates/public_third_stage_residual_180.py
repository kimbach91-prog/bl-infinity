#!/usr/bin/env python3
"""R180: third-stage prior-only residual/dynamic correction cascade.

Pipeline:
  Stage0 exact-state Markov fallback.
  Stage1 R175 patch_recent1_s2 world-overlay renderer.
  Stage2 R178 local_s1 residual correction.
  Stage3 (this rung) learns a NEW residual cache over Stage2 predictions,
         sweeping local/component/coordinate-temporal families.

All stage caches learn only after the current prediction is scored. This is a
public source-assisted prequential diagnostic, not independent generalization
and not a Kaggle score/submission.
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

RUNG=180
FAMILIES=("local","local_prev","component","component_prev","coord","coord_prev","coord_phase2","coord_phase3")
SUPPORTS=(1,2)
MIN_PRIOR_FRAME_OK=2

def names():
    return [f"{f}_s{s}" for f in FAMILIES for s in SUPPORTS]

def audit_trace(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    stage2_cache={f:defaultdict(Counter) for f in r178.FAMILIES}
    stage3_cache={f:defaultdict(Counter) for f in r178.FAMILIES}
    shadow=defaultdict(Counter); stats=defaultdict(Counter)
    s1stats=Counter(); s2stats=Counter()
    pre=events[0]; prev_action="START"; prior_same_run=0; action_index=0

    for e in events[1:]:
      if e.get("type")!="action": pre=e; continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
      run_before=prior_same_run if action==prev_action else 0
      ek=r160.context_exact(before,action); prog=r175.exact_prog(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog is not None else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None

      stage1=None; stage2=None
      if pred_exact is None and sh is not None:
        comps=r175.component_descriptors(before)
        stage1=r175.render_candidate(before,sh,action,"patch_recent1_s2",recent_masks,base_labels,comps)
        e1=r175.score_frame(stage1,after); s1stats["raw"]+=1; s1stats["raw_correct" if e1==0 else "raw_wrong"]+=1; s1stats["cell_errors"]+=e1
        if e1<=4:s1stats["near4"]+=1
        if e1<=16:s1stats["near16"]+=1

        stage2=r178.correct_frame(before,stage1,action,sh,"local_s1",stage2_cache,prev_action,action_index,run_before)
        e2=r175.score_frame(stage2,after); s2stats["raw"]+=1; s2stats["raw_correct" if e2==0 else "raw_wrong"]+=1; s2stats["cell_errors"]+=e2
        if e2<=4:s2stats["near4"]+=1
        if e2<=16:s2stats["near16"]+=1

        for name in names():
          pred=r178.correct_frame(before,stage2,action,sh,name,stage3_cache,prev_action,action_index,run_before)
          err=r175.score_frame(pred,after); c=stats[name]
          c["raw"]+=1; c["cell_errors"]+=err
          c["raw_correct" if err==0 else "raw_wrong"]+=1
          if err<=4:c["near4"]+=1
          if err<=16:c["near16"]+=1
          q=shadow[(name,action)]["ok"]>=MIN_PRIOR_FRAME_OK and shadow[(name,action)]["wrong"]==0
          if q:
            c["qualified"]+=1; c["qualified_correct" if err==0 else "qualified_wrong"]+=1
          shadow[(name,action)]["ok" if err==0 else "wrong"]+=1

      # post-outcome learning only
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
            if stage1 is not None and obs==sh:
              r178.learn_caches(before,stage1,after,action,obs,stage2_cache,prev_action,action_index,run_before)
            if stage2 is not None and obs==sh:
              r178.learn_caches(before,stage2,after,action,obs,stage3_cache,prev_action,action_index,run_before)

      if action==prev_action: prior_same_run=run_before+1
      else: prior_same_run=1
      prev_action=action; action_index+=1

    def pack(c):
      d={k:int(c[k]) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      return d
    return {"stage1":pack(s1stats),"stage2":pack(s2stats),"stage3":{n:pack(stats[n]) for n in names()}}

def run(paths):
    parts=[audit_trace(base.load_events(p)) for p in paths]
    def agg_stage(key):
      ks=("raw","raw_correct","raw_wrong","near4","near16","cell_errors")
      d={k:sum(p[key][k] for p in parts) for k in ks}
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      return d
    agg={}
    for n in names():
      d={k:sum(p["stage3"][n][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
      d["per_trace_raw_correct"]=[p["stage3"][n]["raw_correct"] for p in parts]
      d["per_trace_raw_wrong"]=[p["stage3"][n]["raw_wrong"] for p in parts]
      d["per_trace_qualified_correct"]=[p["stage3"][n]["qualified_correct"] for p in parts]
      d["per_trace_qualified_wrong"]=[p["stage3"][n]["qualified_wrong"] for p in parts]
      d["raw_accuracy"]=round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
      d["mean_cell_errors"]=round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
      d["qualified_accuracy"]=round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
      d["strict_p0_p10_gain"]=bool(len(parts)>=2 and d["qualified_wrong"]==0 and d["per_trace_qualified_correct"][0]>0 and d["per_trace_qualified_correct"][1]>0)
      agg[n]=d
    ranked=sorted(names(),key=lambda n:(-agg[n]["raw_correct"],-agg[n]["near4"],agg[n]["cell_errors"],n))
    strict=[n for n in names() if agg[n]["strict_p0_p10_gain"]]
    return {
      "schema":"deus/arc3-public-third-stage-residual/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_THIRD_STAGE_RESIDUAL_CASCADE",
      "representation_change_from_rung179":{"changed":True,"change":"add a third prior-only KEEP/SET residual stage over frozen R178 local_s1 output"},
      "aggregate":{"stage1_patch":agg_stage("stage1"),"stage2_local_s1":agg_stage("stage2"),"stage3_candidates":agg,"ranking":ranked,"best_diagnostic_candidate":ranked[0] if ranked else None,"strict_p0_p10_candidates":strict,"per_trace":parts},
      "diagnostic_gate":"ZERO_ERROR_P0_P10_THIRD_STAGE_GAIN" if strict else "NO_STRICT_PREQUENTIAL_THIRD_STAGE_GAIN",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"stage1_stage2_frozen_architecture":True,"independent_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
