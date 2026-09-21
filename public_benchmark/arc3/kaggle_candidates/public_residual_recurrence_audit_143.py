#!/usr/bin/env python3
"""Rung 143: residual recurrence / fixed-coordinate diagnostic.

Rung 141 found an action-aligned ±3 multi-component motion core explaining a
median 93.578% of changed pixels, with a small mandatory residual. This rung
uses the same conservative retrospective correspondence to isolate that residual
and asks whether it recurs at stable absolute coordinates (HUD/timer-like), or is
mostly state-local / nonstationary.

This is outcome-assisted public-trace diagnosis only. It does not use residual
outcomes to predict the current transition and makes no generalization, model,
GPU, Kaggle, submission, leaderboard, or award claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base
import public_unique_component_motion_audit_140 as motion

RUNG=143
Grid=list[list[int]]
ACTION_EXPECTED={'UP':(-3,0),'DOWN':(3,0),'LEFT':(0,-3),'RIGHT':(0,3)}


def isolate(before:Grid, after:Grid, action:str)->dict[str,Any]:
    if not base.same_shape(before,after): return {'eligible':False,'reason':'shape_changed','action':action}
    diff={(r,c) for r in range(len(before)) for c in range(len(before[0])) if before[r][c]!=after[r][c]}
    if not diff: return {'eligible':False,'reason':'identity','action':action}
    expected=ACTION_EXPECTED.get(action.upper())
    if expected is None: return {'eligible':False,'reason':'non_directional','action':action}
    matches=motion.unique_matches(before,after)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    if not moved: return {'eligible':False,'reason':'no_motion_core','action':action}
    deltas=Counter((m[2],m[3]) for m in moved)
    if len(deltas)!=1: return {'eligible':False,'reason':'mixed_motion','action':action}
    delta=next(iter(deltas))
    if delta!=expected: return {'eligible':False,'reason':'non_action_aligned','action':action}
    footprint=set()
    for x,y,dr,dc in moved:
        footprint.update(x.cells); footprint.update(y.cells)
    residual=sorted(diff-footprint)
    h,w=len(before),len(before[0])
    cells=[]
    for r,c in residual:
        cells.append({
            'r':r,'c':c,'before':before[r][c],'after':after[r][c],
            'edge_r':min(r,h-1-r),'edge_c':min(c,w-1-c),
        })
    mask_sig=base.stable([(x['r'],x['c']) for x in cells])
    transition_sig=base.stable([(x['r'],x['c'],x['before'],x['after']) for x in cells])
    return {
        'eligible':True,'action':action,'h':h,'w':w,'motion_delta':list(delta),
        'changed_cells':len(diff),'motion_footprint_changed':len(diff & footprint),
        'residual_cells':cells,'residual_count':len(cells),
        'mask_signature':mask_sig,'transition_signature':transition_sig,
    }


def trace_audit(events:list[dict[str,Any]])->dict[str,Any]:
    pre=events[0]
    coord_seen=Counter(); mask_seen=Counter(); trans_seen=Counter()
    eligible=[]
    prequential={
        'eligible':0,'residual_cells':0,'residual_cells_at_previously_seen_coord':0,
        'exact_mask_seen_before':0,'exact_transition_seen_before':0,
    }
    reasons=Counter()
    for e in events[1:]:
        if e.get('type')!='action': pre=e; continue
        r=isolate(base.as_grid(pre['board']),base.as_grid(e['board']),base.action_name(e))
        if not r['eligible']:
            reasons[r['reason']]+=1; pre=e; continue
        eligible.append(r); prequential['eligible']+=1
        coords=[(x['r'],x['c']) for x in r['residual_cells']]
        prequential['residual_cells']+=len(coords)
        prequential['residual_cells_at_previously_seen_coord']+=sum(coord_seen[p]>0 for p in coords)
        prequential['exact_mask_seen_before']+=mask_seen[r['mask_signature']]>0
        prequential['exact_transition_seen_before']+=trans_seen[r['transition_signature']]>0
        for p in coords: coord_seen[p]+=1
        mask_seen[r['mask_signature']]+=1
        trans_seen[r['transition_signature']]+=1
        pre=e
    total_cells=prequential['residual_cells']
    coord_reuse=prequential['residual_cells_at_previously_seen_coord']/total_cells if total_cells else 0
    top_coords=coord_seen.most_common(20)
    top10_mass=sum(v for _,v in top_coords[:10])/total_cells if total_cells else 0
    edge_cells=sum(1 for r in eligible for x in r['residual_cells'] if x['edge_r']<=1 or x['edge_c']<=1)
    return {
        'eligible_transitions':len(eligible),
        'ineligible_reasons':dict(sorted(reasons.items())),
        'residual_count_median':median([r['residual_count'] for r in eligible]) if eligible else None,
        'residual_cells_total':total_cells,
        'unique_absolute_residual_coords':len(coord_seen),
        'prequential_coord_reuse_fraction':round(coord_reuse,6),
        'prequential_exact_mask_reuse_fraction':round(prequential['exact_mask_seen_before']/len(eligible),6) if eligible else 0,
        'prequential_exact_transition_reuse_fraction':round(prequential['exact_transition_seen_before']/len(eligible),6) if eligible else 0,
        'top10_absolute_coord_mass_fraction':round(top10_mass,6),
        'outer_two_cell_band_fraction':round(edge_cells/total_cells,6) if total_cells else 0,
        'unique_mask_signatures':len(mask_seen),
        'unique_transition_signatures':len(trans_seen),
        'top_absolute_coords':[{'r':p[0],'c':p[1],'count':n} for p,n in top_coords],
        'prequential':prequential,
    }


def aggregate(parts:list[dict[str,Any]])->dict[str,Any]:
    eligible=sum(p['eligible_transitions'] for p in parts)
    cells=sum(p['residual_cells_total'] for p in parts)
    reused=sum(p['prequential']['residual_cells_at_previously_seen_coord'] for p in parts)
    mask_reused=sum(p['prequential']['exact_mask_seen_before'] for p in parts)
    trans_reused=sum(p['prequential']['exact_transition_seen_before'] for p in parts)
    reasons=Counter()
    for p in parts: reasons.update(p['ineligible_reasons'])
    return {
        'trace_count':len(parts),'eligible_transitions':eligible,
        'residual_cells_total':cells,
        'prequential_coord_reuse_fraction':round(reused/cells,6) if cells else 0,
        'prequential_exact_mask_reuse_fraction':round(mask_reused/eligible,6) if eligible else 0,
        'prequential_exact_transition_reuse_fraction':round(trans_reused/eligible,6) if eligible else 0,
        'ineligible_reasons':dict(sorted(reasons.items())),
        'per_trace_residual_count_median':[p['residual_count_median'] for p in parts],
        'per_trace_top10_coord_mass_fraction':[p['top10_absolute_coord_mass_fraction'] for p in parts],
        'per_trace_outer_two_cell_band_fraction':[p['outer_two_cell_band_fraction'] for p in parts],
        'per_trace_unique_absolute_residual_coords':[p['unique_absolute_residual_coords'] for p in parts],
    }


def run(paths:list[Path])->dict[str,Any]:
    traces=[]; parts=[]
    for p in paths:
        a=trace_audit(base.load_events(p)); parts.append(a); traces.append({'path':str(p),'audit':a})
    agg=aggregate(parts)
    return {
        'schema':'deus/arc3-public-residual-recurrence-audit/1','rung':RUNG,
        'execution_class':'CPU_PUBLIC_TRACE_RESIDUAL_RECURRENCE_DIAGNOSTIC',
        'representation_change_from_rung141':{
            'changed':True,
            'change':'isolate only residual outside verified action-aligned motion footprints and measure prefix recurrence in absolute coordinates/masks/transitions',
            'regime':'directional_action_aligned_shared_motion_only',
        },
        'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
        'traces':traces,'aggregate':agg,
        'diagnostic_gate':'RESIDUAL_RECURRENCE_CHARACTERIZED',
        'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
        'truth':{
            'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,
            'current_outcome_used_to_isolate_current_residual':True,
            'prequential_recurrence_counts_use_only_prior_seen_sets':True,
            'independent_generalization_claim':False,'solver_behavior_gain_claim':False,
            'model_execution':False,'gpu_execution':False,'kaggle_execution':False,
            'kaggle_submission_attempted':False,'submission_quota_spent':False,
            'leaderboard_score_claim':False,'owner_score_claim':False,
        }
    }


def self_test()->dict[str,Any]:
    # Basic determinism check on identity rejection; full public gate carries the
    # scientific result and no synthetic benchmark is used for promotion.
    a=[[0]*8 for _ in range(8)]
    r=isolate(a,[row[:] for row in a],'RIGHT')
    inv={'identity_rejected':r['eligible'] is False and r['reason']=='identity'}
    return {'schema':'deus/arc3-public-residual-recurrence-selftest/1','rung':RUNG,'passed':all(inv.values()),'invariants':inv}


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path); ap.add_argument('--self-test',action='store_true'); args=ap.parse_args()
    if args.self_test:d=self_test();code=0 if d['passed'] else 2
    else:
        if not args.input: raise SystemExit('at least one --input is required')
        d=run(args.input);code=0
    text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(text,encoding='utf-8')
    print(text,end=''); return code
if __name__=='__main__': raise SystemExit(main())
