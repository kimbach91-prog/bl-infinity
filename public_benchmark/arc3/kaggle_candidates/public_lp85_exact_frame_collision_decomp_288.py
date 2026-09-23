#!/usr/bin/env python3
"""R288: decompose lp85 exact-frame alias collisions after R287 NO_SIGNAL.

This is a causal diagnostic, not a predictor. It asks whether the exact-frame
ambiguity left by the R279 canon_regions_ui state is predominantly static UI
(border/timer) or persists in the masked world interior.

Only p0-p4 public traces are read. No p5-p19, no model selection, no Kaggle use.
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

RUNG=288
TARGET_GAME='lp85-305b61c3'
MODE='canon_regions_ui'


def craw(board, action):
    return r275.canon_board(board, action, use_ui_mask=False)


def cmasked(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def diff_partition(a,b):
    # a,b are already action-canonical and therefore shape-aligned.
    h=min(len(a),len(b)); w=min(len(a[0]) if a else 0,len(b[0]) if b else 0)
    total=ui=world=0
    for r in range(h):
        for c in range(w):
            if a[r][c]==b[r][c]:
                continue
            total+=1
            # Static mask in canonical coordinates is still the outer ring + row1.
            is_ui = c==0 or c==w-1 or r in {0,1,h-1}
            if is_ui: ui+=1
            else: world+=1
    return total,ui,world


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(5)): raise SystemExit(f'exact p0-p4 required, got {nums}')
    rows=r278.annotated_rows(ps)
    rep_tab, rep_fit=r278.fit(rows,MODE)

    grouped=defaultdict(list)
    for rr in rows:
        k=r278.before_key(rr,MODE)
        if k not in rep_tab:
            continue
        grouped[k].append(rr)

    agg=Counter(); details=[]
    for k,rs in grouped.items():
        raw_by={r246.digest(craw(x['after'],x['action'])):craw(x['after'],x['action']) for x in rs}
        masked_by={r246.digest(cmasked(x['after'],x['action'])):cmasked(x['after'],x['action']) for x in rs}
        agg['r279_deterministic_keys']+=1
        if len(raw_by)<=1:
            agg['raw_exact_unique_keys']+=1
            continue
        agg['raw_exact_ambiguous_keys']+=1
        if len(masked_by)==1: agg['ambiguity_collapses_after_ui_mask']+=1
        else: agg['ambiguity_persists_after_ui_mask']+=1
        boards=list(raw_by.values())
        dt=du=dw=0; pairs=0
        for i in range(len(boards)):
            for j in range(i+1,len(boards)):
                t,u,w=diff_partition(boards[i],boards[j]); dt+=t; du+=u; dw+=w; pairs+=1
        agg['pairwise_diff_pixels']+=dt; agg['pairwise_ui_diff_pixels']+=du; agg['pairwise_world_diff_pixels']+=dw
        if len(details)<30:
            details.append({'observations':len(rs),'raw_outcomes':len(raw_by),'masked_outcomes':len(masked_by),'pairs':pairs,'diff_pixels':dt,'ui_diff_pixels':du,'world_diff_pixels':dw})

    dt=agg['pairwise_diff_pixels']
    ui_share=round(agg['pairwise_ui_diff_pixels']/dt,6) if dt else None
    world_share=round(agg['pairwise_world_diff_pixels']/dt,6) if dt else None
    if agg['raw_exact_ambiguous_keys']==0:
        verdict='NO_COLLISION'
    elif agg['ambiguity_persists_after_ui_mask']==0:
        verdict='UI_ONLY_COLLISION'
    elif world_share is not None and world_share>=0.5:
        verdict='WORLD_DOMINANT_COLLISION'
    else:
        verdict='MIXED_COLLISION'
    out={'schema':'deus/arc3-r288-lp85-exact-frame-collision-decomp/1','rung':RUNG,'game':TARGET_GAME,'mode':MODE,'protocol':{'data':'p0-p4 only','p5_p19_read':False,'predictor':False,'threshold_retune':False},'r279_fit':rep_fit,'aggregate':dict(agg)|{'ui_diff_share':ui_share,'world_diff_share':world_share},'examples':details,'verdict':verdict,'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p5_p19_read':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'r279_fit':rep_fit,'aggregate':out['aggregate']},sort_keys=True))

if __name__=='__main__': main()
