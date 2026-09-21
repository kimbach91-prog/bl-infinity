#!/usr/bin/env python3
"""Rung 145: translation- and action-canonical residual-shape recurrence.

Rung 144 showed that neither absolute residual coordinates nor a single mover-bbox
anchor explains p0/p10. This rung changes representation again: it strips absolute
translation from the residual mask, and separately rotates directional actions into
a common RIGHT-facing frame before translation normalization. This asks whether
the residual is a recurrent local *shape/animation motif* whose position changes.

Retrospective public diagnostic only. Current outcome is required for conservative
component correspondence and residual isolation. Recurrence counters are prefix-
only. No predictive/generalization/model/GPU/Kaggle/submission/leaderboard claim.
"""
from __future__ import annotations

import argparse,json
from collections import Counter
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_unique_component_motion_audit_140 as motion

RUNG=145
Grid=list[list[int]]
ACTION_EXPECTED={'UP':(-3,0),'DOWN':(3,0),'LEFT':(0,-3),'RIGHT':(0,3)}


def normalize(points:list[tuple[int,int]])->list[tuple[int,int]]:
    if not points:return []
    r0=min(r for r,c in points); c0=min(c for r,c in points)
    return sorted((r-r0,c-c0) for r,c in points)


def rotate_to_right(points:list[tuple[int,int]],action:str)->list[tuple[int,int]]:
    a=action.upper(); out=[]
    for r,c in points:
        if a=='RIGHT': rr,cc=r,c
        elif a=='LEFT': rr,cc=-r,-c
        elif a=='DOWN': rr,cc=-c,r
        elif a=='UP': rr,cc=c,-r
        else: rr,cc=r,c
        out.append((rr,cc))
    return normalize(out)


def encode(before:Grid,after:Grid,action:str)->dict[str,Any]:
    if not base.same_shape(before,after):return {'eligible':False,'reason':'shape_changed'}
    diff={(r,c) for r in range(len(before)) for c in range(len(before[0])) if before[r][c]!=after[r][c]}
    if not diff:return {'eligible':False,'reason':'identity'}
    expected=ACTION_EXPECTED.get(action.upper())
    if expected is None:return {'eligible':False,'reason':'non_directional'}
    matches=motion.unique_matches(before,after)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    if not moved:return {'eligible':False,'reason':'no_motion_core'}
    deltas=Counter((m[2],m[3]) for m in moved)
    if len(deltas)!=1:return {'eligible':False,'reason':'mixed_motion'}
    if next(iter(deltas))!=expected:return {'eligible':False,'reason':'non_action_aligned'}
    footprint=set()
    for x,y,dr,dc in moved: footprint.update(x.cells);footprint.update(y.cells)
    residual=sorted(diff-footprint)
    if not residual:return {'eligible':False,'reason':'zero_residual'}
    abs_mask=base.stable(residual)
    norm_mask=base.stable(normalize(residual))
    action_mask=base.stable(rotate_to_right(residual,action))
    # Value-pair multiset adds local transition semantics while remaining
    # independent of absolute position.
    value_pairs=base.stable(sorted((before[r][c],after[r][c]) for r,c in residual))
    return {'eligible':True,'absolute_mask':abs_mask,'normalized_mask':norm_mask,'action_canonical_mask':action_mask,'value_pair_multiset':value_pairs}


def trace_audit(events:list[dict[str,Any]])->dict[str,Any]:
    keys=('absolute_mask','normalized_mask','action_canonical_mask','value_pair_multiset')
    seen={k:Counter() for k in keys};reuse=Counter();eligible=0;reasons=Counter();pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        r=encode(base.as_grid(pre['board']),base.as_grid(e['board']),base.action_name(e));pre=e
        if not r['eligible']:reasons[r['reason']]+=1;continue
        eligible+=1
        for k in keys:reuse[k]+=seen[k][r[k]]>0
        for k in keys:seen[k][r[k]]+=1
    return {'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),'reuse_counts':dict(reuse),'reuse_fraction':{k:round(reuse[k]/eligible,6) if eligible else 0 for k in keys},'unique_signatures':{k:len(seen[k]) for k in keys}}


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    keys=('absolute_mask','normalized_mask','action_canonical_mask','value_pair_multiset');eligible=sum(p['eligible_transitions'] for p in parts);reuse=Counter();reasons=Counter()
    for p in parts:reuse.update(p['reuse_counts']);reasons.update(p['ineligible_reasons'])
    frac={k:round(reuse[k]/eligible,6) if eligible else 0 for k in keys}
    return {'trace_count':len(parts),'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),'reuse_counts':dict(reuse),'reuse_fraction':frac,'translation_normalization_improvement':round(frac['normalized_mask']-frac['absolute_mask'],6),'action_canonical_improvement_over_normalized':round(frac['action_canonical_mask']-frac['normalized_mask'],6),'per_trace_reuse_fraction':[p['reuse_fraction'] for p in parts]}


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=trace_audit(base.load_events(p));parts.append(a);traces.append({'path':str(p),'audit':a})
    return {'schema':'deus/arc3-public-residual-shape-canonical-audit/1','rung':RUNG,'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_SHAPE_CANONICAL_DIAGNOSTIC','representation_change_from_rung144':{'changed':True,'change':'strip residual absolute translation and optionally rotate directional actions into a common RIGHT-facing coordinate frame'},'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},'traces':traces,'aggregate':aggregate(parts),'diagnostic_gate':'RESIDUAL_SHAPE_CANONICALIZATION_CHARACTERIZED','promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'current_outcome_used_for_correspondence_and_residual':True,'recurrence_lookup_is_prefix_only':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
