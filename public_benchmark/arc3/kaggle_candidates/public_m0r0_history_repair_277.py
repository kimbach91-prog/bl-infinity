#!/usr/bin/env python3
"""R277 bounded action-history repair for the single R276 m0r0 mismatch.

Falsifier: R276's frozen action-canonical representation produced 1484 correct / 1 wrong
on reused public-development p10-p19 for m0r0. This rung does not threshold-retune the
static representation. It tests a materially different, bounded temporal context inspired
by public event-history work:
  zzZYHarold/arc-agi-3-ls20-agent@bcf25348fd88fddbaaabb5c332f6bf3bb3a3fb60
  src/ls20/event_history.py

Protocol:
  * representation family fixed before runtime: previous 1-2 actions, either raw or
    expressed relative to the current action after the same rotation used by R275;
  * p0-p4 fit, p5-p9 chooses at most one history variant using zero-wrong + >=95% of
    R275 base validation correct; no p10-p19 values participate in variant selection;
  * selected history variant is refit on p0-p9 then evaluated on p10-p19;
  * p10-p19 is reused public development and the family hypothesis was motivated by the
    known R276 mismatch, so any gain is SOURCE-ASSISTED PUBLIC REPAIR, not independent
    generalization and not Kaggle evidence.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_action_canonical_topology_diag_275 as r275

GAME='m0r0-492f87ba'
BASE_MODE='canon_nodes_ui'
SOURCE_REF='zzZYHarold/arc-agi-3-ls20-agent@bcf25348fd88fddbaaabb5c332f6bf3bb3a3fb60:src/ls20/event_history.py'
DIRS={'UP':(-1,0),'DOWN':(1,0),'LEFT':(0,-1),'RIGHT':(0,1)}
INV={v:k for k,v in DIRS.items()}
VARIANTS=('prev1_rel','prev2_rel','prev1_raw','prev2_raw')


def rotate_vec(v, current):
    dr,dc=v
    if current=='UP': return dr,dc
    if current=='DOWN': return -dr,-dc
    if current=='LEFT': return dc,-dr
    if current=='RIGHT': return -dc,dr
    return dr,dc


def relative_action(prev,current):
    p=str(prev).upper() if prev else '<START>'
    c=str(current).upper()
    if p not in DIRS or c not in DIRS: return p
    return INV[rotate_vec(DIRS[p],c)]


def annotated_rows(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        rs=r251.prepare_rows([p])
        hist=[]
        for idx,r in enumerate(rs):
            x=dict(r)
            x['_idx']=idx
            x['_prev1']=hist[-1] if len(hist)>=1 else '<START>'
            x['_prev2']=hist[-2] if len(hist)>=2 else '<START>'
            out.append(x)
            hist.append(str(r['action']).upper())
    return out


def state_action_base(r):
    return r275.key(r['before'],r['action'],BASE_MODE)


def next_digest(r):
    return r275.key(r['after'],r['action'],BASE_MODE)[0]


def k_for(r,variant):
    d,ac=state_action_base(r)
    if variant=='base': return (d,ac)
    cur=str(r['action']).upper()
    if variant=='prev1_rel': return (d,ac,relative_action(r['_prev1'],cur))
    if variant=='prev2_rel': return (d,ac,relative_action(r['_prev2'],cur),relative_action(r['_prev1'],cur))
    if variant=='prev1_raw': return (d,ac,r['_prev1'])
    if variant=='prev2_raw': return (d,ac,r['_prev2'],r['_prev1'])
    raise KeyError(variant)


def fit(rows,variant):
    obs=defaultdict(Counter)
    for r in rows: obs[k_for(r,variant)][next_digest(r)]+=1
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    return tab,{'keys':len(obs),'deterministic':len(tab),'ambiguous':sum(len(v)>1 for v in obs.values())}


def evaluate(rows,tab,variant,include_wrong=False):
    s=Counter(); wrongs=[]
    for r in rows:
        s['transitions']+=1; k=k_for(r,variant); pred=tab.get(k)
        if pred is None:
            s['abstain']+=1; continue
        s['predictions']+=1; actual=next_digest(r); ok=pred==actual
        s['correct' if ok else 'wrong']+=1
        if include_wrong and not ok:
            wrongs.append({'trace':r['trace'],'row_index':r['_idx'],'action':r['action'],'prev2':r['_prev2'],'prev1':r['_prev1'],'key':repr(k),'predicted':pred,'actual':actual})
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None
    return dict(s),wrongs


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if not ps or any(r246.game_id(p)!=GAME for p in ps): raise SystemExit('exact m0r0 traces required')
    if [r246.pnum(p) for p in ps]!=list(range(20)): raise SystemExit('exact p0-p19 required')
    parts={r246.pnum(p):annotated_rows([p]) for p in ps}
    tr=[r for i in range(5) for r in parts[i]]
    va=[r for i in range(5,10) for r in parts[i]]
    fitall=[r for i in range(10) for r in parts[i]]
    ho=[r for i in range(10,20) for r in parts[i]]

    base_tab,base_fit=fit(tr,'base'); base_val,_=evaluate(va,base_tab,'base')
    diagnostic={}; eligible=[]
    floor_correct=max(1,int(0.95*int(base_val.get('correct',0))))
    for v in VARIANTS:
        tab,fs=fit(tr,v); met,_=evaluate(va,tab,v)
        diagnostic[v]={'fit':fs,'validation':met}
        if int(met.get('wrong',0))==0 and int(met.get('correct',0))>=floor_correct and int(met.get('predictions',0))>0:
            eligible.append(v)
    chosen=None
    if eligible:
        chosen=sorted(eligible,key=lambda v:(-int(diagnostic[v]['validation'].get('correct',0)),-int(diagnostic[v]['validation'].get('predictions',0)),VARIANTS.index(v)))[0]

    base_all,_=fit(fitall,'base'); base_hold,base_wrongs=evaluate(ho,base_all,'base',True)
    chosen_hold=None; chosen_wrongs=[]
    if chosen:
        tab,_=fit(fitall,chosen); chosen_hold,chosen_wrongs=evaluate(ho,tab,chosen,True)

    if chosen is None:
        verdict='HOLD_NO_EARLY_HISTORY_DISCRIMINATOR'
    elif int(chosen_hold.get('wrong',0))==0 and int(chosen_hold.get('correct',0))>=int(base_hold.get('correct',0))-2:
        verdict='PROMOTE_SOURCE_ASSISTED_HISTORY_REPAIR'
    else:
        verdict='NO_PROMOTION'

    out={
      'schema':'deus/arc3-r277-m0r0-history-repair/1','rung':277,'game':GAME,
      'source_grounding':{'reference':SOURCE_REF,'idea':'bounded recent event/action history as temporal causal context','implementation':'independent minimal action-history diagnostic; no upstream runtime or score imported'},
      'falsifier':{'r276_run':35809358813,'r276_artifact':10729595370,'base_holdout':'1484 correct / 1 wrong / 1485 predictions'},
      'protocol':{'fit':'p0-p4','variant_selection':'p5-p9 only','refit':'p0-p9','evaluation':'p10-p19 reused public development','p10_p19_selects_variant':False,'family_hypothesis_motivated_by_known_r276_mismatch':True},
      'base_validation':base_val,'base_fit':base_fit,'validation_floor_correct':floor_correct,'diagnostic':diagnostic,'eligible_variants':eligible,'chosen_variant':chosen,
      'base_public_development':base_hold,'base_wrong_examples':base_wrongs,
      'chosen_public_development':chosen_hold,'chosen_wrong_examples':chosen_wrongs,
      'verdict':verdict,
      'truth':{'public_trace_only':True,'source_assisted_repair':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r277':False,'full_game_solver_claim':False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'base_validation':base_val,'eligible':eligible,'chosen':chosen,'base_holdout':base_hold,'chosen_holdout':chosen_hold,'base_wrongs':base_wrongs,'chosen_wrongs':chosen_wrongs},sort_keys=True))

if __name__=='__main__': main()
