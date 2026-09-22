#!/usr/bin/env python3
"""R217: ft09 virtual-goal scene-transition expert.

R216 leaves exactly 8 gameplay-frame errors. Audit shows every one is an actual
level-completion transition (level 1->2 or 2->3) that the local R211 recolor
cannot render because the environment immediately swaps to the next scene.

R217 does NOT use heldout level_completed as a predictor. On p0-p9 only:
  - fit the frozen R211 ring2 target-color model,
  - virtually apply that local recolor to each pre-action board,
  - record a virtual gameplay-board signature as a goal signature only when
    every occurrence is a completion and the same next-scene gameplay output
    is observed in >=2 distinct traces.

Heldout trigger uses only:
  current level + pre-action board + action + R211-predicted local target.
If the resulting virtual gameplay signature matches a cross-trace training goal
signature, emit the learned next-scene gameplay board. Otherwise fall through to
R216 scene_exact -> R202 identity -> R211 local recolor -> abstain.

HUD row 63 is excluded from goal keys, outputs, and scoring.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_executable_world_model_134 as base
import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_scene_exact_expert_216 as r216

RUNG=217
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def level_meta(path:Path):
    ev=base.load_events(path)
    pre=ev[0]; step=0; out={}
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        out[step]={
          'level_before':int(pre.get('level',0) or 0),
          'level_after':int(e.get('level',0) or 0),
          'score_before':int(pre.get('score',0) or 0),
          'score_after':int(e.get('score',0) or 0),
        }
        pre=e; step+=1
    return out

def goal_key(level_before:int, virtual_board):
    return base.stable({'level':int(level_before),'virtual_gp':gp(virtual_board)})

def fit_goal(paths,rm,min_traces=2):
    obs=defaultdict(lambda:{
      'labels':Counter(),'traces':set(),'outs':{},'out_counts':Counter(),
      'levels':set(),
    })
    stats=Counter()
    for p in paths:
        meta=level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            tgt=rm.get(repr((r['base'],r['ring2'])))
            if tgt is None:
                stats['target_abstain']+=1; continue
            virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            lm=meta.get(r['step0'])
            if lm is None: continue
            completion=lm['level_after']>lm['level_before']
            k=goal_key(lm['level_before'],virtual)
            x=obs[k]; x['labels'][completion]+=1; x['traces'].add(r['path']); x['levels'].add(lm['level_before'])
            if completion:
                out=gp(r['after']); dg=base.digest(out)
                x['outs'][dg]=out; x['out_counts'][dg]+=1
                stats['completion_examples']+=1
            else:
                stats['noncompletion_examples']+=1
    model={}; rejected=Counter()
    for k,x in obs.items():
        if x['labels'][False]:
            rejected['noncompletion_collision']+=1; continue
        if not x['labels'][True]:
            rejected['no_completion']+=1; continue
        if len(x['traces'])<min_traces:
            rejected['low_trace_support']+=1; continue
        if len(x['out_counts'])!=1:
            rejected['output_conflict']+=1; continue
        dg=next(iter(x['out_counts']))
        model[k]=x['outs'][dg]
    return model,obs,stats,rejected

def evaluate(paths,goal,scene,im,rm):
    s=Counter(); branches={k:Counter() for k in ('virtual_goal','scene_exact','identity','ring2_recolor')}
    wrong=[];hits=[]
    for p in paths:
        meta=level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1
            lm=meta.get(r['step0'])
            branch=None; pred_gp=None

            tgt=rm.get(repr((r['base'],r['ring2'])))
            if tgt is not None and lm is not None:
                virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                gk=goal_key(lm['level_before'],virtual)
                if gk in goal:
                    branch='virtual_goal'; pred_gp=[row[:] for row in goal[gk]]
                    if len(hits)<30:
                        hits.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],
                          'action':r['action'],'level_before':lm['level_before'],
                          'level_after_actual':lm['level_after'],
                        })

            if pred_gp is None:
                sk=r216.scene_key(r)
                if sk in scene:
                    branch='scene_exact'; pred_gp=[row[:] for row in scene[sk]]

            if pred_gp is None:
                idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                if idkey in im:
                    branch='identity'; pred_gp=gp(r['before'])

            if pred_gp is None and tgt is not None:
                branch='ring2_recolor'
                pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                pred_gp=gp(pred)

            if pred_gp is None:
                s['abstain']+=1; continue

            s['predictions']+=1; branches[branch]['predictions']+=1
            actual=gp(r['after'])
            if pred_gp==actual:
                s['correct']+=1; branches[branch]['correct']+=1
            else:
                s['wrong']+=1; branches[branch]['wrong']+=1
                if len(wrong)<30:
                    wrong.append({
                      'trace':r['path'],'p':r['p'],'step0':r['step0'],
                      'branch':branch,'action':r['action'],
                      'level_before':lm['level_before'] if lm else None,
                      'level_after':lm['level_after'] if lm else None,
                      'current':r.get('current'),'target':r.get('target'),
                    })

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    return metrics,branches,wrong,hits

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train=ps[:10]; held=ps[10:]

    rm=r212.ring2_model(train)
    im=r212.identity_model(train)
    scene,scene_obs=r216.fit_scene(train,2)
    goal,goal_obs,gstats,rejected=fit_goal(train,rm,2)

    metrics,branches,wrong,hits=evaluate(held,goal,scene,im,rm)
    gate=bool(metrics.get('predictions',0)>=100 and metrics.get('wrong',0)==0 and (metrics.get('accuracy') or 0)>=0.99)

    return {
      'schema':'deus/arc3-ft09-virtual-goal-scene-expert/1','rung':RUNG,'game':GAME,
      'goal_model':{
        'keys':len(goal),'observed_virtual_keys':len(goal_obs),'min_trace_support':2,
        'training_stats':dict(gstats),'rejected':dict(rejected),
        'key':'current level + exact virtual rows0..62 after frozen R211 local recolor',
      },
      'scene_model_keys':len(scene),
      'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'goal_hits':hits},
      'zero_wrong_gate_pass':gate,
      'promotion':{
        'gameplay_mechanism_gate':gate,
        'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong, preserve expert precedence and expand policy/action coverage; otherwise analyze only remaining residuals',
      },
      'truth':{
        'public_trace_only':True,'p0_p9_fit_only':True,'heldout_never_updates_models':True,
        'goal_labels_from_training_outcomes_only':True,
        'heldout_trigger_uses_preaction_state_plus_frozen_r211_prediction_only':True,
        'cross_trace_support_required':True,
        'hud_row_excluded_from_goal_key_output_and_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'goal_model':d['goal_model'],'heldout':d['heldout']['all'],
      'branches':d['heldout']['by_branch'],'goal_hits':d['heldout']['goal_hits'],
      'wrong':d['heldout']['wrong_examples'],'gate':d['zero_wrong_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
