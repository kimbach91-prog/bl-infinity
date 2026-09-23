#!/usr/bin/env python3
"""R291: lp85 coarse occupancy-residual diagnostic after R289/R290 NO_SIGNAL.

Falsifiers:
- R289: increasing modal region resolution G8 -> G16 did not split exact-frame aliases.
- R290: exact per-color row/column projections over-split state identity and produced
  no repeat-supported deterministic exact-frame key.

R291 tests the middle mechanism only: action-canonical, static-UI-masked world
with a fixed G8 foreground occupancy-density residual. Each 8x8 spatial cell is
represented by a coarse, fixed occupancy bin rather than its modal color or an
exact projection. This preserves thin/local structure while deliberately
retaining recurrence.

Protocol is fixed before diagnostic data: p0-p4 fit/collision -> p5-p9 diagnostic;
p10-p19 forbidden. PUBLIC_OFFLINE/source-free only. No solver/Kaggle promotion.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG = 291
TARGET_GAME = "lp85-305b61c3"
BASE_MODE = "canon_regions_ui"
MIN_DISTINCT_PRESTATES = 2
G = 8


def canon_masked(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def canon_raw(board, action):
    return r275.canon_board(board, action, use_ui_mask=False)


def occ_bin(n: int) -> int:
    # Fixed before p5-p9 is staged. Cell area is at most 64 pixels for 64x64/G8.
    if n == 0: return 0
    if n <= 4: return 1
    if n <= 16: return 2
    if n <= 32: return 3
    return 4


def occupancy_signature(board, action):
    """G8 grid of coarse foreground occupancy counts, relative to global mode bg."""
    b = canon_masked(board, action)
    h = len(b); w = len(b[0]) if h else 0
    bg = r246.bg(b)
    sig=[]
    for gy in range(G):
        r0=(gy*h)//G; r1=((gy+1)*h)//G
        row=[]
        for gx in range(G):
            c0=(gx*w)//G; c1=((gx+1)*w)//G
            n=sum(int(b[r][c]) != bg for r in range(r0,r1) for c in range(c0,c1))
            row.append(occ_bin(n))
        sig.append(tuple(row))
    return tuple(sig)


def base_key(r):
    return r278.before_key(r, BASE_MODE)


def candidate_key(r):
    return (base_key(r), r246.stable(occupancy_signature(r['before'], r['action'])))


def exact_after(r):
    return r246.digest(canon_raw(r['after'], r['action']))


def fit_exact(rows, key_fn):
    outcomes=defaultdict(Counter); prestates=defaultdict(set)
    for r in rows:
        k=key_fn(r); outcomes[k][exact_after(r)] += 1; prestates[k].add(r246.digest(r['before']))
    tab={k:next(iter(v)) for k,v in outcomes.items() if len(v)==1 and len(prestates[k])>=MIN_DISTINCT_PRESTATES}
    return tab, {
        'keys':len(outcomes),
        'deterministic_keys':sum(len(v)==1 for v in outcomes.values()),
        'ambiguous_keys':sum(len(v)>1 for v in outcomes.values()),
        'repeat_supported_keys':sum(len(prestates[k])>=MIN_DISTINCT_PRESTATES for k in outcomes),
        'eligible_exact_keys':len(tab),
    }


def collision_stats(rows,key_fn):
    outcomes=defaultdict(set); prestates=defaultdict(set)
    for r in rows:
        k=key_fn(r); outcomes[k].add(exact_after(r)); prestates[k].add(r246.digest(r['before']))
    supported=[k for k in outcomes if len(prestates[k])>=MIN_DISTINCT_PRESTATES]
    return {
        'keys':len(outcomes),
        'repeat_supported_keys':len(supported),
        'repeat_supported_exact_unique':sum(len(outcomes[k])==1 for k in supported),
        'repeat_supported_exact_ambiguous':sum(len(outcomes[k])>1 for k in supported),
    }


def evaluate(rows,tab,key_fn):
    s=Counter()
    for r in rows:
        s['transitions']+=1; pred=tab.get(key_fn(r))
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1
        s['correct' if pred==exact_after(r) else 'wrong']+=1
    p=s['predictions']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/s['transitions'],6) if s['transitions'] else 0.0}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    train=r278.annotated_rows(ps[:5]); val=r278.annotated_rows(ps[5:])

    bt,bf=fit_exact(train,base_key); ct,cf=fit_exact(train,candidate_key)
    bv=evaluate(val,bt,base_key); cv=evaluate(val,ct,candidate_key)
    bc=collision_stats(train,base_key); cc=collision_stats(train,candidate_key)
    bcor=int(bv.get('correct',0) or 0); ccor=int(cv.get('correct',0) or 0); cwrong=int(cv.get('wrong',0) or 0); cpred=int(cv.get('predictions',0) or 0)
    if cpred>0 and cwrong==0 and ccor>bcor: verdict='ZERO_WRONG_EXACT_FRAME_GAIN'
    elif cpred>0 and cwrong>0: verdict='REJECT_MISMATCH'
    else: verdict='NO_SIGNAL'

    out={
      'schema':'deus/arc3-r291-lp85-occupancy-residual-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{'r288':'world-dominant exact-frame collision','r289':'G16 modal multires NO_SIGNAL','r290':'exact row/column projection NO_SIGNAL','repair':'fixed coarse occupancy-density residual; no threshold sweep'},
      'mechanism':{'base':'R279 action-canonical static-UI-masked G8 modal regions + pooled action','delta':'append fixed G8 foreground occupancy-density bins','grid':G,'bins':'0,1-4,5-16,17-32,33+ non-background pixels','min_distinct_prestates':MIN_DISTINCT_PRESTATES,'prediction_target':'action-canonical exact next-frame digest'},
      'protocol':{'fit_collision_analysis':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'candidate_fixed_before_diagnostic':True,'threshold_sweep':False,'promotion_in_r291':False,'signal_rule':'candidate predictions>0 AND wrong=0 AND candidate correct>base correct'},
      'base':{'fit':bf,'validation':bv,'collisions':bc},'candidate':{'fit':cf,'validation':cv,'collisions':cc},
      'delta':{'repeat_supported_exact_unique_delta':cc['repeat_supported_exact_unique']-bc['repeat_supported_exact_unique'],'repeat_supported_exact_ambiguous_delta':cc['repeat_supported_exact_ambiguous']-bc['repeat_supported_exact_ambiguous'],'validation_correct_delta':ccor-bcor,'validation_prediction_delta':cpred-int(bv.get('predictions',0) or 0),'validation_wrong_delta':cwrong-int(bv.get('wrong',0) or 0)},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r291':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'base_collision':bc,'candidate_collision':cc,'base_validation':bv,'candidate_validation':cv,'delta':out['delta']},sort_keys=True))

if __name__=='__main__': main()
