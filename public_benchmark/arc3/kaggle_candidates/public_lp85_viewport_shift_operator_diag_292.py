#!/usr/bin/env python3
"""R292: lp85 action-aligned viewport-shift operator diagnostic.

Upgrade patch after three state-identity falsifiers:
- R289 modal multiresolution: NO_SIGNAL.
- R290 exact row/column projection: NO_SIGNAL and over-split recurrence.
- R291 coarse occupancy residual: NO_SIGNAL and left all 15 repeat-supported
  exact-frame aliases unchanged.

The failure pattern says the next hypothesis should model the *mechanism of
transition* rather than add another static state fingerprint. R292 tests the
specific viewport-transform mechanism named by the ARC repair law: after
rotating directional actions into an UP-aligned frame and masking static UI,
can the next world be explained by a small global image shift?

The shift family and range are fixed before diagnostic data: dx,dy in [-8,8].
p0-p4 fit/causal analysis -> p5-p9 diagnostic; p10-p19 forbidden. The rung may
report a partial mechanistic signal from Hamming reduction, but only exact
masked-world predictions with zero validation errors qualify as an exact gain.
No solver/Kaggle promotion occurs here.
"""
from __future__ import annotations

import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG=292
TARGET_GAME='lp85-305b61c3'
BASE_MODE='canon_regions_ui'
SHIFT_MIN=-8
SHIFT_MAX=8
MIN_DISTINCT_PRESTATES=2


def world(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def digest_world(board, action):
    return r246.digest(world(board, action))


def shift_board(b,dy,dx,fill):
    h=len(b); w=len(b[0]) if h else 0
    out=[[fill for _ in range(w)] for _ in range(h)]
    for r in range(h):
        sr=r-dy
        if sr<0 or sr>=h: continue
        for c in range(w):
            sc=c-dx
            if 0<=sc<w: out[r][c]=int(b[sr][sc])
    return out


def hamming(a,b):
    return sum(int(x)!=int(y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))


def best_shift(before,after):
    fill=r246.bg(before)
    identity=hamming(before,after)
    best=None
    for dy in range(SHIFT_MIN,SHIFT_MAX+1):
        for dx in range(SHIFT_MIN,SHIFT_MAX+1):
            p=shift_board(before,dy,dx,fill)
            m=hamming(p,after)
            cand=(m,abs(dy)+abs(dx),abs(dy),abs(dx),dy,dx)
            if best is None or cand<best[0]: best=(cand,p)
    m,_,_,_,dy,dx=best[0]
    total=max(1,len(after)*(len(after[0]) if after else 0))
    return {'dy':dy,'dx':dx,'mismatch':m,'identity_mismatch':identity,
            'reduction':identity-m,'reduction_fraction':round((identity-m)/total,6),
            'exact':m==0}


def base_key(r):
    return r278.before_key(r,BASE_MODE)


def fit(rows):
    shifts=defaultdict(list); prestates=defaultdict(set); exact_train=defaultdict(list)
    stats=[]
    for r in rows:
        b=world(r['before'],r['action']); a=world(r['after'],r['action'])
        s=best_shift(b,a); stats.append(s); k=base_key(r)
        shifts[k].append((s['dy'],s['dx'])); prestates[k].add(r246.digest(r['before'])); exact_train[k].append(s['exact'])
    table={}
    for k,vals in shifts.items():
        if len(prestates[k])<MIN_DISTINCT_PRESTATES: continue
        if len(set(vals))==1 and all(exact_train[k]): table[k]=vals[0]
    return table,stats,{
        'keys':len(shifts),
        'repeat_supported_keys':sum(len(prestates[k])>=MIN_DISTINCT_PRESTATES for k in shifts),
        'deterministic_shift_repeat_keys':sum(len(prestates[k])>=MIN_DISTINCT_PRESTATES and len(set(v))==1 for k,v in shifts.items()),
        'eligible_exact_shift_keys':len(table),
        'exact_best_shift_transitions':sum(s['exact'] for s in stats),
        'transitions':len(stats),
    }


def evaluate(rows,table):
    s=Counter(); reductions=[]; best_exact=0
    for r in rows:
        s['transitions']+=1
        b=world(r['before'],r['action']); a=world(r['after'],r['action'])
        bs=best_shift(b,a); reductions.append(bs['reduction']); best_exact += int(bs['exact'])
        op=table.get(base_key(r))
        if op is None:
            s['abstain']+=1; continue
        p=shift_board(b,op[0],op[1],r246.bg(b)); s['predictions']+=1
        s['correct' if p==a else 'wrong']+=1
    p=s['predictions']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage':round(p/s['transitions'],6) if s['transitions'] else 0.0,
            'oracle_best_shift_exact':best_exact,
            'oracle_best_shift_positive_reduction':sum(x>0 for x in reductions),
            'oracle_best_shift_total_reduction_pixels':sum(reductions),
            'oracle_best_shift_median_reduction_pixels':statistics.median(reductions) if reductions else 0}


def summarize(stats):
    shifts=Counter((s['dy'],s['dx']) for s in stats)
    return {
        'transitions':len(stats),'exact_best_shift':sum(s['exact'] for s in stats),
        'positive_reduction':sum(s['reduction']>0 for s in stats),
        'total_reduction_pixels':sum(s['reduction'] for s in stats),
        'median_reduction_pixels':statistics.median([s['reduction'] for s in stats]) if stats else 0,
        'top_shifts':[{'dy':dy,'dx':dx,'count':n} for (dy,dx),n in shifts.most_common(8)]}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    tr=r278.annotated_rows(ps[:5]); va=r278.annotated_rows(ps[5:])
    tab,tstats,fit_stats=fit(tr); vv=evaluate(va,tab); ts=summarize(tstats)
    pred=int(vv.get('predictions',0) or 0); wrong=int(vv.get('wrong',0) or 0); correct=int(vv.get('correct',0) or 0)
    if pred>0 and wrong==0 and correct>0: verdict='ZERO_WRONG_EXACT_WORLD_GAIN'
    elif pred>0 and wrong>0: verdict='REJECT_EXACT_SHIFT_MISMATCH'
    elif int(vv['oracle_best_shift_positive_reduction'])>0: verdict='VIEWPORT_SHIFT_PARTIAL_SIGNAL_ONLY'
    else: verdict='VIEWPORT_SHIFT_NO_SIGNAL'
    out={
      'schema':'deus/arc3-r292-lp85-viewport-shift-operator-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'upgrade_patch':{'reason':'repeated static-state identity failures R289/R290/R291','solver_selection_change':'stop adding static state fingerprints; test transition operator family','retry_strategy':'mechanism shift from state identity to action-aligned viewport transform'},
      'mechanism':{'world':'action-canonical static-UI-masked board','operator':'global integer image shift with modal-background fill','shift_range':[SHIFT_MIN,SHIFT_MAX],'base_key':'R279 canon_regions_ui','eligibility':'repeat-supported key, deterministic shift, and exact shifted world on all p0-p4 fit observations'},
      'protocol':{'fit_causal':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'operator_family_fixed_before_diagnostic':True,'threshold_sweep':False,'promotion_in_r292':False},
      'fit':fit_stats,'fit_shift_summary':ts,'validation':vv,'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'oracle_best_shift_is_diagnostic_not_predictor':True,'partial_hamming_reduction_is_not_exact_gain':True,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r292':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'fit':fit_stats,'fit_shift_summary':ts,'validation':vv},sort_keys=True))

if __name__=='__main__': main()
