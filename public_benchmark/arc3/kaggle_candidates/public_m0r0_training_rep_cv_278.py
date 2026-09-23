#!/usr/bin/env python3
"""R278: p0-p9-only source-free representation CV for m0r0.

Triggered by R277's coarse-state alias falsifier, but this run never stages or reads
p10-p19. It compares predeclared finer structural representations using leave-one-trace-
out CV across p0-p9. This is diagnostic only; any later replay of the known p12 error is
public-development-informed, not independent heldout evidence.
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
MODES=(
    'nodes_coarse_ui',
    'graph_coarse_ui',
    'nodes_exact_ui',
    'nodes_exact_noedge_ui',
    'graph_exact_ui',
    'graph_exact_noedge_ui',
)

def dig(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def rep_desc(board,action,mode):
    b=r275.canon_board(board,action,use_ui_mask=True)
    base=mode[:-3] if mode.endswith('_ui') else mode
    if base=='nodes_coarse': d=r274.desc(b,'nodes_coarse')
    elif base=='graph_coarse': d=r274.desc(b,'graph_coarse_noedge')
    elif base=='nodes_exact': d=r274.desc(b,'nodes_exact')
    elif base=='nodes_exact_noedge': d=r274.desc(b,'nodes_exact_noedge')
    elif base=='graph_exact': d=r274.desc(b,'graph_exact')
    elif base=='graph_exact_noedge': d=r274.desc(b,'graph_exact_noedge')
    else: raise KeyError(mode)
    return d

def key(board,action,mode):
    return (dig(rep_desc(board,action,mode)), r275.action_class(action))

def raw_digest(board):
    return r246.digest(board)

def fit(rows,mode):
    obs=defaultdict(Counter)
    raw_alias=defaultdict(set)
    for r in rows:
        k=key(r['before'],r['action'],mode)
        obs[k][key(r['after'],r['action'],mode)[0]]+=1
        raw_alias[k].add(raw_digest(r['before']))
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    alias_sizes=[len(v) for v in raw_alias.values()]
    stats={
        'keys':len(obs),
        'deterministic_keys':len(tab),
        'ambiguous_keys':sum(len(v)>1 for v in obs.values()),
        'alias_keys_ge2':sum(n>=2 for n in alias_sizes),
        'max_distinct_raw_before_per_key':max(alias_sizes) if alias_sizes else 0,
        'mean_distinct_raw_before_per_key':round(sum(alias_sizes)/len(alias_sizes),6) if alias_sizes else 0,
    }
    return tab,stats

def evaluate(rows,tab,mode):
    s=Counter()
    for r in rows:
        s['transitions']+=1
        k=key(r['before'],r['action'],mode); pred=tab.get(k)
        if pred is None:
            s['abstain']+=1; continue
        s['predictions']+=1
        actual=key(r['after'],r['action'],mode)[0]
        s['correct' if pred==actual else 'wrong']+=1
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None
    return dict(s)

def sum_stats(xs):
    out=Counter()
    for x in xs:
        for k in ('transitions','predictions','correct','wrong','abstain'): out[k]+=int(x.get(k,0))
    p=out['predictions']; out['accuracy']=round(out['correct']/p,6) if p else None
    return dict(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if len(ps)!=10 or any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(10)):
        raise SystemExit('exact m0r0 p0-p9 required; p10-p19 forbidden')
    by_trace=[r268.rows([p]) for p in ps]
    modes={}
    for mode in MODES:
        folds=[]
        for i in range(10):
            tr=[r for j,rows in enumerate(by_trace) if j!=i for r in rows]
            va=by_trace[i]
            tab,fs=fit(tr,mode); ev=evaluate(va,tab,mode)
            folds.append({'heldout_p':i,'fit':fs,'validation':ev})
        full_tab,full_fit=fit([r for rows in by_trace for r in rows],mode)
        agg=sum_stats([f['validation'] for f in folds])
        modes[mode]={'loto':agg,'folds':folds,'full_p0_p9_fit':full_fit}
    zero_wrong=[m for m in MODES if int(modes[m]['loto'].get('wrong',0))==0]
    best=None
    if zero_wrong:
        best=max(zero_wrong,key=lambda m:(
            int(modes[m]['loto'].get('correct',0)),
            -int(modes[m]['full_p0_p9_fit']['max_distinct_raw_before_per_key']),
            -int(modes[m]['full_p0_p9_fit']['ambiguous_keys']),
        ))
    base=modes['nodes_coarse_ui']
    verdict='TRAIN_SIDE_REPRESENTATION_SIGNAL' if best and best!='nodes_coarse_ui' else 'NO_MATERIAL_TRAIN_SIDE_SIGNAL'
    out={
      'schema':'deus/arc3-r278-m0r0-training-representation-cv/1','rung':278,'game':GAME,
      'lineage':{'r277_falsifier':'coarse-state alias candidate; known p12 error NOT read in R278'},
      'protocol':{'data':'public p0-p9 only','selection':'10-fold leave-one-trace-out CV','p10_p19_staged_or_read':False,'promotion_in_r278':False},
      'modes':modes,'zero_wrong_modes':zero_wrong,'selected_training_side_mode':best,
      'baseline_nodes_coarse_ui':{'loto':base['loto'],'fit':base['full_p0_p9_fit']},
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'diagnostic_only':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r278':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'selected':best,'zero_wrong_modes':zero_wrong,'summary':{m:{'loto':modes[m]['loto'],'fit':modes[m]['full_p0_p9_fit']} for m in MODES}},sort_keys=True))
if __name__=='__main__': main()
