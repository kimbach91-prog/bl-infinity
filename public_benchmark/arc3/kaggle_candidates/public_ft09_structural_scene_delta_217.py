#!/usr/bin/env python3
"""R217: ft09 structural scene-delta expert over R216 precedence.

Fit on p0-p9 only. For each R211 structural key (base, ring2), learn a scene
delta only when:
  - R211 supplies a target color,
  - every observed occurrence of that key has a large non-HUD residual >=100,
  - the exact delta template (r,c,new_value) is identical,
  - the key appears in >=2 distinct traces.

Heldout precedence:
  R216 exact scene -> R217 structural scene delta -> R202 identity -> R211 ring2.

No heldout outcome updates the model; HUD row 63 excluded.
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

def gp(board): return [row[:] for row in board[:-1]]

def delta_template(pred,actual):
    out=[]
    for r,(a,b) in enumerate(zip(gp(pred),gp(actual))):
        for c,(x,y) in enumerate(zip(a,b)):
            if x!=y: out.append((r,c,int(y)))
    return tuple(out)

def structural_key(r):
    return repr((r['base'],r['ring2']))

def fit_structural_scene(paths,rm,min_traces=2):
    obs=defaultdict(lambda:{'scene':0,'nonscene':0,'templates':Counter(),'template_values':{},'traces':set()})
    for p in paths:
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            tgt=rm.get(structural_key(r))
            if tgt is None:continue
            pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            dt=delta_template(pred,r['after'])
            x=obs[structural_key(r)]
            x['traces'].add(r['path'])
            if len(dt)>=100:
                x['scene']+=1
                dg=base.digest(dt);x['templates'][dg]+=1;x['template_values'][dg]=dt
            else:
                x['nonscene']+=1
    model={}
    for k,x in obs.items():
        if x['scene']>0 and x['nonscene']==0 and len(x['templates'])==1 and len(x['traces'])>=min_traces:
            dg=next(iter(x['templates']))
            model[k]=x['template_values'][dg]
    return model,obs

def apply_delta(pred,dt):
    out=[row[:] for row in pred]
    for r,c,v in dt:
        if r>=len(out)-1: raise ValueError('R217 delta touches HUD row')
        out[r][c]=v
    return out

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    scene_exact,_=r216.fit_scene(train,2)
    im=r212.identity_model(train);rm=r212.ring2_model(train)
    structural,obs=fit_structural_scene(train,rm,2)

    s=Counter();branches={k:Counter() for k in ('scene_exact','scene_structural_delta','identity','ring2_recolor')}
    wrong=[];struct_hits=[]
    for p in held:
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1
            branch=None;pred=None
            sk=r216.scene_key(r)
            if sk in scene_exact:
                branch='scene_exact';pred=scene_exact[sk]+[r['before'][-1][:]]
            else:
                tgt=rm.get(structural_key(r))
                if tgt is not None and structural_key(r) in structural:
                    branch='scene_structural_delta'
                    local=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                    pred=apply_delta(local,structural[structural_key(r)])
                    if len(struct_hits)<20:
                        struct_hits.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'delta_cells':len(structural[structural_key(r)])})
                else:
                    idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                    if idkey in im:
                        branch='identity';pred=[row[:] for row in r['before']]
                    elif tgt is not None:
                        branch='ring2_recolor';pred=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            if pred is None:
                s['abstain']+=1;continue
            s['predictions']+=1;branches[branch]['predictions']+=1
            if gp(pred)==gp(r['after']):
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<30:wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'action':r['action'],'current':r.get('current'),'target':r.get('target')})
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    gate=bool(p>=100 and s['wrong']==0 and (metrics.get('accuracy') or 0)>=0.99)
    return {
      'schema':'deus/arc3-ft09-structural-scene-delta/1','rung':RUNG,'game':GAME,
      'model':{'structural_keys':len(structural),'observed_keys':len(obs),'key':'R211 (base,ring2)','min_trace_support':2,'scene_residual_threshold':100},
      'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'structural_scene_hits':struct_hits},
      'zero_wrong_gate_pass':gate,
      'promotion':{'gameplay_mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'if residuals remain, inspect only unmatched phase-transition trigger abstractions; never loosen zero-wrong experts'},
      'truth':{
        'public_trace_only':True,'p0_p9_fit_only':True,'heldout_never_updates_models':True,
        'all_occurrences_scene_required_per_key':True,'identical_delta_required':True,'cross_trace_support_required':True,
        'hud_row_excluded':True,'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False
      }
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'model':d['model'],'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],'hits':d['heldout']['structural_scene_hits'],'gate':d['zero_wrong_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
