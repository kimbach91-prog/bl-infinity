#!/usr/bin/env python3
"""R264: source-free object-relative residual diagnostic for re86.

R263 shows post-transport residuals are not concentrated at fixed screen
coordinates. R264 tests whether those residuals concentrate relative to the
predicted destinations of moved visible objects, which would support an
object-local/orientation/compositing mechanism rather than HUD coordinates.

Fit transport on p0-p4, diagnose p5-p9. No p10-p19, game source, Kaggle score,
or promotion.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257

MAX_AREA=13; MIN_FRAC=.8; MIN_SUPPORT=3

def prep(p):
    out=[]
    for i,r in enumerate(r251.prepare_rows([p])):
        x=dict(r); x['transition_id']=f'{p.name}#{i}'; out.append(x)
    return out

def conc(c):
    n=sum(c.values()); vals=[v for _,v in c.most_common()]
    def s(k): return round(sum(vals[:k])/n,6) if n else 0.0
    return {'total':n,'unique':len(c),'top1':s(1),'top5':s(5),'top10':s(10),'top25':s(25),'top':[[list(k) if isinstance(k,tuple) else k,v] for k,v in c.most_common(20)]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(nums)
    tr=[r for p in ps[:5] for r in prep(p)]; va=[r for p in ps[5:] for r in prep(p)]
    by=defaultdict(list)
    for r in tr: by[r['action']].append(r)
    models={act:r257.learn(rows,MAX_AREA,MIN_FRAC,MIN_SUPPORT) for act,rows in by.items()}
    exact=r251.fit_exact(tr)
    out_by=defaultdict(lambda:{'screen':Counter(),'dest_offset':Counter(),'source_offset':Counter(),'class_dest_offset':Counter(),'frames':0,'mismatch':0,'assigned':0})
    for row in va:
        if row['exact_key'] in exact: continue
        model=models.get(row['action'])
        if not model or not model[0] or not model[1]: continue
        vector,movable=model; pred=r257.render(row['before'],vector,movable,MAX_AREA)
        if pred is None: continue
        dr,dc=vector
        comps=[c for c in r254.components(row['before']) if c['area']<=MAX_AREA and r257.cls(c) in movable]
        if not comps: continue
        x=out_by[row['action']]; x['frames']+=1
        for rr in range(len(pred)):
            for cc in range(len(pred[0])):
                if int(pred[rr][cc])==int(row['after'][rr][cc]): continue
                x['mismatch']+=1; x['screen'][(rr,cc)]+=1
                # nearest predicted destination bbox center
                ranked=[]
                for c in comps:
                    d_r0=c['r0']+dr; d_c0=c['c0']+dc
                    cr=(d_r0+c['r1']+dr)/2; ccol=(d_c0+c['c1']+dc)/2
                    dist=abs(rr-cr)+abs(cc-ccol)
                    ranked.append((dist,c,d_r0,d_c0))
                ranked.sort(key=lambda z:z[0])
                _,c,d_r0,d_c0=ranked[0]
                do=(rr-d_r0,cc-d_c0); so=(rr-c['r0'],cc-c['c0']); cls=(int(c['color']),int(c['area']),r246.stable(c['shape']))
                x['dest_offset'][do]+=1; x['source_offset'][so]+=1; x['class_dest_offset'][(cls[0],cls[1],cls[2],do[0],do[1])]+=1; x['assigned']+=1
    result={}
    for act,x in sorted(out_by.items()):
        result[act]={'frames':x['frames'],'mismatch_cells':x['mismatch'],'assigned':x['assigned'],
                     'screen_concentration':conc(x['screen']),'dest_offset_concentration':conc(x['dest_offset']),
                     'source_offset_concentration':conc(x['source_offset']),'class_dest_offset_concentration':conc(x['class_dest_offset'])}
    out={'schema':'deus/arc3-r264-object-relative-residual-diagnostic/1','rung':264,
         'lineage':{'r263':'run35800062104/artifact10724964094','question':'are dispersed residuals object-relative rather than screen-fixed'},
         'protocol':{'fit':'p0-p4','diagnostic_eval':'p5-p9','transport_variant':'a13_f80_s3','p10_p19_read':False,'promotion':False},
         'actions':result,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({a:{'screen10':x['screen_concentration']['top10'],'dest10':x['dest_offset_concentration']['top10'],'class_dest10':x['class_dest_offset_concentration']['top10']} for a,x in result.items()},sort_keys=True))
if __name__=='__main__': main()
