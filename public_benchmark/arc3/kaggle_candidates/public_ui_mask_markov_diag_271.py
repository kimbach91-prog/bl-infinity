#!/usr/bin/env python3
"""R271: harness-repaired equivalent of R268 static UI-mask Markov diagnostic.

R268 accidentally routed every frame through the full R251 six-lens feature
extractor although this diagnostic only needs state digests. R271 preserves the
same data split and representation exactly, but decodes each trace once and
computes only raw/UI-masked digests. No solver semantics or selection rule is
changed.

Protocol: p0-p4 fit; p5-p9 diagnostic eval; p10-p19 are not read.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=271
SENTINEL=16
SOURCE_REF='shloksah/arc-agi-3-agent@7dccef15650fa00ef1db1c21cc7279adcf4a9e2a:core/frugal_explorer.py'


def masked(board):
    x=[list(map(int,row)) for row in board]
    if not x or not x[0]: return x
    h,w=len(x),len(x[0])
    for r in range(h):
        x[r][0]=SENTINEL
        if w>1: x[r][w-1]=SENTINEL
    for r in {0,1,h-1}:
        if 0<=r<h:
            for c in range(w): x[r][c]=SENTINEL
    return x


def prep(path:Path):
    ev=r246.load_events(path); rows=[]; pre=ev[0]
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        before=[[int(v) for v in row] for row in pre['board']]
        after=[[int(v) for v in row] for row in e['board']]
        if len(before)==len(after) and before and after and len(before[0])==len(after[0]):
            rows.append({
                'action':r246.action_name(e),
                'raw_before':r246.digest(before),
                'raw_after':r246.digest(after),
                'mask_before':r246.digest(masked(before)),
                'mask_after':r246.digest(masked(after)),
            })
        pre=e
    return rows


def fit(rows,mode):
    obs=defaultdict(Counter); states=set(); bp='mask_before' if mode=='ui_mask' else 'raw_before'; ap='mask_after' if mode=='ui_mask' else 'raw_after'
    for r in rows:
        states.add(r[bp]); obs[(r[bp],r['action'])][r[ap]]+=1
    tab={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    return tab,{'unique_before_states':len(states),'state_action_keys':len(obs),'deterministic_keys':len(tab),'ambiguous_keys':sum(len(c)>1 for c in obs.values()),'deterministic_fraction':round(len(tab)/len(obs),6) if obs else 0.0}


def evaluate(rows,tab,mode):
    s=Counter(); bp='mask_before' if mode=='ui_mask' else 'raw_before'; ap='mask_after' if mode=='ui_mask' else 'raw_after'
    for r in rows:
        s['transitions']+=1; pred=tab.get((r[bp],r['action']))
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1; s['correct' if pred==r[ap] else 'wrong']+=1
    p=s['predictions']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/s['transitions'],6) if s['transitions'] else 0.0}


def game(paths):
    ps=sorted(paths,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(nums)
    parts=[prep(p) for p in ps]; tr=[r for x in parts[:5] for r in x]; va=[r for x in parts[5:] for r in x]
    out={}
    for mode in ('raw','ui_mask'):
        tab,fs=fit(tr,mode); out[mode]={'fit':fs,'validation':evaluate(va,tab,mode)}
    rv,mv=out['raw']['validation'],out['ui_mask']['validation']
    out['delta']={'correct':int(mv.get('correct',0))-int(rv.get('correct',0)),'wrong':int(mv.get('wrong',0))-int(rv.get('wrong',0)),'predictions':int(mv.get('predictions',0))-int(rv.get('predictions',0)),'unique_train_states':out['ui_mask']['fit']['unique_before_states']-out['raw']['fit']['unique_before_states']}
    out['signal']=bool(out['delta']['correct']>0 and int(mv.get('wrong',0))<=int(rv.get('wrong',0)))
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:game(ps) for g,ps in sorted(by.items())}; signal=[g for g,x in games.items() if x['signal']]
    agg=Counter()
    for x in games.values():
        for mode in ('raw','ui_mask'):
            for k in ('transitions','predictions','correct','wrong','abstain'): agg[f'{mode}_{k}']+=int(x[mode]['validation'].get(k,0) or 0)
    rp,mp=agg['raw_predictions'],agg['ui_mask_predictions']; ad=dict(agg); ad['raw_accuracy']=round(agg['raw_correct']/rp,6) if rp else None; ad['ui_mask_accuracy']=round(agg['ui_mask_correct']/mp,6) if mp else None; ad['correct_delta']=agg['ui_mask_correct']-agg['raw_correct']; ad['wrong_delta']=agg['ui_mask_wrong']-agg['raw_wrong']
    out={'schema':'deus/arc3-r271-ui-mask-markov-harness-repair/1','rung':RUNG,'semantics_equivalent_to':'R268 static UI mask diagnostic','repair':'remove unnecessary R251 six-lens frame_features; digest-only decode','source_grounding':{'reference':SOURCE_REF,'idea':'freeze/remove engine UI border pixels from state hashing','implementation':'independent diagnostic implementation; no upstream runtime/score imported'},'protocol':{'fit':'p0-p4','diagnostic_eval':'p5-p9','p10_p19_read':False,'metric':'next normalized-state-key prediction, not full-frame rendering','promotion':False},'aggregate':ad,'signal_games':signal,'games':games,'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'source_assisted_idea':True,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'aggregate':ad,'signal_games':signal},sort_keys=True))

if __name__=='__main__': main()
