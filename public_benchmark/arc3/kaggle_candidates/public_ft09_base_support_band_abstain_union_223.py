#!/usr/bin/env python3
"""R223: p0-p9-selected deterministic base-support band expert for ft09.

R221/R222 showed deterministic base support>=2 adds useful coverage but two
heldout errors both occur at full-training support=3. R223 does NOT hardcode a
heldout-derived support choice. Instead it enumerates support bands over {2,3,4}
and uses leave-one-trace-out p0-p9 target CV on the residual domain after the
verified base-support>=5 fallback.

Candidate bands:
  {2}, {3}, {4}, {2,3}, {2,4}, {3,4}, {2,3,4}

Selection priority:
  1) zero wrong,
  2) higher accuracy,
  3) more correct,
  4) more predictions,
  5) fewer allowed support values,
  6) deterministic lexical tie-break.

Heldout band expert fires only after R218 and R219 abstain and renders local
clicked-6x6 recolor only. Every output is exact-scored on gameplay rows0..62.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_low_support_base_abstain_union_221 as r221

RUNG=223
GAME='ft09-0d8bbf25'
INCUMBENT_BASE_MIN=5
BANDS=((2,),(3,),(4,),(2,3),(2,4),(3,4),(2,3,4))

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def band_predict(r,tab,band):
    b=tab.get(repr(r['base']))
    if not b:return None
    sup=int(b['support'])
    if sup>=INCUMBENT_BASE_MIN or sup not in band:return None
    return b['pred']

def cv_band(trace_rows,band):
    s=Counter();folds=[]
    for hold in range(10):
        train=[r for i in range(10) if i!=hold for r in trace_rows[i]]
        test=trace_rows[hold]
        bt=cv212.fit(train,'base')
        f=Counter()
        for r in test:
            f['eligible']+=1
            pred=band_predict(r,bt,band)
            if pred is None:
                f['abstain']+=1;continue
            f['predictions']+=1
            if pred==r['target']:f['correct']+=1
            else:f['wrong']+=1
        for k in ('eligible','abstain','predictions','correct','wrong'):s[k]+=f[k]
        folds.append({'hold':hold,**{k:int(f[k]) for k in ('predictions','correct','wrong')}})
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage_all':round(p/e,6) if e else 0.0,'folds':folds}

def select_band(train_paths):
    trace_rows=[[r for r in r211.rows(p)] for p in train_paths]
    cand={','.join(map(str,b)):cv_band(trace_rows,b) for b in BANDS}
    def key(item):
        name,x=item
        band=tuple(map(int,name.split(',')))
        acc=x['accuracy'] or 0.0
        return (x.get('wrong',0),-acc,-x.get('correct',0),-x.get('predictions',0),len(band),name)
    ranking=[name for name,_ in sorted(cand.items(),key=key)]
    sel=ranking[0]
    return {'config':sel,'band':tuple(map(int,sel.split(','))),'cv':cand[sel],
            'ranking':ranking,'candidates':cand}

def build_models(train):
    m=r221.build_models(train)
    # R221's selected threshold is not used for the new band; retain base and
    # all high-confidence R218/R219 models, replace only low-support policy.
    m['band_policy']=select_band(train)
    return m

def lowband_local_only(r,m):
    tgt=band_predict(r,m['base'],m['band_policy']['band'])
    if tgt is None:return None,None
    pred=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
    return gp(pred),'r223_lowband_local_only'

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:];m=build_models(train)

    s=Counter();stage=defaultdict(Counter);wrong=[];added=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,branch=r221.r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch=lowband_local_only(r,m);stage_name='r223_lowband'
            if pred is None:
                s['abstain']+=1;continue

            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1
            if stage_name=='r223_lowband' and len(added)<80:
                b=m['base'].get(repr(r['base']))
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'action':r['action'],'correct':ok,
                              'base_support':int(b['support']) if b else None})
            if not ok and len(wrong)<40:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'stage':stage_name,'action':r['action']})

    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0,dict(stage['r219_base5'])

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r223_lowband'];gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and
              s.get('wrong',0)==0 and gain>0)
    pol=m['band_policy']
    return {
      'schema':'deus/arc3-ft09-base-support-band-abstain-union/1',
      'rung':RUNG,'game':GAME,
      'policy':{
        'config':pol['config'],'allowed_supports':list(pol['band']),
        'cv':{k:pol['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
        'ranking':pol['ranking'],
        'candidate_summary':{k:{x:v.get(x) for x in ('predictions','correct','wrong','accuracy','coverage_all')}
                             for k,v in pol['candidates'].items()},
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'r223_added_examples':added,'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'r218_precedence_preserved':True,
        'r219_base5_precedence_preserved':True,
        'support_band_selected_p0_p9_loto_only':True,
        'r223_only_after_r218_r219_abstain':True,
        'r223_local_recolor_only':True,
        'heldout_never_updates_policy_or_models':True,
        'exact_gameplay_rows0_62_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'policy':d['policy'],'heldout':d['heldout']['all'],
                      'stages':d['heldout']['stage_metrics'],'added':d['heldout']['r223_added_examples'],
                      'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
