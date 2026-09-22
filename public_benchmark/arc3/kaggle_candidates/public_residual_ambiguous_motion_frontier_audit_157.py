#!/usr/bin/env python3
"""Rung 157: repair ambiguous action-aligned correspondence, then predict a border frontier.

Rung156 exposed a concrete failure mode in the conservative residual isolation used
by r145-r156: every covered residual touches the right border, while the remaining
0<->9 edits also lie directly on action-movable/blocked component boxes. The earlier
`unique_matches` correspondence intentionally left repeated identical movers out of
the motion footprint, so ambiguous but action-aligned movers leaked into the
'residual'.

This rung changes representation in two steps:
1) retrospectively expand the scoring/isolation footprint to *all* before objects
   whose exact expected action-aligned translation exists as a same-color/same-shape
   object after the action, even if identity is ambiguous;
2) on the refined residual, evaluate prefix-only one-cell border-frontier rules.
   The old->new transition pair is learned from prior one-cell refined residuals
   (>=2 identical supports) and the current location is selected only from the
   pre-action right border (top/bottom old cell or old/new boundary variants).

The expanded correspondence still uses the current outcome for residual isolation,
so even a perfect frontier result is source-assisted diagnostic evidence, not a
full-frame or independent-generalization result. No model/GPU/Kaggle/submission/
leaderboard claim is made.
"""
from __future__ import annotations

import argparse, json
from collections import Counter
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_action_mobility_selector_audit_149 as sel149

RUNG=157
MIN_PAIR_SUPPORT=2
Grid=list[list[int]]
Edit=tuple[int,int,int,int]
RULES=(
    "right_topmost_old",
    "right_bottommost_old",
    "right_topmost_old_with_above_new",
    "right_bottommost_old_with_above_new",
    "right_topmost_old_with_below_new",
    "right_bottommost_old_with_below_new",
)


def expanded_residual(before:Grid,after:Grid,action:str)->list[Edit]|None:
    if not base.same_shape(before,after): return None
    delta=sel149.ACTION_DELTA.get(action.upper())
    if delta is None: return None
    dr,dc=delta; h,w=len(before),len(before[0])
    obs=obj138.objects(before); oas=obj138.objects(after)
    after_index={(o.color,o.shape,frozenset(o.cells)) for o in oas}
    footprint:set[tuple[int,int]]=set()
    for o in obs:
        dst={(r+dr,c+dc) for r,c in o.cells}
        if any(r<0 or r>=h or c<0 or c>=w for r,c in dst): continue
        key=(o.color,o.shape,frozenset(dst))
        if key in after_index:
            footprint.update(o.cells); footprint.update(dst)
    edits=[]
    for r in range(h):
        for c in range(w):
            if before[r][c]!=after[r][c] and (r,c) not in footprint:
                edits.append((r,c,before[r][c],after[r][c]))
    return edits


def learned_pair(bank:Counter[str])->tuple[int,int]|None:
    if len(bank)!=1: return None
    raw,n=next(iter(bank.items()))
    if n<MIN_PAIR_SUPPORT: return None
    a=json.loads(raw)
    return int(a[0]),int(a[1])


