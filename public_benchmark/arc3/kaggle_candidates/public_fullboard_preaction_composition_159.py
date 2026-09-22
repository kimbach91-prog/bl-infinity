#!/usr/bin/env python3
"""Rung 159: pre-action full-board composition from mover dynamics + r158 frontier.

Rung158 produced a zero-error, nonzero p0+p10 exact *refined-residual* prediction,
but its scoring target still depended on outcome-assisted ambiguous correspondence.
This rung removes that dependence from the prediction itself and asks a harder
question: can the complete next visible board be reconstructed before the current
outcome is revealed?

The predictor composes:
  * the retained prefix-only r149/r153 semantic predictor;
  * the r158 right-border frontier derived from that predicted semantic;
  * one of three pre-action mover selectors:
      - all_legal: shift every object individually legal for the action delta;
      - learned_colors_all: shift all objects whose mover-color set was learned
        from prior outcomes only;
      - learned_colors_legal: learned mover colors intersected with pre-action
        individual legality.

Mover-color sets are inferred from prior outcomes only and require >=2 identical
prior observations. Current outcome is scored only after the current full-board
prediction is locked, then may update the mover-color bank. This is still public
source-sequence replay, not hidden-Kaggle evidence or cross-game generalization.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_action_mobility_selector_audit_149 as sel149
import public_residual_placement_reconstruction_audit_150 as r150
import public_residual_history_state_machine_audit_153 as r153
import public_residual_semantic_frontier_composition_158 as r158

RUNG=159
MIN_MOVER_SET_SUPPORT=2
VARIANTS=("all_legal","learned_colors_all","learned_colors_legal")
Grid=list[list[int]]


def stable_mover_set(counter:Counter[str])->set[int]|None:
    if len(counter)!=1:return None
    raw,n=next(iter(counter.items()))
    if n<MIN_MOVER_SET_SUPPORT:return None
    return {int(x) for x in json.loads(raw)}


def observed_mover_colors(before:Grid,after:Grid,action:str)->set[int]:
    delta=sel149.ACTION_DELTA.get(action.upper())
    if delta is None:return set()
    dr,dc=delta; h,w=len(before),len(before[0]); after_objs=obj138.objects(after)
    after_keys={(o.color,o.shape,frozenset(o.cells)) for o in after_objs}
    out=set()
    for o in obj138.objects(before):
        dst={(r+dr,c+dc) for r,c in o.cells}
        if any(r<0 or r>=h or c<0 or c>=w for r,c in dst):continue
        if (o.color,o.shape,frozenset(dst)) in after_keys:
            out.add(o.color)
    return out


def select_objects(board:Grid,action:str,variant:str,mover_colors:set[int]|None):
    delta=sel149.ACTION_DELTA.get(action.upper())
    if delta is None:return []
    dr,dc=delta; obs=obj138.objects(board)
    if variant=="all_legal":
        return [o for o in obs if sel149.can_shift(board,o,dr,dc)]
    if mover_colors is None:return []
    if variant=="learned_colors_all":
        return [o for o in obs if o.color in mover_colors]
    if variant=="learned_colors_legal":
        return [o for o in obs if o.color in mover_colors and sel149.can_shift(board,o,dr,dc)]
    raise ValueError(variant)


def simultaneous_shift(board:Grid,objs,action:str)->Grid|None:
    delta=sel149.ACTION_DELTA.get(action.upper())
    if delta is None:return None
    dr,dc=delta; h,w=len(board),len(board[0]); bg=obj138.background_color(board)
    src=set(); dst_owner={}
    for i,o in enumerate(objs):
        src.update(o.cells)
        for r,c in o.cells:
            q=(r+dr,c+dc)
            if not (0<=q[0]<h and 0<=q[1]<w):return None
            if q in dst_owner and dst_owner[q]!=o.color:return None
            dst_owner[q]=o.color
    for q in dst_owner:
        if q not in src and board[q[0]][q[1]]!=bg:return None
    out=[row[:] for row in board]
    for r,c in src-set(dst_owner):out[r][c]=bg
    for (r,c),color in dst_owner.items():out[r][c]=color
    return out


def apply_frontier(board:Grid,frontier)->Grid|None:
    if frontier is None or len(frontier)!=1:return None
    r,c,old,new=frontier[0]
    if not (0<=r<len(board) and 0<=c<len(board[0])):return None
    # The mover transform may have changed this cell; only accept if the expected
    # old value still holds, otherwise the composition is not causally compatible.
    if board[r][c]!=old:return None
    out=[row[:] for row in board];out[r][c]=new;return out


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    semantic_bank=defaultdict(Counter); mover_bank=defaultdict(Counter)
    stats={v:{"predictions":0,"correct":0,"wrong":0,"no_mover_model":0,"invalid_shift":0,"invalid_frontier_apply":0} for v in VARIANTS}
    prev2=prev1=None;pre=events[0];semantic_predictions=semantic_correct=semantic_wrong=0
    for e in events[1:]:
        if e.get("type")!="action":pre=e;continue
        before=base.as_grid(pre["board"]);after=base.as_grid(e["board"]);action=base.action_name(e);pre=e
        detail=r150.residual_edits(before,after,action)
        if detail is None:continue
        _edits,target_sem=detail
        ctx=r153.semantic_context(before,action,prev2,prev1)
        sem_pred=r153.unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None
        learned=stable_mover_set(mover_bank[action])
        if sem_pred is not None:
            semantic_predictions+=1
            if sem_pred==target_sem:semantic_correct+=1
            else:semantic_wrong+=1
            frontier=r158.predicted_frontier(before,sem_pred)
            for v in VARIANTS:
                s=stats[v]
                if v!="all_legal" and learned is None:
                    s["no_mover_model"]+=1;continue
                objs=select_objects(before,action,v,learned)
                moved=simultaneous_shift(before,objs,action)
                if moved is None:
                    s["invalid_shift"]+=1;continue
                pred=apply_frontier(moved,frontier)
                if pred is None:
                    s["invalid_frontier_apply"]+=1;continue
                s["predictions"]+=1
                if pred==after:s["correct"]+=1
                else:s["wrong"]+=1
        # Ingest only after current predictions are locked/scored.
        if ctx is not None:semantic_bank[ctx][target_sem]+=1
        mover_bank[action][base.stable(sorted(observed_mover_colors(before,after,action)))]+=1
        prev2,prev1=prev1,target_sem
    for v,s in stats.items():
        s["accuracy"]=round(s["correct"]/s["predictions"],6) if s["predictions"] else None
        s["strict_zero_error_fullboard"]=bool(s["predictions"] and s["wrong"]==0 and semantic_wrong==0)
    return {"semantic_predictions":semantic_predictions,"semantic_correct":semantic_correct,"semantic_wrong":semantic_wrong,"variants":stats}


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    out={};hard=[]
    for v in VARIANTS:
        pred=sum(p["variants"][v]["predictions"] for p in parts);cor=sum(p["variants"][v]["correct"] for p in parts);wrong=sum(p["variants"][v]["wrong"] for p in parts)
        pp=[p["variants"][v]["predictions"] for p in parts];pc=[p["variants"][v]["correct"] for p in parts];pw=[p["variants"][v]["wrong"] for p in parts];sw=[p["semantic_wrong"] for p in parts]
        out[v]={"predictions":pred,"correct":cor,"wrong":wrong,"accuracy":round(cor/pred,6) if pred else None,"strict_zero_error_fullboard":bool(pred and wrong==0 and sum(sw)==0),"per_trace_predictions":pp,"per_trace_correct":pc,"per_trace_wrong":pw,"per_trace_semantic_wrong":sw}
        if len(pp)>=2 and pp[0]>0 and pp[1]>0 and pw[0]==0 and pw[1]==0 and sw[0]==0 and sw[1]==0:hard.append((pp[0]+pp[1],v))
    return {"trace_count":len(parts),"semantic_predictions":sum(p["semantic_predictions"] for p in parts),"semantic_correct":sum(p["semantic_correct"] for p in parts),"semantic_wrong":sum(p["semantic_wrong"] for p in parts),"variants":out,"best_zero_error_p0_p10_fullboard_variant":max(hard)[1] if hard else None,"per_trace":parts}


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({"path":str(p),"audit":a})
    agg=aggregate(parts)
    gate="ZERO_ERROR_P0_P10_PREACTION_FULLBOARD_GAIN" if agg["best_zero_error_p0_p10_fullboard_variant"] else "NO_ZERO_ERROR_P0_P10_PREACTION_FULLBOARD_GAIN"
    return {"schema":"deus/arc3-public-fullboard-preaction-composition/1","rung":RUNG,"execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_FULLBOARD_COMPOSITION_DIAGNOSTIC","representation_change_from_rung158":{"changed":True,"change":"remove current-outcome dependence from the predicted board by composing prefix-learned mover-color dynamics or pre-action legality with the semantic-gated frontier, then score the complete next frame"},"parameters":{"min_mover_set_support":MIN_MOVER_SET_SUPPORT},"source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},"traces":traces,"aggregate":agg,"diagnostic_gate":gate,"promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"diagnostic_only":True,"current_fullboard_prediction_uses_preaction_and_prior_outcomes_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"full_frame_prediction_claim":True,"cross_game_independent_generalization_claim":False,"solver_behavior_gain_claim":False,"model_execution":False,"gpu_execution":False,"kaggle_execution":False,"kaggle_submission_attempted":False,"submission_quota_spent":False,"leaderboard_score_claim":False,"owner_score_claim":False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit("at least one --input is required")
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    print(text,end="");return 0
if __name__=="__main__":raise SystemExit(main())
