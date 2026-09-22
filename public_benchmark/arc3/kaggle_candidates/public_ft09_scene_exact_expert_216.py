#!/usr/bin/env python3
"""R216: ft09 conservative scene-transition expert + R215 composer.

Only adds a cross-trace exact gameplay-state/action expert trained on p0-p9:
  key = rows0..62 exact board + exact action
  output = rows0..62 exact post-action board
Promotion to the cache requires one conflict-free output observed in >=2 traces.

Heldout precedence:
  exact-scene cache -> R202 identity -> R211 ring2 local recolor -> abstain

Bottom HUD row 63 is excluded from both exact-scene key/output and scoring.
No heldout outcome updates any model.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_executable_world_model_134 as base
import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202

RUNG=216
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def scene_key(r):
    return base.stable({'board':gp(r['before']),'action':r['action']})

def fit_scene(paths,min_traces=2):
    obs=defaultdict(lambda:{'outs':{},'counts':Counter(),'traces':set()})
    for p in paths:
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            k=scene_key(r); out=gp(r['after']); dg=base.digest(out)
            obs[k]['outs'][dg]=out
            obs[k]['counts'][dg]+=1
            obs[k]['traces'].add(r['path'])
    model={}
    for k,x in obs.items():
        if len(x['counts'])==1 and len(x['traces'])>=min_traces:
            dg=next(iter(x['counts']))
            model[k]=x['outs'][dg]
    return model,obs

def evaluate(paths,scene,im,rm):
    s=Counter();branches={k:Counter() for k in ('scene_exact','identity','ring2_recolor')}
    wrong=[];scene_hits=[]
    for p in paths:
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1
            branch=None; pred_gp=None
            sk=scene_key(r)
            if sk in scene:
                branch='scene_exact';pred_gp=[row[:] for row in scene[sk]]
                if len(scene_hits)<20:scene_hits.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action']})
            else:
                idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                if idkey in im:
                    branch='identity';pred_gp=gp(r['before'])
                else:
                    tgt=rm.get(repr((r['base'],r['ring2'])))
                    if tgt is not None:
                        branch='ring2_recolor'
                        pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                        pred_gp=gp(pred)
            if pred_gp is None:
                s['abstain']+=1;continue
            s['predictions']+=1;branches[branch]['predictions']+=1
            if pred_gp==gp(r['after']):
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<30:
                    wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'action':r['action'],'current':r.get('current'),'target':r.get('target')})
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    return metrics,branches,wrong,scene_hits

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    scene,obs=fit_scene(train,2)
    im=r212.identity_model(train);rm=r212.ring2_model(train)
    metrics,branches,wrong,hits=evaluate(held,scene,im,rm)
    gate=bool(metrics.get('predictions',0)>=100 and metrics.get('wrong',0)==0 and (metrics.get('accuracy') or 0)>=0.99)
    return {
      'schema':'deus/arc3-ft09-scene-exact-expert/1','rung':RUNG,'game':GAME,
      'scene_model':{'keys':len(scene),'observed_keys':len(obs),'min_trace_support':2,'key':'exact rows0..62 + exact action'},
      'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'scene_hits':hits},
      'zero_wrong_gate_pass':gate,
      'promotion':{'gameplay_mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'if scene branch closes residuals, expand action/policy coverage without weakening zero-wrong precedence'},
      'truth':{
        'public_trace_only':True,'p0_p9_fit_only':True,'heldout_never_updates_models':True,
        'cross_trace_support_required':True,'hud_row_excluded_from_scene_key_output_and_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False,
      }
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'scene_model':d['scene_model'],'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],'scene_hits':d['heldout']['scene_hits'],'gate':d['zero_wrong_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
