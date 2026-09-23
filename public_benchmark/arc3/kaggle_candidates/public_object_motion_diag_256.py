#!/usr/bin/env python3
"""R256: source-free object-motion diagnostic for re86."""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_component_delta_operator_254 as r254
MAX_AREA=36
MAX_MATCH_DISTANCE=12
def center(c): return ((c['r0']+c['r1'])/2.0,(c['c0']+c['c1'])/2.0)
def shape_sig(c): return (int(c['color']), tuple(tuple(x) for x in c['shape']))
def match_components(before,after):
    bs=[c for c in r254.components(before) if c['area']<=MAX_AREA]; aa=[c for c in r254.components(after) if c['area']<=MAX_AREA]
    by_b=defaultdict(list); by_a=defaultdict(list)
    for i,c in enumerate(bs): by_b[shape_sig(c)].append((i,c))
    for j,c in enumerate(aa): by_a[shape_sig(c)].append((j,c))
    matches=[]; destroyed=[]; created=[]
    for sig in sorted(set(by_b)|set(by_a),key=str):
        left=by_b.get(sig,[]); right=by_a.get(sig,[]); pairs=[]
        for i,b in left:
            br,bc=center(b)
            for j,a in right:
                ar,ac=center(a); d=abs(ar-br)+abs(ac-bc)
                if d<=MAX_MATCH_DISTANCE: pairs.append((d,i,j,b,a))
        pairs.sort(key=lambda x:(x[0],x[1],x[2])); ui=set(); uj=set()
        for d,i,j,b,a in pairs:
            if i in ui or j in uj: continue
            ui.add(i); uj.add(j); matches.append((b,a))
        destroyed.extend(b for i,b in left if i not in ui); created.extend(a for j,a in right if j not in uj)
    return matches,destroyed,created
def load_rows(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        if r246.pnum(p)>=10: raise ValueError('R256 is p0-p9 only')
        ev=r246.load_events(p); pre=ev[0]
        for e in ev[1:]:
            if e.get('type')!='action': pre=e; continue
            b=[[int(v) for v in row] for row in pre['board']]; a=[[int(v) for v in row] for row in e['board']]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                matches,destroyed,created=match_components(b,a); moved=[]; stationary=0
                for x,y in matches:
                    dr=y['r0']-x['r0']; dc=y['c0']-x['c0']
                    if dr or dc: moved.append({'color':x['color'],'area':x['area'],'shape':r246.stable(x['shape']),'d':[dr,dc]})
                    else: stationary+=1
                out.append({'trace':p.name,'action':r246.action_name(e),'moved':moved,'stationary':stationary,'destroyed':len(destroyed),'created':len(created),'matched':len(matches)})
            pre=e
    return out
def summarize(rows):
    by=defaultdict(list)
    for r in rows: by[r['action']].append(r)
    out={}
    for act,rs in sorted(by.items()):
        move_class=Counter(); vector=Counter(); color_vec=Counter(); move_counts=[]
        for r in rs:
            move_counts.append(len(r['moved']))
            for m in r['moved']:
                key=(m['color'],m['area'],m['shape'],tuple(m['d'])); move_class[key]+=1; vector[tuple(m['d'])]+=1; color_vec[(m['color'],tuple(m['d']))]+=1
        total_moves=sum(move_counts); trans_with_move=sum(bool(r['moved']) for r in rs)
        out[act]={'transitions':len(rs),'transitions_with_small_object_motion':trans_with_move,'motion_transition_fraction':round(trans_with_move/len(rs),6) if rs else 0.0,'median_moved_components':statistics.median(move_counts) if move_counts else 0,'total_matched_small_components':sum(r['matched'] for r in rs),'total_created_small_components':sum(r['created'] for r in rs),'total_destroyed_small_components':sum(r['destroyed'] for r in rs),'top_motion_vectors':[[list(k),v] for k,v in vector.most_common(10)],'top_color_vectors':[[[k[0],list(k[1])],v] for k,v in color_vec.most_common(12)],'top_object_motion_classes':[[{'color':k[0],'area':k[1],'shape':k[2],'d':list(k[3])},v] for k,v in move_class.most_common(12)],'top_motion_class_share':round(move_class.most_common(1)[0][1]/total_moves,6) if total_moves else 0.0}
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    rows=load_rows(ps); summary=summarize(rows); out={'schema':'deus/arc3-r256-object-motion-diagnostic/1','rung':256,'protocol':{'scope':'p0-p9 only','max_area':MAX_AREA,'max_match_distance':MAX_MATCH_DISTANCE,'promotion':False},'summary':summary,'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps(summary,sort_keys=True))
if __name__=='__main__': main()
