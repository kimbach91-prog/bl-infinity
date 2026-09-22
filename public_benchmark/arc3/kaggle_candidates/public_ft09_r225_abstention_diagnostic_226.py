#!/usr/bin/env python3
"""R226: diagnostic decomposition of R225 abstentions.

This rung does NOT create or promote a solver expert. It rebuilds the frozen
R225 stack from p0-p9 and verifies the 307/914 zero-wrong heldout anchor, then
classifies the remaining p10-p19 abstentions by why no target/frame prediction
was available.

It also measures, for diagnostic purposes only, what would happen if support-1
base keys were locally recolored after the same goal-manifold veto. Those
heldout outcome measurements are explicitly non-promotable and may only guide
the next p0-p9-selected candidate design.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212ff
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_structural_goal_scene_expert_218 as r218
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_goal_manifold_veto_225 as r225

RUNG=226
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def goal_veto_reason(r,lm,m,target):
    virtual=r212ff.recolor_bbox(r['before'],r['bbox'],target)
    if lm is not None:
        ek=r217.goal_key(lm['level_before'],virtual)
        if ek in m['exact_goal']:
            return 'exact_goal'
        sk=r218.structural_key(m['fam'],lm['level_before'],virtual)
        if sk in m['struct_goal']:
            return 'struct_goal'
    return None

def classify_abstain(r,lm,m):
    b=m['base'].get(repr(r['base']))
    if b is None:
        return 'base_unseen',None,None

    sup=int(b['support'])
    pred=int(b['pred'])
    veto=goal_veto_reason(r,lm,m,pred)

    if sup>=5:
        return 'unexpected_support_ge5',sup,veto
    if sup>=m['policy']['min_support']:
        # R225 should only abstain here when goal veto fires.
        return f'lowbase_veto_{veto or "unexpected"}',sup,veto
    if sup==1:
        return 'base_support1',sup,veto
    return f'base_support{sup}',sup,veto

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):
        raise ValueError('exact p0..p19 required')

    train=ps[:10];held=ps[10:]
    m=r221.build_models(train)

    s=Counter(); reasons=Counter(); levels=defaultdict(Counter)
    support1=Counter();support1_examples=[];unseen=Counter();unseen_examples=[]
    veto_examples=[]; wrong=[]

    for p in held:
        meta=r217.level_meta(p)
        for r in r212ff.all_rows(p):
            if not r['eligible']:
                continue
            s['eligible']+=1
            lm=meta.get(r['step0'])

            pred,branch=r221.r218_predict(r,lm,m)
            if pred is None:
                pred,branch=r221.r219_predict(r,lm,m)
            if pred is None:
                pred,branch,veto=r225.r225_predict(r,lm,m)

            if pred is not None:
                ok=pred==gp(r['after'])
                s['predictions']+=1
                s['correct' if ok else 'wrong']+=1
                if not ok and len(wrong)<20:
                    wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch})
                continue

            s['abstain']+=1
            reason,sup,veto=classify_abstain(r,lm,m)
            reasons[reason]+=1
            level=lm['level_before'] if lm else -1
            levels[level][reason]+=1

            if reason.startswith('lowbase_veto_'):
                if len(veto_examples)<30:
                    veto_examples.append({
                        'trace':r['path'],'p':r['p'],'step0':r['step0'],
                        'action':r['action'],'reason':reason,'support':sup,
                        'level_before':level,
                    })

            if reason=='base_support1':
                b=m['base'][repr(r['base'])]
                target=int(b['pred'])
                virtual=r212ff.recolor_bbox(r['before'],r['bbox'],target)
                gv=goal_veto_reason(r,lm,m,target)
                support1['rows']+=1
                support1['goal_veto']+=int(gv is not None)
                support1['actual_identity']+=int(r['target']==r['current'])
                support1['actual_changed']+=int(r['target']!=r['current'])
                support1['target_correct']+=int(target==r['target'])
                support1['target_wrong']+=int(target!=r['target'])
                frame_ok=(gv is None and gp(virtual)==gp(r['after']))
                support1['frame_correct_if_nonveto']+=int(frame_ok)
                support1['frame_wrong_if_nonveto']+=int(gv is None and not frame_ok)
                if len(support1_examples)<50:
                    support1_examples.append({
                        'trace':r['path'],'p':r['p'],'step0':r['step0'],
                        'action':r['action'],'level_before':level,
                        'pred_target':target,'actual_target':r['target'],
                        'current':r['current'],'goal_veto':gv,
                        'target_correct':target==r['target'],
                        'frame_correct_if_nonveto':frame_ok,
                    })

            if reason=='base_unseen':
                unseen['rows']+=1
                unseen['actual_identity']+=int(r['target']==r['current'])
                unseen['actual_changed']+=int(r['target']!=r['current'])
                if len(unseen_examples)<40:
                    unseen_examples.append({
                        'trace':r['path'],'p':r['p'],'step0':r['step0'],
                        'action':r['action'],'level_before':level,
                        'current':r['current'],'actual_target':r['target'],
                        'actual_identity':r['target']==r['current'],
                    })

    assert s['predictions']==307,dict(s)
    assert s['correct']==307,dict(s)
    assert s['wrong']==0,dict(s)
    assert s['abstain']==607,dict(s)

    p=s['predictions'];e=s['eligible']
    return {
      'schema':'deus/arc3-ft09-r225-abstention-diagnostic/1',
      'rung':RUNG,'game':GAME,
      'r225_anchor':{
        **dict(s),
        'accuracy':round(s['correct']/p,6),
        'coverage':round(p/e,6),
      },
      'abstention_reasons':dict(reasons),
      'abstentions_by_level':{str(k):dict(v) for k,v in sorted(levels.items())},
      'support1_diagnostic':{
        **dict(support1),
        'examples':support1_examples,
      },
      'unseen_base_diagnostic':{
        **dict(unseen),
        'examples':unseen_examples,
      },
      'veto_examples':veto_examples,
      'anchor_wrong_examples':wrong,
      'promotion':{
        'solver_promotion':False,
        'coverage_expert_promotion':False,
        'kaggle_packaging':False,
        'next_gate':'design next candidate only from p0-p9-selected logic; heldout diagnostic outcomes may not directly set a policy',
      },
      'truth':{
        'public_trace_only':True,
        'r225_anchor_rebuilt_from_p0_p9_only':True,
        'heldout_used_for_diagnostic_decomposition_only':True,
        'support1_outcomes_are_nonpromotable_diagnostic':True,
        'heldout_never_updates_model':True,
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
      'anchor':d['r225_anchor'],
      'reasons':d['abstention_reasons'],
      'by_level':d['abstentions_by_level'],
      'support1':{k:v for k,v in d['support1_diagnostic'].items() if k!='examples'},
      'unseen':{k:v for k,v in d['unseen_base_diagnostic'].items() if k!='examples'},
    },sort_keys=True))
if __name__=='__main__':
    main()
