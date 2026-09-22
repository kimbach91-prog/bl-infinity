#!/usr/bin/env python3
"""R219: abstain-only union of R218 gameplay expert stack with R212-CV target expert.

R218 is the zero-wrong anchor: 290 exact gameplay-frame predictions on frozen
p10-p19. This rung preserves R218 precedence unchanged. Only when R218 fully
abstains may the independently p0-p9-CV-selected R212 target-color policy fire.

A CV fallback target is converted to a virtual gameplay board, passed through
the already-frozen R217/R218 goal-reset experts, and otherwise rendered as the
local 6x6 recolor. Therefore target correctness alone never counts as a gameplay
coverage gain.

R212-CV policy parameters are re-selected using p0-p9 leave-one-trace-out CV
inside this run. Heldout never selects policy or updates models.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_scene_exact_expert_216 as r216
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218

RUNG=219
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

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
      'config':selected,'mode':mode,
      'base_min':int(bpart[1:]),'ring_min':int(rpart[1:]),
      'cv':candidates[selected],'ranking':ranking[:12],
    }

def models(train):
    rm=r212ff.ring2_model(train)
    im=r212ff.identity_model(train)
    scene,_=r216.fit_scene(train,2)
    exact_goal,_,_,_=r217.fit_goal(train,rm,2)
    selected_family,struct_goal,family_stats=r218.choose_family(train,rm)
    cvpol=select_cv_policy(train)
    cv_rows=[r for p in train for r in r211.rows(p)]
    cv_base=cv212.fit(cv_rows,'base')
    cv_ring=cv212.fit(cv_rows,'ring2')
    return {
      'rm':rm,'im':im,'scene':scene,'exact_goal':exact_goal,
      'selected_family':selected_family,'struct_goal':struct_goal,
      'family_stats':family_stats,'cv_policy':cvpol,
      'cv_base':cv_base,'cv_ring':cv_ring,
    }

def r218_predict(r,lm,m):
    tgt=m['rm'].get(repr((r['base'],r['ring2'])))
    virtual=None
    if tgt is not None and lm is not None:
        virtual=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return gp(m['exact_goal'][ek]),'exact_goal'
        sk=r218.structural_key(m['selected_family'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return gp(m['struct_goal'][sk]),'struct_goal'

    sk2=r216.scene_key(r)
    if sk2 in m['scene']:
        return gp(m['scene'][sk2]),'scene_exact'

    idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
    if idkey in m['im']:
        return gp(r['before']),'identity'

    if tgt is not None:
        return gp(r212ff.recolor_bbox(r['before'],r['bbox'],tgt)),'ring2_recolor'
    return None,None

def cv_fallback_predict(r,lm,m):
    pol=m['cv_policy']
    tgt=cv212.predict(
      r,m['cv_base'],m['cv_ring'],
      pol['base_min'],pol['ring_min'],pol['mode']
    )
    if tgt is None:
        return None,None

    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return gp(m['exact_goal'][ek]),'cv_exact_goal'
        sk=r218.structural_key(m['selected_family'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return gp(m['struct_goal'][sk]),'cv_struct_goal'
    return gp(virtual),'cv_local_recolor'

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    m=models(train)

    s=Counter();anchor=Counter();inc=Counter()
    branches=Counter();wrong=[];inc_examples=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1
            lm=meta.get(r['step0'])
            pred,branch=r218_predict(r,lm,m)
            if pred is not None:
                anchor['predictions']+=1
                ok=pred==gp(r['after'])
                anchor['correct' if ok else 'wrong']+=1
            else:
                pred,branch=cv_fallback_predict(r,lm,m)
                if pred is not None:
                    inc['predictions']+=1
                    ok=pred==gp(r['after'])
                    inc['correct' if ok else 'wrong']+=1
                    if len(inc_examples)<30:
                        inc_examples.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],
                          'branch':branch,'action':r['action'],'correct':ok,
                        })
                else:
                    s['abstain']+=1
                    continue

            s['predictions']+=1;branches[branch]+=1
            if pred==gp(r['after']):
                s['correct']+=1
            else:
                s['wrong']+=1
                if len(wrong)<30:
                    wrong.append({
                      'trace':r['path'],'p':r['p'],'step0':r['step0'],
                      'branch':branch,'action':r['action'],
                    })

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    gain=metrics.get('coverage',0.0)-0.317287
    gate=bool(
      anchor.get('wrong',0)==0
      and inc.get('predictions',0)>0
      and inc.get('wrong',0)==0
      and metrics.get('wrong',0)==0
      and gain>0
    )
    return {
      'schema':'deus/arc3-ft09-r218-cv-abstain-union/1','rung':RUNG,'game':GAME,
      'cv_policy':{
        'config':m['cv_policy']['config'],'mode':m['cv_policy']['mode'],
        'base_support_min':m['cv_policy']['base_min'],'ring2_support_min':m['cv_policy']['ring_min'],
        'cv':{k:m['cv_policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage')},
      },
      'r218_anchor':dict(anchor),
      'incremental_cv_fallback':{**dict(inc),'examples':inc_examples},
      'heldout':{
        'all':metrics,'branch_counts':dict(branches),'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{
        'coverage_expert_promotion':gate,
        'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if no unique zero-wrong gain, reject CV fallback and test another abstain-only expert; if gain, freeze union then continue coverage expansion',
      },
      'truth':{
        'public_trace_only':True,
        'r218_precedence_unchanged':True,
        'cv_policy_selected_from_p0_p9_only':True,
        'cv_fallback_only_when_r218_abstains':True,
        'target_prediction_must_pass_gameplay_frame_scoring':True,
        'heldout_never_updates_policy_or_models':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'cv_policy':d['cv_policy'],'anchor':d['r218_anchor'],
      'incremental':d['incremental_cv_fallback'],
      'heldout':d['heldout']['all'],'gain':d['heldout']['coverage_gain_abs'],
      'gate':d['zero_wrong_coverage_gain_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