def select_right(board:Grid,old:int,new:int,rule:str)->tuple[int,int]|None:
    c=len(board[0])-1; h=len(board)
    rows=[r for r in range(h) if board[r][c]==old]
    if "with_above_new" in rule:
        rows=[r for r in rows if r>0 and board[r-1][c]==new]
    if "with_below_new" in rule:
        rows=[r for r in rows if r+1<h and board[r+1][c]==new]
    if not rows: return None
    r=min(rows) if "topmost" in rule else max(rows)
    return r,c


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    pair_bank:Counter[str]=Counter()
    stats={r:{"predictions":0,"correct":0,"wrong":0,"no_pair":0,"no_location":0} for r in RULES}
    refined=0; one_cell=0; one_cell_right=0; pair_counts=Counter(); edit_counts=Counter(); pre=events[0]
    samples=[]
    for ei,e in enumerate(events[1:],1):
        if e.get("type")!="action": pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        edits=expanded_residual(before,after,action)
        if edits is None: continue
        refined+=1; edit_counts[len(edits)]+=1
        pair=learned_pair(pair_bank)
        for rule in RULES:
            s=stats[rule]
            if pair is None:
                s["no_pair"]+=1; continue
            old,new=pair; loc=select_right(before,old,new,rule)
            if loc is None:
                s["no_location"]+=1; continue
            pred=[(loc[0],loc[1],old,new)]
            s["predictions"]+=1
            if pred==sorted(edits): s["correct"]+=1
            else: s["wrong"]+=1
        if len(edits)==1:
            one_cell+=1; r,c,old,new=edits[0]
            pair_counts[base.stable([old,new])]+=1
            if c==len(before[0])-1: one_cell_right+=1
            if len(samples)<12:
                samples.append({"event_index":ei,"action":action,"edit":edits[0],"right_border_values":[before[x][-1] for x in range(len(before))]})
            # Ingest only after all predictions for this event are locked.
            pair_bank[base.stable([old,new])]+=1
    for rule,s in stats.items():
        s["accuracy"]=round(s["correct"]/s["predictions"],6) if s["predictions"] else None
        s["strict_zero_error"]=bool(s["predictions"] and s["wrong"]==0)
    return {"refined_directional_transitions":refined,"refined_edit_count_distribution":dict(sorted(edit_counts.items())),"one_cell_refined":one_cell,"one_cell_right_border":one_cell_right,"one_cell_pair_counts":dict(pair_counts),"rules":stats,"samples":samples}


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    out={}; hard=[]
    for rule in RULES:
        pred=sum(p["rules"][rule]["predictions"] for p in parts); cor=sum(p["rules"][rule]["correct"] for p in parts); wrong=sum(p["rules"][rule]["wrong"] for p in parts)
        pp=[p["rules"][rule]["predictions"] for p in parts]; pc=[p["rules"][rule]["correct"] for p in parts]; pw=[p["rules"][rule]["wrong"] for p in parts]
        out[rule]={"predictions":pred,"correct":cor,"wrong":wrong,"accuracy":round(cor/pred,6) if pred else None,"strict_zero_error":bool(pred and wrong==0),"per_trace_predictions":pp,"per_trace_correct":pc,"per_trace_wrong":pw}
        if len(pp)>=2 and pp[0]>0 and pp[1]>0 and pw[0]==0 and pw[1]==0: hard.append((pp[0]+pp[1],rule))
    counts=Counter(); pairs=Counter()
    for p in parts:
        counts.update({int(k):v for k,v in p["refined_edit_count_distribution"].items()}); pairs.update(p["one_cell_pair_counts"])
    return {"trace_count":len(parts),"refined_directional_transitions":sum(p["refined_directional_transitions"] for p in parts),"refined_edit_count_distribution":dict(sorted(counts.items())),"one_cell_refined":sum(p["one_cell_refined"] for p in parts),"one_cell_right_border":sum(p["one_cell_right_border"] for p in parts),"one_cell_pair_counts":dict(pairs),"rules":out,"best_zero_error_p0_p10_border_rule":max(hard)[1] if hard else None,"per_trace":parts}


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p));parts.append(a);traces.append({"path":str(p),"audit":a})
    return {"schema":"deus/arc3-public-residual-ambiguous-motion-frontier-audit/1","rung":RUNG,"execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_AMBIGUOUS_MOTION_FRONTIER_DIAGNOSTIC","representation_change_from_rung156":{"changed":True,"change":"expand action-aligned correspondence across repeated identical objects before modeling the residual; then test learned-pair right-border frontier rules on the refined residual"},"parameters":{"min_pair_support":MIN_PAIR_SUPPORT},"source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},"traces":traces,"aggregate":aggregate(parts),"diagnostic_gate":"AMBIGUOUS_MOTION_FRONTIER_CHARACTERIZED","promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},"truth":{"public_trace_only":True,"source_assisted_replay":True,"diagnostic_only":True,"expanded_correspondence_uses_current_outcome_for_residual_isolation":True,"frontier_pair_and_location_prediction_prior_only":True,"current_pair_ingested_after_prediction":True,"hard_trace_gate_requires_p0_and_p10_nonzero_zero_error_coverage":True,"full_frame_prediction_claim":False,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"model_execution":False,"gpu_execution":False,"kaggle_execution":False,"kaggle_submission_attempted":False,"submission_quota_spent":False,"leaderboard_score_claim":False,"owner_score_claim":False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit("at least one --input is required")
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    print(text,end="");return 0
if __name__=="__main__":raise SystemExit(main())
