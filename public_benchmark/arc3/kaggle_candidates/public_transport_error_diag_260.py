#!/usr/bin/env python3
"""R260: source-free near-exact error diagnostic for re86 selective transport.

R259 shows observed moved-object footprints explain ~95%+ of movement changed
cells, while R257 exact full-frame selection fails. R260 measures whether the
R257 predictive transport models are nevertheless *near exact* on p5-p9 and
which residual classes remain, compared with identity on the same baseline-
abstain transitions. This is diagnostic-only; it does not select on p10-p19.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_selective_object_transport_257 as r257


def hamming(a,b):
    return sum(int(x)!=int(y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))

def residual_pairs(pred,after):
    c=Counter()
    for ra,rb in zip(pred,after):
        for x,y in zip(ra,rb):
            if int(x)!=int(y): c[(int(x),int(y))]+=1
    return c

def summarize(vals):
    if not vals:return {'n':0}
    vals=sorted(vals); n=len(vals)
    return {'n':n,'mean':round(sum(vals)/n,6),'median':statistics.median(vals),'p90':vals[min(n-1,max(0,int(.9*n)))],
            'le1':round(sum(v<=1 for v in vals)/n,6),'le2':round(sum(v<=2 for v in vals)/n,6),
            'le4':round(sum(v<=4 for v in vals)/n,6),'le8':round(sum(v<=8 for v in vals)/n,6),'exact':sum(v==0 for v in vals)}

def prepare(paths):
    out=[]
    for p in paths:
        for step,row in enumerate(r251.prepare_rows([p])):
            x=dict(row); x['transition_id']=f'{p.name}#{step}'; out.append(x)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    tr=prepare(ps[:5]); va=prepare(ps[5:]); exact=r251.fit_exact(tr)
    tr_by=defaultdict(list); va_by=defaultdict(list)
    for r in tr: tr_by[r['action']].append(r)
    for r in va: va_by[r['action']].append(r)
    out_actions={}
    for action in sorted(set(tr_by)|set(va_by)):
        variants={}
        for max_area,min_frac,min_support in r257.VARIANTS:
            model=r257.learn(tr_by[action],max_area,min_frac,min_support)
            errs=[]; iderrs=[]; pairs=Counter(); predictions=0
            for row in va_by[action]:
                if row['exact_key'] in exact: continue
                p=r257.render(row['before'],model[0],model[1],max_area)
                if p is None: continue
                predictions+=1; e=hamming(p,row['after']); ie=hamming(row['before'],row['after'])
                errs.append(e); iderrs.append(ie); pairs.update(residual_pairs(p,row['after']))
            key=f'a{max_area}_f{int(min_frac*100)}_s{min_support}'
            variants[key]={'predictions':predictions,'transport_error':summarize(errs),'identity_error_same_rows':summarize(iderrs),
                           'error_reduction_fraction':round(1-(sum(errs)/sum(iderrs)),6) if iderrs and sum(iderrs)>0 else None,
                           'top_residual_pairs':[[list(k),v] for k,v in pairs.most_common(12)],
                           'vector':list(model[0]) if model[0] else None,'movable_class_count':len(model[1])}
        ranked=[(v['transport_error'].get('median',10**9),v['transport_error'].get('mean',10**9),-v['predictions'],k) for k,v in variants.items() if v['predictions']>0]
        ranked.sort(); best=ranked[0][3] if ranked else None
        out_actions[action]={'best_variant':best,'variants':variants}
    out={'schema':'deus/arc3-r260-transport-error-diagnostic/1','rung':260,
         'protocol':{'fit':'p0-p4','diagnostic_eval':'p5-p9 baseline-abstain only','promotion':False,'p10_p19_read':False},
         'actions':out_actions,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,
                  'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    compact={a:{'best':x['best_variant'],'metrics':x['variants'].get(x['best_variant'],{})} for a,x in out_actions.items()}
    print(json.dumps(compact,sort_keys=True))
if __name__=='__main__': main()
