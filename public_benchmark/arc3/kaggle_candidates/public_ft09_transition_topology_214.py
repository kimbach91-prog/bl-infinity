#!/usr/bin/env python3
"""R214: ft09 macro transition-topology discovery gate.

Independent implementation from public trace pixels. It tests a bounded
mechanism hypothesis suggested by prior R210 evidence and public descriptions:
plain phases should mostly change the clicked tile, while a distinct functional
phase may couple the clicked tile to one or more other macro tiles.

No external solver code is imported. p0-p9 fit only; p10-p19 frozen audit.
This is mechanism discovery, not a solver or Kaggle promotion.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path

import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191

RUNG=214
GAME='ft09-0d8bbf25'
Grid=list[list[int]]

def pnum(p:Path)->int:
    m=re.search(r'_p(\d+)_events\.jsonl$',p.name)
    return int(m.group(1)) if m else -1

def bbox(points):
    rs=[r for r,c in points]; cs=[c for r,c in points]
    return (min(rs),min(cs),max(rs),max(cs)) if points else None

def dominant_bg(board:Grid)->int:
    return base.dominant_background(board)

def nonbg_components(board:Grid):
    h,w=len(board),len(board[0]); bg=dominant_bg(board)
    pts={(r,c) for r in range(h) for c in range(w) if board[r][c]!=bg}
    out=[]
    while pts:
        z=next(iter(pts));pts.remove(z);q=[z];comp=[z]
        for r,c in q:
            for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                y=(r+dr,c+dc)
                if y in pts:
                    pts.remove(y);q.append(y);comp.append(y)
        bb=bbox(comp);r0,c0,r1,c1=bb
        pal=Counter(board[r][c] for r,c in comp)
        out.append({'cells':comp,'bbox':bb,'h':r1-r0+1,'w':c1-c0+1,'n':len(comp),
                    'palette':tuple(sorted((int(k),int(v)) for k,v in pal.items())),
                    'marker6':int(pal.get(6,0))})
    return out

def tiles(board:Grid):
    # Full or near-full 6x6 non-background objects. Near-full admits marked/glyph tiles.
    return [x for x in nonbg_components(board) if x['h']==6 and x['w']==6 and x['n']>=20]

def find_clicked_tile(board:Grid,click):
    r,c=click
    cs=[]
    for t in tiles(board):
        r0,c0,r1,c1=t['bbox']
        if r0<=r<=r1 and c0<=c<=c1: cs.append(t)
    if len(cs)==1:return cs[0]
    return None

def diff_components(a:Grid,b:Grid):
    h,w=len(a),len(a[0])
    pts={(r,c) for r in range(h) for c in range(w) if a[r][c]!=b[r][c]}
    out=[]
    while pts:
        z=next(iter(pts));pts.remove(z);q=[z];comp=[z]
        for r,c in q:
            for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                y=(r+dr,c+dc)
                if y in pts:
                    pts.remove(y);q.append(y);comp.append(y)
        bb=bbox(comp);r0,c0,r1,c1=bb
        out.append({'cells':comp,'bbox':bb,'h':r1-r0+1,'w':c1-c0+1,'n':len(comp)})
    return sorted(out,key=lambda x:(x['bbox'],x['n']))

def rel_offset(click_tile,comp):
    a=click_tile['bbox'];b=comp['bbox']
    ar=(a[0]+a[2])//2; ac=(a[1]+a[3])//2
    br=(b[0]+b[2])//2; bc=(b[1]+b[3])//2
    dr,dc=br-ar,bc-ac
    # Typical ft09 lattice pitch is 8px. Preserve raw offset if not aligned.
    if dr%8==0 and dc%8==0:return ('g',dr//8,dc//8)
    return ('p',dr,dc)

def level_token(pre,e):
    for k in ('level','level_index','levels_completed'):
        if k in e:return (k,e.get(k))
        if k in pre:return (k,pre.get(k))
    return ('unknown',None)

def palette_shape(pal):
    # Color-role agnostic multiplicity profile plus explicit marker-6 count.
    return tuple(sorted((n for c,n in pal),reverse=True))

def board_mode(board):
    ts=tiles(board)
    return {
      'tile_count':len(ts),
      'marker6_tile_count':sum(t['marker6']>0 for t in ts),
      'marker6_pixels':sum(t['marker6'] for t in ts),
      'tile_shapes':tuple(sorted((palette_shape(t['palette']),t['marker6']) for t in ts)),
    }

def rows(path:Path):
    ev=base.load_events(path);pre=ev[0];step=0
    out=[]
    for e in ev[1:]:
        if e.get('type')!='action':pre=e;continue
        before=base.as_grid(pre['board']);after=base.as_grid(e['board'])
        a=base.action_name(e);step+=1
        if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':
            pre=e;continue
        click=c191.parse_mouse(a)
        if click is None:
            pre=e;continue
        ct=find_clicked_tile(before,click)
        if ct is None:
            pre=e;continue
        comps=diff_components(before,after)
        macro=[x for x in comps if x['h']==6 and x['w']==6 and x['n']==36]
        residual=[x for x in comps if x not in macro]
        offs=tuple(sorted(rel_offset(ct,x) for x in macro))
        mode=board_mode(before)
        lvl=level_token(pre,e)
        rec={
          'trace':path.name,'p':pnum(path),'step':step,'level':lvl,'click':click,
          'clicked_palette':ct['palette'],'clicked_shape':palette_shape(ct['palette']),
          'clicked_marker6':ct['marker6'],
          'mode':mode,
          'macro_offsets':offs,
          'macro_count':len(macro),
          'residual_cells':sum(x['n'] for x in residual),
          'residual_components':tuple((x['h'],x['w'],x['n']) for x in residual),
          'diff_cells':sum(x['n'] for x in comps),
        }
        if offs==(('g',0,0),) and rec['residual_cells']==0: rec['class']='self_only'
        elif ('g',0,0) in offs and len(offs)>=2: rec['class']='self_plus_other'
        elif len(offs)>=1: rec['class']='macro_other'
        elif rec['diff_cells']==0: rec['class']='no_change'
        else: rec['class']='nonmacro'
        out.append(rec)
        pre=e
    return out

def key(rec,kind):
    m=rec['mode']
    common=(rec['clicked_shape'],rec['clicked_marker6'],m['tile_count'],m['marker6_tile_count'],m['marker6_pixels'])
    if kind=='mode':return common
    if kind=='mode_level':return common+(rec['level'],)
    if kind=='marker_level':return (rec['clicked_marker6'],m['marker6_tile_count'],rec['level'])
    if kind=='shape_level':return (rec['clicked_shape'],rec['clicked_marker6'],rec['level'])
    raise ValueError(kind)

def target(rec):
    return (rec['macro_offsets'],rec['residual_components'])

def fit(train,kind):
    obs=defaultdict(Counter)
    for r in train:obs[repr(key(r,kind))][repr(target(r))]+=1
    table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
    return table,obs

def evaluate(table,held,kind):
    s=Counter();mistakes=[]
    for r in held:
        s['eligible']+=1
        k=repr(key(r,kind));pred=table.get(k)
        if pred is None:s['abstain']+=1;continue
        s['predictions']+=1
        ok=pred==repr(target(r))
        s['correct' if ok else 'wrong']+=1
        if not ok and len(mistakes)<20:
            mistakes.append({'trace':r['trace'],'p':r['p'],'step':r['step'],'level':r['level'],
              'class':r['class'],'macro_offsets':r['macro_offsets'],'residual_components':r['residual_components'],
              'pred':pred,'key':repr(key(r,kind))})
    p=s['predictions'];e=s['eligible']
    return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,
            'coverage':round(p/e,6) if e else 0.0,'mistakes':mistakes}

def summarize(rs):
    by=defaultdict(Counter);offs=defaultdict(Counter)
    for r in rs:
        g=repr(r['level'])
        by[g][r['class']]+=1
        offs[g][repr(r['macro_offsets'])]+=1
    return {
      'by_level_class':{g:dict(c) for g,c in sorted(by.items())},
      'by_level_offsets':{g:dict(c.most_common(12)) for g,c in sorted(offs.items())},
    }

def run(paths):
    ps=sorted(paths,key=pnum)
    if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
    train=[r for p in ps[:10] for r in rows(p)]
    held=[r for p in ps[10:] for r in rows(p)]
    kinds=('mode','mode_level','marker_level','shape_level')
    models={}
    for kind in kinds:
        tab,obs=fit(train,kind)
        models[kind]={'train':{'keys':len(obs),'deterministic_keys':len(tab),
                              'conflicted_keys':sum(len(c)>1 for c in obs.values())},
                      'heldout':evaluate(tab,held,kind)}
    # Mechanism signal: observed self+other transitions and at least one zero-wrong
    # frozen predictor with nontrivial coverage. This does not imply full solver.
    multi_train=sum(r['class']=='self_plus_other' for r in train)
    multi_held=sum(r['class']=='self_plus_other' for r in held)
    zero=[k for k,v in models.items() if (v['heldout'].get('predictions',0)>=30 and
          v['heldout'].get('wrong',0)==0 and (v['heldout'].get('accuracy') or 0)==1.0)]
    gate=bool(multi_train>0 and multi_held>0 and zero)
    return {
      'schema':'deus/arc3-ft09-transition-topology-discovery/1','rung':RUNG,'game':GAME,
      'train_count':len(train),'heldout_count':len(held),
      'train_summary':summarize(train),'heldout_summary':summarize(held),
      'models':models,
      'coupling_evidence':{'self_plus_other_train':multi_train,'self_plus_other_heldout':multi_held,
                           'zero_wrong_model_keys':zero},
      'mechanism_gate_pass':gate,
      'promotion':{'mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,
                   'next_if_pass':'infer explicit coupling graph / GF2 only for the empirically coupled phase; otherwise reject coupling hypothesis'},
      'truth':{'public_trace_only':True,'independent_implementation':True,
               'external_solver_code_imported':False,'p0_p9_fit_only':True,
               'p10_p19_never_update_model':True,'iterative_public_heldout_research':True,
               'independent_generalization_claim':False,'full_frame_solver_claim':False,
               'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'rung':RUNG,'counts':[d['train_count'],d['heldout_count']],
      'coupling':d['coupling_evidence'],'gate':d['mechanism_gate_pass'],
      'models':{k:{x:v['heldout'].get(x) for x in ('predictions','correct','wrong','accuracy','coverage')} for k,v in d['models'].items()},
      'heldout_classes':d['heldout_summary']['by_level_class']},sort_keys=True))
if __name__=='__main__':main()
