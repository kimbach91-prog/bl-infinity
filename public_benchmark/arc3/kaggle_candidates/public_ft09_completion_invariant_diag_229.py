#!/usr/bin/env python3
"""R229: outcome-assisted structural diagnostic for the four R227 false positives.

R228 proved that exact-ish pre-action row/column fingerprints do not transfer to
heldout completion states: selected rowcol_pos|t2 emitted zero vetoes and left
R227 unchanged at 342/346.  This diagnostic changes representation again.

It reconstructs the frozen R225 -> R227 candidate lane, virtually applies the
R227 local recolor, and measures low-dimensional structural invariants available
from pre-action state + frozen R227 target only.  Completion labels are used ONLY
to rank diagnostic separability across the public traces; no predictor is
promoted from this file.  Output is intended to select the next p0-p9-only
falsifiable family, not to claim independent generalization.
"""
from __future__ import annotations
import argparse,json,re,math
from collections import Counter,defaultdict,deque
from pathlib import Path

import public_ft09_full_frame_composer_212 as r212
import public_ft09_virtual_goal_scene_expert_217 as r217
import public_ft09_low_support_base_abstain_union_221 as r221
import public_ft09_low_confidence_goal_manifold_veto_225 as r225
import public_ft09_coarse_local_target_gate_227 as r227

RUNG=229
GAME='ft09-0d8bbf25'

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def gp(b):return [row[:] for row in b[:-1]]

def components(g):
    h=len(g);w=len(g[0]);seen=set();out=[]
    for r in range(h):
        for c in range(w):
            if (r,c) in seen:continue
            col=g[r][c];q=deque([(r,c)]);seen.add((r,c));pts=[]
            while q:
                rr,cc=q.popleft();pts.append((rr,cc))
                for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    nr,nc=rr+dr,cc+dc
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==col:
                        seen.add((nr,nc));q.append((nr,nc))
            rs=[x for x,y in pts];cs=[y for x,y in pts]
            out.append((int(col),len(pts),min(rs),max(rs),min(cs),max(cs)))
    return out

def comp_at(g,r,c):
    h=len(g);w=len(g[0]);col=g[r][c];q=deque([(r,c)]);seen={(r,c)}
    while q:
        rr,cc=q.popleft()
        for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nr,nc=rr+dr,cc+dc
            if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and g[nr][nc]==col:
                seen.add((nr,nc));q.append((nr,nc))
    rs=[x for x,y in seen];cs=[y for x,y in seen]
    return (len(seen),max(rs)-min(rs)+1,max(cs)-min(cs)+1)

