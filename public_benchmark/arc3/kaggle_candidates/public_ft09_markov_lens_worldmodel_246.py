#!/usr/bin/env python3
"""R246: source-free Markov-fidelity lens + executable-mechanism residual adapter.

Bounded public-development diagnostic.  p0-p9 only are used to choose a lens and
support threshold by leave-one-trace-out (LOTO).  The chosen adapter is frozen
before evaluation on p10-p19 and can act only after the R225 source-free
incumbent abstains.  No game source/runtime implementation is imported.

Architecture is inspired by the public OpenWorld/Fable E134 pattern: compare
multiple perception lenses by Markov consistency, SELECT one representation,
then use an executable transition mechanism with verification/abstention rather
than averaging representations.  Mechanisms here are clean-room and tiny:
identity, clicked-bbox recolor, or one unambiguous R134 executable rule.

Because p10-p19 have already been reused during iterative public research, this
run can establish only a source-free development diagnostic, not independent
generalization or a Kaggle score.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict, deque
from pathlib import Path

import public_executable_world_model_134 as r134
import public_ft09_full_frame_composer_212 as r212
import public_ft09_low_confidence_goal_manifold_veto_225 as r225

RUNG=246
GAME='ft09-0d8bbf25'
MIN_SUPPORTS=(2,3,4,5)


def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def bg(board):
    c=Counter(v for row in board for v in row)
    return min(c,key=lambda x:(-c[x],x))

def comps(board, exclude_rows=()):
    h,w=len(board),len(board[0]); b=bg(board); skip=set(exclude_rows); seen=set(); out=[]
    for y in range(h):
        if y in skip: continue
        for x in range(w):
            if board[y][x]==b or (y,x) in seen: continue
            q=deque([(y,x)]); seen.add((y,x)); pts=[]
            while q:
                yy,xx=q.popleft(); pts.append((yy,xx,board[yy][xx]))
                for ny,nx in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
                    if 0<=ny<h and 0<=nx<w and ny not in skip and board[ny][nx]!=b and (ny,nx) not in seen:
                        seen.add((ny,nx)); q.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            out.append((pts[0][2],len(pts),min(ys),min(xs),max(ys)-min(ys)+1,max(xs)-min(xs)+1))
    return tuple(sorted(out))

def lens_objects(r):
    return (bg(r['before']), comps(r['before']))

def lens_salience(r):
    b=r['before']; h=len(b); skip=(0,h-1) if h>1 else ()
    small=[x for x in comps(b,skip) if x[1]<=16]
    return tuple(sorted(small,key=lambda z:(z[1],z[0],z[2],z[3])))

def lens_meter(r):
    b=r['before']; b0=bg(b)
    def edge(row): return tuple(sorted(Counter(v for v in row if v!=b0).items()))
    return (edge(b[0]),edge(b[-1]))

def lens_symmetry(r):
    a=r['before']; h,w=len(a),len(a[0])
    hs=all(a[y][x]==a[y][w-1-x] for y in range(h) for x in range(w))
    vs=all(a[y][x]==a[h-1-y][x] for y in range(h) for x in range(w))
    ds=h==w and all(a[y][x]==a[x][y] for y in range(h) for x in range(w))
    return (hs,vs,ds)

def lens_palette(r):
    return tuple(sorted(Counter(v for row in r['before'] for v in row).items()))

def region_key(board,G=8):
    h,w=len(board),len(board[0]); b0=bg(board); out=[]
    for gy in range(G):
        row=[]
        y0=int(gy*h/G); y1=max(y0+1,int((gy+1)*h/G))
        for gx in range(G):
            x0=int(gx*w/G); x1=max(x0+1,int((gx+1)*w/G))
            vals=[board[y][x] for y in range(y0,min(y1,h)) for x in range(x0,min(x1,w)) if board[y][x]!=b0]
            if not vals: row.append(b0)
            else:
                c=Counter(vals); row.append(min(c,key=lambda z:(-c[z],z)))
        out.append(tuple(row))
    return tuple(out)

def lens_regions(r): return region_key(r['before'],8)

LENSES={
 'objects':lens_objects,
 'salience':lens_salience,
 'meter_edges':lens_meter,
 'symmetry':lens_symmetry,
 'palette':lens_palette,
 'regions8':lens_regions,
}

def action_token(r):
    return r212.c191.action_class(r['action'])

def mech_from_row(r):
    before,after=r['before'],r['after']
    if before==after: return ('identity',)
    if r.get('eligible'):
        r0,c0,r1,c1,_=r['bbox']; outside=False
        for y in range(len(before)):
            for x in range(len(before[0])):
                if before[y][x]!=after[y][x] and not (r0<=y<=r1 and c0<=x<=c1): outside=True
        vals={after[y][x] for y in range(r0,r1+1) for x in range(c0,c1+1)}
        if not outside and len(vals)==1:
            return ('bbox_recolor',next(iter(vals)))
    rules=r134.infer_rules(before,after)
    if len(rules)==1:
        return ('r134_rule',json.dumps(rules[0],sort_keys=True,separators=(',',':')))
    return None

def apply_mech(mech,r):
    if mech[0]=='identity': return [x[:] for x in r['before']]
    if mech[0]=='bbox_recolor' and r.get('eligible'):
        return r212.recolor_bbox(r['before'],r['bbox'],int(mech[1]))
    if mech[0]=='r134_rule':
        return r134.apply_rule(json.loads(mech[1]),r['before'])
    return None

def markov_fidelity(rows,lens):
    tab=defaultdict(set); keys=set()
    for r in rows:
        k=lens(r); keys.add(repr(k)); mk=mech_from_row(r)
        if mk is not None: tab[(repr(k),action_token(r))].add(repr(mk))
    if len(keys)<2 or not tab: return 0.0,0.0
    consistent=sum(1 for v in tab.values() if len(v)==1)
    recurrent=sum(1 for k,v in tab.items() if sum(1 for r in rows if (repr(lens(r)),action_token(r))==k)>=2)
    return consistent/len(tab), recurrent/len(tab)

def build_adapter(paths,lens_name,min_support):
    lens=LENSES[lens_name]; raw=defaultdict(list)
    for p in paths:
        for r in r212.all_rows(p):
            if not r.get('eligible'): continue
            m=mech_from_row(r)
            if m is None: continue
            raw[(repr(lens(r)),action_token(r))].append((m,pnum(p)))
    model={}
    for k,vals in raw.items():
        ms={repr(m):m for m,_ in vals}; traces={pn for _,pn in vals}
        if len(ms)==1 and len(vals)>=min_support and len(traces)>=2:
            model[k]=next(iter(ms.values()))
    rows=[r for p in paths for r in r212.all_rows(p) if r.get('eligible')]
    fid,rec=markov_fidelity(rows,lens)
    return model,{'fidelity':round(fid,6),'recurrent_pair_fraction':round(rec,6),'keys':len(model)}

def incumbent_model(paths):
    return r225.r221.build_models(paths)

def incumbent_predict(r,lm,m):
    pred,branch=r225.r221.r218_predict(r,lm,m)
    if pred is None: pred,branch=r225.r221.r219_predict(r,lm,m)
    if pred is None:
        pred,branch,_=r225.lowbase_goal_veto(r,lm,m)
    return pred

def eval_paths(train,eval_paths,lens_name,min_support,examples=False):
    model,diag=build_adapter(train,lens_name,min_support); inc=incumbent_model(train); s=Counter(); ex=[]
    for p in eval_paths:
        meta=r225.r217.level_meta(p)
        for r in r212.all_rows(p):
            if not r.get('eligible'): continue
            s['eligible']+=1; lm=meta.get(r['step0'])
            ip=incumbent_predict(r,lm,inc)
            if ip is not None:
                s['incumbent_predictions']+=1
                if ip==r225.gp(r['after']): s['incumbent_correct']+=1
                else: s['incumbent_wrong']+=1
                continue
            k=(repr(LENSES[lens_name](r)),action_token(r)); mech=model.get(k)
            if mech is None: s['adapter_abstain']+=1; continue
            pred=apply_mech(mech,r); s['adapter_predictions']+=1
            ok=pred==r['after'] if pred is not None else False
            s['adapter_correct' if ok else 'adapter_wrong']+=1
            if examples and len(ex)<40: ex.append({'p':r['p'],'step0':r['step0'],'ok':ok,'mech':mech[0]})
    s['union_predictions']=s['incumbent_predictions']+s['adapter_predictions']
    s['union_correct']=s['incumbent_correct']+s['adapter_correct']
    s['union_wrong']=s['incumbent_wrong']+s['adapter_wrong']
    return s,diag,ex

def select_config(train):
    scores=[]
    for lname in sorted(LENSES):
        for sup in MIN_SUPPORTS:
            total=Counter(); fids=[]
            for i,val in enumerate(train):
                tr=[p for j,p in enumerate(train) if j!=i]
                ss,dd,_=eval_paths(tr,[val],lname,sup)
                total.update(ss); fids.append(dd['fidelity'])
            scores.append({'lens':lname,'min_support':sup,'metrics':dict(total),'mean_fidelity':round(sum(fids)/len(fids),6)})
    safe=[x for x in scores if x['metrics'].get('adapter_wrong',0)==0 and x['metrics'].get('adapter_predictions',0)>0]
    pool=safe if safe else scores
    chosen=max(pool,key=lambda x:(x['metrics'].get('adapter_correct',0)-10*x['metrics'].get('adapter_wrong',0),x['metrics'].get('adapter_predictions',0),x['mean_fidelity'],-x['min_support'],x['lens']))
    return chosen,scores

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
    train,held=ps[:10],ps[10:]
    chosen,scores=select_config(train)
    hs,diag,examples=eval_paths(train,held,chosen['lens'],chosen['min_support'],True)
    eligible=hs['eligible']; union=hs['union_predictions']
    held_metrics={**dict(hs),'union_accuracy':round(hs['union_correct']/union,6) if union else None,'union_coverage':round(union/eligible,6) if eligible else 0.0}
    strict_gain=bool(hs['adapter_predictions']>0 and hs['adapter_wrong']==0 and hs['union_wrong']==0 and hs['union_predictions']>307)
    return {
      'schema':'deus/arc3-ft09-markov-lens-worldmodel/1','rung':RUNG,'game':GAME,
      'source_grounding':{'pattern':'OpenWorld/Fable E134 Markov fidelity SELECT + executable verification','upstream_commit':'e8248685e4f682dd6587e1af6296733cf3838a59','upstream_files':['experiments/e134/composite.py','experiments/e134/perceptors.py'],'implementation':'clean-room source-free adapter; no game source/runtime'},
      'selection':{'protocol':'p0-p9 leave-one-trace-out only; zero-wrong-first residual selection','chosen':chosen,'candidate_count':len(scores),'all_candidates':scores},
      'frozen_adapter':diag,
      'reused_public_development_p10_p19':{'metrics':held_metrics,'examples':examples,'strict_zero_wrong_gain_vs_r225':strict_gain},
      'promotion':{'source_free_adapter_diagnostic_accept':strict_gain,'independent_generalization':False,'solver_promotion':False,'kaggle_packaging':False,'next_gate':'if gain, require a genuinely untouched/frozen family or future provider Output audit before rank integration'},
      'truth':{'public_trace_only':True,'source_free_game_runtime':True,'p10_p19_reused_public_development':True,'heldout_never_updates_adapter':True,'source_assisted_replay':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'leaderboard_score_claim':False,'submission_quota_spent':False}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'chosen':d['selection']['chosen'],'adapter':d['frozen_adapter'],'held':d['reused_public_development_p10_p19']['metrics'],'gate':d['reused_public_development_p10_p19']['strict_zero_wrong_gain_vs_r225']},sort_keys=True))
if __name__=='__main__': main()
