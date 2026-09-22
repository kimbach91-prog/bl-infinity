#!/usr/bin/env python3
"""Rung 156: characterize the unresolved residual placement mechanism.

Rung155 showed that whole residual edit programs do not recur relative to simple
current-state anchors. This rung is intentionally diagnostic: factor the residual
into spatial statistics, connected components, boundary relation, and distances to
pre-action objects/role anchors, but only for events where the retained rung149
semantic predictor has already made a prefix-only prediction. The goal is to select
the next representation instead of blindly retrying another placement lookup.

Current outcomes are used for characterization/scoring after the semantic prediction
is locked. No solver/model/GPU/Kaggle/submission/leaderboard claim is made.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as obj138
import public_residual_action_mobility_selector_audit_149 as sel149
import public_residual_history_state_machine_audit_153 as r153
import public_residual_placement_reconstruction_audit_150 as r150
import public_residual_shape_canonical_audit_145 as shape145

RUNG=156
SAMPLE_LIMIT=12
Grid=list[list[int]]
Edit=tuple[int,int,int,int]


def bbox(edits:list[Edit])->tuple[int,int,int,int]:
    rs=[e[0] for e in edits]; cs=[e[1] for e in edits]
    return min(rs),min(cs),max(rs),max(cs)


def comps(edits:list[Edit])->int:
    pts={(r,c) for r,c,_o,_n in edits}; n=0
    while pts:
        n+=1; stack=[pts.pop()]
        while stack:
            r,c=stack.pop()
            for q in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if q in pts:
                    pts.remove(q); stack.append(q)
    return n


def object_relations(board:Grid, edits:list[Edit], action:str)->dict[str,Any]:
    r0,c0,r1,c1=bbox(edits); obs=obj138.objects(board); roles=obj138.role_indices(board)
    role_offsets={}
    for role,idx in roles.items():
        if 0<=idx<len(obs):
            o=obs[idx]
            role_offsets[role]=[r0-o.r0,c0-o.c0]
    delta=sel149.ACTION_DELTA.get(action.upper()); nearest_movable=None; nearest_blocked=None
    if delta is not None:
        dr,dc=delta
        for label,want in (("movable",True),("blocked",False)):
            group=[o for o in obs if sel149.can_shift(board,o,dr,dc)==want]
            vals=[]
            for o in group:
                d=max(0,o.r0-r1,r0-o.r1)+max(0,o.c0-c1,c0-o.c1)
                vals.append((d,o.area,o.r0,o.c0,o.r1,o.c1))
            best=min(vals) if vals else None
            if label=="movable": nearest_movable=best
            else: nearest_blocked=best
    return {
        "role_tl_offsets":role_offsets,
        "nearest_movable_bbox_distance":nearest_movable,
        "nearest_blocked_bbox_distance":nearest_blocked,
    }


def audit_trace(events:list[dict[str,Any]])->dict[str,Any]:
    semantic_bank:dict[str,Counter[str]]=defaultdict(Counter)
    prev2=prev1=None; pre=events[0]; covered=[]; all_stats=[]
    for ei,e in enumerate(events[1:],1):
        if e.get("type")!="action": pre=e; continue
        before=base.as_grid(pre["board"]); after=base.as_grid(e["board"]); action=base.action_name(e); pre=e
        detail=r150.residual_edits(before,after,action)
        if detail is None: continue
        edits,target_sem=detail
        ctx=r153.semantic_context(before,action,prev2,prev1)
        sem_pred=r153.unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None
        if sem_pred is not None:
            r0,c0,r1,c1=bbox(edits); h,w=len(before),len(before[0])
            enc=shape145.encode(before,after,action)
            rec={
                "event_index":ei,"action":action,"board_hw":[h,w],
                "semantic_correct":sem_pred==target_sem,
                "edit_count":len(edits),"bbox":[r0,c0,r1,c1],"bbox_hw":[r1-r0+1,c1-c0+1],
                "component_count":comps(edits),
                "border_distances":[r0,c0,h-1-r1,w-1-c1],
                "pair_counts":sorted([[list(k),v] for k,v in Counter((o,n) for _r,_c,o,n in edits).items()]),
                "normalized_mask":json.loads(enc["normalized_mask"]) if enc.get("eligible") else None,
                "action_canonical_mask":json.loads(enc["action_canonical_mask"]) if enc.get("eligible") else None,
                "relations":object_relations(before,edits,action),
                "edits":edits if len(covered)<SAMPLE_LIMIT else None,
            }
            all_stats.append(rec)
            if len(covered)<SAMPLE_LIMIT: covered.append(rec)
        if ctx is not None: semantic_bank[ctx][target_sem]+=1
        prev2,prev1=prev1,target_sem
    nums=lambda key:[x[key] for x in all_stats]
    return {
        "covered_predictions":len(all_stats),
        "semantic_wrong":sum(not x["semantic_correct"] for x in all_stats),
        "edit_count_summary":summary(nums("edit_count")),
        "bbox_h_summary":summary([x["bbox_hw"][0] for x in all_stats]),
        "bbox_w_summary":summary([x["bbox_hw"][1] for x in all_stats]),
        "component_count_summary":summary(nums("component_count")),
        "border_touch_counts":[sum(x["border_distances"][i]==0 for x in all_stats) for i in range(4)],
        "nearest_movable_zero_distance":sum((x["relations"]["nearest_movable_bbox_distance"] or [999])[0]==0 for x in all_stats),
        "nearest_blocked_zero_distance":sum((x["relations"]["nearest_blocked_bbox_distance"] or [999])[0]==0 for x in all_stats),
        "samples":covered,
    }


def summary(xs:list[int])->dict[str,Any]:
    if not xs:return {"n":0,"min":None,"median":None,"max":None,"unique":0}
    return {"n":len(xs),"min":min(xs),"median":median(xs),"max":max(xs),"unique":len(set(xs))}


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    return {
        "trace_count":len(parts),
        "covered_predictions":sum(p["covered_predictions"] for p in parts),
        "semantic_wrong":sum(p["semantic_wrong"] for p in parts),
        "per_trace_covered_predictions":[p["covered_predictions"] for p in parts],
        "per_trace_edit_count_summary":[p["edit_count_summary"] for p in parts],
        "per_trace_bbox_h_summary":[p["bbox_h_summary"] for p in parts],
        "per_trace_bbox_w_summary":[p["bbox_w_summary"] for p in parts],
        "per_trace_component_count_summary":[p["component_count_summary"] for p in parts],
        "per_trace_border_touch_counts":[p["border_touch_counts"] for p in parts],
        "per_trace_nearest_movable_zero_distance":[p["nearest_movable_zero_distance"] for p in parts],
        "per_trace_nearest_blocked_zero_distance":[p["nearest_blocked_zero_distance"] for p in parts],
        "per_trace":parts,
    }


def run(paths:list[Path])->dict[str,Any]:
    parts=[]; traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p)); parts.append(a); traces.append({"path":str(p),"audit":a})
    return {
        "schema":"deus/arc3-public-residual-mechanism-characterization/1","rung":RUNG,
        "execution_class":"CPU_PUBLIC_TRACE_RETROSPECTIVE_MECHANISM_CHARACTERIZATION",
        "representation_change_from_rung155":{"changed":True,"change":"stop fitting whole anchor programs; factor unresolved placement into spatial/component/object-relation observables to select a new causal representation"},
        "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
        "traces":traces,"aggregate":aggregate(parts),"diagnostic_gate":"RESIDUAL_MECHANISM_CHARACTERIZED",
        "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
        "truth":{"public_trace_only":True,"source_assisted_replay":True,"diagnostic_only":True,"semantic_prediction_prefix_only":True,"current_outcome_used_after_prediction_for_characterization":True,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"model_execution":False,"gpu_execution":False,"kaggle_execution":False,"kaggle_submission_attempted":False,"submission_quota_spent":False,"leaderboard_score_claim":False,"owner_score_claim":False}
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); args=ap.parse_args()
    if not args.input: raise SystemExit("at least one --input is required")
    d=run(args.input); text=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.write_text(text,encoding="utf-8")
    print(text,end=""); return 0
if __name__=="__main__": raise SystemExit(main())
