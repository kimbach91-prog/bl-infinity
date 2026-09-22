#!/usr/bin/env python3
"""R181: frozen AR25 all-20 trajectory stress for the R180-selected pipeline.

Architecture is frozen before heldout evaluation:
  stage1 = R175 patch_recent1_s2 world-overlay renderer
  stage2 = R178 local_s1 residual correction
  stage3 = R178 component_s1 residual correction over stage2

Each trajectory p0..p19 is evaluated independently with fresh online state.
Selection traces are p0,p10,p11 because those were used to choose the
architecture. The remaining 17 paths are heldout same-game trajectories and
MUST NOT alter architecture or hyperparameters.

All predictions are pre-action/prior-history-only. Current outcomes are used
only for scoring and post-prediction online learning. Public source-assisted
replay only; no independent-generalization or Kaggle-score claim.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175
import public_residual_correction_178 as r178

RUNG=181
SELECTION_PATHS={"p0","p10","p11"}

def path_id(p:Path)->str:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return f"p{m.group(1)}" if m else p.stem

def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact=defaultdict(Counter)
    shifts=defaultdict(Counter)
    recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    stage2_cache={f:defaultdict(Counter) for f in r178.FAMILIES}
    stage3_cache={f:defaultdict(Counter) for f in r178.FAMILIES}

    stats=Counter()
    per_action=defaultdict(Counter)
    pre=events[0]
    prev_action="START"
    prior_same_run=0
    action_index=0

    for e in events[1:]:
        if e.get("type")!="action":
            pre=e
            continue
        before=base.as_grid(pre["board"])
        after=base.as_grid(e["board"])
        action=base.action_name(e)
        pre=e
        if len(before)!=len(after) or len(before[0])!=len(after[0]):
            continue

        run_before=prior_same_run if action==prev_action else 0
        ek=r160.context_exact(before,action)
        prog=r175.exact_prog(exact[ek],1) if ek in exact else None
        pred_exact=r160.apply_program(before,prog) if prog is not None else None
        sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None

        stage1=stage2=None
        if pred_exact is None and sh is not None:
            comps=r175.component_descriptors(before)
            stage1=r175.render_candidate(
                before,sh,action,"patch_recent1_s2",
                recent_masks,base_labels,comps
            )
            stage2=r178.correct_frame(
                before,stage1,action,sh,"local_s1",
                stage2_cache,prev_action,action_index,run_before
            )
            stage3=r178.correct_frame(
                before,stage2,action,sh,"component_s1",
                stage3_cache,prev_action,action_index,run_before
            )
            err=r175.score_frame(stage3,after)
            stats["opportunities"]+=1
            stats["exact" if err==0 else "wrong"]+=1
            stats["cell_errors"]+=err
            if err<=4: stats["near4"]+=1
            if err<=16: stats["near16"]+=1
            pa=per_action[action]
            pa["opportunities"]+=1
            pa["exact" if err==0 else "wrong"]+=1
            pa["cell_errors"]+=err

        # Post-outcome learning only.
        exact[ek][r160.program(before,after)]+=1
        if action in r172.CAMERA_ACTIONS:
            changed=sum(
                before[r][c]!=after[r][c]
                for r in range(len(before))
                for c in range(len(before[0]))
            )
            if changed:
                b=r167.best_nonzero_shift(before,after)
                if float(b["valid_match_fraction"])>=r172.MIN_TRANSITION_FIT:
                    obs=(int(b["dr"]),int(b["dc"]))
                    shifts[action][obs]+=1
                    comps=r175.component_descriptors(before)
                    r175.learn_morph(before,after,obs,action,base_labels,comps)
                    recent_masks[action].append(
                        r175.fixed_mask_from_transition(before,after,obs)
                    )
                    if len(recent_masks[action])>3:
                        recent_masks[action]=recent_masks[action][-3:]
                    if stage1 is not None and obs==sh:
                        r178.learn_caches(
                            before,stage1,after,action,obs,
                            stage2_cache,prev_action,action_index,run_before
                        )
                    if stage2 is not None and obs==sh:
                        r178.learn_caches(
                            before,stage2,after,action,obs,
                            stage3_cache,prev_action,action_index,run_before
                        )

        if action==prev_action:
            prior_same_run=run_before+1
        else:
            prior_same_run=1
        prev_action=action
        action_index+=1

    out={k:int(stats[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    out["accuracy"]=round(out["exact"]/out["opportunities"],6) if out["opportunities"] else None
    out["mean_cell_errors"]=round(out["cell_errors"]/out["opportunities"],3) if out["opportunities"] else None
    out["per_action"]={}
    for a,c in per_action.items():
        d={k:int(c[k]) for k in ("opportunities","exact","wrong","cell_errors")}
        d["accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
        out["per_action"][a]=d
    return out

def aggregate(rows:list[dict[str,Any]])->dict[str,Any]:
    d={k:sum(int(x.get(k,0)) for x in rows) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    d["accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
    d["mean_cell_errors"]=round(d["cell_errors"]/d["opportunities"],3) if d["opportunities"] else None
    return d

def run(paths:list[Path])->dict[str,Any]:
    results=[]
    for p in sorted(paths,key=lambda x:int(path_id(x)[1:]) if path_id(x).startswith("p") and path_id(x)[1:].isdigit() else 999):
        pid=path_id(p)
        r=audit_trace(base.load_events(p))
        r["path"]=pid
        r["file"]=p.name
        r["split"]="selection" if pid in SELECTION_PATHS else "heldout_same_game"
        results.append(r)

    selection=[x for x in results if x["split"]=="selection"]
    heldout=[x for x in results if x["split"]=="heldout_same_game"]
    return {
        "schema":"deus/arc3-ar25-all20-frozen-pipeline/1",
        "rung":RUNG,
        "execution_class":"CPU_PUBLIC_TRACE_FROZEN_PIPELINE_AR25_ALL20_TRAJECTORY_STRESS",
        "architecture":{
            "stage1":"patch_recent1_s2",
            "stage2":"local_s1",
            "stage3":"component_s1",
            "frozen_from_r180":True,
        },
        "selection_paths":sorted(SELECTION_PATHS),
        "aggregate":{
            "selection":aggregate(selection),
            "heldout_same_game":aggregate(heldout),
            "all20":aggregate(results),
            "heldout_path_count":len(heldout),
            "selection_path_count":len(selection),
            "per_path":results,
        },
        "diagnostic_gate":"AR25_ALL20_FROZEN_TRAJECTORY_STRESS_COMPLETE",
        "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
        "truth":{
            "public_trace_only":True,
            "source_assisted_sequence_replay":True,
            "architecture_frozen_before_heldout":True,
            "heldout_paths_not_used_for_architecture_selection":True,
            "online_state_reset_per_trajectory":True,
            "current_prediction_uses_preaction_and_prior_history_only":True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning":True,
            "independent_generalization_claim":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    if len(a.input)!=20:
        raise SystemExit(f"expected 20 ar25 trajectories, got {len(a.input)}")
    d=run(a.input)
    s=json.dumps(d,indent=2,sort_keys=True)+"\n"
    print(s,end="")
    if a.output:
        a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":
    main()
