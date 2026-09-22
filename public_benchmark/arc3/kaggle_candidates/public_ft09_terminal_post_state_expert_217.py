#!/usr/bin/env python3
"""R217: ft09 terminal-post-state expert + R216 precedence.

R216 leaves 8 gameplay-frame residuals. Direct trace inspection shows all 8 are
real level-completion transitions (level_completed=true; score increments;
level advances), split across level1->2 and level2->3.

R217 learns a conservative trigger from p0-p9 only:
  - use frozen R202/R211 local predictor to form the hypothetical post-click
    gameplay board (rows 0..62; HUD excluded)
  - key = (current level, exact hypothetical local-post gameplay board)
  - retain only keys observed as level-completing in >=2 distinct training traces
    with one conflict-free next-scene gameplay output

Heldout precedence:
  terminal-post-state expert -> R216 scene_exact -> R202 identity
  -> R211 ring2 local recolor -> abstain

Heldout outcomes never update any model. This is same-game public iterative
research, not independent hidden generalization or Kaggle execution.
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

def action_meta(path:Path):
    ev=base.load_events(path)
    pre=ev[0]; step=0; out={}
    for e in ev[1:]:
        if e.get('type')!='action':
            pre=e; continue
        out[step]={
            'level_before':pre.get('level'),
            'level_after':e.get('level'),
            'score_before':pre.get('score'),
            'score_after':e.get('score'),
            'level_completed':bool(e.get('level_completed',False)),
            'reward':e.get('reward'),
            'done':bool(e.get('done',False)),
            'run_complete':bool(e.get('run_complete',False)),
            'game_over':bool(e.get('game_over',False)),
        }
        pre=e; step+=1
    return out

def local_pred(r,im,rm):
    idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
    if idkey in im:
        return [row[:] for row in r['before']],'identity'
    tgt=rm.get(repr((r['base'],r['ring2'])))
    if tgt is not None:
        return r212.recolor_bbox(r['before'],r['bbox'],tgt),'ring2_recolor'
    return None,None

def terminal_key(level,pred):
    return base.stable({'level':level,'local_post_gameplay':r216.gp(pred)})

def fit_terminal(paths,im,rm,min_traces=2):
    obs=defaultdict(lambda:{'outs':{},'counts':Counter(),'traces':set(),'examples':[]})
    all_completed=0; predictable_completed=0
    for p in paths:
        meta=action_meta(p)
        for r in r212.all_rows(p):
            m=meta.get(r['step0'],{})
            if not m.get('level_completed'): continue
            all_completed+=1
            pred,src=local_pred(r,im,rm)
            if pred is None: continue
            predictable_completed+=1
            k=terminal_key(m.get('level_before'),pred)
            out=r216.gp(r['after']); dg=base.digest(out)
            x=obs[k]
            x['outs'][dg]=out; x['counts'][dg]+=1; x['traces'].add(r['path'])
            if len(x['examples'])<10:
                x['examples'].append({
                  'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],
                  'source':src,'level_before':m.get('level_before'),'level_after':m.get('level_after'),
                  'score_before':m.get('score_before'),'score_after':m.get('score_after'),
                })
    model={}
    for k,x in obs.items():
        if len(x['counts'])==1 and len(x['traces'])>=min_traces:
            dg=next(iter(x['counts'])); model[k]=x['outs'][dg]
    return model,obs,{'all_completed':all_completed,'predictable_completed':predictable_completed}

def evaluate(paths,terminal,scene,im,rm):
    s=Counter()
    branches={k:Counter() for k in ('terminal_post','scene_exact','identity','ring2_recolor')}
    wrong=[];hits=[];missed_completed=[]
    for p in paths:
        meta=action_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            m=meta.get(r['step0'],{})
            s['eligible']+=1
            pred_gp=None; branch=None
            local,local_src=local_pred(r,im,rm)
            if local is not None:
                tk=terminal_key(m.get('level_before'),local)
                if tk in terminal:
                    branch='terminal_post'; pred_gp=[row[:] for row in terminal[tk]]
                    if len(hits)<30:
                        hits.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],
                          'actual_level_completed':m.get('level_completed'),
                          'level_before':m.get('level_before'),'level_after':m.get('level_after'),
                          'score_before':m.get('score_before'),'score_after':m.get('score_after'),
                        })
            if pred_gp is None:
                sk=r216.scene_key(r)
                if sk in scene:
                    branch='scene_exact';pred_gp=[row[:] for row in scene[sk]]
                elif local_src=='identity' and local is not None:
                    branch='identity';pred_gp=r216.gp(local)
                elif local_src=='ring2_recolor' and local is not None:
                    branch='ring2_recolor';pred_gp=r216.gp(local)

            if pred_gp is None:
                s['abstain']+=1
                if m.get('level_completed') and len(missed_completed)<20:
                    missed_completed.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'reason':'abstain'})
                continue
            s['predictions']+=1;branches[branch]['predictions']+=1
            actual=r216.gp(r['after'])
            if pred_gp==actual:
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<30:
                    wrong.append({
                      'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'action':r['action'],
                      'actual_level_completed':m.get('level_completed'),
                      'level_before':m.get('level_before'),'level_after':m.get('level_after'),
                      'score_before':m.get('score_before'),'score_after':m.get('score_after'),
                      'current':r.get('current'),'target':r.get('target'),
                    })
                if m.get('level_completed') and len(missed_completed)<20:
                    missed_completed.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'reason':'wrong','branch':branch})
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    return metrics,branches,wrong,hits,missed_completed

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    im=r212.identity_model(train); rm=r212.ring2_model(train)
    scene,_=r216.fit_scene(train,2)
    terminal,obs,train_stats=fit_terminal(train,im,rm,2)
    metrics,branches,wrong,hits,missed=evaluate(held,terminal,scene,im,rm)
    terminal_branch=branches['terminal_post']
    terminal_gate=bool(terminal_branch.get('predictions',0)>=2 and terminal_branch.get('wrong',0)==0)
    overall_gate=bool(metrics.get('predictions',0)>=100 and metrics.get('wrong',0)==0 and (metrics.get('accuracy') or 0)>=0.99)
    return {
      'schema':'deus/arc3-ft09-terminal-post-state-expert/1','rung':RUNG,'game':GAME,
      'terminal_model':{
        'keys':len(terminal),'observed_terminal_keys':len(obs),'min_trace_support':2,
        'key':'level_before + exact hypothetical post-local gameplay board rows0..62',
        'train_stats':train_stats,
      },
      'heldout':{
        'all':metrics,'by_branch':branches,'wrong_examples':wrong,
        'terminal_hits':hits,'missed_level_completions':missed,
      },
      'terminal_zero_wrong_gate_pass':terminal_gate,
      'overall_zero_wrong_gate_pass':overall_gate,
      'promotion':{
        'terminal_mechanism_gate':terminal_gate,'gameplay_mechanism_gate':overall_gate,
        'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong closes gameplay residuals, expand policy/action coverage; otherwise analyze only remaining residual class',
      },
      'truth':{
        'public_trace_only':True,'p0_p9_fit_only':True,'heldout_never_updates_models':True,
        'terminal_labels_from_training_outcomes_only':True,'cross_trace_support_required':True,
        'hud_row_excluded_from_terminal_key_output_and_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'terminal_model':d['terminal_model'],
      'heldout':d['heldout']['all'],
      'branches':d['heldout']['by_branch'],
      'terminal_hits':d['heldout']['terminal_hits'],
      'missed_level_completions':d['heldout']['missed_level_completions'],
      'terminal_gate':d['terminal_zero_wrong_gate_pass'],
      'overall_gate':d['overall_zero_wrong_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
