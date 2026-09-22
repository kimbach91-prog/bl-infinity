#!/usr/bin/env python3
"""R232F: cached equivalent of R232 nested-LOTO stability audit.

Same truth/protocol as R232, but precomputes every trace row and feature key once.
No heldout outcome is used for selection beyond the outer fold being evaluated.
p10-p19 remains reused development corroboration only.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from functools import lru_cache
from pathlib import Path

import public_ft09_coarse_local_target_gate_227 as r227

RUNG="232F"
GAME='ft09-0d8bbf25'

def pnum(p):
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def pack(s):
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage':round(p/e,6) if e else 0.0}

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')

    # Cache row truth + every feature family once. Exact local-frame correctness
    # is equivalent to actual transition being local-only with the same target.
    traces=[]
    for p in ps:
        rows=[]
        for r,lm in r227.rows_with_meta([p]):
            local=r227.is_local_only(r)
            label=('local',int(r['target'])) if local else ('nonlocal',)
            rows.append({
              'label':label,
              'keys':{fam:repr(r227.feat(fam,r,lm)) for fam in r227.FAMILIES},
            })
        traces.append(rows)

    @lru_cache(maxsize=None)
    def fit_meta(trace_tuple,fam):
        obs=defaultdict(lambda:{'labels':Counter(),'traces':defaultdict(set)})
        for ti in trace_tuple:
            for row in traces[ti]:
                k=row['keys'][fam];label=row['label']
                x=obs[k];x['labels'][label]+=1;x['traces'][label].add(ti)
        meta={}
        for k,x in obs.items():
            if len(x['labels'])!=1: continue
            label=next(iter(x['labels']))
            if label[0]!='local': continue
            meta[k]=(int(label[1]),len(x['traces'][label]))
        return meta

    def eval_trace(ti,meta,fam,sup):
        s=Counter()
        for row in traces[ti]:
            s['eligible']+=1
            z=meta.get(row['keys'][fam])
            if z is None or z[1]<sup:
                s['abstain']+=1;continue
            pred=z[0];s['predictions']+=1
            if row['label']==('local',pred):s['correct']+=1
            else:s['wrong']+=1
        return pack(s)

    def loto_score(pool,fam,sup):
        s=Counter();folds=[]
        for hold in pool:
            tr=tuple(x for x in pool if x!=hold)
            meta=fit_meta(tr,fam)
            met=eval_trace(hold,meta,fam,sup)
            for k in ('eligible','abstain','predictions','correct','wrong'):s[k]+=met.get(k,0)
            folds.append({'hold_p':hold,**{k:met.get(k) for k in ('predictions','correct','wrong','coverage')}})
        return {**pack(s),'folds':folds}

    famrank={f:i for i,f in enumerate(r227.FAMILIES)}
    def select(pool):
        cand={}
        for fam in r227.FAMILIES:
            for sup in r227.SUPPORTS:
                name=f'{fam}|t{sup}'
                cand[name]={'family':fam,'min_traces':sup,'loto':loto_score(tuple(pool),fam,sup)}
        zero=[(k,v) for k,v in cand.items() if v['loto']['predictions']>0 and v['loto']['wrong']==0]
        if not zero:return None,cand
        zero.sort(key=lambda kv:(-kv[1]['loto']['correct'],-kv[1]['loto']['predictions'],
                                 -kv[1]['min_traces'],famrank[kv[1]['family']],kv[0]))
        return zero[0][0],cand

    outer_s=Counter();outer_folds=[];selected_counts=Counter()
    train_ids=tuple(range(10))
    for outer in train_ids:
        pool=tuple(x for x in train_ids if x!=outer)
        cfg,cand=select(pool)
        if cfg is None:
            outer_folds.append({'hold_p':outer,'selected':None,'status':'NO_ZERO_WRONG_INNER_CONFIG'})
            continue
        fam=cand[cfg]['family'];sup=cand[cfg]['min_traces']
        meta=fit_meta(pool,fam)
        met=eval_trace(outer,meta,fam,sup)
        for k in ('eligible','abstain','predictions','correct','wrong'):outer_s[k]+=met.get(k,0)
        selected_counts[cfg]+=1
        outer_folds.append({'hold_p':outer,'selected':cfg,
          'inner_loto':{k:cand[cfg]['loto'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')},
          'outer':{k:met.get(k) for k in ('eligible','predictions','correct','wrong','accuracy','coverage')}})

    final_cfg,allcand=select(train_ids)
    final=None
    if final_cfg:
        fam=allcand[final_cfg]['family'];sup=allcand[final_cfg]['min_traces']
        meta=fit_meta(train_ids,fam)
        ds=Counter()
        for ti in range(10,20):
            met=eval_trace(ti,meta,fam,sup)
            for k in ('eligible','abstain','predictions','correct','wrong'):ds[k]+=met.get(k,0)
        final={'config':final_cfg,'family':fam,'min_traces':sup,
          'p0_p9_loto':{k:allcand[final_cfg]['loto'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')},
          'p10_p19_reused_development_only':pack(ds)}

    outer=pack(outer_s)
    gate=bool(outer['predictions']>0 and outer['wrong']==0 and
              outer['correct']==outer['predictions'] and final_cfg is not None and
              allcand[final_cfg]['loto']['wrong']==0)
    return {
      'schema':'deus/arc3-ft09-r227-nested-loto-stability-fast/1','rung':RUNG,'game':GAME,
      'nested_outer':{'aggregate_outer':outer,'selected_config_counts':dict(selected_counts),'folds':outer_folds},
      'final_source_assisted_config':final,
      'methodology_stability_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':False,'solver_promotion':False,'kaggle_packaging':False,
        'reason':'nested source-side stability only; p10-p19 is reused development',
        'next_gate':'require genuinely untouched public/provider evidence before independent promotion'},
      'truth':{'public_trace_only':True,'cached_equivalent_of_r232_protocol':True,
        'nested_outer_holdout_excluded_from_inner_selection_and_fit':True,
        'family_and_support_selected_inside_each_outer_fold':True,
        'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT',
        'p10_p19_not_used_for_selection_or_methodology_gate':True,
        'independent_generalization_claim':False,'predictor_promotion':False,
        'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'outer':d['nested_outer']['aggregate_outer'],'selected_counts':d['nested_outer']['selected_config_counts'],
                      'final':d['final_source_assisted_config'],'gate':d['methodology_stability_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
