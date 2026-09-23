#!/usr/bin/env python3
"""R263: source-free residual-coordinate concentration diagnostic for re86.

R260 established that selective object transport materially reduces movement
frame error but leaves sparse/non-sparse residuals. R261 falsified a simple
screen-coordinate underlay cache as the missing mechanism. R263 asks whether
the remaining predictive residuals concentrate at stable screen coordinates
(HUD/screen-fixed layer) or remain spatially dispersed (world/agent/state layer).

Diagnostic only. Models fit on p0-p4 and residuals measured on p5-p9. No
p10-p19, no game source, no hidden data, no Kaggle runtime/score, no promotion.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_selective_object_transport_257 as r257

VARIANTS=((13,.8,3),(13,1.0,3),(36,.9,5))

def prep(path):
    out=[]
    for step,row in enumerate(r251.prepare_rows([path])):
        x=dict(row); x['transition_id']=f'{path.name}#{step}'; out.append(x)
    return out

def concentration(c:Counter):
    total=sum(c.values())
    top=[n for _,n in c.most_common()]
    def share(k): return round(sum(top[:k])/total,6) if total else 0.0
    return {'total_mismatch_cells':total,'unique_coords':len(c),'top1_share':share(1),'top5_share':share(5),'top10_share':share(10),'top25_share':share(25),
            'top_coords':[[list(k),v] for k,v in c.most_common(20)]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    tr=[r for p in ps[:5] for r in prep(p)]; va=[r for p in ps[5:] for r in prep(p)]
    tr_by=defaultdict(list)
    for r in tr: tr_by[r['action']].append(r)
    exact=r251.fit_exact(tr)
    variants={}
    for max_area,min_frac,min_support in VARIANTS:
        models={a:r257.learn(rows,max_area,min_frac,min_support) for a,rows in tr_by.items()}
        coord=Counter(); edge=0; total=0; pairs=Counter(); frame_err=[]; by=defaultdict(lambda:{'coord':Counter(),'pairs':Counter(),'errs':[],'edge':0,'total':0})
        for row in va:
            if row['exact_key'] in exact: continue
            model=models.get(row['action'])
            if not model: continue
            pred=r257.render(row['before'],model[0],model[1],max_area)
            if pred is None: continue
            h=len(pred); w=len(pred[0]); e=0
            for rr in range(h):
                for cc in range(w):
                    if int(pred[rr][cc])!=int(row['after'][rr][cc]):
                        e+=1; coord[(rr,cc)]+=1; pairs[(int(pred[rr][cc]),int(row['after'][rr][cc]))]+=1; total+=1
                        by[row['action']]['coord'][(rr,cc)]+=1; by[row['action']]['pairs'][(int(pred[rr][cc]),int(row['after'][rr][cc]))]+=1; by[row['action']]['total']+=1
                        if rr in (0,h-1) or cc in (0,w-1): edge+=1; by[row['action']]['edge']+=1
            frame_err.append(e); by[row['action']]['errs'].append(e)
        key=f'a{max_area}_f{int(min_frac*100)}_s{min_support}'
        variants[key]={
          'frames':len(frame_err),'median_frame_error':statistics.median(frame_err) if frame_err else None,
          'mean_frame_error':round(sum(frame_err)/len(frame_err),6) if frame_err else None,
          'edge_residual_fraction':round(edge/total,6) if total else 0.0,
          'coord_concentration':concentration(coord),
          'top_residual_pairs':[[list(k),v] for k,v in pairs.most_common(15)],
          'by_action':{act:{'frames':len(x['errs']),'median_frame_error':statistics.median(x['errs']) if x['errs'] else None,
                            'edge_residual_fraction':round(x['edge']/x['total'],6) if x['total'] else 0.0,
                            'coord_concentration':concentration(x['coord']),
                            'top_residual_pairs':[[list(k),v] for k,v in x['pairs'].most_common(10)]}
                       for act,x in sorted(by.items())}
        }
    out={'schema':'deus/arc3-r263-residual-coordinate-diagnostic/1','rung':263,
         'lineage':{'r260':'run35799394728/artifact10725301644','r261':'run35799624454/artifact10725003555',
                    'question':'are post-transport residuals screen-coordinate concentrated or spatially dispersed'},
         'protocol':{'fit':'p0-p4','diagnostic_eval':'p5-p9','p10_p19_read':False,'promotion':False},
         'variants':variants,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:{'frames':v['frames'],'median':v['median_frame_error'],'edge':v['edge_residual_fraction'],'top10':v['coord_concentration']['top10_share'],'unique':v['coord_concentration']['unique_coords']} for k,v in variants.items()},sort_keys=True))
if __name__=='__main__':main()
