#!/usr/bin/env python3
"""R289: lp85 multires world-state identity diagnostic after R288.

R288 showed that 88.1179% of exact-output alias differences inside R279
canon_regions_ui keys live in the world interior, not static UI. R289 changes
one mechanism only: retain the frozen action-canonical/UI-masked G=8 region
state and add a finer G=16 region residual. This tests whether missing spatial
world identity/viewport detail explains a useful subset of the aliases.

Protocol: p0-p4 fit/collision analysis -> p5-p9 diagnostic. p10-p19 forbidden.
No threshold sweep; G=16 is fixed in source before diagnostic traces are staged.
PUBLIC_OFFLINE/source-free diagnostic only.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG=289
TARGET_GAME='lp85-305b61c3'
G_COARSE=8
G_FINE=16
MIN_DISTINCT_PRESTATES=2


def canon_masked(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def base_key(r):
    return r278.before_key(r,'canon_regions_ui')


def base_next(r):
    return r278.after_key(r,'canon_regions_ui')


def refined_state(board,action):
    b=canon_masked(board,action)
    return (r246.regions(b,G_COARSE),r246.regions(b,G_FINE))


def refined_key(r):
    return (r246.stable(refined_state(r['before'],r['action'])),r275.action_class(r['action']))


def refined_next(r):
    return r246.stable(refined_state(r['after'],r['action']))


def fit_rep(rows,key_fn,next_fn):
    obs=defaultdict(Counter); pre=defaultdict(set)
    for r in rows:
        k=key_fn(r); obs[k][next_fn(r)]+=1; pre[k].add(r246.digest(r['before']))
    table={k:next(iter(v)) for k,v in obs.items() if len(v)==1 and len(pre[k])>=MIN_DISTINCT_PRESTATES}
    return table,{
        'keys':len(obs),
        'deterministic_keys':sum(len(v)==1 for v in obs.values()),
        'ambiguous_keys':sum(len(v)>1 for v in obs.values()),
        'repeat_supported_keys':sum(len(pre[k])>=MIN_DISTINCT_PRESTATES for k in obs),
        'eligible_keys':len(table),
    }


def eval_rep(rows,table,key_fn,next_fn):
    s=Counter()
    for r in rows:
        s['transitions']+=1; pred=table.get(key_fn(r))
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1
        s['correct' if pred==next_fn(r) else 'wrong']+=1
    p=s['predictions']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None}


def exact_collision_stats(rows,key_fn):
    outs=defaultdict(set); pre=defaultdict(set)
    for r in rows:
        k=key_fn(r); outs[k].add(r246.digest(r275.canon_board(r['after'],r['action'],use_ui_mask=False))); pre[k].add(r246.digest(r['before']))
    supported=[k for k in outs if len(pre[k])>=MIN_DISTINCT_PRESTATES]
    return {
        'keys':len(outs),
        'repeat_supported_keys':len(supported),
        'repeat_supported_exact_unique':sum(len(outs[k])==1 for k in supported),
        'repeat_supported_exact_ambiguous':sum(len(outs[k])>1 for k in supported),
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    tr=r278.annotated_rows(ps[:5]); va=r278.annotated_rows(ps[5:])

    base_tab,base_fit=fit_rep(tr,base_key,base_next)
    ref_tab,ref_fit=fit_rep(tr,refined_key,refined_next)
    base_val=eval_rep(va,base_tab,base_key,base_next)
    ref_val=eval_rep(va,ref_tab,refined_key,refined_next)
    base_col=exact_collision_stats(tr,base_key); ref_col=exact_collision_stats(tr,refined_key)

    amb_reduction=base_col['repeat_supported_exact_ambiguous']-ref_col['repeat_supported_exact_ambiguous']
    rp=int(ref_val.get('predictions',0) or 0); rw=int(ref_val.get('wrong',0) or 0); rc=int(ref_val.get('correct',0) or 0)
    if amb_reduction>0 and rp>0 and rw==0 and rc>0:
        verdict='WORLD_IDENTITY_SIGNAL'
    elif rp>0 and rw>0:
        verdict='REJECT_MISMATCH'
    else:
        verdict='NO_SIGNAL'

    out={
      'schema':'deus/arc3-r289-lp85-multires-world-identity-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'mechanism':{'base':'action-canonical static-UI-masked regions G8','delta':'append G16 regions as finer world-state/viewport residual','g_coarse':G_COARSE,'g_fine':G_FINE,'min_distinct_prestates':MIN_DISTINCT_PRESTATES},
      'protocol':{'fit_collision_analysis':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'candidate_fixed_before_diagnostic':True,'threshold_sweep':False,'promotion_in_r289':False},
      'base':{'fit':base_fit,'validation':base_val,'exact_output_collisions':base_col},
      'candidate':{'fit':ref_fit,'validation':ref_val,'exact_output_collisions':ref_col},
      'delta':{'repeat_supported_exact_ambiguity_reduction':amb_reduction,'validation_correct_delta':int(ref_val.get('correct',0) or 0)-int(base_val.get('correct',0) or 0),'validation_wrong_delta':int(ref_val.get('wrong',0) or 0)-int(base_val.get('wrong',0) or 0)},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r289':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'base_collision':base_col,'candidate_collision':ref_col,'base_validation':base_val,'candidate_validation':ref_val,'delta':out['delta']},sort_keys=True))

if __name__=='__main__': main()
