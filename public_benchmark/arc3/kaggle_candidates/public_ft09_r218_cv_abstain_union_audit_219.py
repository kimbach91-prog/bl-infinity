#!/usr/bin/env python3
"""R219: audit R212_CV as abstain-only exact-frame union on top of R218.

R218 is the frozen zero-wrong gameplay-frame precedence (290/290 exact rows0..62,
coverage 31.7287%). R212_CV is only a target-color expert (101/101), so R219
NEVER adds its target metric directly.

Protocol:
  1. Rebuild R218 models from p0-p9 exactly.
  2. Rebuild R212_CV support policy selected by leave-one-trace-out CV on p0-p9.
  3. On p10-p19, execute R218 precedence first.
  4. Only when R218 abstains, let R212_CV predict target color and render exactly
     the clicked 6x6 bbox; score the resulting gameplay frame rows0..62.
  5. Candidate can be retained only if unique added predictions are zero-wrong.

No heldout outcome updates any model or policy.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_scene_exact_expert_216 as r216
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_cv_support_ensemble_212 as cv212

RUNG=219
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def select_cv_policy(ps):
    trace_rows=[[r for r in r211.rows(p)] for p in ps[:10]]
    candidates={}
    for mode in ('ring_first','consensus','ring_only_conflict_abstain'):
        for base_min in (1,2,3,4,5,6,8):
            for ring_min in (1,2,3,4):
                cfg=f'{mode}|b{base_min}|r{ring_min}'
                candidates[cfg]=cv212.cv_score(trace_rows,base_min,ring_min,mode)
    ranking=[cfg for cfg,_ in sorted(candidates.items(),key=cv212.selection_key)]
    selected=ranking[0]
    mode,bpart,rpart=selected.split('|')
    return {
      'config':selected,'mode':mode,'base_min':int(bpart[1:]),'ring_min':int(rpart[1:]),
      'cv':candidates[selected],'ranking':ranking[:20],
    }

def build_models(train):
    rm=r212.ring2_model(train)
    im=r212.identity_model(train)
    scene,_=r216.fit_scene(train,2)
    exact_goal,_,_,_=r217.fit_goal(train,rm,2)
    fam,struct_goal,fstats=r218.choose_family(train,rm)

    trace_rows=[[r for r in r211.rows(p)] for p in train]
    train_rows=[r for rs in trace_rows for r in rs]
    pol=select_cv_policy(train)
    base_tab=cv212.fit(train_rows,'base')
    ring_tab=cv212.fit(train_rows,'ring2')
    return {
      'rm':rm,'im':im,'scene':scene,'exact_goal':exact_goal,
      'struct_family':fam,'struct_goal':struct_goal,'family_stats':fstats,
      'cv_policy':pol,'cv_base':base_tab,'cv_ring':ring_tab,
    }

def eval_union(paths,m):
    s=Counter()
    branches={k:Counter() for k in ('exact_goal','struct_goal','scene_exact','identity','ring2_recolor','cv_abstain_fill')}
    wrong=[]; cv_examples=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1
            lm=meta.get(r['step0'])
            tgt=m['rm'].get(repr((r['base'],r['ring2'])))
            pred_gp=None;branch=None;virtual=None

            if tgt is not None and lm is not None:
                virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                ek=r217.goal_key(lm['level_before'],virtual)
                if ek in m['exact_goal']:
                    branch='exact_goal';pred_gp=[row[:] for row in m['exact_goal'][ek]]

            if pred_gp is None and virtual is not None and lm is not None:
                sk=r218.structural_key(m['struct_family'],lm['level_before'],virtual)
                if sk in m['struct_goal']:
                    branch='struct_goal';pred_gp=[row[:] for row in m['struct_goal'][sk]]

            if pred_gp is None:
                sk2=r216.scene_key(r)
                if sk2 in m['scene']:
                    branch='scene_exact';pred_gp=[row[:] for row in m['scene'][sk2]]

            if pred_gp is None:
                idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                if idkey in m['im']:
                    branch='identity';pred_gp=r216.gp(r['before'])

            if pred_gp is None and tgt is not None:
                branch='ring2_recolor'
                pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                pred_gp=r216.gp(pred)

            # R212_CV is allowed only on true R218 abstains.
            if pred_gp is None:
                cvrow={'base':r['base'],'ring2':r['ring2']}
                cp=cv212.predict(
                    cvrow,m['cv_base'],m['cv_ring'],
                    m['cv_policy']['base_min'],m['cv_policy']['ring_min'],m['cv_policy']['mode'])
                if cp is not None:
                    branch='cv_abstain_fill'
                    pred=r212.recolor_bbox(r['before'],r['bbox'],cp)
                    pred_gp=r216.gp(pred)

            if pred_gp is None:
                s['abstain']+=1;continue

            s['predictions']+=1;branches[branch]['predictions']+=1
            actual=r216.gp(r['after'])
            if pred_gp==actual:
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<30:
                    wrong.append({
                      'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,
                      'action':r['action'],
                      'level_before':lm['level_before'] if lm else None,
                      'level_after':lm['level_after'] if lm else None,
                    })
            if branch=='cv_abstain_fill' and len(cv_examples)<40:
                cv_examples.append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],
                  'correct':pred_gp==actual,
                })

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    return metrics,branches,wrong,cv_examples

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    m=build_models(train)

    # Re-read the R218 baseline from the same frozen models.
    bmetrics,bbranches,bwrong,_=r218.evaluate(
        held,m['exact_goal'],m['struct_goal'],m['struct_family'],m['scene'],m['im'],m['rm'])
    metrics,branches,wrong,cv_examples=eval_union(held,m)

    inc=metrics.get('predictions',0)-bmetrics.get('predictions',0)
    cvb=branches['cv_abstain_fill']
    candidate_gate=bool(
      bmetrics.get('wrong',0)==0 and bmetrics.get('predictions',0)==290
      and inc>0 and cvb.get('predictions',0)==inc and cvb.get('wrong',0)==0
      and metrics.get('wrong',0)==0
    )
    return {
      'schema':'deus/arc3-ft09-r218-cv-abstain-union-audit/1','rung':RUNG,'game':GAME,
      'r218_baseline':{'all':bmetrics,'by_branch':bbranches,'wrong_examples':bwrong},
      'cv_policy':m['cv_policy'],
      'union':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'cv_unique_examples':cv_examples},
      'unique_incremental_predictions':inc,
      'unique_incremental_coverage':round(inc/metrics['eligible'],6) if metrics.get('eligible') else 0.0,
      'candidate_zero_wrong_gate_pass':candidate_gate,
      'promotion':{
        'retain_cv_abstain_fill':candidate_gate,'solver_promotion':False,'kaggle_packaging':False,
        'reason':'coverage audit only; R218 precedence cannot be overridden',
      },
      'truth':{
        'public_trace_only':True,'p0_p9_cv_policy_selection_only':True,
        'p0_p9_model_fit_only':True,'heldout_never_updates_models_or_policy':True,
        'r218_precedence_preserved':True,'cv_used_only_after_r218_abstain':True,
        'gameplay_rows0_62_exact_scoring':True,'hud_row_excluded':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'baseline':d['r218_baseline']['all'],'cv_policy':d['cv_policy'],
      'union':d['union']['all'],'branches':d['union']['by_branch'],
      'incremental_predictions':d['unique_incremental_predictions'],
      'incremental_coverage':d['unique_incremental_coverage'],
      'gate':d['candidate_zero_wrong_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
