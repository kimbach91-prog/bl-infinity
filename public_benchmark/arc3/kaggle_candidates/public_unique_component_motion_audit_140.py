#!/usr/bin/env python3
"""Rung 140: conservative multi-component motion audit on pinned public traces.

Rung 139 showed sparse but multi-region effects and zero strict single-component
translations. This diagnostic asks whether those effects are actually a composite
sprite/object movement: uniquely identifiable same-color connected components
whose shapes persist while their positions change.

Only components whose (literal color, normalized shape) signature occurs exactly
once both before and after are tracked. A transition is reconstructable only when
moving all such displaced unique components simultaneously reproduces the exact
after-frame. Ambiguous repeated components are ignored, never guessed.

Diagnostic only: no hidden prediction, model/GPU/Kaggle execution or score claim.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base
import public_object_role_transition_prequential_138 as objmod

RUNG=140
Grid=list[list[int]]


def sig(o: objmod.Obj) -> str:
    return base.stable({'color':o.color,'shape':o.shape})


def unique_matches(before: Grid, after: Grid) -> list[tuple[objmod.Obj,objmod.Obj,int,int]]:
    bo=objmod.objects(before); ao=objmod.objects(after)
    bg=defaultdict(list); ag=defaultdict(list)
    for o in bo: bg[sig(o)].append(o)
    for o in ao: ag[sig(o)].append(o)
    out=[]
    for k, xs in bg.items():
        ys=ag.get(k,[])
        if len(xs)==1 and len(ys)==1:
            x,y=xs[0],ys[0]
            out.append((x,y,y.r0-x.r0,y.c0-x.c0))
    return out


def reconstruct(before: Grid, matches: list[tuple[objmod.Obj,objmod.Obj,int,int]]) -> Grid | None:
    bg=objmod.background_color(before)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    if not moved: return [row[:] for row in before]
    h,w=len(before),len(before[0])
    src=set(); placements=[]
    for x,y,dr,dc in moved:
        cells={(r+dr,c+dc) for r,c in x.cells}
        if any(not(0<=r<h and 0<=c<w) for r,c in cells): return None
        src.update(x.cells); placements.append((x.color,cells))
    # Destination collision among moved components or with unmatched content.
    all_dst=set()
    for _,cells in placements:
        if all_dst & cells: return None
        all_dst |= cells
    for r,c in all_dst-src:
        if before[r][c]!=bg: return None
    out=[row[:] for row in before]
    for r,c in src-all_dst: out[r][c]=bg
    for color,cells in placements:
        for r,c in cells: out[r][c]=color
    return out


def analyze(before: Grid, after: Grid, action: str) -> dict[str,Any]:
    if not base.same_shape(before,after): return {'same_shape':False,'action':action}
    matches=unique_matches(before,after)
    moved=[m for m in matches if (m[2],m[3])!=(0,0)]
    deltas=Counter((m[2],m[3]) for m in moved)
    pred=reconstruct(before,matches)
    return {
        'same_shape':True,
        'action':action,
        'identity':before==after,
        'unique_trackable_components':len(matches),
        'moved_unique_components':len(moved),
        'unique_motion_deltas':len(deltas),
        'all_movers_share_delta':len(deltas)==1 and bool(moved),
        'dominant_delta':list(deltas.most_common(1)[0][0]) if deltas else None,
        'dominant_delta_support':deltas.most_common(1)[0][1] if deltas else 0,
        'exact_reconstructable_from_unique_component_motion':pred==after and bool(moved),
    }


def summarize(rows:list[dict[str,Any]])->dict[str,Any]:
    same=[r for r in rows if r.get('same_shape')]
    non=[r for r in same if not r['identity']]
    moved=[r for r in non if r['moved_unique_components']>0]
    recon=[r for r in non if r['exact_reconstructable_from_unique_component_motion']]
    shared=[r for r in moved if r['all_movers_share_delta']]
    delta_hist=Counter(tuple(r['dominant_delta']) for r in shared if r['dominant_delta'] is not None)
    by_action={}
    groups=defaultdict(list)
    for r in non: groups[r['action']].append(r)
    for a,rs in sorted(groups.items()):
        by_action[a]={
            'nonidentity':len(rs),
            'with_unique_mover':sum(r['moved_unique_components']>0 for r in rs),
            'shared_delta':sum(r['all_movers_share_delta'] for r in rs),
            'exact_reconstructable':sum(r['exact_reconstructable_from_unique_component_motion'] for r in rs),
            'moved_unique_components_median':median([r['moved_unique_components'] for r in rs]) if rs else None,
        }
    return {
        'transitions':len(rows),
        'same_shape':len(same),
        'identity':len(same)-len(non),
        'nonidentity':len(non),
        'nonidentity_with_unique_mover':len(moved),
        'nonidentity_with_unique_mover_fraction':round(len(moved)/len(non),6) if non else 0,
        'nonidentity_all_movers_share_delta':len(shared),
        'nonidentity_all_movers_share_delta_fraction':round(len(shared)/len(non),6) if non else 0,
        'nonidentity_exact_reconstructable':len(recon),
        'nonidentity_exact_reconstructable_fraction':round(len(recon)/len(non),6) if non else 0,
        'dominant_delta_histogram':{str(k):v for k,v in delta_hist.most_common(12)},
        'actions':by_action,
    }


def run(paths:list[Path])->dict[str,Any]:
    rows=[]; traces=[]
    for p in paths:
        events=base.load_events(p); pre=events[0]; local=[]
        for e in events[1:]:
            if e.get('type')!='action': pre=e; continue
            r=analyze(base.as_grid(pre['board']),base.as_grid(e['board']),base.action_name(e))
            rows.append(r); local.append(r); pre=e
        traces.append({'path':str(p),'summary':summarize(local)})
    agg=summarize(rows)
    return {
        'schema':'deus/arc3-public-unique-component-motion-audit/1','rung':RUNG,
        'execution_class':'CPU_PUBLIC_TRACE_UNIQUE_COMPONENT_MOTION_DIAGNOSTIC',
        'representation_change_from_rung139':{
            'changed':True,
            'change':'test conservative persistent multi-component motion rather than single-object translation or raw delta topology',
            'ambiguous_repeated_component_policy':'IGNORE_NOT_GUESS',
            'exact_reconstruction_required':True,
        },
        'source_grounding':{'public_trace_repo':base.TUFA_REPO,'public_trace_commit':base.TUFA_COMMIT,'clean_room_implementation':True},
        'traces':traces,'aggregate':agg,
        'diagnostic_gate':'UNIQUE_COMPONENT_MOTION_CHARACTERIZED',
        'promotion':{'candidate_model_promotion':False,'kaggle_packaging':False},
        'truth':{'public_trace_only':True,'source_assisted_replay':True,'diagnostic_only':True,'independent_generalization_claim':False,'solver_behavior_gain_claim':False,'model_execution':False,'gpu_execution':False,'kaggle_execution':False,'kaggle_submission_attempted':False,'submission_quota_spent':False,'leaderboard_score_claim':False,'owner_score_claim':False},
    }


def self_test()->dict[str,Any]:
    a=[[0]*10 for _ in range(7)]; b=[row[:] for row in a]
    # two unique persistent components move RIGHT by one, a third is stationary
    a[1][1]=1; b[1][2]=1
    for r,c in ((3,3),(3,4)): a[r][c]=2
    for r,c in ((3,4),(3,5)): b[r][c]=2
    a[5][8]=3; b[5][8]=3
    r=analyze(a,b,'RIGHT')
    inv={'two_movers':r['moved_unique_components']==2,'shared_delta':r['all_movers_share_delta'] is True,'exact_reconstructable':r['exact_reconstructable_from_unique_component_motion'] is True}
    return {'schema':'deus/arc3-public-unique-component-motion-selftest/1','rung':RUNG,'passed':all(inv.values()),'invariants':inv,'record':r}


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path); ap.add_argument('--self-test',action='store_true'); args=ap.parse_args()
    if args.self_test: d=self_test(); code=0 if d['passed'] else 2
    else:
        if not args.input: raise SystemExit('at least one --input is required')
        d=run(args.input); code=0
    text=json.dumps(d,indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(text,encoding='utf-8')
    print(text,end=''); return code
if __name__=='__main__': raise SystemExit(main())
