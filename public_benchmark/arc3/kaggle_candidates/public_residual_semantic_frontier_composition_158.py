#!/usr/bin/env python3
"""Rung 158: compose r149 semantic prediction with the r157 right-border frontier.

Rung157 repaired a correspondence leak: repeated identical action-aligned movers
were being left in the conservative residual. Rung156 also showed that the retained
r149 semantic predictor fires on a much smaller, zero-observed-error subset than the
all-directional stream tested by r157. This rung composes those two facts rather than
letting a border rule fire on every action.

Prediction order is strict:
  pre-action board/history -> r149/r153 semantic prediction from prior observations
  -> parse that predicted value-pair multiset -> find a unique right-border boundary
     where a predicted old->new pair is visible as NEW immediately above OLD
  -> emit exactly that one-cell edit
  -> only then reveal the current outcome, score against the r157 refined residual,
     and ingest the current original semantic target.

The r157 refined residual still uses current outcome to expand ambiguous component
correspondence, so this remains source-assisted diagnostic evidence rather than a
full-frame independent solver result. No model/GPU/Kaggle/submission claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_residual_placement_reconstruction_audit_150 as r150
import public_residual_history_state_machine_audit_153 as r153
import public_residual_ambiguous_motion_frontier_audit_157 as r157

RUNG=158
Grid=list[list[int]]
Edit=tuple[int,int,int,int]


def predicted_frontier(board:Grid, sem_pred:str)->list[Edit]|None:
    try:
        pairs=json.loads(sem_pred)
    except Exception:
        return None
    if not isinstance(pairs,list): return None
    c=len(board[0])-1; h=len(board); proposals=[]
    # The predicted semantic is a multiset, so deduplicate pair candidates while
    # retaining only transitions actually grounded by a visible right-border
    # NEW|OLD frontier in the current pre-action board.
    for pair in {tuple(map(int,p)) for p in pairs if isinstance(p,list) and len(p)==2}:
        old,new=pair
        rows=[r for r in range(1,h) if board[r][c]==old and board[r-1][c]==new]
        if len(rows)==1:
            proposals.append((rows[0],c,old,new))
    # Multiple semantically-supported frontiers are ambiguous: fail closed.
    if len(proposals)!=1: return None
    return [proposals[0]]


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    semantic_bank:dict[str,Counter[str]]=defaultdict(Counter)
    prev2=prev1=None; pre=events[0]
    s={"semantic_predictions":0,"semantic_correct":0,"semantic_wrong":0,
       "frontier_predictions":0,"frontier_correct":0,"frontier_wrong":0,
       "frontier_abstentions":0,"refined_one_cell_on_semantic_covered":0,
       "refined_empty_on_semantic_covered":0,"refined_multi_on_semantic_covered":0}
    samples=[]
    for ei,e in enumerate(events[1:],1):
        if e.get("type")!="action": pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        original=r150.residual_edits(before,after,action)
        if original is None: continue
        _orig_edits,target_sem=original
        ctx=r153.semantic_context(before,action,prev2,prev1)
        sem_pred=r153.unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None
        if sem_pred is not None:
            s["semantic_predictions"]+=1
            if sem_pred==target_sem:s["semantic_correct"]+=1
            else:s["semantic_wrong"]+=1
            pred=predicted_frontier(before,sem_pred)
            refined=r157.expanded_residual(before,after,action)
            refined=[] if refined is None else sorted(refined)
            if len(refined)==0:s["refined_empty_on_semantic_covered"]+=1
            elif len(refined)==1:s["refined_one_cell_on_semantic_covered"]+=1
            else:s["refined_multi_on_semantic_covered"]+=1
            if pred is None:
                s["frontier_abstentions"]+=1
            else:
                s["frontier_predictions"]+=1
                if pred==refined:s["frontier_correct"]+=1
                else:s["frontier_wrong"]+=1
                if len(samples)<12:
                    samples.append({"event_index":ei,"action":action,"prediction":pred,"refined":refined[:20],"refined_count":len(refined),"semantic_correct":sem_pred==target_sem})
        # Current target enters memory only after current prediction and scoring.
        if ctx is not None: semantic_bank[ctx][target_sem]+=1
        prev2,prev1=prev1,target_sem
    s["semantic_accuracy"]=round(s["semantic_correct"]/s["semantic_predictions"],6) if s["semantic_predictions"] else None
    s["frontier_accuracy"]=round(s["frontier_correct"]/s["frontier_predictions"],6) if s["frontier_predictions"] else None
    s["strict_zero_error_frontier"]=bool(s["frontier_predictions"] and s["frontier_wrong"]==0 and s["semantic_wrong"]==0)
    s["samples"]=samples
    return s


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    keys=("semantic_predictions","semantic_correct","semantic_wrong","frontier_predictions","frontier_correct","frontier_wrong","frontier_abstentions","refined_one_cell_on_semantic_covered","refined_empty_on_semantic_covered","refined_multi_on_semantic_covered")
    s={k:sum(p[k] for p in parts) for k in keys}
    pp=[p["frontier_predictions"] for p in parts]; pc=[p["frontier_correct"] for p in parts]; pw=[p["frontier_wrong"] for p in parts]; sw=[p["semantic_wrong"] for p in parts]
    s.update({"semantic_accuracy":round(s["semantic_correct"]/s["semantic_predictions"],6) if s["semantic_predictions"] else None,"frontier_accuracy":round(s["frontier_correct"]/s["frontier_predictions"],6) if s["frontier_predictions"] else None,"strict_zero_error_frontier":bool(s["frontier_predictions"] and s["frontier_wrong"]==0 and s["semantic_wrong"]==0),"per_trace_frontier_predictions":pp,"per_trace_frontier_correct":pc,"per_trace_frontier_wrong":pw,"per_trace_semantic_wrong":sw,"zero_error_nonzero_p0_p10":bool(len(pp)>=2 and pp[0]>0 and pp[1]>0 and pw[0]==0 and pw[1]==0 and sw[0]==0 and sw[1]==0),"per_trace":parts})
    return s


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({"path":str(p),"audit":a})
    agg=aggregate(parts)
    gate="ZERO_ERROR_P0_P10_REFINED_FRONTIER_GAIN" if agg["zero_error_nonzero_p0_p10"] else "NO_ZERO_ERROR_P0_P10_REFINED_FRONTIER_GAIN"
    return {"schema":"deus/arc3-public-residual-semantic-frontier-composition/1","rung":RUNG,"execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_SEMANTIC_FRONTIER_COMPOSITION_DIAGNOSTIC","representation_change_from_rung157":{"changed":True,"change":"gate the right-border frontier with the retained r149 prefix-only semantic predictor and derive old->new directly from the predicted semantic multiset instead of firing on every directional action"},"source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},"traces":traces,"aggregate":agg,"diagnostic_gate":gate,"promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"source_assisted_replay":True,"diagnostic_only":True,"semantic_prediction_prior_only":True,"frontier_location_and_pair_derived_pre_outcome":True,"current_target_ingested_after_prediction":True,"expanded_correspondence_uses_current_outcome_for_scoring_target":True,"refined_residual_exact_gain_not_full_frame_gain":True,"full_frame_prediction_claim":False,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"model_execution":False,"gpu_execution":False,"kaggle_execution":False,"kaggle_submission_attempted":False,"submission_quota_spent":False,"leaderboard_score_claim":False,"owner_score_claim":False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit("at least one --input is required")
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    print(text,end="");return 0
if __name__=="__main__":raise SystemExit(main())