def feature(r,lm,tgt):
    virtual=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt));h=len(virtual);w=len(virtual[0])
    r0,c0,r1,c1,_=r['bbox'];cr=(r0+r1)//2;cc=(c0+c1)//2
    comps=components(virtual);hist=Counter(v for row in virtual for v in row)
    macro=[x for x in comps if x[1]==36 and x[3]-x[2]+1==6 and x[5]-x[4]+1==6]
    mh=Counter(x[0] for x in macro);mshape=tuple(sorted(mh.values(),reverse=True))
    sizes=sorted((x[1] for x in comps),reverse=True)
    tshape=comp_at(virtual,cr,cc)
    nbr4=[];nbr8=[]
    for dr,dc in ((-8,0),(8,0),(0,-8),(0,8)):
        rr,ccc=cr+dr,cc+dc
        if 0<=rr<h and 0<=ccc<w:nbr4.append(virtual[rr][ccc])
    for dr in (-8,0,8):
        for dc in (-8,0,8):
            if dr==dc==0:continue
            rr,ccc=cr+dr,cc+dc
            if 0<=rr<h and 0<=ccc<w:nbr8.append(virtual[rr][ccc])
    edges=0
    for rr in range(h):
        for c in range(w):
            if rr+1<h and virtual[rr][c]!=virtual[rr+1][c]:edges+=1
            if c+1<w and virtual[rr][c]!=virtual[rr][c+1]:edges+=1
    return {
      'level':int(lm['level_before']) if lm else -1,
      'num_colors':len(hist),'color_count_shape':tuple(sorted(hist.values(),reverse=True)[:8]),
      'total_components':len(comps),'component_size_shape':tuple(sizes[:10]),
      'macro6_total':len(macro),'macro6_distinct':len(mh),'macro6_count_shape':mshape,
      'macro6_target_count':mh.get(int(tgt),0),'macro6_max_count':max(mh.values()) if mh else 0,
      'target_component_size':tshape[0],'target_component_hw':(tshape[1],tshape[2]),
      'same_nbr4':sum(x==tgt for x in nbr4),'same_nbr8':sum(x==tgt for x in nbr8),
      'nbr4_count_shape':tuple(sorted(Counter(nbr4).values(),reverse=True)),
      'nbr8_count_shape':tuple(sorted(Counter(nbr8).values(),reverse=True)),
      'target_pixels':hist.get(int(tgt),0),'edge_transitions':edges,
      'click_macro_pos':(r0//8,c0//8),
    }

def build_lane(train,paths):
    # Recreate frozen R227 selection/model and incumbent R225 models from p0-p9.
    sel,cand=r227.select(train[:5],train[5:10]);cfg=cand[sel]
    tab,_=r227.fit(train,cfg['family'],cfg['min_traces']);m=r221.build_models(train)
    rows=[]
    for p in paths:
        meta=r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r['eligible']:continue
            lm=meta.get(r['step0'])
            pred,_=r221.r218_predict(r,lm,m)
            if pred is None:pred,_=r221.r219_predict(r,lm,m)
            if pred is None:pred,_,_=r225.lowbase_goal_veto(r,lm,m)
            if pred is not None:continue
            tgt=tab.get(repr(r227.feat(cfg['family'],r,lm)))
            if tgt is None or r227.goal_veto(r,lm,tgt,m) is not None:continue
            f=feature(r,lm,tgt);completion=bool(lm and lm['level_after']>lm['level_before'])
            local_pred=gp(r212.recolor_bbox(r['before'],r['bbox'],tgt));ok=local_pred==gp(r['after'])
            rows.append({'p':r['p'],'step0':r['step0'],'path':r['path'],'action':r['action'],'target':tgt,
              'completion':completion,'local_exact':ok,'level_before':lm['level_before'] if lm else None,'level_after':lm['level_after'] if lm else None,'f':f})
    return sel,cfg,rows

def pure_groups(rows):
    names=[k for k in rows[0]['f'] if k!='click_macro_pos'] if rows else []
    scored=[]
    for name in names:
        groups=defaultdict(list)
        for x in rows:groups[repr(x['f'][name])].append(x)
        tp=fp=keys=traces=0;examples=[]
        for val,xs in groups.items():
            labs={x['completion'] for x in xs}
            tr={x['path'] for x in xs}
            if labs=={True} and len(tr)>=2:
                keys+=1;tp+=len(xs);traces+=len(tr)
                if len(examples)<12:examples.append({'value':val,'n':len(xs),'traces':len(tr),'examples':[(x['p'],x['step0']) for x in xs[:5]]})
        if tp:scored.append({'feature':name,'pure_completion_examples':tp,'pure_keys':keys,'trace_support_sum':traces,'examples':examples})
    scored.sort(key=lambda z:(-z['pure_completion_examples'],z['pure_keys'],z['feature']))
    return scored

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    sel,cfg,rows=build_lane(ps[:10],ps)
    wrong=[x for x in rows if not x['local_exact']]
    completions=[x for x in rows if x['completion']]
    noncomp=[x for x in rows if not x['completion']]
    return {'schema':'deus/arc3-ft09-completion-invariant-diagnostic/1','rung':RUNG,'game':GAME,
      'r227':{'selected':sel,'family':cfg['family'],'min_traces':cfg['min_traces']},
      'population':{'candidate_rows':len(rows),'completion_rows':len(completions),'noncompletion_rows':len(noncomp),'local_wrong':len(wrong)},
      'wrong_rows':wrong,'top_pure_completion_single_features':pure_groups(rows)[:20],
      'completion_feature_examples':completions[:30],
      'truth':{'public_trace_only':True,'outcome_assisted_diagnostic':True,'predictor_promotion':False,'heldout_used_for_diagnostic_only':True,
        'next_predictor_must_refit_and_select_without_p10_p19':True,'independent_generalization_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'r227':d['r227'],'population':d['population'],'wrong_rows':d['wrong_rows'],'top':d['top_pure_completion_single_features'][:10]},sort_keys=True))
if __name__=='__main__':main()
