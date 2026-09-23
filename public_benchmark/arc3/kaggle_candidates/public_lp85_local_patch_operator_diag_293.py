#!/usr/bin/env python3
"""R293: source-free local transition-operator diagnostic for lp85.

R292 falsified global viewport translation: the best shift was (0,0) for every
p0-p4 transition and no p5-p9 transition had positive Hamming reduction. R293
therefore moves one causal level down instead of adding another static state
fingerprint: learn a translation-invariant local 3x3 -> next-center operator in
the action-canonical, static-UI-masked world.

Rules are fit on p0-p4 only and require a deterministic output observed in at
least two distinct transitions. Unseen/ambiguous neighborhoods preserve the
input center. The frozen rule table is then evaluated on p5-p9. p10-p19 are
forbidden. This is PUBLIC_OFFLINE mechanism research; even a positive result is
not a whole-game solver, hidden/Kaggle score, or submission candidate.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG=293
TARGET_GAME='lp85-305b61c3'
RADIUS=1
MIN_DISTINCT_TRANSITIONS=2
PAD=-1


def world(board, action):
    return r275.canon_board(board, action, use_ui_mask=True)


def patch_key(b,r,c):
    h=len(b); w=len(b[0]) if h else 0
    vals=[]
    for dr in range(-RADIUS,RADIUS+1):
        rr=r+dr
        for dc in range(-RADIUS,RADIUS+1):
            cc=c+dc
            vals.append(int(b[rr][cc]) if 0<=rr<h and 0<=cc<w else PAD)
    return tuple(vals)


def fit(rows):
    outcomes=defaultdict(Counter)
    transition_support=defaultdict(set)
    for ti,row in enumerate(rows):
        b=world(row['before'],row['action']); a=world(row['after'],row['action'])
        h=len(b); w=len(b[0]) if h else 0
        for r in range(h):
            for c in range(w):
                k=patch_key(b,r,c)
                outcomes[k][int(a[r][c])] += 1
                transition_support[k].add(ti)
    rules={}
    for k,out in outcomes.items():
        if len(out)==1 and len(transition_support[k])>=MIN_DISTINCT_TRANSITIONS:
            rules[k]=next(iter(out))
    return rules,{
        'observed_patch_keys':len(outcomes),
        'deterministic_patch_keys':sum(len(v)==1 for v in outcomes.values()),
        'repeat_supported_patch_keys':sum(len(transition_support[k])>=MIN_DISTINCT_TRANSITIONS for k in outcomes),
        'eligible_rules':len(rules),
        'ambiguous_patch_keys':sum(len(v)>1 for v in outcomes.values()),
    }


def predict(b,rules):
    h=len(b); w=len(b[0]) if h else 0
    out=[list(map(int,row)) for row in b]
    used=0; predicted_changes=0
    for r in range(h):
        for c in range(w):
            k=patch_key(b,r,c)
            if k in rules:
                used += 1
                v=int(rules[k])
                if v!=int(b[r][c]): predicted_changes += 1
                out[r][c]=v
    return out,used,predicted_changes


def evaluate(rows,rules):
    m=Counter()
    per=[]
    for row in rows:
        b=world(row['before'],row['action']); a=world(row['after'],row['action'])
        p,used,pchg=predict(b,rules)
        total=len(b)*(len(b[0]) if b else 0)
        id_err=sum(int(x)!=int(y) for rb,ra in zip(b,a) for x,y in zip(rb,ra))
        cand_err=sum(int(x)!=int(y) for rp,ra in zip(p,a) for x,y in zip(rp,ra))
        target_changed=sum(int(x)!=int(y) for rb,ra in zip(b,a) for x,y in zip(rb,ra))
        predicted_changed=sum(int(x)!=int(y) for rb,rp in zip(b,p) for x,y in zip(rb,rp))
        true_changed_correct=sum(
            int(b[r][c])!=int(a[r][c]) and int(p[r][c])==int(a[r][c])
            for r in range(len(b)) for c in range(len(b[0]) if b else 0)
        )
        false_changes=sum(
            int(p[r][c])!=int(b[r][c]) and int(p[r][c])!=int(a[r][c])
            for r in range(len(b)) for c in range(len(b[0]) if b else 0)
        )
        m['frames']+=1; m['pixels']+=total; m['identity_errors']+=id_err; m['candidate_errors']+=cand_err
        m['identity_exact_frames']+=int(id_err==0); m['candidate_exact_frames']+=int(cand_err==0)
        m['rule_applications']+=used; m['predicted_changes']+=predicted_changed
        m['target_changed_pixels']+=target_changed; m['true_changed_correct']+=true_changed_correct; m['false_changes']+=false_changes
        per.append({'identity_errors':id_err,'candidate_errors':cand_err,'predicted_changes':predicted_changed,'target_changed_pixels':target_changed,'true_changed_correct':true_changed_correct,'false_changes':false_changes})
    m['identity_pixel_correct']=m['pixels']-m['identity_errors']
    m['candidate_pixel_correct']=m['pixels']-m['candidate_errors']
    return dict(m),per


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    tr=r278.annotated_rows(ps[:5]); va=r278.annotated_rows(ps[5:])
    rules,fit_stats=fit(tr); val,per=evaluate(va,rules)
    exact_delta=val['candidate_exact_frames']-val['identity_exact_frames']
    pixel_delta=val['candidate_pixel_correct']-val['identity_pixel_correct']
    if exact_delta>0 and pixel_delta>0:
        verdict='LOCAL_PATCH_EXACT_FRAME_SIGNAL'
    elif pixel_delta>0:
        verdict='LOCAL_PATCH_PIXEL_SIGNAL_ONLY'
    elif pixel_delta<0:
        verdict='REJECT_LOCAL_PATCH_OPERATOR'
    else:
        verdict='LOCAL_PATCH_NO_SIGNAL'
    out={
      'schema':'deus/arc3-r293-lp85-local-patch-operator-diagnostic/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{'r292':'global viewport shift NO_SIGNAL','repair':'change mechanism from global transform to local translation-invariant transition operator'},
      'mechanism':{'world':'action-canonical static-UI-masked board','operator':'3x3 before-neighborhood -> next center color','radius':RADIUS,'padding':PAD,'eligibility':f'deterministic output and support in >= {MIN_DISTINCT_TRANSITIONS} distinct p0-p4 transitions','fallback':'identity center for unseen or ambiguous patch'},
      'protocol':{'fit':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'operator_fixed_before_diagnostic':True,'threshold_sweep':False,'promotion_in_r293':False},
      'fit':fit_stats,'validation':val,
      'delta':{'exact_frame_delta_vs_identity':exact_delta,'pixel_correct_delta_vs_identity':pixel_delta,'error_reduction_vs_identity':val['identity_errors']-val['candidate_errors']},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'pixel_signal_is_not_exact_frame_gain':True,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r293':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'fit':fit_stats,'validation':val,'delta':out['delta']},sort_keys=True))

if __name__=='__main__': main()
