#!/usr/bin/env python3
"""R225: low-confidence goal-manifold veto for ft09 residual coverage.

Grounding:
- R219 is the verified zero-wrong incumbent (296/296).
- R221 selected deterministic low-base support>=2 from p0-p9 LOTO but added
  11/13 exact gameplay predictions with two wrong.
- R222 proved those two remain wrong under local-only rendering.
- Public trace audit shows the training same-base examples behind both wrong
  targets are level-completion actions, whereas the frozen falsifiers are
  non-completion actions.
- R224 base+ring2 is safe but adds zero heldout coverage.

R225 keeps the R221 p0-p9-selected s2 target domain, but enforces a conservative
authority rule BEFORE heldout evaluation:
  after R218 + R219 abstain, form the low-support virtual local recolor.
  If that virtual gameplay board lies on an exact or structural goal manifold
  already learned from p0-p9 cross-trace completion evidence, ABSTAIN.
  Otherwise emit only the local 6x6 recolor.

This turns known goal manifolds into a veto for low-confidence target experts;
low-confidence evidence cannot claim a terminal/scene-transition state.

HUD row63 is excluded from goal keys and exact gameplay scoring.
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

def lowbase_goal_veto(r,lm,m):
    tgt=r221.low_base_predict(r,m['base'],m['policy']['min_support'])
    if tgt is None:
        return None,None,None

    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
    veto=None
    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            veto='exact_goal_manifold'
        else:
            sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
            if sk in m['struct_goal']:
                veto='structural_goal_manifold'
    if veto is not None:
        return None,None,veto
    return gp(virtual),'r225_lowbase_local_only',None

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    m=r221.build_models(train)

    s=Counter();stage=defaultdict(Counter);vetoes=Counter();added=[];veto_examples=[];wrong=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])

            pred,branch=r221.r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch,veto=lowbase_goal_veto(r,lm,m);stage_name='r225_lowbase_veto'
                if veto is not None:
                    vetoes[veto]+=1
                    s['abstain']+=1
                    if len(veto_examples)<40:
                        b=m['base'].get(repr(r['base']))
                        veto_examples.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],
                          'action':r['action'],'veto':veto,
                          'base_support':int(b['support']) if b else None,
                          'actual_level_before':lm['level_before'] if lm else None,
                          'actual_level_after':lm['level_after'] if lm else None,
                        })
                    continue

            if pred is None:
                s['abstain']+=1;continue

            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1

            if stage_name=='r225_lowbase_veto' and len(added)<80:
                b=m['base'].get(repr(r['base']))
                added.append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],
                  'action':r['action'],'correct':ok,
                  'base_support':int(b['support']) if b else None,
                })
            if not ok and len(wrong)<40:
                wrong.append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],
                  'stage':stage_name,'action':r['action'],
                })

    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0,dict(stage['r219_base5'])

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r225_lowbase_veto']
    gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and
              s.get('wrong',0)==0 and gain>0)

    return {
      'schema':'deus/arc3-ft09-low-confidence-goal-manifold-veto/1',
      'rung':RUNG,'game':GAME,
      'policy':{
        'source':'R221 p0-p9 LOTO selected low-base threshold',
        'config':m['policy']['config'],'min_support':m['policy']['min_support'],
        'cv':{k:m['policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
      },
      'veto_contract':{
        'low_support_can_trigger_goal_reset':False,
        'low_support_can_enter_known_goal_manifold':False,
        'veto_sources':['exact_goal_manifold','structural_goal_manifold'],
        'goal_models_fit':'p0-p9 cross-trace only',
        'post_veto_render':'clicked_6x6_local_recolor_only',
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'veto_counts':dict(vetoes),'veto_examples':veto_examples,
        'r225_added_examples':added,'wrong_examples':wrong,
        'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{
        'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if promoted, freeze goal-manifold-veto precedence and continue residual coverage/policy expansion',
      },
      'truth':{
        'public_trace_only':True,'iterative_public_heldout_research':True,
        'r218_precedence_preserved':True,'r219_base5_precedence_preserved':True,
        'low_support_threshold_reused_from_p0_p9_only_r221_selection':True,
        'goal_manifolds_fit_from_p0_p9_only':True,
        'veto_rule_fixed_before_r225_heldout_eval':True,
        'r225_only_after_r218_r219_abstain':True,
        'heldout_never_updates_policy_or_models':True,
        'exact_gameplay_rows0_62_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'policy':d['policy'],'veto':d['veto_contract'],
      'heldout':d['heldout']['all'],'stages':d['heldout']['stage_metrics'],
      'veto_counts':d['heldout']['veto_counts'],'veto_examples':d['heldout']['veto_examples'],
      'added':d['heldout']['r225_added_examples'],'wrong':d['heldout']['wrong_examples'],
      'gain':d['heldout']['coverage_gain_abs'],'gate':d['zero_wrong_coverage_gain_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
