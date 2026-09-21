#!/usr/bin/env python3
"""Rung 141: quantify motion-core coverage and residual effect topology.

Rung 140 found that most nonidentity transitions contain uniquely trackable
components and often a shared action-aligned displacement, yet pure component
motion never reconstructs the full frame. This diagnostic measures how much of
the observed pixel delta lies inside the source/destination footprint of those
movers, and characterizes what remains outside that footprint.

Outcome is used only for retrospective public-trace diagnostics; no prediction or
solver/model/GPU/Kaggle claim is made.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict, deque
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base
import public_unique_component_motion_audit_140 as motion

RUNG=141
Grid=list[list[int]]

ACTION_EXPECTED={'UP':(-3,0),'DOWN':(3,0),'LEFT':(0,-3),'RIGHT':(0,3)}


def comps(cells:set[tuple[int,int]])->int:
    rem=set(cells); n=0
    while rem:
        n+=1; start=rem.pop(); q=deque([start])
        while q:
            r,c=q.popleft()
            for nb in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if nb in rem: rem.remove(nb); q.append(nb)
    return n


def analyze(before:Grid,after:Grid,action:str)->dict[str,Any]:
    if not base.same_shape(before,after): return {'same_shape':False,'action':action}
    diff={(r,c) for r in range(len(before)) for c in range(len(before[0])) if before[r][c]!=after[r][c]}
    ms=motion.unique_matches(before,after)
    moved=[m for m in ms if (m[2],m[3])!=(0,0)]
    deltas=Counter((m[2],m[3]) for m in moved)
    footprint=set()
    for x,y,dr,dc in moved:
        footprint.update(x.cells); footprint.update(y.cells)
    covered=diff & footprint
    residual=diff-footprint
    dominant=deltas.most_common(1)[0] if deltas else None
    expected=ACTION_EXPECTED.get(action.upper())
    return {
        'same_shape':True,'action':action,'identity':not diff,
        'changed_cells':len(diff),'moved_unique_components':len(moved),
        'all_movers_share_delta':len(deltas)==1 and bool(moved),
        'dominant_delta':list(dominant[0]) if dominant else None,
        'dominant_delta_support':dominant[1] if dominant else 0,
        'expected_action_delta':list(expected) if expected else None,
        'dominant_delta_action_aligned':bool(dominant and expected and dominant[0]==expected),
        'motion_footprint_cells':len(footprint),
        'changed_cells_in_motion_footprint':len(covered),
        'motion_coverage_of_changed':round(len(covered)/len(diff),6) if diff else None,
        'residual_changed_cells':len(residual),
        'residual_fraction_of_changed':round(len(residual)/len(diff),6) if diff else None,
        'residual_components':comps(residual),
    }


def bucket(x:float)->str:
    if x>=0.95:return '>=95%'
    if x>=0.80:return '80-95%'
    if x>=0.50:return '50-80%'
    if x>0:return '0-50%'
    return '0%'


def summarize(rows:list[dict[str,Any]])->dict[str,Any]:
    same=[r for r in rows if r.get('same_shape')]; non=[r for r in same if not r['identity']]
    mover=[r for r in non if r['moved_unique_components']>0]
    shared=[r for r in mover if r['all_movers_share_delta']]
    aligned=[r for r in shared if r['dominant_delta_action_aligned']]
    cov=[r['motion_coverage_of_changed'] for r in mover]
    res=[r['residual_changed_cells'] for r in mover]
    rescomp=[r['residual_components'] for r in mover]
    by_action={}; groups=defaultdict(list)
    for r in non: groups[r['action']].append(r)
    for a,rs in sorted(groups.items()):
        mr=[r for r in rs if r['moved_unique_components']>0]
        sr=[r for r in mr if r['all_movers_share_delta']]
        by_action[a]={
            'nonidentity':len(rs),'with_motion_core':len(mr),'shared_delta':len(sr),
            'action_aligned_shared_delta':sum(r['dominant_delta_action_aligned'] for r in sr),
            'motion_coverage_median':median([r['motion_coverage_of_changed'] for r in mr]) if mr else None,
            'residual_changed_cells_median':median([r['residual_changed_cells'] for r in mr]) if mr else None,
            'residual_components_median':median([r['residual_components'] for r in mr]) if mr else None,
        }
    return {
        'transitions':len(rows),'identity':len(same)-len(non),'nonidentity':len(non),
        'nonidentity_with_motion_core':len(mover),
        'shared_delta_motion_core':len(shared),
        'action_aligned_shared_delta_motion_core':len(aligned),
        'motion_coverage_median':median(cov) if cov else None,
        'motion_coverage_buckets':dict(sorted(Counter(bucket(x) for x in cov).items())),
        'residual_changed_cells_median':median(res) if res else None,
        'residual_components_median':median(rescomp) if rescomp else None,
        'zero_residual':sum(x==0 for x in res),
        'actions':by_action,
    }


def run(paths:list[Path])->dict[str,Any]:
    rows=[]; traces=[]
    for p in paths:
        events=base.load_events(p); pre=events[0]; local=[]
        for e in events[1:]:
            if e.get('type')!='action': pre=e; continue
            r=analyze(base.as_grid(pre['board']),base.as_grid(e['board']),base.action_name(e)); rows.append(r); local.append(r); pre=e
        traces.append({'path':str(p),'summary':summarize(local)})
    return {
        'schema':'deus/arc3-public-motion-core-residual-audit/1','rung':RUNG,
        'execution_class':'CPU_PUBLIC_TRACE_MOTION_CORE_RESIDUAL_DIAGNOSTIC',
        'representation_change_from_rung140':{'changed':True,'change':'retain conservative unique-component motion as a causal core and explicitly quantify the unexplained residual rather than requiring pure-motion exact reconstruction'},
        'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
        'traces':traces,'aggregate':summarize(rows),'diagnostic_gate':'MOTION_CORE_RESIDUAL_CHARACTERIZED',
        'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
        'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'outcome_used_retrospectively':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False},
    }


def self_test()->dict[str,Any]:
    a=[[0]*10 for _ in range(7)]; b=[row[:] for row in a]
    a[1][1]=1; b[1][2]=1
    a[5][8]=3; b[5][8]=3
    # residual independent update
    a[6][0]=4; b[6][0]=5
    r=analyze(a,b,'RIGHT')
    inv={'mover_found':r['moved_unique_components']>=1,'motion_covers_move':r['changed_cells_in_motion_footprint']>=2,'residual_detected':r['residual_changed_cells']>=1}
    return {'schema':'deus/arc3-public-motion-core-residual-selftest/1','rung':RUNG,'passed':all(inv.values()),'invariants':inv,'record':r}


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path); ap.add_argument('--self-test',action='store_true'); args=ap.parse_args()
    if args.self_test:d=self_test();code=0 if d['passed'] else 2
    else:
        if not args.input: raise SystemExit('at least one --input is required')
        d=run(args.input);code=0
    text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='');return code
if __name__=='__main__':raise SystemExit(main())
