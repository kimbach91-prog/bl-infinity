#!/usr/bin/env python3
"""R279: public-development-informed repair replay for m0r0.

R277 revealed a coarse-state alias in the known p12 mismatch. R278 then selected
nodes_exact_ui using p0-p9-only leave-one-trace-out CV. R279 freezes that selected
representation, refits p0-p9, and replays p10-p19 only to test whether it removes
R276's one known wrong transition without introducing new wrong predictions.

Because the representation family was investigated after R277 exposed p12, this is
NOT independent heldout evidence. PUBLIC_OFFLINE repair validation only.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274
import public_action_canonical_topology_diag_275 as r275

GAME='m0r0-492f87ba'
MODE='nodes_exact_ui'
BASELINE='nodes_coarse_ui'

def dig(x:Any)->str: return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def desc(board,action,mode):
    b=r275.canon_board(board,action,use_ui_mask=True)
    kind='nodes_exact' if mode==MODE else 'nodes_coarse'
    return r274.desc(b,kind)

def rec(r,mode):
    ac=r275.action_class(r['action'])
    return (dig(desc(r['before'],r['action'],mode)),ac,dig(desc(r['after'],r['action'],mode)))

def fit(records):
    obs=defaultdict(Counter)
    for before,ac,after in records: obs[(before,ac)][after]+=1
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    return tab,{'keys':len(obs),'deterministic_keys':len(tab),'ambiguous_keys':sum(len(v)>1 for v in obs.values())}

def ev(records,tab):
    s=Counter(); wrong_rows=[]
    for row,(before,ac,after) in records:
        s['transitions']+=1; pred=tab.get((before,ac))
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1
        if pred==after: s['correct']+=1
        else:
            s['wrong']+=1
            wrong_rows.append({'trace':row['trace'],'pnum':row['_pnum'],'trace_row':row['_row'],'action':row['action'],'prev_action':row.get('_prev_action'),'pred':pred,'actual':after})
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None
    return dict(s),wrong_rows

def annotate(paths):
    out=[]
    for p in paths:
        prev=None
        for i,row in enumerate(r268.rows([p])):
            rr=dict(row); rr['_pnum']=r246.pnum(p); rr['_row']=i; rr['_prev_action']=prev; prev=row['action']; out.append(rr)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if len(ps)!=20 or any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(20)): raise SystemExit('exact m0r0 p0-p19 required')
    train=annotate(ps[:10]); replay=annotate(ps[10:])
    results={}
    for mode in (BASELINE,MODE):
        tr=[rec(r,mode) for r in train]
        rp=[(r,rec(r,mode)) for r in replay]
        tab,fs=fit(tr); es,wr=ev(rp,tab)
        results[mode]={'fit':fs,'replay':es,'wrong_rows':wr}
    b=results[BASELINE]['replay']; x=results[MODE]['replay']
    repair=(int(b.get('wrong',0))==1 and int(x.get('wrong',0))==0 and int(x.get('correct',0))>=int(b.get('correct',0)) and int(x.get('predictions',0))>=math.ceil(.95*int(b.get('predictions',0))))
    verdict='REPAIR_SIGNAL_PUBLIC_DEV_INFORMED' if repair else 'NO_REPAIR_SIGNAL'
    out={'schema':'deus/arc3-r279-m0r0-exact-node-replay/1','rung':279,'game':GAME,
      'lineage':{'r276_run':35809358813,'r277_run':35810307244,'r278_run':35811044277,'r278_head':'244f3be5e6c85fe98330a2d8e448bf836765dd1c','selected_mode':MODE},
      'protocol':{'fit':'p0-p9','replay':'p10-p19 reused public-development','representation_frozen_from_r278_before_r279_p10_p19_read':True,'p10_p19_updates_model':False,'p10_p19_updates_representation_in_r279':False},
      'results':results,'verdict':verdict,
      'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'public_development_informed_by_r277':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r279':False,'solver_promotion':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'baseline':b,'exact':x,'baseline_wrong_rows':results[BASELINE]['wrong_rows'],'exact_wrong_rows':results[MODE]['wrong_rows']},sort_keys=True))
if __name__=='__main__': main()
