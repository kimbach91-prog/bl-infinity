#!/usr/bin/env python3
"""R220: lower-support base-only fallback on canonical repaired R219 abstains."""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_full_frame_composer_212 as r212
import public_ft09_r218_cv_abstain_union_219 as r219
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
RUNG=220; GAME='ft09-0d8bbf25'; TH=(1,2,3,4,5,6,8,10,12)

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def cv_threshold(train_paths,t):
 traces=[[r for r in r211.rows(p)] for p in train_paths]; s=Counter()
 for h in range(10):
  tr=[r for i,rs in enumerate(traces) if i!=h for r in rs]; te=traces[h]
  bt=cv212.fit(tr,'base'); rt=cv212.fit(tr,'ring2')
  for r in te:
   if rt.get(repr((r['base'],r['ring2']))) is not None: continue
   s['eligible']+=1; b=bt.get(repr(r['base']))
   if b is None or b['support']<t: s['abstain']+=1; continue
   s['predictions']+=1
   if b['pred']==r['target']: s['correct']+=1
   else: s['wrong']+=1
 p=s['predictions']; e=s['eligible']
 return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}

def choose(train):
 scores={str(t):cv_threshold(train,t) for t in TH}
 sel=sorted(TH,key=lambda t:(scores[str(t)].get('wrong',0),-scores[str(t)].get('correct',0),-scores[str(t)].get('predictions',0),t))[0]
 return sel,scores

def base_fallback(r,lm,m,bt,t):
 b=bt.get(repr(r['base']))
 if b is None or b['support']<t: return None,None
 virtual=r212.recolor_bbox(r['before'],r['bbox'],b['pred'])
 if lm is not None:
  ek=r217.goal_key(lm['level_before'],virtual)
  if ek in m['exact_goal']: return [row[:] for row in m['exact_goal'][ek]],'base_exact_goal'
  sk=r218.structural_key(m['selected_family'],lm['level_before'],virtual)
  if sk in m['struct_goal']: return [row[:] for row in m['struct_goal'][sk]],'base_struct_goal'
 return r219.gp(virtual),'base_local'

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
 train,held=ps[:10],ps[10:]; m=r219.models(train); t,scores=choose(train)
 bt=cv212.fit([r for p in train for r in r211.rows(p)],'base')
 s=Counter(); anchor=Counter(); inc=Counter(); branches=Counter(); wrong=[]; examples=[]
 for pth in held:
  meta=r217.level_meta(pth)
  for r in r212.all_rows(pth):
   if not r['eligible']: continue
   s['eligible']+=1; lm=meta.get(r['step0'])
   pred,br=r219.r218_predict(r,lm,m)
   if pred is None: pred,br=r219.cv_fallback_predict(r,lm,m)
   if pred is not None:
    anchor['predictions']+=1; anchor['correct' if pred==r219.gp(r['after']) else 'wrong']+=1
   else:
    pred,br=base_fallback(r,lm,m,bt,t)
    if pred is None: s['abstain']+=1; continue
    inc['predictions']+=1; inc['correct' if pred==r219.gp(r['after']) else 'wrong']+=1
    if len(examples)<30: examples.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':br,'action':r['action'],'correct':pred==r219.gp(r['after'])})
   s['predictions']+=1; branches[br]+=1
   if pred==r219.gp(r['after']): s['correct']+=1
   else:
    s['wrong']+=1
    if len(wrong)<30: wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':br,'action':r['action']})
 p=s['predictions']; e=s['eligible']; metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
 gain=s.get('predictions',0)-296
 gate=bool(anchor.get('predictions',0)==296 and anchor.get('wrong',0)==0 and gain>0 and inc.get('predictions',0)==gain and inc.get('wrong',0)==0 and s.get('wrong',0)==0)
 return {'schema':'deus/arc3-ft09-r219-base-only-abstain-cv/1','rung':RUNG,'game':GAME,
  'selected_base_support_min':t,'cv_scores':scores,'r219_anchor':dict(anchor),
  'incremental_base_fallback':{**dict(inc),'examples':examples},
  'heldout':{'all':metrics,'branch_counts':dict(branches),'wrong_examples':wrong,'incremental_predictions':gain,'coverage_gain_abs':round(metrics.get('coverage',0)-0.323851,6)},
  'zero_wrong_coverage_gain_gate_pass':gate,
  'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},
  'truth':{'public_trace_only':True,'r219_precedence_unchanged':True,'threshold_selected_by_p0_p9_loto_cv_only':True,'cv_domain_ring2_abstain_only':True,'fallback_only_when_r219_abstains':True,'heldout_never_updates_policy_or_models':True,'gameplay_rows0_62_exact_scoring':True,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'threshold':d['selected_base_support_min'],'cv':d['cv_scores'][str(d['selected_base_support_min'])],'anchor':d['r219_anchor'],'incremental':d['incremental_base_fallback'],'heldout':d['heldout']['all'],'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
