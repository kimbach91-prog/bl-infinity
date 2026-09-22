#!/usr/bin/env python3
"""R218: ft09 structural solved-state fingerprint expert.

R217's exact virtual-goal signature closes all but one heldout completion
transition. R218 keeps R217 exact-goal precedence, then adds ONE structural
virtual-goal family selected using p0-p9 only.

For each candidate fingerprint, p0-p9 observations are grouped by:
  current level + fingerprint(virtual board after frozen R211 local recolor).
A structural goal key is accepted only when:
  - every training occurrence is a level completion,
  - support spans >=2 distinct traces,
  - all completion occurrences lead to one exact next-scene gameplay board.

Family selection uses training evidence only: maximize covered completion
examples, then prefer fewer accepted keys and lower predefined complexity.
Heldout never changes family/model selection.

HUD row 63 is excluded from fingerprints, outputs, and scoring.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path

import public_executable_world_model_134 as base
import public_ft09_full_frame_composer_212 as r212
import public_ft09_phase_hud_identity_gate_202 as r202
import public_ft09_scene_exact_expert_216 as r216
import public_ft09_virtual_goal_scene_expert_217 as r217

RUNG=218
GAME='ft09-0d8bbf25'
FAMILIES=('color_hist','macro6_hist','component_spectrum','quadrant_hist','rowcol_bands','exact')
COMPLEXITY={name:i for i,name in enumerate(FAMILIES)}

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def gp(board):
    return [row[:] for row in board[:-1]]

def color_hist(board):
    c=Counter(v for row in gp(board) for v in row)
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def components(board):
    g=gp(board);h=len(g);w=len(g[0]);seen=set();out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen: continue
            col=g[r][c];q=deque([(r,c)]);seen.add((r,c));pts=[]
            while q:
                rr,cc=q.popleft();pts.append((rr,cc))
                for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==col:
                        seen.add((nr,nc));q.append((nr,nc))
            rs=[x for x,y in pts];cs=[y for x,y in pts]
            out.append((int(col),len(pts),max(rs)-min(rs)+1,max(cs)-min(cs)+1))
    return out

def component_spectrum(board):
    by=defaultdict(list)
    for col,n,h,w in components(board):
        by[col].append((n,h,w))
    return tuple((int(col),tuple(sorted(vals))) for col,vals in sorted(by.items()))

def macro6_hist(board):
    c=Counter()
    for col,n,h,w in components(board):
        if n==36 and h==6 and w==6:
            c[col]+=1
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def region_hist(g,r0,r1,c0,c1):
    c=Counter(g[r][cc] for r in range(r0,r1) for cc in range(c0,c1))
    return tuple(sorted((int(k),int(v)) for k,v in c.items()))

def quadrant_hist(board):
    g=gp(board);h=len(g);w=len(g[0]);rm=h//2;cm=w//2
    return (
      region_hist(g,0,rm,0,cm),region_hist(g,0,rm,cm,w),
      region_hist(g,rm,h,0,cm),region_hist(g,rm,h,cm,w),
    )

def rowcol_bands(board):
    g=gp(board);h=len(g);w=len(g[0]);rb=[];cb=[]
    for i in range(4):
        r0=i*h//4;r1=(i+1)*h//4
        rb.append(region_hist(g,r0,r1,0,w))
        c0=i*w//4;c1=(i+1)*w//4
        cb.append(region_hist(g,0,h,c0,c1))
    return (tuple(rb),tuple(cb))

def fp(fam,board):
    if fam=='color_hist': return color_hist(board)
    if fam=='macro6_hist': return macro6_hist(board)
    if fam=='component_spectrum': return component_spectrum(board)
    if fam=='quadrant_hist': return quadrant_hist(board)
    if fam=='rowcol_bands': return rowcol_bands(board)
    if fam=='exact': return base.stable(gp(board))
    raise ValueError(fam)

def structural_key(fam,level_before,virtual):
    return base.stable({'level':int(level_before),'family':fam,'fp':fp(fam,virtual)})

def fit_family(paths,rm,fam,min_traces=2):
    obs=defaultdict(lambda:{'labels':Counter(),'traces':set(),'outs':{},'out_counts':Counter(),'completion_n':0})
    total_completion=0
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            tgt=rm.get(repr((r['base'],r['ring2'])))
            if tgt is None: continue
            lm=meta.get(r['step0'])
            if lm is None: continue
            virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
            completion=lm['level_after']>lm['level_before']
            if completion: total_completion+=1
            k=structural_key(fam,lm['level_before'],virtual)
            x=obs[k];x['labels'][completion]+=1;x['traces'].add(r['path'])
            if completion:
                x['completion_n']+=1
                out=gp(r['after']);dg=base.digest(out)
                x['outs'][dg]=out;x['out_counts'][dg]+=1
    model={};covered=0;accepted_meta={}
    for k,x in obs.items():
        if x['labels'][False] or not x['labels'][True]: continue
        if len(x['traces'])<min_traces: continue
        if len(x['out_counts'])!=1: continue
        dg=next(iter(x['out_counts']))
        model[k]=x['outs'][dg]
        covered+=x['completion_n']
        accepted_meta[k]={'completion_examples':x['completion_n'],'trace_support':len(x['traces'])}
    return model,obs,{
      'accepted_keys':len(model),'completion_examples_covered':covered,
      'total_completion_examples':total_completion,
      'coverage':round(covered/total_completion,6) if total_completion else 0.0,
      'accepted_meta':accepted_meta,
    }

def choose_family(paths,rm):
    stats={};models={}
    for fam in FAMILIES:
        m,obs,s=fit_family(paths,rm,fam,2)
        stats[fam]={k:v for k,v in s.items() if k!='accepted_meta'}
        models[fam]=m
    selected=sorted(
      FAMILIES,
      key=lambda fam:(-stats[fam]['completion_examples_covered'],stats[fam]['accepted_keys'],COMPLEXITY[fam])
    )[0]
    return selected,models[selected],stats

def evaluate(paths,exact_goal,struct_goal,fam,scene,im,rm):
    s=Counter();branches={k:Counter() for k in ('exact_goal','struct_goal','scene_exact','identity','ring2_recolor')}
    wrong=[];hits=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']: continue
            s['eligible']+=1;lm=meta.get(r['step0'])
            tgt=rm.get(repr((r['base'],r['ring2'])))
            pred_gp=None;branch=None
            virtual=None

            if tgt is not None and lm is not None:
                virtual=r212.recolor_bbox(r['before'],r['bbox'],tgt)
                ek=r217.goal_key(lm['level_before'],virtual)
                if ek in exact_goal:
                    branch='exact_goal';pred_gp=[row[:] for row in exact_goal[ek]]

            if pred_gp is None and virtual is not None and lm is not None:
                sk=structural_key(fam,lm['level_before'],virtual)
                if sk in struct_goal:
                    branch='struct_goal';pred_gp=[row[:] for row in struct_goal[sk]]
                    if len(hits)<30:
                        hits.append({
                          'trace':r['path'],'p':r['p'],'step0':r['step0'],'action':r['action'],
                          'level_before':lm['level_before'],'level_after_actual':lm['level_after'],
                        })

            if pred_gp is None:
                sk2=r216.scene_key(r)
                if sk2 in scene:
                    branch='scene_exact';pred_gp=[row[:] for row in scene[sk2]]

            if pred_gp is None:
                idkey=r202.feature('local',r['before'],r['action'],r['prev_action'],r['run_len'],r['step0'])
                if idkey in im:
                    branch='identity';pred_gp=gp(r['before'])

            if pred_gp is None and tgt is not None:
                branch='ring2_recolor'
                pred=r212.recolor_bbox(r['before'],r['bbox'],tgt);pred_gp=gp(pred)

            if pred_gp is None:
                s['abstain']+=1;continue
            s['predictions']+=1;branches[branch]['predictions']+=1
            if pred_gp==gp(r['after']):
                s['correct']+=1;branches[branch]['correct']+=1
            else:
                s['wrong']+=1;branches[branch]['wrong']+=1
                if len(wrong)<30:
                    wrong.append({
                      'trace':r['path'],'p':r['p'],'step0':r['step0'],'branch':branch,'action':r['action'],
                      'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None,
                    })

    p=s['predictions'];e=s['eligible']
    metrics={**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/e,6) if e else 0.0}
    for k,v in branches.items():
        pp=v['predictions'];branches[k]={**dict(v),'accuracy':round(v['correct']/pp,6) if pp else None}
    return metrics,branches,wrong,hits

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=ps[:10];held=ps[10:]
    rm=r212.ring2_model(train);im=r212.identity_model(train)
    scene,_=r216.fit_scene(train,2)
    exact_goal,_,_,_=r217.fit_goal(train,rm,2)
    selected,struct_goal,family_stats=choose_family(train,rm)

    metrics,branches,wrong,hits=evaluate(held,exact_goal,struct_goal,selected,scene,im,rm)
    gate=bool(metrics.get('predictions',0)>=100 and metrics.get('wrong',0)==0 and (metrics.get('accuracy') or 0)>=0.99)

    return {
      'schema':'deus/arc3-ft09-structural-goal-scene-expert/1','rung':RUNG,'game':GAME,
      'selected_family':selected,'family_stats':family_stats,
      'models':{'exact_goal_keys':len(exact_goal),'structural_goal_keys':len(struct_goal),'scene_exact_keys':len(scene)},
      'heldout':{'all':metrics,'by_branch':branches,'wrong_examples':wrong,'structural_goal_hits':hits},
      'zero_wrong_gate_pass':gate,
      'promotion':{
        'gameplay_mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,
        'next_gate':'if zero-wrong, freeze precedence and expand policy/action coverage; otherwise inspect only remaining residual',
      },
      'truth':{
        'public_trace_only':True,'p0_p9_family_selection_and_fit_only':True,
        'heldout_never_updates_family_or_models':True,'cross_trace_support_required':True,
        'exact_goal_precedence_preserved':True,'hud_row_excluded_from_goal_key_output_and_scoring':True,
        'independent_generalization_claim':False,'kaggle_execution':False,
        'submission_quota_spent':False,'owner_score_claim':False,
      },
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
      'selected_family':d['selected_family'],'family_stats':d['family_stats'],
      'models':d['models'],'heldout':d['heldout']['all'],'branches':d['heldout']['by_branch'],
      'hits':d['heldout']['structural_goal_hits'],'wrong':d['heldout']['wrong_examples'],'gate':d['zero_wrong_gate_pass'],
    },sort_keys=True))
if __name__=='__main__':main()
