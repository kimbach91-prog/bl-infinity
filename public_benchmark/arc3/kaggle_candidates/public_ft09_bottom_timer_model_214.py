#!/usr/bin/env python3
"""R214: ft09 bottom-HUD/timer transition model with frozen heldout gate.

R213 proved a bottom countdown rule is material but the naive "rightmost pair
12->11 every predicted action" over-decrements in 62/282 ring2 cases.

R214 learns ONLY the bottom-row transition from p0-p9, selecting a compact
pre-action feature family on p0-p4 -> p5-p9 validation, then refitting p0-p9
and freezing on p10-p19. The target is the exact post-action bottom row.

No gameplay target-color or full-frame model is changed here.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212

RUNG=214
GAME='ft09-0d8bbf25'
FAMILIES=('exact','rle','counts_edges','counts','remaining12')

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def rle(row):
    out=[]
    for v in row:
        if out and out[-1][0]==v: out[-1][1]+=1
        else: out.append([int(v),1])
    return tuple((a,b) for a,b in out)

def edges(row,v):
    xs=[i for i,x in enumerate(row) if x==v]
    return (len(xs), xs[0] if xs else -1, xs[-1] if xs else -1)

def feature(fam,row):
    c=Counter(row)
    if fam=='exact': return tuple(row)
    if fam=='rle': return rle(row)
    if fam=='counts_edges':
        return (tuple(sorted((int(k),int(v)) for k,v in c.items())), edges(row,12), edges(row,11))
    if fam=='counts': return tuple(sorted((int(k),int(v)) for k,v in c.items()))
    if fam=='remaining12': return (int(c[12]),int(c[11]))
    raise ValueError(fam)

def rows(path:Path):
    for r in r212.all_rows(path):
        if not r['eligible']: continue
        before=tuple(r['before'][-1]); after=tuple(r['after'][-1])
        yield {
          'trace':r['path'],'p':r['p'],'step0':r['step0'],
          'before':before,'after':after,
          'changed':before!=after,
          'delta_count':sum(a!=b for a,b in zip(before,after)),
          'pairs':dict(Counter(f'{a}->{b}' for a,b in zip(before,after) if a!=b)),
        }

def fit(rs,fam,min_traces=2):
    obs=defaultdict(lambda:{'outs':Counter(),'traces':set()})
    for r in rs:
        k=repr(feature(fam,r['before']))
        obs[k]['outs'][r['after']]+=1
        obs[k]['traces'].add(r['trace'])
    model={}
    for k,x in obs.items():
        if len(x['outs'])==1 and len(x['traces'])>=min_traces:
            model[k]=next(iter(x['outs']))
    return model,obs

def evaluate(rs,model,fam):
    s=Counter(); mistakes=[]; deltas=Counter()
    for r in rs:
        s['eligible']+=1
        deltas[r['delta_count']]+=1
        pred=model.get(repr(feature(fam,r['before'])))
        if pred is None:
            s['abstain']+=1; continue
        s['predictions']+=1
        if pred==r['after']:
            s['correct']+=1
        else:
            s['wrong']+=1
            if len(mistakes)<30:
                mistakes.append({
                  'trace':r['trace'],'p':r['p'],'step0':r['step0'],
                  'delta_count':r['delta_count'],'pairs':r['pairs'],
                  'before_rle':rle(r['before']),'actual_after_rle':rle(r['after']),
                  'pred_after_rle':rle(pred),
                })
    p=s['predictions'];e=s['eligible']
    return {
      **dict(s),
      'accuracy':round(s['correct']/p,6) if p else None,
      'coverage':round(p/e,6) if e else 0.0,
      'actual_delta_hist':{str(k):int(v) for k,v in sorted(deltas.items())},
      'mistakes':mistakes,
    }

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    tr=[x for p in ps[:5] for x in rows(p)]
    va=[x for p in ps[5:10] for x in rows(p)]
    ft=[x for p in ps[:10] for x in rows(p)]
    ho=[x for p in ps[10:] for x in rows(p)]
    configs={}
    for fam in FAMILIES:
        m,_=fit(tr,fam)
        configs[fam]={'model_keys':len(m),'validation':evaluate(va,m,fam)}
    def rank(item):
        fam,d=item;v=d['validation']
        return (v.get('wrong',0),-v.get('correct',0),-v.get('coverage',0.0),fam)
    selected=sorted(configs.items(),key=rank)[0][0]
    frozen,_=fit(ft,selected)
    held=evaluate(ho,frozen,selected)
    gate=bool(held.get('predictions',0)>=100 and held.get('wrong',0)==0 and (held.get('accuracy') or 0)>=0.99)
    return {
      'schema':'deus/arc3-ft09-bottom-timer-model/1','rung':RUNG,'game':GAME,
      'protocol':{'inner_train':'p0-p4','inner_validation':'p5-p9','refit':'p0-p9','heldout':'p10-p19','min_trace_support':2},
      'configs':configs,'selected':selected,'frozen_model_keys':len(frozen),
      'heldout':held,'timer_gate_pass':gate,
      'promotion':{'timer_mechanism_gate':gate,'full_frame_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'same_game_public_heldout':True,
        'family_selection_uses_only_p0_p9':True,'heldout_never_updates_model':True,
        'bottom_row_only':True,'independent_generalization_claim':False,
        'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'selected':d['selected'],'configs':{k:{x:v['validation'].get(x) for x in ('predictions','correct','wrong','accuracy','coverage')} for k,v in d['configs'].items()},'heldout':{k:d['heldout'].get(k) for k in ('eligible','predictions','correct','wrong','accuracy','coverage','actual_delta_hist')},'gate':d['timer_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
