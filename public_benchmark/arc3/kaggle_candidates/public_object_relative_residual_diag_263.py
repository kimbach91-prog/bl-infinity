#!/usr/bin/env python3
"""R263: source-free object-relative residual diagnostic for re86.

R260 established that action-aligned selective transport is materially closer
than identity but leaves sparse residuals. R261 falsified simple cached-underlay
repair, and a noncanonical coordinate/HUD side probe added zero predictions.
R263 changes representation: residual corrections are learned in coordinates
relative to the transported component's source/destination footprint, testing
an agent/occlusion-local mechanism rather than screen-coordinate memorization.

Protocol:
  p0-p4: fit selective transport and pure object-relative residual rules
  p5-p9: diagnostic evaluation only
  p10-p19: never read
No solver/Kaggle promotion is made here.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257

RUNG=263
# Frozen from already-canonical R260 public-development diagnosis; this rung is
# explicitly descriptive/diagnostic and makes no independent-generalization claim.
CFG={
    'DOWN':(13,1.00,3),
    'LEFT':(36,0.90,5),
    'RIGHT':(13,0.80,3),
    'UP':(13,0.80,3),
}
RADII=(0,1,2,3)
SUPPORTS=(2,3,5)

def ham(a,b):
    return sum(int(x)!=int(y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))

def prep(paths):
    out=[]
    for p in paths:
        for i,row in enumerate(r251.prepare_rows([p])):
            x=dict(row); x['transition_id']=f'{p.name}#{i}'; out.append(x)
    return out

def moved_components(board,movable,max_area):
    return [c for c in r254.components(board) if c['area']<=max_area and r257.cls(c) in movable]

def cells_around(c,side,vector,radius,h,w):
    dr,dc=vector
    ar=c['r0']+(dr if side=='dst' else 0)
    ac=c['c0']+(dc if side=='dst' else 0)
    r0=max(0,ar-radius); r1=min(h-1, ar+(c['r1']-c['r0'])+radius)
    c0=max(0,ac-radius); c1=min(w-1, ac+(c['c1']-c['c0'])+radius)
    for r in range(r0,r1+1):
        for col in range(c0,c1+1):
            yield r,col,r-ar,col-ac

def sig(row,comp,side,rr,cc,relr,relc,pred):
    return r246.stable([
        row['action'],side,list(r257.cls(comp)),int(relr),int(relc),
        int(pred[rr][cc]),int(row['before'][rr][cc])
    ])

def fit_rules(rows,model,max_area,radius,min_support):
    vector,movable=model
    obs=defaultdict(Counter); tids=defaultdict(set); mismatch_zone=Counter(); total_resid=0
    if not vector or not movable: return {}, {'observed_rule_keys':0,'pure_rule_count':0,'training_residual_cells':0,'training_zone_counts':{}}
    for row in rows:
        pred=r257.render(row['before'],vector,movable,max_area)
        if pred is None: continue
        h=len(pred); w=len(pred[0]); comps=moved_components(row['before'],movable,max_area)
        seen_mismatch=set()
        for comp in comps:
            for side in ('src','dst'):
                for rr,cc,relr,relc in cells_around(comp,side,vector,radius,h,w):
                    if int(pred[rr][cc])==int(row['after'][rr][cc]): continue
                    k=sig(row,comp,side,rr,cc,relr,relc,pred)
                    obs[k][int(row['after'][rr][cc])]+=1
                    tids[k].add(row['transition_id'])
                    seen_mismatch.add((rr,cc))
                    mismatch_zone[side]+=1
        total_resid += ham(pred,row['after'])
        mismatch_zone['unique_localized'] += len(seen_mismatch)
    rules={}
    for k,c in obs.items():
        if len(c)==1 and len(tids[k])>=min_support:
            rules[k]=int(next(iter(c)))
    return rules, {'observed_rule_keys':len(obs),'pure_rule_count':len(rules),'training_residual_cells':total_resid,'training_zone_counts':dict(mismatch_zone)}

def apply_rules(row,model,max_area,radius,rules):
    vector,movable=model
    pred=r257.render(row['before'],vector,movable,max_area)
    if pred is None: return None,0,0
    h=len(pred); w=len(pred[0]); comps=moved_components(row['before'],movable,max_area)
    proposals=defaultdict(list)
    for comp in comps:
        for side in ('src','dst'):
            for rr,cc,relr,relc in cells_around(comp,side,vector,radius,h,w):
                k=sig(row,comp,side,rr,cc,relr,relc,pred)
                if k in rules: proposals[(rr,cc)].append(rules[k])
    out=[list(map(int,r)) for r in pred]; applied=conflicts=0
    for (rr,cc),vals in proposals.items():
        uniq=set(vals)
        if len(uniq)!=1:
            conflicts+=1; continue
        v=next(iter(uniq))
        if int(out[rr][cc])!=int(v):
            out[rr][cc]=int(v); applied+=1
    return out,applied,conflicts

def summarize(vals):
    if not vals:return {'n':0}
    s=sorted(vals); n=len(s)
    return {'n':n,'mean':round(sum(s)/n,6),'median':statistics.median(s),'p90':s[min(n-1,int(.9*n))],'exact':sum(v==0 for v in s),'le2':round(sum(v<=2 for v in s)/n,6),'le4':round(sum(v<=4 for v in s)/n,6)}

def eval_variant(rows,models,radius,min_support,train_by):
    base=[]; fixed=[]; applied=conflicts=preds=0; rules_count=0; train_meta={}
    rules_by={}
    for action,model_info in models.items():
        max_area,model=model_info
        rules,meta=fit_rules(train_by[action],model,max_area,radius,min_support)
        rules_by[action]=rules; rules_count+=len(rules); train_meta[action]=meta
    by_action=defaultdict(lambda:{'base':[],'fixed':[],'predictions':0,'applied':0})
    for row in rows:
        action=row['action']
        if action not in models: continue
        max_area,model=models[action]
        raw=r257.render(row['before'],model[0],model[1],max_area)
        if raw is None: continue
        out,napp,nconf=apply_rules(row,model,max_area,radius,rules_by[action])
        if out is None: continue
        be=ham(raw,row['after']); fe=ham(out,row['after'])
        base.append(be); fixed.append(fe); preds+=1; applied+=napp; conflicts+=nconf
        x=by_action[action]; x['base'].append(be); x['fixed'].append(fe); x['predictions']+=1; x['applied']+=napp
    bsum=summarize(base); fsum=summarize(fixed)
    reduction=(1-sum(fixed)/sum(base)) if base and sum(base)>0 else None
    return {
      'radius':radius,'min_support':min_support,'rule_count':rules_count,'predictions':preds,
      'base_error':bsum,'corrected_error':fsum,
      'mean_hamming_reduction_fraction':round(reduction,6) if reduction is not None else None,
      'improved_frames':sum(f<b for f,b in zip(fixed,base)),'regressed_frames':sum(f>b for f,b in zip(fixed,base)),
      'same_frames':sum(f==b for f,b in zip(fixed,base)),'applied_cells':applied,'conflict_cells':conflicts,
      'by_action':{a:{'predictions':x['predictions'],'base_error':summarize(x['base']),'corrected_error':summarize(x['fixed']),'applied_cells':x['applied']} for a,x in by_action.items()},
      'train_meta':train_meta,
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    tr=prep(ps[:5]); va=prep(ps[5:]); tr_by=defaultdict(list)
    for r in tr: tr_by[r['action']].append(r)
    models={}
    for action,cfg in CFG.items():
        if action not in tr_by: continue
        max_area,min_frac,min_support=cfg
        models[action]=(max_area,r257.learn(tr_by[action],max_area,min_frac,min_support))
    variants={}
    for radius in RADII:
        for support in SUPPORTS:
            k=f'r{radius}_s{support}'; variants[k]=eval_variant(va,models,radius,support,tr_by)
    ranked=[]
    for k,v in variants.items():
        red=v['mean_hamming_reduction_fraction']
        if red is not None:
            ranked.append((-red,v['regressed_frames'],-v['corrected_error'].get('exact',0),v['rule_count'],k))
    ranked.sort(); best=ranked[0][-1] if ranked else None
    out={'schema':'deus/arc3-r263-object-relative-residual-diagnostic/1','rung':RUNG,
      'lineage':{'r260':'near-exact selective transport','r261':'cached-underlay NO_PROMOTION','side_probe':'coordinate/HUD residual selected none; scar only'},
      'protocol':{'fit':'p0-p4 only','diagnostic_eval':'p5-p9 reused public development','p10_p19_read':False,'representation':'component-relative source/destination residual templates','promotion':False},
      'frozen_transport_cfg':{k:list(v) for k,v in CFG.items()},'variants':variants,'best_variant':best,
      'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'best_variant':best,'best':variants.get(best),'variant_summary':{k:{'rules':v['rule_count'],'reduction':v['mean_hamming_reduction_fraction'],'exact_before':v['base_error'].get('exact'),'exact_after':v['corrected_error'].get('exact'),'improved':v['improved_frames'],'regressed':v['regressed_frames']} for k,v in variants.items()}},sort_keys=True))
if __name__=='__main__': main()
