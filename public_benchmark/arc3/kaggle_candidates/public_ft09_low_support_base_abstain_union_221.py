#!/usr/bin/env python3
"""R221: low-support base abstain-only coverage expert for ft09.

Verified incumbent:
  R218 zero-wrong gameplay expert stack -> 290/290
  R219 empirical deterministic base support>=5 fallback -> +6/6
  total 296/296, coverage 32.3851%.

R220 showed the correctly keyed ring expert adds zero heldout predictions after
that incumbent. R221 therefore tests the next smallest relaxation: deterministic
BASE keys with support 1..4 only.

Threshold selection is leave-one-trace-out on p0-p9 only and evaluates ONLY
rows where the fold's deterministic base-support>=5 predictor abstains.
Selection priority: zero wrong -> accuracy -> correct count -> prediction count
-> higher support threshold.

Heldout R221 fires only after R218 and R219 both abstain. Every selected target
is converted through the already frozen goal-reset experts when applicable and
must pass exact gameplay-frame rows0..62 scoring. HUD row63 is excluded.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_ring2_relational_gate_211 as r211
import public_ft09_cv_support_ensemble_212 as cv212
import public_ft09_scene_exact_expert_216 as r216
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218

RUNG=221
GAME='ft09-0d8bbf25'
INCUMBENT_BASE_MIN=5

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def low_base_predict(r,tab,min_support):
    b=tab.get(repr(r['base']))
    if not b:return None
    sup=int(b['support'])
    # Preserve R219 semantic domain: R221 owns only support below 5.
    if sup>=INCUMBENT_BASE_MIN or sup<min_support:return None
    return b['pred']

def cv_threshold(trace_rows,min_support):
    s=Counter();folds=[]
    for hold in range(10):
        train=[r for i in range(10) if i!=hold for r in trace_rows[i]]
        test=trace_rows[hold]
        bt=cv212.fit(train,'base')
        f=Counter()
        for r in test:
            f['eligible']+=1
            pred=low_base_predict(r,bt,min_support)
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

def select_threshold(train_paths):
    trace_rows=[[r for r in r211.rows(p)] for p in train_paths]
    cand={f's{m}':cv_threshold(trace_rows,m) for m in (1,2,3,4)}
    def key(item):
        name,x=item
        acc=x['accuracy'] or 0.0
        support=int(name[1:])
        return (x.get('wrong',0),-acc,-x.get('correct',0),-x.get('predictions',0),-support)
    ranking=[name for name,_ in sorted(cand.items(),key=key)]
    sel=ranking[0]
    return {'config':sel,'min_support':int(sel[1:]),'cv':cand[sel],
            'ranking':ranking,'candidates':cand}

def build_models(train):
    rm=r212ff.ring2_model(train)
    im=r212ff.identity_model(train)
    scene,_=r216.fit_scene(train,2)
    exact_goal,_,_,_=r217.fit_goal(train,rm,2)
    fam,struct_goal,fstats=r218.choose_family(train,rm)
    rows=[r for p in train for r in r211.rows(p)]
    base=cv212.fit(rows,'base')
    policy=select_threshold(train)
    return {'rm':rm,'im':im,'scene':scene,'exact_goal':exact_goal,
            'fam':fam,'struct_goal':struct_goal,'fstats':fstats,
            'base':base,'policy':policy}

def goal_or_local(r,lm,target,m,prefix):
    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],target)
    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return [row[:] for row in m['exact_goal'][ek]],prefix+'_exact_goal'
        sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return [row[:] for row in m['struct_goal'][sk]],prefix+'_struct_goal'
    return gp(virtual),prefix+'_local_recolor'

def r218_predict(r,lm,m):
    tgt=m['rm'].get(repr((r['base'],r['ring2'])))
    if tgt is not None and lm is not None:
        virtual=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return [row[:] for row in m['exact_goal'][ek]],'exact_goal'
        sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return [row[:] for row in m['struct_goal'][sk]],'struct_goal'
    sk2=r216.scene_key(r)
    if sk2 in m['scene']:
        return [row[:] for row in m['scene'][sk2]],'scene_exact'
    idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
    if idkey in m['im']:
        return gp(r['before']),'identity'
    if tgt is not None:
        return gp(r212ff.recolor_bbox(r['before'],r['bbox'],tgt)),'ring2_recolor'
    return None,None

def r219_predict(r,lm,m):
    b=m['base'].get(repr(r['base']))
    if not b or int(b['support'])<INCUMBENT_BASE_MIN:return None,None
    return goal_or_local(r,lm,b['pred'],m,'r219_base5')

def r221_predict(r,lm,m):
    tgt=low_base_predict(r,m['base'],m['policy']['min_support'])
    if tgt is None:return None,None
    return goal_or_local(r,lm,tgt,m,'r221_lowbase')

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:];m=build_models(train)
    s=Counter();stage=defaultdict(Counter);branches=Counter();wrong=[];added=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            pred,branch=r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch=r221_predict(r,lm,m);stage_name='r221_lowbase'
            if pred is None:
                s['abstain']+=1;continue
            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1
            branches[branch]+=1
            if stage_name=='r221_lowbase' and len(added)<60:
                b=m['base'].get(repr(r['base']))
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'action':r['action'],'branch':branch,'correct':ok,
                              'base_support':int(b['support']) if b else None})
            if not ok and len(wrong)<40:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'stage':stage_name,'branch':branch,'action':r['action']})
    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0,dict(stage['r219_base5'])
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r221_lowbase'];gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and
              s.get('wrong',0)==0 and gain>0)
    return {
      'schema':'deus/arc3-ft09-low-support-base-abstain-union/1','rung':RUNG,'game':GAME,
      'policy':{
        'config':m['policy']['config'],'min_support':m['policy']['min_support'],
        'cv':{k:m['policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
        'ranking':m['policy']['ranking'],
        'candidate_summary':{k:{x:v.get(x) for x in ('predictions','correct','wrong','accuracy','coverage_all')}
                             for k,v in m['policy']['candidates'].items()},
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'branch_counts':dict(branches),'r221_added_examples':added,
        'wrong_examples':wrong,'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'r218_precedence_preserved':True,
        'r219_base5_precedence_preserved':True,
        'threshold_selected_p0_p9_loto_only':True,
        'cv_domain_is_base5_abstain_region':True,
        'r221_only_after_r218_r219_abstain':True,
        'target_must_pass_exact_gameplay_frame_scoring':True,
        'heldout_never_updates_policy_or_models':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'policy':d['policy'],'heldout':d['heldout']['all'],
                      'stages':d['heldout']['stage_metrics'],'added':d['heldout']['r221_added_examples'],
                      'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
