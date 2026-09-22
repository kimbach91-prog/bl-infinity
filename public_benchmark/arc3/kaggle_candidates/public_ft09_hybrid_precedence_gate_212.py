#!/usr/bin/env python3
"""R212: ft09 hybrid precedence gate.

Combine two already-frozen p0-p9 mappings from R211:
  1) ring2 relational mapping when available
  2) R208/base mapping as fallback

No p10-p19 outcome updates either table. The purpose is to test whether the
higher-specificity ring2 key safely overrides the two known base conflicts while
retaining the broader base coverage. This remains iterative public-heldout
mechanism research, not hidden generalization or Kaggle promotion.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path
import public_ft09_ring2_relational_gate_211 as r211

RUNG=212
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    tr=[r for p in ps[:10] for r in r211.rows(p)]
    he=[r for p in ps[10:] for r in r211.rows(p)]
    basefn=lambda r:r['base']
    ringfn=lambda r:(r['base'],r['ring2'])
    bt,bobs=r211.fit(tr,basefn)
    rt,robs=r211.fit(tr,ringfn)

    s=Counter(); mistakes=[]; overrides=[]
    for r in he:
        s['eligible']+=1
        bk=repr(basefn(r)); rk=repr(ringfn(r))
        bp=bt.get(bk); rp=rt.get(rk)
        if rp is not None:
            pred=rp; src='ring2'; s['ring2_predictions']+=1
            if bp is not None:
                s['overlap_predictions']+=1
                if bp!=rp:
                    s['disagreement_overrides']+=1
                    if len(overrides)<20:
                        overrides.append({
                          'trace':r['trace'],'p':r['p'],'step':r['step'],
                          'current':r['current'],'target':r['target'],
                          'base_pred':bp,'ring2_pred':rp,
                          'base_correct':bp==r['target'],'ring2_correct':rp==r['target'],
                          'base':r['base'],'ring2':r['ring2'],
                        })
        elif bp is not None:
            pred=bp; src='base'; s['base_fallback_predictions']+=1
        else:
            s['abstain']+=1
            continue
        s['predictions']+=1
        s[f'{src}_used']+=1
        if pred==r['target']:
            s['correct']+=1
        else:
            s['wrong']+=1
            if len(mistakes)<20:
                mistakes.append({
                  'trace':r['trace'],'p':r['p'],'step':r['step'],
                  'current':r['current'],'target':r['target'],'pred':pred,
                  'source':src,'base':r['base'],'ring2':r['ring2'],
                  'base_pred':bp,'ring2_pred':rp,
                })
    p=s['predictions']; eligible=s['eligible']
    metrics={**dict(s),
      'accuracy':round(s['correct']/p,6) if p else None,
      'coverage':round(p/eligible,6) if eligible else 0.0}
    gate=bool(
      metrics.get('predictions',0)>=373 and
      metrics.get('wrong',0)==0 and
      (metrics.get('accuracy') or 0)>=0.999 and
      metrics.get('coverage',0)>=0.408
    )
    return {
      'schema':'deus/arc3-ft09-hybrid-precedence-gate/1',
      'rung':RUNG,'game':GAME,
      'protocol':{
        'fit':'p0-p9 only',
        'precedence':'ring2 deterministic mapping > base deterministic mapping > abstain',
        'heldout':'p10-p19 frozen; no table updates',
        'gate':'predictions>=373 AND wrong=0 AND accuracy>=0.999 AND coverage>=0.408',
      },
      'train':{
        'base_values':len(bobs),'base_deterministic_values':len(bt),
        'ring2_values':len(robs),'ring2_deterministic_values':len(rt),
      },
      'heldout':metrics,
      'disagreement_overrides':overrides,
      'mistakes':mistakes,
      'mechanism_gate_pass':gate,
      'promotion':{
        'mechanism_gate':gate,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'reason':'target-color selector only; full-frame state transition/rendering and policy remain unresolved',
      },
      'truth':{
        'public_trace_only':True,
        'iterative_public_heldout_research':True,
        'heldout_never_updates_model':True,
        'independent_generalization_claim':False,
        'pre_action_selector_only':True,
        'full_frame_solver_claim':False,
        'kaggle_execution':False,
        'submission_quota_spent':False,
        'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    d=run(a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'heldout':d['heldout'],
      'gate':d['mechanism_gate_pass'],
      'overrides':d['disagreement_overrides'],
      'promotion':d['promotion'],
    },sort_keys=True))
if __name__=='__main__':main()
