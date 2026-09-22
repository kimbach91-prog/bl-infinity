#!/usr/bin/env python3
"""R258: source-free temporal conditioning diagnostic for g50t delta signatures.

R253 found substantial repeated normalized delta signatures in g50t, while R254
showed that static action+visible-component anchoring does not transfer. R258
asks the next discriminating question: does short action history materially
increase the predictability of the observed normalized transition-delta class?

Protocol is diagnostic-only and uses p0-p9 public-development traces:
  p0-p4 fit modal delta signature per context
  p5-p9 evaluate exact signature prediction and coverage
Contexts compared: action, action+prev action, action+prev2, action+run bucket.
No p10-p19, game source, hidden outcome, Kaggle execution or score is read.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_transition_morphology_diag_253 as r253

RUNG=258
CTX=("action","prev1","prev2","run")

def run_bucket(n:int)->str:
    if n<=1:return "1"
    if n==2:return "2"
    if n<=4:return "3-4"
    return "5+"

def extract(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        ev=r246.load_events(p); pre=ev[0]; hist=[]; same_run=0; last=None; step=0
        for e in ev[1:]:
            if e.get('type')!='action': pre=e; continue
            b=[[int(v) for v in row] for row in pre['board']]
            a=[[int(v) for v in row] for row in e['board']]
            act=r246.action_name(e)
            if act==last: same_run+=1
            else: same_run=1
            if len(b)==len(a) and len(b[0])==len(a[0]):
                d=r253.transition_diag(b,a)
                out.append({
                    'trace':p.name,'step':step,'action':act,
                    'prev1':hist[-1] if hist else 'START',
                    'prev2':hist[-2] if len(hist)>=2 else 'START2',
                    'run_bucket':run_bucket(same_run),
                    'delta_sig':d['delta_sig'],'changed':d['changed']
                })
                step+=1
            hist.append(act); last=act; pre=e
    return out

def key(r,mode):
    if mode=='action': return (r['action'],)
    if mode=='prev1': return (r['action'],r['prev1'])
    if mode=='prev2': return (r['action'],r['prev1'],r['prev2'])
    if mode=='run': return (r['action'],r['run_bucket'])
    raise KeyError(mode)

def fit(rows,mode):
    obs=defaultdict(Counter); trace_support=defaultdict(lambda:defaultdict(set))
    for r in rows:
        if r['changed']==0: continue
        k=key(r,mode); s=r['delta_sig']; obs[k][s]+=1; trace_support[k][s].add(r['trace'])
    model={}
    for k,c in obs.items():
        # Pick deterministic modal signature; require evidence from >=2 train traces.
        ranked=sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))
        s,n=ranked[0]
        if len(trace_support[k][s])>=2:
            model[k]=s
    return model

def evaluate(rows,model,mode):
    s=Counter(); by_action=defaultdict(Counter)
    for r in rows:
        if r['changed']==0:
            s['identity_skipped']+=1; continue
        s['nonidentity']+=1; by_action[r['action']]['nonidentity']+=1
        k=key(r,mode)
        if k not in model:
            s['abstain']+=1; by_action[r['action']]['abstain']+=1; continue
        s['predictions']+=1; by_action[r['action']]['predictions']+=1
        ok=model[k]==r['delta_sig']
        s['correct' if ok else 'wrong']+=1; by_action[r['action']]['correct' if ok else 'wrong']+=1
    n=s['predictions']; opp=s['nonidentity']
    return {**dict(s),'accuracy':round(s['correct']/n,6) if n else None,
            'coverage':round(n/opp,6) if opp else 0.0,
            'correct_coverage':round(s['correct']/opp,6) if opp else 0.0,
            'by_action':{a:dict(v) for a,v in sorted(by_action.items())}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    train=extract(ps[:5]); val=extract(ps[5:])
    modes={}
    for mode in CTX:
        m=fit(train,mode); modes[mode]={'model_size':len(m),'validation':evaluate(val,m,mode)}
    base=modes['action']['validation']['correct_coverage']
    for mode in CTX:
        modes[mode]['correct_coverage_delta_vs_action']=round(modes[mode]['validation']['correct_coverage']-base,6)
    best=max(CTX,key=lambda m:(modes[m]['validation']['correct_coverage'],modes[m]['validation']['accuracy'] or 0,m))
    out={'schema':'deus/arc3-r258-temporal-delta-diagnostic/1','rung':RUNG,
         'protocol':{'fit':'p0-p4','validation':'p5-p9','identity_skipped':True,'min_modal_trace_support':2,'promotion':False},
         'modes':modes,'best_mode':best,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'best_mode':best,'modes':{m:modes[m]['validation'] for m in CTX}},sort_keys=True))
if __name__=='__main__': main()
