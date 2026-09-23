#!/usr/bin/env python3
"""R281: lp85 renderer-collision mechanism diagnostic after R280 NO_SIGNAL.

R280 proved that the frozen R279 representation key does not directly map to an
exact next frame with >=2 raw prestate support on p0-p4. R281 changes no solver
thresholds and reads no new heldout traces. It inspects ONLY p0-p4 fit
collisions to identify the discriminating mechanism:

- raw exact-frame identity,
- action-canonical raw frame,
- action-canonical UI-masked frame,
- translation-normalized action-canonical raw pixel delta,
- translation-normalized action-canonical UI-masked pixel delta.

This tells the next renderer whether loss is dominated by action orientation,
translation, HUD/UI, or deeper state aliasing.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG=281
TARGET_GAME="lp85-305b61c3"
MODE="canon_regions_ui"


def digest(x:Any)->str: return r246.digest(x)


def canon_raw(board,action): return r275.canon_board(board,action,use_ui_mask=False)
def canon_ui(board,action): return r275.canon_board(board,action,use_ui_mask=True)


def norm_delta(before,after):
    if len(before)!=len(after) or len(before[0])!=len(after[0]): return ("SHAPE_CHANGE",)
    ds=[]
    for y in range(len(before)):
        for x in range(len(before[0])):
            if before[y][x]!=after[y][x]: ds.append((y,x,int(before[y][x]),int(after[y][x])))
    if not ds: return ("NO_CHANGE",)
    y0=min(y for y,_,_,_ in ds); x0=min(x for _,x,_,_ in ds)
    y1=max(y for y,_,_,_ in ds); x1=max(x for _,x,_,_ in ds)
    return (y1-y0+1,x1-x0+1,tuple(sorted((y-y0,x-x0,b,a) for y,x,b,a in ds)))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if {r246.game_id(p) for p in ps}!={TARGET_GAME} or [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit('exact lp85 p0-p4 required')
    rows=r278.annotated_rows(ps)
    groups=defaultdict(list)
    for r in rows: groups[r278.before_key(r,MODE)].append(r)
    repeated=[]; totals=Counter()
    for k,rs in groups.items():
        prestates={digest(r['before']) for r in rs}
        if len(prestates)<2: continue
        metrics={
          'occurrences':len(rs),'distinct_prestates':len(prestates),
          'raw_after':len({digest(r['after']) for r in rs}),
          'canon_raw_after':len({digest(canon_raw(r['after'],r['action'])) for r in rs}),
          'canon_ui_after':len({digest(canon_ui(r['after'],r['action'])) for r in rs}),
          'norm_canon_raw_delta':len({digest(norm_delta(canon_raw(r['before'],r['action']),canon_raw(r['after'],r['action']))) for r in rs}),
          'norm_canon_ui_delta':len({digest(norm_delta(canon_ui(r['before'],r['action']),canon_ui(r['after'],r['action']))) for r in rs}),
        }
        for name in ('raw_after','canon_raw_after','canon_ui_after','norm_canon_raw_delta','norm_canon_ui_delta'):
            if metrics[name]==1: totals[name+'_deterministic_keys']+=1
        totals['repeated_keys']+=1; totals['repeated_observations']+=len(rs)
        if metrics['raw_after']>1 and metrics['canon_ui_after']==1:
            cls='FRAME_COLLISION_REMOVED_BY_ACTION_CANON_UI'
        elif metrics['norm_canon_raw_delta']==1:
            cls='RAW_FRAME_COLLISION_BUT_TRANSLATION_NORMALIZED_DELTA_DETERMINISTIC'
        elif metrics['norm_canon_ui_delta']==1:
            cls='UI_OR_HUD_BREAKS_RAW_DELTA_BUT_MASKED_DELTA_DETERMINISTIC'
        elif metrics['canon_ui_after']>1:
            cls='REPRESENTATION_ALIAS_REMAINS_AFTER_CANON_UI'
        else:
            cls='OTHER'
        totals['class_'+cls]+=1
        repeated.append({'key_digest':digest(k),'classification':cls,**metrics})
    if totals['repeated_keys']==0:
        verdict='NO_REPEATED_PRESTATE_SUPPORT'
    elif totals['norm_canon_raw_delta_deterministic_keys']>0:
        verdict='TRY_TRANSLATION_NORMALIZED_CANON_RAW_DELTA'
    elif totals['norm_canon_ui_delta_deterministic_keys']>0:
        verdict='TRY_SPLIT_WORLD_DELTA_PLUS_UI_MECHANISM'
    else:
        verdict='DEEPER_STATE_ALIASING'
    out={'schema':'deus/arc3-r281-lp85-renderer-collision-diagnostic/1','rung':RUNG,
         'game':TARGET_GAME,'mode':MODE,
         'protocol':{'fit_collision_diagnostic':'p0-p4 only','p5_p19_staged_or_read':False,'no_threshold_retune':True},
         'summary':dict(totals),'repeated_keys':repeated,'verdict':verdict,
         'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p5_p19_read':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r281':False}}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'summary':dict(totals)},sort_keys=True))
if __name__=='__main__': main()
