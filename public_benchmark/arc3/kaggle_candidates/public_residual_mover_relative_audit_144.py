#!/usr/bin/env python3
"""Rung 144: compare absolute residual recurrence with mover-relative recurrence.

Rung 143 rejected one global fixed-coordinate residual template: p0/p10 had no
exact absolute-mask recurrence while p11 had a recurrent subregime. This rung
changes coordinates instead of retrying the same representation. On the same
strict directional/action-aligned motion-core regime, residual cells are encoded
relative to the bounding-box anchor of the moved components' source and
destination footprints. Prefix recurrence of those signatures is compared with
absolute-coordinate recurrence.

Retrospective public diagnostic only: current outcome is required to establish
component correspondence and isolate the residual. No predictive/generalization,
model/GPU/Kaggle/submission/leaderboard claim is made.
"""
from __future__ import annotations

import argparse, json
from collections import Counter
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_unique_component_motion_audit_140 as motion

RUNG=144
Grid=list[list[int]]
ACTION_EXPECTED={'UP':(-3,0),'DOWN':(3,0),'LEFT':(0,-3),'RIGHT':(0,3)}


def encode(before:Grid,after:Grid,action:str)->dict[str,Any]:
    if not base.same_shape(before,after): return {'eligible':False,'reason':'shape_changed'}
    diff={(r,c) for r in range(len(before)) for c in range(len(before[0])) if before[r][c]!=after[r][c]}
    if not diff:return {'eligible':False,'reason':'identity'}
    expected=ACTION_EXPECTED.get(action.upper())
    if expected is None:return {'eligible':False,'reason':'non_directional'}
    matches=motion.unique_matches(before,after)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    if not moved:return {'eligible':False,'reason':'no_motion_core'}
    deltas=Counter((m[2],m[3]) for m in moved)
    if len(deltas)!=1:return {'eligible':False,'reason':'mixed_motion'}
    delta=next(iter(deltas))
    if delta!=expected:return {'eligible':False,'reason':'non_action_aligned'}
    src=set();dst=set()
    for x,y,dr,dc in moved:
        src.update(x.cells);dst.update(y.cells)
    footprint=src|dst
    residual=sorted(diff-footprint)
    if not residual:return {'eligible':False,'reason':'zero_residual'}
    sr0=min(r for r,c in src);sc0=min(c for r,c in src)
    dr0=min(r for r,c in dst);dc0=min(c for r,c in dst)
    absolute=[(r,c,before[r][c],after[r][c]) for r,c in residual]
    src_rel=[(r-sr0,c-sc0,before[r][c],after[r][c]) for r,c in residual]
    dst_rel=[(r-dr0,c-dc0,before[r][c],after[r][c]) for r,c in residual]
    # shape-only masks isolate geometric recurrence from literal value changes.
    absolute_mask=[(r,c) for r,c in residual]
    src_rel_mask=[(r-sr0,c-sc0) for r,c in residual]
    dst_rel_mask=[(r-dr0,c-dc0) for r,c in residual]
    return {
      'eligible':True,'action':action,'residual_count':len(residual),
      'absolute_mask':base.stable(absolute_mask),'absolute_transition':base.stable(absolute),
      'src_rel_mask':base.stable(src_rel_mask),'src_rel_transition':base.stable(src_rel),
      'dst_rel_mask':base.stable(dst_rel_mask),'dst_rel_transition':base.stable(dst_rel),
    }


def trace_audit(events:list[dict[str,Any]])->dict[str,Any]:
    keys=('absolute_mask','absolute_transition','src_rel_mask','src_rel_transition','dst_rel_mask','dst_rel_transition')
    seen={k:Counter() for k in keys};reuse=Counter();eligible=0;reasons=Counter()
    pre=events[0]
    for e in events[1:]:
        if e.get('type')!='action':pre=e;continue
        r=encode(base.as_grid(pre['board']),base.as_grid(e['board']),base.action_name(e));pre=e
        if not r['eligible']:reasons[r['reason']]+=1;continue
        eligible+=1
        for k in keys:
            reuse[k]+=seen[k][r[k]]>0
        for k in keys:seen[k][r[k]]+=1
    return {
      'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),
      'reuse_counts':dict(reuse),
      'reuse_fraction':{k:round(reuse[k]/eligible,6) if eligible else 0 for k in keys},
      'unique_signatures':{k:len(seen[k]) for k in keys},
    }


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    keys=('absolute_mask','absolute_transition','src_rel_mask','src_rel_transition','dst_rel_mask','dst_rel_transition')
    eligible=sum(p['eligible_transitions'] for p in parts);reuse=Counter();reasons=Counter()
    for p in parts:
        reuse.update(p['reuse_counts']);reasons.update(p['ineligible_reasons'])
    frac={k:round(reuse[k]/eligible,6) if eligible else 0 for k in keys}
    best=max(('absolute_mask','src_rel_mask','dst_rel_mask'),key=lambda k:frac[k]) if eligible else None
    return {
      'trace_count':len(parts),'eligible_transitions':eligible,'ineligible_reasons':dict(sorted(reasons.items())),
      'reuse_counts':dict(reuse),'reuse_fraction':frac,'best_mask_coordinate_system':best,
      'mover_relative_mask_improvement_over_absolute':round(max(frac['src_rel_mask'],frac['dst_rel_mask'])-frac['absolute_mask'],6) if eligible else 0,
      'per_trace_reuse_fraction':[p['reuse_fraction'] for p in parts],
    }


def run(paths:list[Path])->dict[str,Any]:
    parts=[];traces=[]
    for p in paths:
        a=trace_audit(base.load_events(p));parts.append(a);traces.append({'path':str(p),'audit':a})
    agg=aggregate(parts)
    return {
      'schema':'deus/arc3-public-residual-mover-relative-audit/1','rung':RUNG,
      'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_COORDINATE_SYSTEM_DIAGNOSTIC',
      'representation_change_from_rung143':{'changed':True,'change':'replace absolute residual coordinates with source- and destination-mover-bbox-relative coordinates and compare prefix recurrence'},
      'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
      'traces':traces,'aggregate':agg,'diagnostic_gate':'RESIDUAL_COORDINATE_SYSTEM_COMPARED',
      'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
      'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'current_outcome_used_for_correspondence_and_residual':True,'recurrence_lookup_is_prefix_only':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False}
    }


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path);args=ap.parse_args()
    if not args.input:raise SystemExit('at least one --input is required')
    d=run(args.input);text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return 0
if __name__=='__main__':raise SystemExit(main())
