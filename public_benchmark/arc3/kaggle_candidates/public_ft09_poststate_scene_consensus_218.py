#!/usr/bin/env python3
"""R218: ft09 post-local scene consensus expert over R217.

Goal: cover structural scene jumps whose R211 (base,ring2) key varies across
paths, without hardcoding a heldout trace.

Fit p0-p9 only. After the frozen R211 local recolor, build broader pre-scene
signatures:
  - exact gameplay color histogram
  - macro 8x8 lattice center-color histogram
Each signature key is (current,target,signature).

A signature can predict a scene delta only when every training occurrence is a
large scene residual (>=100 cells), one identical delta template, and >=2 trace
support. On heldout, matching experts must agree on the delta.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path

import public_executable_world_model_134 as base
import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_scene_exact_expert_216 as r216
import public_ft09_structural_scene_delta_217 as r217

RUNG=218
GAME='ft09-0d8bbf25'
FAMILIES=('color_hist','macro_hist')

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):return [row[:] for row in board[:-1]]

def color_hist(board):
    c=Counter(v for row in gp(board) for v in row)
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def macro_hist(board):
    # 8-pixel pitch used by the 6x6 tile lattice. Sample conservative center
    # coordinates 6,14,...,54 and ignore HUD row.
    vals=[]
    h=len(board)-1;w=len(board[0])
    for r in range(6,h,8):
        for c in range(6,w,8):
            vals.append(int(board[r][c]))
    return tuple(sorted(Counter(vals).items()))

def sig(fam,pred,r):
    if fam=='color_hist':z=color_hist(pred)
    elif fam=='macro_hist':z=macro_hist(pred)
    else:raise ValueError(fam)
    return repr((int(r['current']),int(r['target']),z))

def delta_template(pred,actual):
    out=[]
    for rr,(a,b) in enumerate(zip(gp(pred),gp(actual))):
        for cc,(x,y) in enumerate(zip(a,b)):
            if x!=y:out.append((rr,cc,int(y)))
    return tuple(out)

def apply_delta(pred,dt):
    out=[row[:] for row in pred]
    for r,c,v in dt:
        if r>=len(out)-1:raise ValueError('HUD delta forbidden')
        out[r][c]=v
    return out

def fit_family(paths,rm,fam,min_traces=2):
    obs=defaultdict(lambda:{'scene':0,'nonscene':0,'templates':Counter(),'template_values':{},'traces':set()})
    for p in paths:
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            tgt=rm.get(r217.structural_key(r))
            if tgt is None:continue
            local=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            dt=delta_template(local,r['after'])
            k=sig(fam,local,r);x=obs[k];x['traces'].add(r['path'])
            if len(dt)>=100:
                x['scene']+=1;dg=base.digest(dt);x['templates'][dg]+=1;x['template_values'][dg]=dt
            else:x['nonscene']+=1
    model={}
    for k,x in obs.items():
        if x['scene']>0 and x['nonscene']==0 and len(x['templates'])==1 and len(x['traces'])>=min_traces:
            dg=next(iter(x['templates']));model[k]=x['template_values'][dg]
    return model,obs

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    scene_exact,_=r216.fit_scene(train,2)
    im=r212.identity_model(train);rm=r212.ring2_model(train)
    structural,_=r217.fit_structural_scene(train,rm,2)
    fam_models={};fam_obs={}
    for fam in FAMILIES:
        fam_models[fam],fam_obs[fam]=fit_family(train,rm,fam,2)

    s=Counter();branches={k:Counter() for k in ('scene_exact','scene_structural_delta','scene_poststate_consensus','identity','ring2_recolor')}
    wrong=[];hits=[];conflicts=0
    for p in held:
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            s['eligible']+=1
            branch=None;pred=None
            sk=r216.scene_key(r)
            tgt=rm.get(r217.structural_key(r))
            if sk in scene_exact:
                branch='scene_exact';pred=scene_exact[sk]+[r['before'][-1][:]]
            elif tgt is not None and r217.structural_key(r) in structural:
                branch='scene_structural_delta'
                local=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                pred=r217.apply_delta(local,structural[r217.structural_key(r)])
            else:
                local=r212.recolor_bbox(r['before'],r['bbox'],tgt) if tgt is not None else None
                candidates={}
                if local is not None:
                    for fam,m in fam_models.items():
                        dt=m.get(sig(fam,local,r))
                        if dt is not None:candidates[base.digest(dt)]=(dt,fam)
                if candidates and len(candidates)==1:
                    dt,fam=next(iter(candidates.values()))
                    branch='scene_poststate_consensus';pred=apply_delta(local,dt)
                    if len(hits)<20:hits.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],'family':fam,'delta_cells':len(dt)})
                elif len(candidates)>1:
                    conflicts+=1
                if pred is None:
                    idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                    if idkey in im:
                        branch='identity';pred=[row[:] for row in r['before']]
                    elif local is not None:
                        branch='ring2_recolor';pred=local
            if pred is None:
                s['abstain']+=1;continue
            s['predictions']+=1;branches[branch]['predictions']+=1
            if gp(pred)==gp(r['after']):
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<20:wrong.append({'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'action':r['action'],'current':r.get('current'),'target':r.get('target')})
    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    gate=bool(p>=100 and s['wrong']==0 and (metrics.get('accuracy') or 0)>=0.99)
    return {
      'schema':'deus/arc3-ft09-poststate-scene-consensus/1','rung':RUNG,'game':GAME,
      'models':{fam:{'keys':len(fam_models[fam]),'observed_keys':len(fam_obs[fam])} for fam in FAMILIES},
      'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'poststate_hits':hits,'expert_conflicts':conflicts},
      'zero_wrong_gate_pass':gate,
      'promotion':{'gameplay_mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'on zero-wrong transition gate, move from transition modeling to action-policy/goal coverage; otherwise inspect only last unmatched scene trigger'},
      'truth':{
        'public_trace_only':True,'p0_p9_fit_only':True,'heldout_never_updates_models':True,
        'all_occurrences_scene_required_per_key':True,'identical_delta_required':True,'cross_trace_support_required':True,
        'multi_expert_agreement_required_when_multiple_match':True,'hud_row_excluded':True,
        'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False
      }
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'models':d['models'],'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],'hits':d['heldout']['poststate_hits'],'conflicts':d['heldout']['expert_conflicts'],'gate':d['zero_wrong_gate_pass']},sort_keys=True))
if __name__=='__main__':main()
