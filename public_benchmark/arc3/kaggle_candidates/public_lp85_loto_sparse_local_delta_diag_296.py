#!/usr/bin/env python3
"""R296: falsifier-driven 5x5 sparse local-delta repair for lp85.

R295 localized the only R294 false change: the 3x3 rule was identical at five
correct firings and one wrong firing, while the surrounding 5x5 context differed.
R296 therefore changes representation once, from radius-1 to radius-2, instead
of tuning coordinates, colors, thresholds, or a one-off exception.

The 5x5 operator and its reliability gate are learned only from p0-p4. A
non-identity rule is accepted iff it is deterministic with support in at least
two p0-p4 transitions and makes at least one zero-error leave-one-trace-out
prediction inside p0-p4. The frozen rule table is replayed on p5-p9 only as a
source-assisted mechanism check because R295 already exposed a p5-p9 falsifier;
that replay is NOT independent heldout evidence. p10-p19 are forbidden.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG=296
TARGET_GAME='lp85-305b61c3'
RADIUS=2
PAD=-1
MIN_DISTINCT_TRANSITIONS=2


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def patch_key(b,r,c):
    h=len(b); w=len(b[0]) if h else 0; vals=[]
    for dr in range(-RADIUS,RADIUS+1):
        rr=r+dr
        for dc in range(-RADIUS,RADIUS+1):
            cc=c+dc
            vals.append(int(b[rr][cc]) if 0<=rr<h and 0<=cc<w else PAD)
    return tuple(vals)


def fit_rules(rows):
    outcomes=defaultdict(Counter); support=defaultdict(set)
    for ti,row in enumerate(rows):
        b=world(row['before'],row['action']); a=world(row['after'],row['action'])
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=patch_key(b,r,c); outcomes[k][int(a[r][c])] += 1; support[k].add(ti)
    rules={k:next(iter(out)) for k,out in outcomes.items() if len(out)==1 and len(support[k])>=MIN_DISTINCT_TRANSITIONS}
    return rules,outcomes,support


def loto_gate(traces):
    stats=defaultdict(Counter)
    for held in range(len(traces)):
        train=[r for i,t in enumerate(traces) if i!=held for r in t]
        rules,_,_=fit_rules(train)
        for row in traces[held]:
            b=world(row['before'],row['action']); a=world(row['after'],row['action'])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    k=patch_key(b,r,c)
                    if k not in rules: continue
                    pred=int(rules[k]); center=int(b[r][c])
                    if pred==center: continue
                    stats[k]['predictions'] += 1
                    stats[k]['correct' if pred==int(a[r][c]) else 'wrong'] += 1
    return stats


def build_frozen_rules(train_rows,trace_rows):
    rules,outcomes,support=fit_rules(train_rows); cv=loto_gate(trace_rows); accepted={}
    for k,pred in rules.items():
        center=k[len(k)//2]; s=cv.get(k,Counter())
        if pred!=center and s['predictions']>0 and s['wrong']==0:
            accepted[k]=pred
    return accepted,{
        'full_fit_eligible_rules':len(rules),
        'full_fit_change_rules':sum(int(v)!=int(k[len(k)//2]) for k,v in rules.items()),
        'loto_tested_change_keys':sum(s['predictions']>0 for s in cv.values()),
        'loto_zero_wrong_change_keys':sum(s['predictions']>0 and s['wrong']==0 for s in cv.values()),
        'accepted_change_rules':len(accepted),
        'accepted_loto_predictions':sum(cv[k]['predictions'] for k in accepted),
        'accepted_loto_correct':sum(cv[k]['correct'] for k in accepted),
        'accepted_loto_wrong':sum(cv[k]['wrong'] for k in accepted),
    }


def evaluate(rows,rules):
    m=Counter()
    for row in rows:
        b=world(row['before'],row['action']); a=world(row['after'],row['action']); p=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=patch_key(b,r,c)
                if k in rules: p[r][c]=int(rules[k])
        id_err=cand_err=0
        for r in range(h):
            for c in range(w):
                bv=int(b[r][c]); av=int(a[r][c]); pv=int(p[r][c])
                id_err += bv!=av; cand_err += pv!=av
                if pv!=bv:
                    m['predicted_changes']+=1
                    if pv==av and bv!=av: m['true_changed_correct']+=1
                    elif pv!=av: m['false_changes']+=1
        m['frames']+=1; m['pixels']+=h*w; m['identity_errors']+=id_err; m['candidate_errors']+=cand_err
        m['identity_exact_frames']+=id_err==0; m['candidate_exact_frames']+=cand_err==0
    m['identity_pixel_correct']=m['pixels']-m['identity_errors']; m['candidate_pixel_correct']=m['pixels']-m['candidate_errors']
    return dict(m)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    train_trace_rows=[r278.annotated_rows([p]) for p in ps[:5]]
    train_rows=[r for tr in train_trace_rows for r in tr]; replay_rows=r278.annotated_rows(ps[5:])
    rules,gate=build_frozen_rules(train_rows,train_trace_rows); val=evaluate(replay_rows,rules)
    exact_delta=val['candidate_exact_frames']-val['identity_exact_frames']; pixel_delta=val['candidate_pixel_correct']-val['identity_pixel_correct']
    if val.get('predicted_changes',0)>0 and val.get('false_changes',0)==0 and pixel_delta>0:
        verdict='R295_REPAIR_ZERO_FALSE_CHANGE_PIXEL_GAIN'
    elif pixel_delta>0:
        verdict='R295_REPAIR_PIXEL_GAIN_WITH_FALSE_CHANGE'
    elif pixel_delta<0:
        verdict='REJECT_5X5_LOCAL_REPAIR'
    else:
        verdict='R295_REPAIR_NO_SIGNAL'
    out={
      'schema':'deus/arc3-r296-lp85-loto-sparse-5x5-repair/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{
        'r294':'radius1 LOTO-gated sparse operator: +9 pixel-correct, 10 true changes, 1 false change, 0 exact-frame delta',
        'r295':'single false firing shares the same 3x3 rule as five correct firings but differs in surrounding 5x5 context',
        'repair':'change representation from radius1 to radius2; no coordinate/color/threshold exception'},
      'mechanism':{'world':'action-canonical static-UI-masked board','operator':'5x5 patch -> next center, non-identity rules only','full_fit_support':f'>={MIN_DISTINCT_TRANSITIONS} distinct p0-p4 transitions','verifier':'accepted rule must make >=1 p0-p4 LOTO prediction and zero LOTO errors','fallback':'identity'},
      'protocol':{'fit_and_loto_verifier':'p0-p4 only','source_assisted_replay':'p5-p9 only','p10_p19_staged_or_read':False,'gate_fixed_before_replay':True,'threshold_sweep':False,'representation_selected_after_r295_p5_p9_falsifier':True,'promotion_in_r296':False},
      'fit_gate':gate,'replay':val,
      'delta':{'exact_frame_delta_vs_identity':exact_delta,'pixel_correct_delta_vs_identity':pixel_delta,'error_reduction_vs_identity':val['identity_errors']-val['candidate_errors']},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'p5_p9_replay_is_not_independent_after_r295':True,'sparse_pixel_gain_is_not_full_frame_gain':True,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r296':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'fit_gate':gate,'replay':val,'delta':out['delta']},sort_keys=True))

if __name__=='__main__': main()
