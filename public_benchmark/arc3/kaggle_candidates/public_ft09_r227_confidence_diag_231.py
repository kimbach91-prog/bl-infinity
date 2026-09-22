#!/usr/bin/env python3
"""R231: diagnose whether R227's four public-development errors are confidence-separable.

This is an outcome-assisted PUBLIC_DEVELOPMENT diagnostic after p10-p19 has
already been inspected by R227-R230.  It must not be described as independent
heldout generalization.  It does not select/promote a solver.  It measures only
pre-action/training-derived confidence statistics of the frozen R227 local key:
training occurrence count, distinct-trace support, level support and
key+macro-position trace support; then reports bounded prospective abstention
families for the already-observed public-development population.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227

RUNG=231; GAME='ft09-0d8bbf25'; FAM='current_ring2hist'
def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1
def gp(b):return [row[:] for row in b[:-1]]
def train_stats(paths):
 d=defaultdict(lambda:{'targets':Counter(),'traces':set(),'levels':set(),'positions':defaultdict(set),'n':0})
 for p in paths:
  meta=r217.level_meta(p)
  for r in r212.all_rows(p):
   if not r['eligible']:continue
   lm=meta.get(r['step0']);k=repr(r227.feat(FAM,r,lm));z=d[k];z['targets'][r['target']]+=1;z['traces'].add(r['path']);z['n']+=1
   if lm:z['levels'].add(int(lm['level_before']))
   r0,c0,_,_,_=r['bbox'];z['positions'][(r0//8,c0//8)].add(r['path'])
 return d
def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('p0..p19 required')
 train=ps[:10];dev=ps[10:];tab,_=r227.fit(train,FAM,2);stats=train_stats(train);m=r221.build_models(train)
 rows=[]
 for p in dev:
  meta=r217.level_meta(p)
  for r in r212.all_rows(p):
   if not r['eligible']:continue
   lm=meta.get(r['step0']);pred,_=r221.r218_predict(r,lm,m)
   if pred is None:pred,_=r221.r219_predict(r,lm,m)
   if pred is None:pred,_,_=r225.lowbase_goal_veto(r,lm,m)
   if pred is not None:continue
   k=repr(r227.feat(FAM,r,lm));tgt=tab.get(k)
   if tgt is None or r227.goal_veto(r,lm,tgt,m) is not None:continue
   r0,c0,_,_,_=r['bbox'];pos=(r0//8,c0//8);z=stats[k]
   ok=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt))==gp(r['after'])
   rows.append({'p':r['p'],'step0':r['step0'],'action':r['action'],'correct':ok,'completion':bool(lm and lm['level_after']>lm['level_before']),
    'train_occurrences':z['n'],'trace_support':len(z['traces']),'level_seen':bool(lm and int(lm['level_before']) in z['levels']),
    'position_trace_support':len(z['positions'].get(pos,set())),'target_train_purity':round(max(z['targets'].values())/sum(z['targets'].values()),6) if z['targets'] else None})
 gates=[]
 for ts in (2,3,4,5,6):
  for occ in (2,3,4,6,8,12):
   for require_level in (False,True):
    for pos_sup in (0,1,2):
     kept=[x for x in rows if x['trace_support']>=ts and x['train_occurrences']>=occ and (not require_level or x['level_seen']) and x['position_trace_support']>=pos_sup]
     if not kept:continue
     c=sum(x['correct'] for x in kept);w=len(kept)-c
     gates.append({'trace_support':ts,'min_occurrences':occ,'require_level_seen':require_level,'min_position_trace_support':pos_sup,'kept':len(kept),'correct':c,'wrong':w,'accuracy':round(c/len(kept),6)})
 gates.sort(key=lambda g:(g['wrong'],-g['correct'],-g['kept'],g['trace_support'],g['min_occurrences'],g['min_position_trace_support']))
 return {'schema':'deus/arc3-ft09-r227-confidence-diagnostic/1','rung':RUNG,'game':GAME,'population':{'candidates':len(rows),'correct':sum(x['correct'] for x in rows),'wrong':sum(not x['correct'] for x in rows)},
  'wrong_rows':[x for x in rows if not x['correct']], 'best_zero_wrong_gates':[g for g in gates if g['wrong']==0][:20],'top_all_gates':gates[:30],
  'truth':{'public_trace_only':True,'p10_p19_status':'PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT','outcome_assisted_diagnostic':True,'predictor_promotion':False,'gate_selection_for_promotion':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'population':d['population'],'wrong_rows':d['wrong_rows'],'best_zero_wrong_gates':d['best_zero_wrong_gates'][:10]},sort_keys=True))
if __name__=='__main__':main()
