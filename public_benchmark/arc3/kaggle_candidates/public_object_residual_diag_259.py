#!/usr/bin/env python3
"""R259: source-free oracle-support diagnostic for re86 object transport residuals.

R256 established strong action-aligned small-object transport; R257 showed that
predictively moving those object classes alone does not reconstruct full next
frames. R259 uses the *observed* before/after pair only as a diagnostic to ask
how much of each transition's changed-cell support lies on matched moved-object
source/destination footprints, and what remains outside that support.

Only p0-p9 public-development traces are read. Diagnostic only: no prediction,
no p10-p19, no game source, no Kaggle execution or score, no promotion.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_motion_diag_256 as r256

MAX_AREA=36

def footprint(comp):
    return {(comp['r0']+dr,comp['c0']+dc) for dr,dc in comp['shape']}

def one(before,after):
    h=len(before); w=len(before[0])
    changed={(r,c) for r in range(h) for c in range(w) if int(before[r][c])!=int(after[r][c])}
    matches,destroyed,created=r256.match_components(before,after)
    support=set(); moved=[]
    for b,a in matches:
        if b['area']>MAX_AREA: continue
        dr=a['r0']-b['r0']; dc=a['c0']-b['c0']
        if dr==0 and dc==0: continue
        support |= footprint(b); support |= footprint(a)
        moved.append((b,a))
    explained=changed & support; residual=changed-support
    edge=sum(r in (0,h-1) or c in (0,w-1) for r,c in residual)
    pair=Counter((int(before[r][c]),int(after[r][c])) for r,c in residual)
    return {
      'changed':len(changed),'moved_matches':len(moved),'support_cells':len(support),
      'explained_changed':len(explained),'residual_changed':len(residual),
      'explained_fraction':(len(explained)/len(changed) if changed else 1.0),
      'residual_edge_fraction':(edge/len(residual) if residual else 0.0),
      'residual_pair_top':[[list(k),v] for k,v in pair.most_common(8)],
      'created_small':sum(c['area']<=MAX_AREA for c in created),
      'destroyed_small':sum(c['area']<=MAX_AREA for c in destroyed),
    }

def load(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        if r246.pnum(p)>=10: raise ValueError('R259 p0-p9 only')
        ev=r246.load_events(p); pre=ev[0]
        for e in ev[1:]:
            if e.get('type')!='action': pre=e; continue
            b=[[int(v) for v in row] for row in pre['board']]
            a=[[int(v) for v in row] for row in e['board']]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                out.append({'trace':p.name,'action':r246.action_name(e),'diag':one(b,a)})
            pre=e
    return out

def pct(vals,p):
    if not vals:return 0.0
    s=sorted(vals); return s[min(len(s)-1,max(0,int(p*len(s))))]

def summarize(rows):
    by=defaultdict(list)
    for x in rows: by[x['action']].append(x['diag'])
    out={}
    for act,xs in sorted(by.items()):
        non=[x for x in xs if x['changed']>0]
        ef=[x['explained_fraction'] for x in non]
        res=[x['residual_changed'] for x in non]
        moved=[x['moved_matches'] for x in non]
        pairs=Counter()
        for x in non:
            for pair,n in x['residual_pair_top']:
                pairs[tuple(pair)]+=n
        out[act]={
          'transitions':len(xs),'nonidentity':len(non),
          'median_explained_fraction':round(statistics.median(ef),6) if ef else 1.0,
          'p25_explained_fraction':round(pct(ef,.25),6) if ef else 1.0,
          'p75_explained_fraction':round(pct(ef,.75),6) if ef else 1.0,
          'ge_0p80_explained_fraction':round(sum(v>=.8 for v in ef)/len(ef),6) if ef else 1.0,
          'median_residual_changed':statistics.median(res) if res else 0,
          'median_moved_matches':statistics.median(moved) if moved else 0,
          'median_residual_edge_fraction':round(statistics.median([x['residual_edge_fraction'] for x in non]),6) if non else 0.0,
          'mean_created_small':round(sum(x['created_small'] for x in non)/len(non),6) if non else 0.0,
          'mean_destroyed_small':round(sum(x['destroyed_small'] for x in non)/len(non),6) if non else 0.0,
          'top_residual_pairs':[[list(k),v] for k,v in pairs.most_common(12)]
        }
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    summary=summarize(load(ps))
    out={'schema':'deus/arc3-r259-object-residual-diagnostic/1','rung':259,
         'protocol':{'scope':'p0-p9 only','max_area':MAX_AREA,'oracle_after_used_for_diagnostic_matching':True,'promotion':False},
         'summary':summary,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'source_assisted_replay':False,
                  'oracle_after_used_for_diagnostic_only':True,'independent_generalization_claim':False,
                  'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps(summary,sort_keys=True))
if __name__=='__main__': main()
