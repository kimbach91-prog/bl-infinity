#!/usr/bin/env python3
"""R298: narrow hierarchical sparse delta gate for lp85.

Lineage:
- R294: two verifier-approved 3x3 change parent rules, but one false p5-p9 firing.
- R295: the false firing collides at 3x3 but differs in surrounding 5x5 context.
- R296: globally widening to 5x5 caused 783 false changes and exact-frame loss.
- R297: on p0-p4 only, each R294 parent has a repeated deterministic 5x5 child.

R298 therefore composes the representations instead of replacing them: a pixel
may change only when BOTH an R294-approved 3x3 parent rule and a p0-p4-supported
stable 5x5 child context agree on the same next-center value. Everything else
falls back to identity. Rules are frozen using p0-p4 only. p5-p9 is a
source-assisted replay because prior rungs already inspected those traces; it is
not independent heldout evidence. p10-p19 are forbidden.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_lp85_loto_sparse_local_delta_diag_294 as r294

RUNG=298
TARGET_GAME='lp85-305b61c3'
PAD=-1
MIN_CHILD_TRANSITIONS=2


def world(board,action):
    return r275.canon_board(board,action,use_ui_mask=True)


def patch(b,r,c,radius):
    h=len(b); w=len(b[0]) if h else 0; vals=[]
    for dr in range(-radius,radius+1):
        rr=r+dr
        for dc in range(-radius,radius+1):
            cc=c+dc
            vals.append(int(b[rr][cc]) if 0<=rr<h and 0<=cc<w else PAD)
    return tuple(vals)


def fit_hierarchy(train_rows,trace_rows):
    parents,parent_gate=r294.build_frozen_rules(train_rows,trace_rows)
    child_out=defaultdict(Counter); child_support=defaultdict(set)
    for ti,tr in enumerate(trace_rows):
        for ri,row in enumerate(tr):
            b=world(row['before'],row['action']); a=world(row['after'],row['action'])
            h=len(b); w=len(b[0]) if h else 0
            for r in range(h):
                for c in range(w):
                    p3=patch(b,r,c,1)
                    if p3 not in parents: continue
                    p5=patch(b,r,c,2); key=(p3,p5); child_out[key][int(a[r][c])] += 1; child_support[key].add((ti,ri))
    accepted={}
    for (p3,p5),outs in child_out.items():
        if len(outs)!=1 or len(child_support[(p3,p5)])<MIN_CHILD_TRANSITIONS: continue
        actual=next(iter(outs)); parent_pred=int(parents[p3]); center=int(p3[len(p3)//2])
        if actual==parent_pred and actual!=center:
            accepted[(p3,p5)]=actual
    stats={
      'r294_parent_rules':len(parents),
      'r294_parent_loto_predictions':parent_gate['accepted_loto_predictions'],
      'r294_parent_loto_wrong':parent_gate['accepted_loto_wrong'],
      'observed_parent_child_pairs':len(child_out),
      'accepted_hierarchical_rules':len(accepted),
      'accepted_support_occurrences':sum(sum(child_out[k].values()) for k in accepted),
      'min_child_distinct_transitions':MIN_CHILD_TRANSITIONS,
    }
    return accepted,stats


def evaluate(rows,rules):
    m=Counter(); per_trace=defaultdict(Counter)
    for row in rows:
        b=world(row['before'],row['action']); a=world(row['after'],row['action']); pred=[list(map(int,x)) for x in b]
        h=len(b); w=len(b[0]) if h else 0
        t=int(row.get('trace_index',-1))
        for r in range(h):
            for c in range(w):
                key=(patch(b,r,c,1),patch(b,r,c,2))
                if key in rules: pred[r][c]=int(rules[key])
        id_err=cand_err=0
        for r in range(h):
            for c in range(w):
                bv=int(b[r][c]); av=int(a[r][c]); pv=int(pred[r][c])
                id_err += bv!=av; cand_err += pv!=av
                if pv!=bv:
                    m['predicted_changes']+=1; per_trace[t]['predicted_changes']+=1
                    if pv==av and bv!=av:
                        m['true_changed_correct']+=1; per_trace[t]['true_changed_correct']+=1
                    elif pv!=av:
                        m['false_changes']+=1; per_trace[t]['false_changes']+=1
        m['frames']+=1; m['pixels']+=h*w; m['identity_errors']+=id_err; m['candidate_errors']+=cand_err
        m['identity_exact_frames']+=id_err==0; m['candidate_exact_frames']+=cand_err==0
    m['identity_pixel_correct']=m['pixels']-m['identity_errors']; m['candidate_pixel_correct']=m['pixels']-m['candidate_errors']
    return dict(m),{str(k):dict(v) for k,v in sorted(per_trace.items())}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={TARGET_GAME}: raise SystemExit(f'exact target required, got {sorted(by)}')
    ps=sorted(by[TARGET_GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f'exact p0-p9 required, got {nums}')
    train_traces=[r278.annotated_rows([p]) for p in ps[:5]]; train_rows=[r for tr in train_traces for r in tr]
    replay_rows=[]
    for idx,p in enumerate(ps[5:],start=5):
        rr=r278.annotated_rows([p])
        for x in rr: x['trace_index']=idx
        replay_rows.extend(rr)
    rules,fit=fit_hierarchy(train_rows,train_traces); val,per_trace=evaluate(replay_rows,rules)
    exact_delta=val['candidate_exact_frames']-val['identity_exact_frames']; pixel_delta=val['candidate_pixel_correct']-val['identity_pixel_correct']
    if val.get('predicted_changes',0)>0 and val.get('false_changes',0)==0 and pixel_delta>0:
        verdict='HIERARCHICAL_GATE_ZERO_FALSE_CHANGE_PIXEL_GAIN'
    elif pixel_delta>0:
        verdict='HIERARCHICAL_GATE_PIXEL_GAIN_WITH_FALSE_CHANGE'
    elif pixel_delta<0:
        verdict='REJECT_HIERARCHICAL_GATE'
    else:
        verdict='HIERARCHICAL_GATE_NO_SIGNAL'
    out={
      'schema':'deus/arc3-r298-lp85-hierarchical-sparse-delta-gate/1','rung':RUNG,'game':TARGET_GAME,
      'lineage':{'r294':'2 verified 3x3 parent rules; p5-p9 replay 10 correct/1 false','r295':'false parent firing discriminated by 5x5 context','r296':'global 5x5 rejected: 783 false changes; exact frames 17->8','r297':'p0-p4 parent-specific child contexts show repeated deterministic signal'},
      'mechanism':{'gate':'R294-approved 3x3 parent AND repeated deterministic 5x5 child must agree','fallback':'identity','fit':'p0-p4 only'},
      'protocol':{'fit':'p0-p4 only','source_assisted_replay':'p5-p9 only','p10_p19_staged_or_read':False,'gate_fixed_before_replay':True,'threshold_sweep':False,'replay_is_not_independent':True,'promotion_in_r298':False},
      'fit_gate':fit,'replay':val,'per_trace':per_trace,
      'delta':{'exact_frame_delta_vs_identity':exact_delta,'pixel_correct_delta_vs_identity':pixel_delta,'error_reduction_vs_identity':val['identity_errors']-val['candidate_errors']},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'p5_p9_replay_is_source_assisted':True,'independent_hidden_generalization_claim':False,'whole_game_policy_claim':False,'solver_promotion':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r298':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'fit_gate':fit,'replay':val,'delta':out['delta'],'per_trace':per_trace},sort_keys=True))

if __name__=='__main__': main()
