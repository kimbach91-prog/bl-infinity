#!/usr/bin/env python3
"""R222: confidence-separated low-support local-only fallback.

R221 found useful low-support base predictions but two false positives came
specifically from allowing that low-confidence target source to invoke the
structural-goal reset expert.

R222 preserves:
  R218 high-confidence zero-wrong stack,
  R219 empirical base-support>=5 fallback with goal/reset authority,
  R221 p0-p9-LOTO-selected low-support threshold.

Change ONE authority rule:
  low-support base fallback may only recolor the clicked 6x6 tile.
  It may NOT invoke exact_goal, structural_goal, or scene-reset experts.

Heldout p10-p19 never changes the threshold or any model. Gameplay scoring is
exact rows0..62; HUD row63 excluded.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221

RUNG=222
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def lowbase_local_only(r,m):
    tgt=r221.low_base_predict(r,m['base'],m['policy']['min_support'])
    if tgt is None:return None,None
    pred=r212ff.recolor_bbox(r['before'],r['bbox'],tgt)
    return gp(pred),'r222_lowbase_local_only'

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    m=r221.build_models(train)

    s=Counter();stage=defaultdict(Counter);branches=Counter();wrong=[];added=[]
    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1;lm=meta.get(r['step0'])

            pred,branch=r221.r218_predict(r,lm,m);stage_name='r218'
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m);stage_name='r219_base5'
            if pred is None:
                pred,branch=lowbase_local_only(r,m);stage_name='r222_lowbase_local_only'
            if pred is None:
                s['abstain']+=1;continue

            ok=pred==gp(r['after'])
            s['predictions']+=1;s['correct' if ok else 'wrong']+=1
            stage[stage_name]['predictions']+=1;stage[stage_name]['correct' if ok else 'wrong']+=1
            branches[branch]+=1

            if stage_name=='r222_lowbase_local_only' and len(added)<80:
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

    assert stage['r218']['predictions']==290 and stage['r218']['correct']==290 and stage['r218']['wrong']==0,dict(stage['r218'])
    assert stage['r219_base5']['predictions']==6 and stage['r219_base5']['correct']==6 and stage['r219_base5']['wrong']==0,dict(stage['r219_base5'])

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
             'coverage':round(p/e,6) if e else 0.0}
    inc=stage['r222_lowbase_local_only']
    gain=metrics.get('coverage',0.0)-0.323851
    gate=bool(inc.get('predictions',0)>0 and inc.get('wrong',0)==0 and
              s.get('wrong',0)==0 and gain>0)

    return {
      'schema':'deus/arc3-ft09-confidence-separated-lowbase-local-only/1',
      'rung':RUNG,'game':GAME,
      'policy':{
        'source':'R221 p0-p9 LOTO residual threshold selection',
        'config':m['policy']['config'],'min_support':m['policy']['min_support'],
        'cv':{k:m['policy']['cv'].get(k) for k in ('predictions','correct','wrong','accuracy','coverage_all')},
      },
      'authority_contract':{
        'r218_can_trigger_goal_reset':True,
        'r219_base5_can_trigger_goal_reset':True,
        'r222_low_support_can_trigger_goal_reset':False,
        'r222_low_support_render':'clicked_6x6_local_recolor_only',
      },
      'heldout':{
        'all':metrics,'stage_metrics':{k:dict(v) for k,v in stage.items()},
        'branch_counts':dict(branches),'r222_added_examples':added,
        'wrong_examples':wrong,'coverage_gain_abs':round(gain,6),
      },
      'zero_wrong_coverage_gain_gate_pass':gate,
      'promotion':{
        'coverage_expert_promotion':gate,'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if promoted, freeze confidence-separated precedence and continue abstain-only structural/local coverage expansion',
      },
      'truth':{
        'public_trace_only':True,
        'r218_precedence_preserved':True,'r219_base5_precedence_preserved':True,
        'threshold_reused_from_p0_p9_only_r221_selection':True,
        'low_support_goal_reset_authority_disabled_before_r222_heldout_eval':True,
        'r222_only_after_r218_r219_abstain':True,
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
      'policy':d['policy'],'authority':d['authority_contract'],
      'heldout':d['heldout']['all'],'stages':d['heldout']['stage_metrics'],
      'added':d['heldout']['r222_added_examples'],'gain':d['heldout']['coverage_gain_abs'],
      'gate':d['zero_wrong_coverage_gain_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
