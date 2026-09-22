#!/usr/bin/env python3
"""R182: frozen AR25 all-20 stage ablation for the R180A pipeline.

No architecture selection occurs here. The already-frozen pipeline is replayed
on all 20 public AR25 trajectories with fresh online state per trajectory and
we score, on the SAME opportunities, three pre-action/prior-only predictions:
  S1 = R175 patch_recent1_s2
  S2 = S1 + R178 local_s1
  S3 = S2 + R178 component_s1

Selection paths p0,p10,p11 are reported separately from the 17 same-game
withheld paths. This diagnoses whether residual stages transfer rather than
merely fitting the three selection trajectories. Public source-assisted replay
only; not independent ARC-AGI-3 generalization or a Kaggle score.
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
SELECTION={"p0","p10","p11"}
STAGES=("stage1","stage2","stage3")

def pid(p:Path)->str:
    m=re.search(r"_p(\d+)_events\.jsonl$",p.name)
    return f"p{m.group(1)}" if m else p.stem

def score_add(c:Counter, pred, after):
    err=r175.score_frame(pred,after)
    c["opportunities"]+=1; c["cell_errors"]+=err
    c["exact" if err==0 else "wrong"]+=1
    if err<=4:c["near4"]+=1
    if err<=16:c["near16"]+=1

def pack(c:Counter)->dict[str,Any]:
    d={k:int(c[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    d["accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
    d["mean_cell_errors"]=round(d["cell_errors"]/d["opportunities"],3) if d["opportunities"] else None
    return d

def audit(events:list[dict[str,Any]])->dict[str,Any]:
    exact=defaultdict(Counter); shifts=defaultdict(Counter); recent_masks=defaultdict(list)
    base_labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    c2={f:defaultdict(Counter) for f in r178.FAMILIES}
    c3={f:defaultdict(Counter) for f in r178.FAMILIES}
    stats={s:Counter() for s in STAGES}
    pre=events[0]; prev="START"; runlen=0; idx=0
    for e in events[1:]:
        if e.get("type")!="action": pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        if len(before)!=len(after) or len(before[0])!=len(after[0]): continue
        rb=runlen if action==prev else 0
        ek=r160.context_exact(before,action)
        prog=r175.exact_prog(exact[ek],1) if ek in exact else None
        pred_exact=r160.apply_program(before,prog) if prog is not None else None
        sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
        s1=s2=None
        if pred_exact is None and sh is not None:
            comps=r175.component_descriptors(before)
            s1=r175.render_candidate(before,sh,action,"patch_recent1_s2",recent_masks,base_labels,comps)
            s2=r178.correct_frame(before,s1,action,sh,"local_s1",c2,prev,idx,rb)
            s3=r178.correct_frame(before,s2,action,sh,"component_s1",c3,prev,idx,rb)
            score_add(stats["stage1"],s1,after); score_add(stats["stage2"],s2,after); score_add(stats["stage3"],s3,after)
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
                    if s1 is not None and obs==sh: r178.learn_caches(before,s1,after,action,obs,c2,prev,idx,rb)
                    if s2 is not None and obs==sh: r178.learn_caches(before,s2,after,action,obs,c3,prev,idx,rb)
        runlen=rb+1 if action==prev else 1; prev=action; idx+=1
    return {s:pack(stats[s]) for s in STAGES}

def sum_stage(rows, stage):
    c=Counter()
    for x in rows:
        d=x[stage]
        for k in ("opportunities","exact","wrong","near4","near16","cell_errors"): c[k]+=d[k]
    return pack(c)

def run(paths:list[Path])->dict[str,Any]:
    rows=[]
    for p in sorted(paths,key=lambda x:int(pid(x)[1:])):
        r=audit(base.load_events(p)); r["path"]=pid(p); r["split"]="selection" if pid(p) in SELECTION else "heldout_same_game"; rows.append(r)
    sel=[x for x in rows if x["split"]=="selection"]; hold=[x for x in rows if x["split"]=="heldout_same_game"]
    aggregates={}
    for split,rr in (("selection",sel),("heldout_same_game",hold),("all20",rows)):
        aggregates[split]={s:sum_stage(rr,s) for s in STAGES}
        aggregates[split]["delta_s2_vs_s1_exact"]=aggregates[split]["stage2"]["exact"]-aggregates[split]["stage1"]["exact"]
        aggregates[split]["delta_s3_vs_s2_exact"]=aggregates[split]["stage3"]["exact"]-aggregates[split]["stage2"]["exact"]
        aggregates[split]["delta_s3_vs_s1_exact"]=aggregates[split]["stage3"]["exact"]-aggregates[split]["stage1"]["exact"]
    h=aggregates["heldout_same_game"]
    transfer=bool(h["delta_s2_vs_s1_exact"]>0 and h["delta_s3_vs_s2_exact"]>=0 and h["stage3"]["cell_errors"]<=h["stage1"]["cell_errors"])
    return {
      "schema":"deus/arc3-ar25-all20-stage-ablation/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_FROZEN_AR25_ALL20_STAGE_ABLATION",
      "architecture":{"stage1":"patch_recent1_s2","stage2":"local_s1","stage3":"component_s1","frozen_before_r182":True},
      "aggregate":aggregates,"per_path":rows,
      "diagnostic_gate":"HELDOUT_RESIDUAL_STAGE_TRANSFER_OBSERVED" if transfer else "HELDOUT_RESIDUAL_STAGE_TRANSFER_NOT_ESTABLISHED",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"architecture_frozen_before_evaluation":True,"heldout_paths_not_used_for_architecture_selection":True,"online_state_reset_per_trajectory":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"independent_generalization_claim":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); a=ap.parse_args()
    if len(a.input)!=20: raise SystemExit(f"expected20 got{len(a.input)}")
    d=run(a.input); s=json.dumps(d,indent=2,sort_keys=True)+"\n"; print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":main()
