#!/usr/bin/env python3
"""R261: source-free temporal underlay-memory diagnostic for re86.

R260 shows selective object transport cuts movement-frame Hamming error by about
58-72%, with many predictions only 1-4 cells wrong. R259 shows observed moved
object footprints explain ~95-98% median changed-cell support. A likely specific
remaining defect is source-cell restoration: R257 clears vacated object cells to
a single dominant background even when a screen-fixed substrate was previously
visible there.

R261 tests that mechanism only. It learns the same object-transport models from
p0-p4, then evaluates p5-p9 sequentially. For each validation trace it keeps an
online screen-coordinate underlay cache populated only from PAST observed
pre-action frames at cells not occupied by any learned movable class. Vacated
object cells are restored from that cache when known, else background. It
compares cached restoration with R257's background restoration on exactly the
same predicted transitions.

Diagnostic only: p0-p9 public-development traces, no p10-p19, no game source,
no hidden data, no Kaggle runtime/score, no promotion.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257


def hamming(a,b):
    return sum(int(x)!=int(y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))


def prep_one(path):
    rows=[]
    for step,row in enumerate(r251.prepare_rows([path])):
        x=dict(row); x['transition_id']=f'{path.name}#{step}'; rows.append(x)
    return rows


def summarize(vals):
    if not vals: return {'n':0}
    s=sorted(vals); n=len(s)
    return {'n':n,'mean':round(sum(s)/n,6),'median':statistics.median(s),
            'p90':s[min(n-1,max(0,int(.9*n)))],
            'exact':sum(v==0 for v in s),'le1':round(sum(v<=1 for v in s)/n,6),
            'le2':round(sum(v<=2 for v in s)/n,6),'le4':round(sum(v<=4 for v in s)/n,6),
            'le8':round(sum(v<=8 for v in s)/n,6)}


def movable_cells(board, movable_classes, max_area):
    cells=set()
    for c in r254.components(board):
        if c['area']<=max_area and r257.cls(c) in movable_classes:
            for dr,dc in c['shape']:
                cells.add((c['r0']+dr,c['c0']+dc))
    return cells


def render_cached(board, vector, movable, max_area, cache):
    if not vector or not movable: return None
    comps=[c for c in r254.components(board) if c['area']<=max_area and r257.cls(c) in movable]
    if not comps: return None
    h=len(board); w=len(board[0]); bg=r246.bg(board); dr,dc=vector
    for c in comps:
        if c['r0']+dr<0 or c['c0']+dc<0 or c['r1']+dr>=h or c['c1']+dc>=w: return None
    out=[list(map(int,row)) for row in board]
    for c in comps:
        for rr,cc in c['shape']:
            r=c['r0']+rr; col=c['c0']+cc
            out[r][col]=int(cache.get((r,col),bg))
    for c in comps:
        for rr,cc in c['shape']:
            out[c['r0']+rr+dr][c['c0']+cc+dc]=int(c['color'])
    return out


def evaluate_variant(train_by, val_paths, max_area, min_frac, min_support):
    models={}
    union_classes=set()
    for action,rows in train_by.items():
        model=r257.learn(rows,max_area,min_frac,min_support)
        models[action]=model
        union_classes.update(model[1].keys())
    bg_err=[]; cache_err=[]; improvements=[]; regressions=0; improved=0; same=0
    exact_bg=0; exact_cache=0; by_action=defaultdict(lambda:{'bg':[],'cache':[]})
    # Each p5..p9 trace has its own causal cache. Cache sees only current/past pre-action frames.
    for path in val_paths:
        rows=prep_one(path); cache={}
        for row in rows:
            board=row['before']; action=row['action']
            # First ingest currently visible cells that are not occupied by any class learned as movable.
            occ=movable_cells(board,union_classes,max_area)
            for r in range(len(board)):
                for c in range(len(board[0])):
                    if (r,c) not in occ:
                        cache[(r,c)]=int(board[r][c])
            model=models.get(action)
            if not model: continue
            vector,movable=model
            p_bg=r257.render(board,vector,movable,max_area)
            if p_bg is None: continue
            p_cache=render_cached(board,vector,movable,max_area,cache)
            if p_cache is None: continue
            e0=hamming(p_bg,row['after']); e1=hamming(p_cache,row['after'])
            bg_err.append(e0); cache_err.append(e1); improvements.append(e0-e1)
            by_action[action]['bg'].append(e0); by_action[action]['cache'].append(e1)
            exact_bg+=int(e0==0); exact_cache+=int(e1==0)
            if e1<e0: improved+=1
            elif e1>e0: regressions+=1
            else: same+=1
    n=len(bg_err)
    return {
      'predictions':n,'bg_restore':summarize(bg_err),'cached_restore':summarize(cache_err),
      'exact_gain':exact_cache-exact_bg,
      'mean_hamming_reduction_fraction':round(1-(sum(cache_err)/sum(bg_err)),6) if bg_err and sum(bg_err)>0 else None,
      'improved_fraction':round(improved/n,6) if n else 0.0,'regressed_fraction':round(regressions/n,6) if n else 0.0,
      'same_fraction':round(same/n,6) if n else 0.0,
      'by_action':{a:{'bg':summarize(v['bg']),'cache':summarize(v['cache'])} for a,v in sorted(by_action.items())},
      'union_movable_class_count':len(union_classes)
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    train=[r for p in ps[:5] for r in prep_one(p)]; train_by=defaultdict(list)
    for r in train: train_by[r['action']].append(r)
    variants={}
    for max_area,min_frac,min_support in r257.VARIANTS:
        k=f'a{max_area}_f{int(min_frac*100)}_s{min_support}'
        variants[k]=evaluate_variant(train_by,ps[5:],max_area,min_frac,min_support)
    ranked=[(-v['exact_gain'], -(v['mean_hamming_reduction_fraction'] or -999), v['cached_restore'].get('median',10**9), k) for k,v in variants.items() if v['predictions']>0]
    ranked.sort(); best=ranked[0][3] if ranked else None
    out={'schema':'deus/arc3-r261-underlay-memory-diagnostic/1','rung':261,
         'lineage':{'r259':'run35799253399/artifact10724893447','r260':'run35799394728/artifact10725301644',
                    'hypothesis':'vacated moving-object cells require causal screen-fixed underlay restoration, not global background'},
         'protocol':{'fit':'p0-p4','diagnostic_eval':'p5-p9 sequential causal cache','p10_p19_read':False,'promotion':False},
         'best_variant':best,'variants':variants,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'cache_uses_past_and_current_preaction_only':True,
                  'future_after_used_for_cache':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'best_variant':best,'best':variants.get(best)},sort_keys=True))
if __name__=='__main__': main()
