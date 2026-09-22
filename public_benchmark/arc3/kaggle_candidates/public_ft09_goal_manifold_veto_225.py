#!/usr/bin/env python3
"""R225: goal-manifold veto for low-support ft09 fallback.

Canonical incumbent is R219: 296/296 zero wrong, coverage 32.3851%.
R221/R222/R223 show the p0-p9-selected low-support base fallback adds useful
local predictions but produces two frozen heldout errors at p13s78/p16s48.
Audit shows both wrong predictions enter a training-derived goal-completion
manifold while the heldout transitions are non-completions.

R225 changes no target model and selects no new threshold on heldout:
  - rebuild the same R221 low-support base policy from p0-p9 only,
  - execute only after R218 + R219 abstain,
  - render local 6x6 recolor only,
  - VETO the candidate if its virtual gameplay board matches either the exact
    virtual-goal manifold or the selected structural-goal manifold learned from
    p0-p9 with cross-trace support.

Heldout p10-p19 only scores the frozen policy. HUD row63 is excluded.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221

RUNG=225
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def r225_predict(r,lm,m):
    tgt=r221.low_base_predict(r,m['base'],m['policy']['min_support'])
    if tgt is None:
        return None,None,None

    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)

    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return None,'r225_veto_exact_goal','exact_goal'

        sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return None,'r225_veto_struct_goal','struct_goal'

    return gp(virtual),'r225_lowbase_local',None

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')

    train=ps[:10];held=ps[10:]
    m=r221.build_models(train)

    s=Counter();stage=defaultdict(Counter);branches=Counter()
    vetoes=Counter();veto_examples=[];added=[];wrong=[]

    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:
                continue
            s['eligible']+=1
            lm=meta.get(r['step0'])

            pred,branch=r221.r218_predict(r,lm,m)
            stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m)
                stage_name='r219_base5'

            if pred is None:
                pred,branch,veto=r225_predict(r,lm,m)
                stage_name='r225_lowbase_veto'
                if veto is not None:
                    vetoes[veto]+=1
                    if len(veto_examples)<40:
                        veto_examples.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],
                          'action':r['action'],'veto':veto,
                        })

            if pred is None:
                s['abstain']+=1
                continue

            ok=pred==gp(r['after'])
            s['predictions']+=1
            s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1
            stage[stage_name]['correct' if ok else 'wrong']+=1
            branches[branch]+=1

            if stage_name=='r225_lowbase_veto' and len(added)<60:
                b=m['base'].get(repr(r['base']))
                added.append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],
                  'action':r['action'],'correct':ok,
                  'base_support':int(b['support']) if b else None,
                })

            if not ok and len(wrong)<40:
                wrong.append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],
                  'stage':stage_name,'branch':branch,'action':r['action'],
                })

    assert stage['r218']['predictions']==290
    assert stage['r218']['correct']==290
    assert stage['r218']['wrong']==0
    assert stage['r219_base5']['predictions']==6
    assert stage['r219_base5']['correct']==6
    assert stage['r219_base5']['wrong']==0

    p=s['predictions'];e=s['eligible']
    metrics={
      **dict(s),
      'accuracy':round(s['correct']/p,6) if p else None,
      'coverage':round(p/e,6) if e else 0.0,
    }
    inc=stage['r225_lowbase_veto']
    gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(
      inc.get('predictions',0)>0
      and inc.get('wrong',0)==0
      and s.get('wrong',0)==0
      and gain>0
    )

    return {
      'schema':'deus/arc3-ft09-goal-manifold-veto/1',
      'rung':RUNG,'game':GAME,
      'policy':{
        'source':'R221 p0-p9 LOTO low-support base policy',
        'config':m['policy']['config'],
        'min_support':m['policy']['min_support'],
        'cv':{k:m['policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
        'goal_veto':{
          'exact_goal_keys':len(m['exact_goal']),
          'structural_family':m['fam'],
          'structural_goal_keys':len(m['struct_goal']),
        },
      },
      'heldout':{
        'all':metrics,
        'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'branch_counts':dict(branches),
        'veto_counts':dict(vetoes),
        'veto_examples':veto_examples,
        'r225_added_examples':added,
        'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{
        'coverage_expert_promotion':gate,
        'solver_promotion':False,
        'kaggle_packaging':False,
        'next_gate':'if zero-wrong gain, freeze R225 precedence and continue abstain-only coverage expansion; otherwise retain R219 incumbent',
      },
      'truth':{
        'public_trace_only':True,
        'r218_precedence_preserved':True,
        'r219_base5_precedence_preserved':True,
        'low_support_policy_selected_p0_p9_loto_only':True,
        'goal_manifolds_fit_p0_p9_only':True,
        'cross_trace_goal_support_preserved':True,
        'r225_only_after_r218_r219_abstain':True,
        'r225_local_recolor_only_if_not_vetoed':True,
        'heldout_never_updates_policy_or_goal_manifolds':True,
        'exact_gameplay_rows0_62_scoring':True,
        'independent_generalization_claim':False,
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
      'policy':d['policy'],
      'heldout':d['heldout']['all'],
      'stages':d['heldout']['stage_metrics'],
      'veto_counts':d['heldout']['veto_counts'],
      'added':d['heldout']['r225_added_examples'],
      'wrong':d['heldout']['wrong_examples'],
      'gain':d['heldout']['coverage_gain_abs'],
      'gate':d['zero_wrong_coverage_gain_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':
    main()
