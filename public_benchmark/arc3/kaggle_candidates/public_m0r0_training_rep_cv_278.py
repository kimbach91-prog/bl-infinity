#!/usr/bin/env python3
"""R278v2: p0-p9-only source-free representation CV for m0r0.

Same frozen candidate set and LOTO protocol as R278v1. Harness-only repair: precompute
representation keys once per transition/mode rather than re-extracting component graphs
inside every fold. p10-p19 are never staged/read. Diagnostic only.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274
import public_action_canonical_topology_diag_275 as r275

GAME='m0r0-492f87ba'
MODES=('nodes_coarse_ui','graph_coarse_ui','nodes_exact_ui','nodes_exact_noedge_ui','graph_exact_ui','graph_exact_noedge_ui')

def dig(x:Any)->str: return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def rep_desc(board,action,mode):
    b=r275.canon_board(board,action,use_ui_mask=True); base=mode[:-3] if mode.endswith('_ui') else mode
    table={
      'nodes_coarse':'nodes_coarse','graph_coarse':'graph_coarse_noedge','nodes_exact':'nodes_exact',
      'nodes_exact_noedge':'nodes_exact_noedge','graph_exact':'graph_exact','graph_exact_noedge':'graph_exact_noedge'}
    return r274.desc(b,table[base])

def make_record(r,mode):
    ac=r275.action_class(r['action'])
    return (dig(rep_desc(r['before'],r['action'],mode)), ac, dig(rep_desc(r['after'],r['action'],mode)), r246.digest(r['before']))

def fit_records(records):
    obs=defaultdict(Counter); alias=defaultdict(set)
    for before,ac,after,raw in records:
        k=(before,ac); obs[k][after]+=1; alias[k].add(raw)
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}; sizes=[len(v) for v in alias.values()]
    return tab,{
      'keys':len(obs),'deterministic_keys':len(tab),'ambiguous_keys':sum(len(v)>1 for v in obs.values()),
      'alias_keys_ge2':sum(n>=2 for n in sizes),'max_distinct_raw_before_per_key':max(sizes) if sizes else 0,
      'mean_distinct_raw_before_per_key':round(sum(sizes)/len(sizes),6) if sizes else 0}

def eval_records(records,tab):
    s=Counter()
    for before,ac,after,_ in records:
        s['transitions']+=1; pred=tab.get((before,ac))
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1; s['correct' if pred==after else 'wrong']+=1
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None; return dict(s)

def sum_stats(xs):
    s=Counter()
    for x in xs:
        for k in ('transitions','predictions','correct','wrong','abstain'): s[k]+=int(x.get(k,0))
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None; return dict(s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if len(ps)!=10 or any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit('exact m0r0 p0-p9 required; p10-p19 forbidden')
    rows_by_trace=[r268.rows([p]) for p in ps]; modes={}
    for mode in MODES:
        rec_by_trace=[[make_record(r,mode) for r in rows] for rows in rows_by_trace]
        folds=[]
        for i in range(10):
            train=[x for j,rs in enumerate(rec_by_trace) if j!=i for x in rs]; tab,fs=fit_records(train); ev=eval_records(rec_by_trace[i],tab)
            folds.append({'heldout_p':i,'fit':fs,'validation':ev})
        full=[x for rs in rec_by_trace for x in rs]; _,full_fit=fit_records(full); agg=sum_stats([f['validation'] for f in folds])
        modes[mode]={'loto':agg,'folds':folds,'full_p0_p9_fit':full_fit}
    zero=[m for m in MODES if int(modes[m]['loto'].get('wrong',0))==0]; best=None
    if zero:
        best=max(zero,key=lambda m:(int(modes[m]['loto'].get('correct',0)),-int(modes[m]['full_p0_p9_fit']['max_distinct_raw_before_per_key']),-int(modes[m]['full_p0_p9_fit']['ambiguous_keys'])))
    base=modes['nodes_coarse_ui']; verdict='TRAIN_SIDE_REPRESENTATION_SIGNAL' if best and best!='nodes_coarse_ui' else 'NO_MATERIAL_TRAIN_SIDE_SIGNAL'
    out={'schema':'deus/arc3-r278-m0r0-training-representation-cv/1','rung':278,'harness_revision':'v2_precomputed_keys_same_candidates_same_loto','game':GAME,
      'lineage':{'r277_falsifier':'coarse-state alias candidate; known p12 error NOT read in R278'},
      'protocol':{'data':'public p0-p9 only','selection':'10-fold leave-one-trace-out CV','p10_p19_staged_or_read':False,'promotion_in_r278':False},
      'modes':modes,'zero_wrong_modes':zero,'selected_training_side_mode':best,'baseline_nodes_coarse_ui':{'loto':base['loto'],'fit':base['full_p0_p9_fit']},'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'diagnostic_only':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r278':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'selected':best,'zero_wrong_modes':zero,'summary':{m:{'loto':modes[m]['loto'],'fit':modes[m]['full_p0_p9_fit']} for m in MODES}},sort_keys=True))
if __name__=='__main__': main()
