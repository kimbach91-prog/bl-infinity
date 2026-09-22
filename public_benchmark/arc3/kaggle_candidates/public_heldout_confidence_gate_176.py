#!/usr/bin/env python3
"""R176: train-on-p0, lock, then held-out confidence gate for R175 best family.

R175 materially improved the public prequential exact-frame rate with
patch_recent1_s2, but its all-history shadow gate was not zero-error. R176 does
not change the renderer. It tests whether PRIOR-ONLY confidence signals can
select a reliable subset without looking at the current outcome.

Protocol:
  * generate pre-action records with patch_recent1_s2;
  * search a fixed gate grid on p0 only;
  * lock one gate before examining p10/p11 outcomes;
  * evaluate that exact gate on p10 and p11.

The gate may use only prior correctness streak, current learned-patch coverage,
prior fixed-mask history depth, and prior mask Jaccard stability. This is still
public/source-assisted replay, not independent generalization or a Kaggle score.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175

RUNG=176
CANDIDATE="patch_recent1_s2"
STREAKS=(0,1,2,3,4)
COVERAGES=(0.0,0.25,0.5,0.75,0.9)
DEPTHS=(1,2,3)
JACCARDS=(0.0,0.5,0.75,0.9)
MIN_TRAIN_SELECTED=2


def unique(bank:Counter[str], support:int=1):
    if len(bank)!=1:return None
    k,n=next(iter(bank.items())); return k if n>=support else None


def jaccard(a:set[tuple[int,int]], b:set[tuple[int,int]])->float:
    if not a and not b:return 1.0
    u=len(a|b)
    return len(a&b)/u if u else 1.0


def trailing_true(xs:deque[bool])->int:
    n=0
    for v in reversed(xs):
        if not v:break
        n+=1
    return n


def pre_features(before,shift,action,recent_masks,labels,comps,prior_ok):
    dr,dc=shift; h,w=len(before),len(before[0])
    disagree=0; labeled=0; label_fixed=0; fallback_recent_fixed=0
    for r in range(h):
      for c in range(w):
        sr,sc=r-dr,c-dc
        if not (0<=sr<h and 0<=sc<w):continue
        fixed,world=before[r][c],before[sr][sc]
        if fixed==world:continue
        disagree+=1
        key=r175.morph_feature("patch",action,before,r,c,sr,sc,comps)
        lab=unique(labels["patch"][key],2)
        if lab is not None:
            labeled+=1
            if lab=="fixed":label_fixed+=1
        elif r175.recent_decision("recent1",recent_masks[action],(r,c)):
            fallback_recent_fixed+=1
    hist=recent_masks[action]
    jac=jaccard(hist[-1],hist[-2]) if len(hist)>=2 else 0.0
    return {
      "streak":trailing_true(prior_ok[action]),
      "patch_coverage":round(labeled/disagree,6) if disagree else 1.0,
      "recent_depth":len(hist),
      "recent_jaccard":round(jac,6),
      "disagree_cells":disagree,
      "labeled_cells":labeled,
      "label_fixed_cells":label_fixed,
      "fallback_recent_fixed_cells":fallback_recent_fixed,
    }


def records(events:list[dict[str,Any]]):
    exact=defaultdict(Counter); shifts=defaultdict(Counter)
    recent_masks=defaultdict(list)
    labels={f:defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    prior_ok=defaultdict(lambda:deque(maxlen=8))
    out=[]; pre=events[0]
    for e in events[1:]:
      if e.get("type")!="action":pre=e;continue
      before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
      if len(before)!=len(after) or len(before[0])!=len(after[0]):continue
      ek=r160.context_exact(before,action); prog=unique(exact[ek],1) if ek in exact else None
      pred_exact=r160.apply_program(before,prog) if prog is not None else None
      sh=r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
      if pred_exact is None and sh is not None:
        comps=r175.component_descriptors(before)
        f=pre_features(before,sh,action,recent_masks,labels,comps,prior_ok)
        pred=r175.render_candidate(before,sh,action,CANDIDATE,recent_masks,labels,comps)
        err=r175.score_frame(pred,after)
        out.append({"action":action,**f,"correct":err==0,"cell_errors":err})
        prior_ok[action].append(err==0)

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
            if len(recent_masks[action])>3:recent_masks[action]=recent_masks[action][-3:]
    return out


def configs():
    for st in STREAKS:
      for cov in COVERAGES:
        for dep in DEPTHS:
          for jac in JACCARDS:
            yield {"streak_min":st,"coverage_min":cov,"depth_min":dep,"jaccard_min":jac}


def passes(r,c):
    return (
      r["streak"]>=c["streak_min"]
      and r["patch_coverage"]>=c["coverage_min"]
      and r["recent_depth"]>=c["depth_min"]
      and r["recent_jaccard"]>=c["jaccard_min"]
    )


def eval_gate(rs,c):
    sel=[r for r in rs if passes(r,c)]
    cor=sum(r["correct"] for r in sel); wrong=len(sel)-cor
    return {
      "selected":len(sel),"correct":cor,"wrong":wrong,
      "accuracy":round(cor/len(sel),6) if sel else None,
      "cell_errors":sum(r["cell_errors"] for r in sel),
      "per_action":{a:{
        "selected":sum(1 for r in sel if r["action"]==a),
        "correct":sum(1 for r in sel if r["action"]==a and r["correct"]),
        "wrong":sum(1 for r in sel if r["action"]==a and not r["correct"]),
      } for a in sorted({r["action"] for r in rs})},
    }


def choose_gate(train):
    scored=[]
    for c in configs():
      e=eval_gate(train,c)
      if e["selected"]<MIN_TRAIN_SELECTED:continue
      zero=e["wrong"]==0
      scored.append((c,e,zero))
    if not scored:return None,None,False
    zeros=[x for x in scored if x[2]]
    pool=zeros if zeros else scored
    # Max selected/correct, then fewer errors, then simpler/lower thresholds.
    c,e,z=max(pool,key=lambda x:(
      x[1]["selected"] if z else x[1]["accuracy"] or 0,
      x[1]["correct"],
      -x[1]["wrong"],
      -x[1]["cell_errors"],
      -x[0]["streak_min"],
      -x[0]["coverage_min"],
      -x[0]["depth_min"],
      -x[0]["jaccard_min"],
    ))
    return c,e,z


def summarize_all(rs):
    return {
      "records":len(rs),
      "correct":sum(r["correct"] for r in rs),
      "wrong":sum(not r["correct"] for r in rs),
      "raw_accuracy":round(sum(r["correct"] for r in rs)/len(rs),6) if rs else None,
      "near4":sum(r["cell_errors"]<=4 for r in rs),
      "near16":sum(r["cell_errors"]<=16 for r in rs),
    }


def run(paths):
    recs=[records(base.load_events(p)) for p in paths]
    train=recs[0]
    gate,train_eval,train_zero=choose_gate(train)
    held=[]
    if gate is not None:
      held=[eval_gate(rs,gate) for rs in recs[1:]]
    heldout_nonzero=bool(held and all(e["selected"]>0 for e in held))
    heldout_zero=bool(heldout_nonzero and all(e["wrong"]==0 for e in held))
    return {
      "schema":"deus/arc3-public-heldout-confidence-gate/1","rung":RUNG,
      "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_TRAIN_P0_LOCK_GATE_HELDOUT_P10_P11",
      "representation_change_from_rung175":{"changed":True,"change":"keep R175 best renderer fixed; replace brittle all-history shadow gate with a p0-trained prior-only confidence gate locked before p10/p11 evaluation"},
      "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
      "protocol":{"candidate":CANDIDATE,"train_trace_index":0,"heldout_trace_indices":[1,2],"gate_grid":{"streaks":list(STREAKS),"coverages":list(COVERAGES),"depths":list(DEPTHS),"jaccards":list(JACCARDS)},"min_train_selected":MIN_TRAIN_SELECTED},
      "raw_per_trace":[summarize_all(rs) for rs in recs],
      "locked_gate":gate,
      "train_eval":train_eval,
      "train_zero_error_selected":train_zero,
      "heldout_eval":held,
      "diagnostic_gate":"HELDOUT_P10_P11_ZERO_ERROR_NONZERO" if heldout_zero else "NO_HELDOUT_ZERO_ERROR_CONFIDENCE_GATE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"gate_selected_from_p0_only":True,"gate_locked_before_p10_p11_outcomes_are_used_for_evaluation":True,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"gpu_execution":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path);a=ap.parse_args()
    if len(a.input)<3:raise SystemExit("three ordered inputs required: p0,p10,p11")
    d=run(a.input);s=json.dumps(d,indent=2,sort_keys=True)+"\n";print(s,end="")
    if a.output:a.output.write_text(s,encoding="utf-8")


if __name__=="__main__":main()
