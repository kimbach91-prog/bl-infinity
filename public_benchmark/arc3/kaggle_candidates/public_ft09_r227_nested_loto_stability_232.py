#!/usr/bin/env python3
"""R232: nested LOTO stability audit for the R227 coarse-local confidence family.

Truth boundary
--------------
p10-p19 has already been reused during R227-R231 falsifier-driven development,
so it is NOT an independent heldout set anymore. R232 therefore does not use
p10-p19 to select or validate a promotable confidence gate.

Instead R232 runs a fully nested procedure on p0-p9:
  * OUTER LOTO: one trace is held completely outside selection+fit.
  * INNER LOTO on the remaining 9 traces selects family + min_trace_support
    from the original R227 search space using exact gameplay-frame correctness.
  * The selected config is refit on the 9 outer-training traces and scored on
    the untouched outer trace.

Separately, a full p0-p9 LOTO table selects one final source-assisted config.
That config may be shown on reused p10-p19 only as NON-INDEPENDENT development
corroboration; those outcomes cannot promote the solver.

This rung validates methodology stability, not Kaggle score or independent
generalization.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_coarse_local_target_gate_227 as r227

RUNG=232
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def add_metrics(total,met):
    for k in ('eligible','abstain','predictions','correct','wrong'):
        total[k]+=int(met.get(k,0) or 0)

def pack(total):
    p=total['predictions'];e=total['eligible']
    return {
      **dict(total),
      'accuracy':round(total['correct']/p,6) if p else None,
      'coverage':round(p/e,6) if e else 0.0,
    }

def loto_score(paths,fam,sup):
    total=Counter();folds=[]
    for hold in range(len(paths)):
        tr=[p for i,p in enumerate(paths) if i!=hold]
        va=[paths[hold]]
        tab,_=r227.fit(tr,fam,sup)
        met=r227.eval_plain(va,tab,fam)
        add_metrics(total,met)
        folds.append({
          'hold_p':pnum(paths[hold]),
          'predictions':met.get('predictions',0),
          'correct':met.get('correct',0),
          'wrong':met.get('wrong',0),
          'coverage':met.get('coverage',0.0),
        })
    return {**pack(total),'folds':folds}

def select_by_loto(paths):
    cand={}
    famrank={f:i for i,f in enumerate(r227.FAMILIES)}
    for fam in r227.FAMILIES:
        for sup in r227.SUPPORTS:
            name=f'{fam}|t{sup}'
            cand[name]={
              'family':fam,'min_traces':sup,
              'loto':loto_score(paths,fam,sup),
            }
    zero=[(k,v) for k,v in cand.items()
          if v['loto'].get('predictions',0)>0 and v['loto'].get('wrong',0)==0]
    if not zero:
        return None,cand
    zero.sort(key=lambda kv:(
      -kv[1]['loto'].get('correct',0),
      -kv[1]['loto'].get('predictions',0),
      -kv[1]['min_traces'],
      famrank[kv[1]['family']],
      kv[0],
    ))
    return zero[0][0],cand

def nested_outer(paths):
    rows=[];agg=Counter();selected=Counter()
    for outer in range(len(paths)):
        pool=[p for i,p in enumerate(paths) if i!=outer]
        held=[paths[outer]]
        cfg,cand=select_by_loto(pool)
        if cfg is None:
            rows.append({'hold_p':pnum(paths[outer]),'selected':None,'status':'NO_ZERO_WRONG_INNER_CONFIG'})
            continue
        fam=cand[cfg]['family'];sup=cand[cfg]['min_traces']
        tab,_=r227.fit(pool,fam,sup)
        met=r227.eval_plain(held,tab,fam)
        add_metrics(agg,met);selected[cfg]+=1
        rows.append({
          'hold_p':pnum(paths[outer]),
          'selected':cfg,
          'inner_loto':{k:cand[cfg]['loto'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')},
          'outer':{k:met.get(k) for k in ('eligible','predictions','correct','wrong','accuracy','coverage')},
        })
    return {
      'aggregate_outer':pack(agg),
      'selected_config_counts':dict(selected),
      'folds':rows,
    }

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')

    train=ps[:10];dev=ps[10:]

    nested=nested_outer(train)
    final_cfg,allcand=select_by_loto(train)

    final=None
    if final_cfg is not None:
        fam=allcand[final_cfg]['family'];sup=allcand[final_cfg]['min_traces']
        tab,_=r227.fit(train,fam,sup)
        dev_met=r227.eval_plain(dev,tab,fam)
        final={
          'config':final_cfg,
          'family':fam,
          'min_traces':sup,
          'p0_p9_loto':{k:allcand[final_cfg]['loto'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')},
          'p10_p19_reused_development_only':{k:dev_met.get(k) for k in ('eligible','predictions','correct','wrong','accuracy','coverage')},
        }

    outer=nested['aggregate_outer']
    methodology_pass=bool(
      outer.get('predictions',0)>0
      and outer.get('wrong',0)==0
      and outer.get('correct',0)==outer.get('predictions',0)
      and final_cfg is not None
      and allcand[final_cfg]['loto'].get('wrong',0)==0
    )

    summary={}
    for name,v in allcand.items():
        summary[name]={k:v['loto'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')}

    return {
      'schema':'deus/arc3-ft09-r227-nested-loto-stability/1',
      'rung':RUNG,'game':GAME,
      'nested_outer':nested,
      'final_source_assisted_config':final,
      'p0_p9_candidate_summary':summary,
      'methodology_stability_gate_pass':methodology_pass,
      'promotion':{
        'coverage_expert_promotion':False,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'reason':'nested source-side stability only; no genuinely untouched public p10-p19 remains',
        'next_gate':'if methodology passes, require genuinely untouched public trace/family or provider/private evidence before independent promotion; otherwise close R227 confidence family',
      },
      'truth':{
        'public_trace_only':True,
        'nested_outer_holdout_excluded_from_inner_selection_and_fit':True,
        'family_and_support_selected_inside_each_outer_fold':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT',
        'p10_p19_not_used_for_selection_or_methodology_gate':True,
        'p10_p19_metrics_if_present_are_corroboration_only':True,
        'independent_generalization_claim':False,
        'predictor_promotion':False,
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
      'nested_outer':d['nested_outer']['aggregate_outer'],
      'selected_counts':d['nested_outer']['selected_config_counts'],
      'final':d['final_source_assisted_config'],
      'methodology_gate':d['methodology_stability_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':
    main()
