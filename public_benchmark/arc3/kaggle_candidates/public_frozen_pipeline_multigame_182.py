#!/usr/bin/env python3
"""R182: frozen R180 pipeline cross-game applicability stress.

Runs the exact R180-selected architecture independently on arbitrary public
trajectory files, resetting online state for every trajectory. No architecture
or thresholds are tuned from these files. This rung is intended first for p0
across every public game prefix, then can be reused by broader suites.

Frozen architecture:
  stage1 patch_recent1_s2 -> stage2 local_s1 -> stage3 component_s1.

Predictions are pre-action/prior-history-only. Outcomes are used only for
scoring and post-prediction online learning. Public source-assisted replay only.
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

RUNG=182

def parse_id(p:Path)->tuple[str,str]:
    m=re.match(r"(.+)_p(\d+)_events\.jsonl$",p.name)
    if not m: return p.stem,"unknown"
    return m.group(1),f"p{m.group(2)}"

def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    stage2_cache={f:defaultdict(Counter) for f in r178.FAMILIES}
    stage3_cache={f:defaultdict(Counter) for f in r178.FAMILIES}
    stats=Counter(); actions=Counter()
    pre=events[0]; prev_action="START"; prior_same_run=0; action_index=0

    for e in events[1:]:
        if e.get("type")!="action":
            pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"])
        action=base.action_name(e); pre=e
        actions[action]+=1
        if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
        run_before=prior_same_run if action==prev_action else 0
        ek=r160.context_exact(before,action)
        prog=r175.exact_prog(exact[ek],1) if ek in exact else None
        pred_exact=r160.apply_program(before,prog) if prog is not None else None
        sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
        stage1=stage2=None

        if pred_exact is None and sh is not None:
            comps=r175.component_descriptors(before)
            stage1=r175.render_candidate(before,sh,action,"patch_recent1_s2",recent_masks,base_labels,comps)
            stage2=r178.correct_frame(before,stage1,action,sh,"local_s1",stage2_cache,prev_action,action_index,run_before)
            pred=r178.correct_frame(before,stage2,action,sh,"component_s1",stage3_cache,prev_action,action_index,run_before)
            err=r175.score_frame(pred,after)
            stats["opportunities"]+=1
            stats["exact" if err==0 else "wrong"]+=1
            stats["cell_errors"]+=err
            if err<=4: stats["near4"]+=1
            if err<=16: stats["near16"]+=1

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

    d={k:int(stats[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    d["accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
    d["mean_cell_errors"]=round(d["cell_errors"]/d["opportunities"],3) if d["opportunities"] else None
    d["actions"]=dict(actions)
    d["camera_action_count"]=int(actions["UP"]+actions["DOWN"])
    return d

def aggregate(xs:list[dict[str,Any]])->dict[str,Any]:
    d={k:sum(int(x.get(k,0)) for x in xs) for k in ("opportunities","exact","wrong","near4","near16","cell_errors","camera_action_count")}
    d["accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
    d["files_with_opportunities"]=sum(1 for x in xs if x["opportunities"]>0)
    d["files_total"]=len(xs)
    return d

def run(paths:list[Path])->dict[str,Any]:
    rows=[]
    for p in sorted(paths,key=lambda x:x.name):
        game,path=parse_id(p); r=audit_trace(base.load_events(p))
        r.update({"game":game,"path":path,"file":p.name})
        rows.append(r)
    by_game={}
    for g in sorted({x["game"] for x in rows}):
        by_game[g]=aggregate([x for x in rows if x["game"]==g])
    return {
        "schema":"deus/arc3-frozen-pipeline-multigame/1",
        "rung":RUNG,
        "execution_class":"CPU_PUBLIC_TRACE_FROZEN_PIPELINE_CROSS_GAME_APPLICABILITY",
        "architecture":{"stage1":"patch_recent1_s2","stage2":"local_s1","stage3":"component_s1","frozen_from_r180":True},
        "aggregate":{"all":aggregate(rows),"by_game":by_game,"per_file":rows},
        "diagnostic_gate":"FROZEN_MULTIGAME_APPLICABILITY_STRESS_COMPLETE",
        "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
        "truth":{
            "public_trace_only":True,
            "source_assisted_sequence_replay":True,
            "architecture_frozen_before_cross_game_evaluation":True,
            "cross_game_files_not_used_for_architecture_selection":True,
            "online_state_reset_per_trajectory":True,
            "current_prediction_uses_preaction_and_prior_history_only":True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning":True,
            "independent_generalization_claim":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False
        }
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
