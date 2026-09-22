#!/usr/bin/env python3
"""R220: repair the R212-CV ring-key contract and audit an abstain-only ring fallback.

Scar preserved:
  R212-CV fit its ring table with key=r['ring2'] but predict() looked up
  key=(r['base'], r['ring2']). Therefore its selected "consensus|b5|r1"
  behavior degenerated to a base-only support>=5 predictor.

R219 remains valid as an empirical gameplay-frame expert because its six added
predictions were exact-frame audited. R220 repairs only the semantic/key
contract and asks whether a correctly keyed composite ring expert can add
further predictions AFTER:
  R218 zero-wrong anchor -> legacy R219 base-support>=5 fallback -> R220 ring.

R220 ring policy is selected by leave-one-trace-out p0-p9 CV ONLY on rows where
the legacy base-support>=5 fallback would abstain. Heldout never selects or
updates policy/models. Every added target must still pass exact gameplay-frame
(rows0..62) scoring; HUD row63 remains excluded.
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

RUNG=220
GAME='ft09-0d8bbf25'
LEGACY_BASE_MIN=5

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def fit_ring(rows):
    obs=defaultdict(Counter)
    for r in rows:
        if not r['changed']: continue
        obs[repr((r['base'],r['ring2']))][r['target']]+=1
    table={}
    for k,c in obs.items():
        if len(c)==1:
            table[k]={'pred':next(iter(c)),'support':int(sum(c.values()))}
    return table

def ring_predict(r,base_tab,ring_tab,ring_min,mode):
    # R220 only fires after the legacy base>=5 predictor abstains.
    b=base_tab.get(repr(r['base']))
    if b and b['support']>=LEGACY_BASE_MIN:
        return None
    q=ring_tab.get(repr((r['base'],r['ring2'])))
    if not q or q['support']<ring_min:
        return None
    if mode=='ring_conflict_abstain' and b and b['pred']!=q['pred']:
        return None
    if mode in ('ring_only','ring_conflict_abstain'):
        return q['pred']
    raise ValueError(mode)

def cv_policy(trace_rows,ring_min,mode):
    s=Counter();folds=[]
    for hold in range(10):
        train=[r for i in range(10) if i!=hold for r in trace_rows[i]]
        test=trace_rows[hold]
        bt=cv212.fit(train,'base');rt=fit_ring(train)
        f=Counter()
        for r in test:
            f['eligible']+=1
            pred=ring_predict(r,bt,rt,ring_min,mode)
            if pred is None:
                f['abstain']+=1;continue
            f['predictions']+=1
            if pred==r['target']: f['correct']+=1
            else: f['wrong']+=1
        for k in ('eligible','abstain','predictions','correct','wrong'):s[k]+=f[k]
        folds.append({'hold':hold,**{k:int(f[k]) for k in ('predictions','correct','wrong')}})
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage_all':round(p/e,6) if e else 0.0,'folds':folds}

def select_ring_policy(train_paths):
    trace_rows=[[r for r in r211.rows(p)] for p in train_paths]
    cand={}
    for mode in ('ring_only','ring_conflict_abstain'):
        for rmin in (1,2,3,4,5,6,8):
            cfg=f'{mode}|r{rmin}'
            cand[cfg]=cv_policy(trace_rows,rmin,mode)
    def key(item):
        cfg,m=item;acc=m['accuracy'] or 0.0
        return (m.get('wrong',0),-acc,-m.get('correct',0),-m.get('predictions',0),cfg)
    ranking=[cfg for cfg,_ in sorted(cand.items(),key=key)]
    sel=ranking[0];mode,rpart=sel.split('|')
    return {'config':sel,'mode':mode,'ring_min':int(rpart[1:]),
            'cv':cand[sel],'ranking':ranking}

def build_models(train):
    rm=r212ff.ring2_model(train)
    im=r212ff.identity_model(train)
    scene,_=r216.fit_scene(train,2)
    exact_goal,_,_,_=r217.fit_goal(train,rm,2)
    fam,struct_goal,fstats=r218.choose_family(train,rm)
    rows=[r for p in train for r in r211.rows(p)]
    base=cv212.fit(rows,'base')
    ring=fit_ring(rows)
    policy=select_ring_policy(train)
    return {'rm':rm,'im':im,'scene':scene,'exact_goal':exact_goal,
            'fam':fam,'struct_goal':struct_goal,'fstats':fstats,
            'base':base,'ring':ring,'policy':policy}

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

def legacy_r219_predict(r,lm,m):
    b=m['base'].get(repr(r['base']))
    if not b or b['support']<LEGACY_BASE_MIN:
        return None,None
    return goal_or_local(r,lm,b['pred'],m,'legacy_base5')

def r220_predict(r,lm,m):
    pol=m['policy']
    tgt=ring_predict(r,m['base'],m['ring'],pol['ring_min'],pol['mode'])
    if tgt is None:return None,None
    return goal_or_local(r,lm,tgt,m,'r220_ring')

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
                pred,branch=legacy_r219_predict(r,lm,m);stage_name='r219_legacy_base5'
            if pred is None:
                pred,branch=r220_predict(r,lm,m);stage_name='r220_corrected_ring'
            if pred is None:
                s['abstain']+=1;continue
            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1
            branches[branch]+=1
            if stage_name=='r220_corrected_ring' and len(added)<40:
                added.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'action':r['action'],'branch':branch,'correct':ok})
            if not ok and len(wrong)<30:
                wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],
                              'stage':stage_name,'branch':branch,'action':r['action']})
    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_legacy_base5']['predictions']==6 and stage['r219_legacy_base5']['correct']==6 and stage['r219_legacy_base5']['wrong']==0,dict(stage['r219_legacy_base5'])
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r220_corrected_ring']
    gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and s.get('wrong',0)==0 and gain>0)
    return {
      'schema':'deus/arc3-ft09-corrected-ring-abstain-union/1','rung':RUNG,'game':GAME,
      'scar':{
        'r212_cv_contract_bug':'fit ring key=r[ring2] but predict lookup=(base,ring2)',
        'r219_empirical_predictions_remain_valid':True,
        'r219_actual_semantics':'base-only deterministic support>=5 fallback',
      },
      'ring_policy':{
        'config':m['policy']['config'],'mode':m['policy']['mode'],'ring_support_min':m['policy']['ring_min'],
        'cv':{k:m['policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
        'ranking':m['policy']['ranking'][:10],
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'branch_counts':dict(branches),'r220_added_examples':added,
        'wrong_examples':wrong,'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False},
      'truth':{
        'public_trace_only':True,'r218_precedence_preserved':True,
        'r219_empirical_base5_fallback_preserved':True,
        'r220_policy_selected_p0_p9_loto_only':True,
        'r220_only_after_r218_and_r219_abstain':True,
        'target_must_pass_exact_gameplay_frame_scoring':True,
        'heldout_never_updates_policy_or_models':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'scar':d['scar'],'policy':d['ring_policy'],'heldout':d['heldout']['all'],
                      'stages':d['heldout']['stage_metrics'],'added':d['heldout']['r220_added_examples'],
                      'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
