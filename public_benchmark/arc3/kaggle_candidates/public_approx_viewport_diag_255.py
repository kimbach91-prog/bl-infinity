#!/usr/bin/env python3
"""R255: source-free approximate viewport-shift diagnostic for re86.

R253 found no *exact* whole-frame shifts, but re86 movement transitions change
~58-61 cells with frequent edge contact and very low normalized delta reuse.
That pattern can still arise from a stable viewport translation plus sparse HUD,
agent or boundary residuals. R255 tests that falsifier directly.

Only p0-p9 public-development transitions are read. This is diagnostic-only:
no p10-p19 access, no model promotion, no game source, no Kaggle/runtime score.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG=255
RADIUS=4

def shifted(board,dr,dc,bg):
    h=len(board); w=len(board[0]); out=[]
    for r in range(h):
        row=[]
        for c in range(w):
            sr=r-dr; sc=c-dc
            row.append(int(board[sr][sc]) if 0<=sr<h and 0<=sc<w else int(bg))
        out.append(row)
    return out

def mismatch(a,b):
    return sum(int(x)!=int(y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))

def residual_edge_fraction(pred,after):
    h=len(pred); w=len(pred[0]); pts=[]
    for r in range(h):
        for c in range(w):
            if int(pred[r][c])!=int(after[r][c]): pts.append((r,c))
    if not pts: return 0.0
    edge=sum(r in (0,h-1) or c in (0,w-1) for r,c in pts)
    return edge/len(pts)

def one(before,after):
    bg=r246.bg(before)
    ident=mismatch(before,after)
    cand=[]
    for dr in range(-RADIUS,RADIUS+1):
        for dc in range(-RADIUS,RADIUS+1):
            if dr==0 and dc==0: continue
            p=shifted(before,dr,dc,bg); m=mismatch(p,after)
            cand.append((m,abs(dr)+abs(dc),dr,dc,p))
    cand.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    m,_,dr,dc,p=cand[0]
    improve=(ident-m)/ident if ident else 0.0
    return {"identity_mismatch":ident,"best_shift":[dr,dc],"best_shift_mismatch":m,
            "improvement_fraction":improve,"residual_edge_fraction":residual_edge_fraction(p,after)}

def rows(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        if r246.pnum(p)>=10: raise ValueError("R255 is p0-p9 only")
        ev=r246.load_events(p); pre=ev[0]
        for e in ev[1:]:
            if e.get('type')!='action': pre=e; continue
            b=[[int(v) for v in row] for row in pre['board']]
            a=[[int(v) for v in row] for row in e['board']]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                out.append({"trace":p.name,"action":r246.action_name(e),"diag":one(b,a)})
            pre=e
    return out

def q(vals,p):
    if not vals:return 0.0
    s=sorted(vals); return s[min(len(s)-1,max(0,int(p*len(s))))]

def summarize(rs):
    by=defaultdict(list)
    for r in rs: by[r['action']].append(r['diag'])
    out={}
    for act,xs in sorted(by.items()):
        imp=[x['improvement_fraction'] for x in xs if x['identity_mismatch']>0]
        residual=[x['best_shift_mismatch'] for x in xs if x['identity_mismatch']>0]
        edge=[x['residual_edge_fraction'] for x in xs if x['identity_mismatch']>0]
        shifts=Counter(tuple(x['best_shift']) for x in xs if x['identity_mismatch']>0)
        strong=sum(v>=0.5 for v in imp); very=sum(v>=0.8 for v in imp)
        out[act]={
            "transitions":len(xs),"nonidentity":len(imp),
            "median_improvement":round(statistics.median(imp),6) if imp else 0.0,
            "p25_improvement":round(q(imp,0.25),6) if imp else 0.0,
            "p75_improvement":round(q(imp,0.75),6) if imp else 0.0,
            "strong_ge_0p5_fraction":round(strong/len(imp),6) if imp else 0.0,
            "very_strong_ge_0p8_fraction":round(very/len(imp),6) if imp else 0.0,
            "median_residual_cells":statistics.median(residual) if residual else 0,
            "median_residual_edge_fraction":round(statistics.median(edge),6) if edge else 0.0,
            "modal_shifts":[[list(k),v] for k,v in shifts.most_common(8)]
        }
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    rs=rows(ps); s=summarize(rs)
    out={"schema":"deus/arc3-r255-approx-viewport-diagnostic/1","rung":RUNG,
         "protocol":{"scope":"p0-p9 only","shift_radius":RADIUS,"promotion":False},
         "summary":s,
         "truth":{"public_trace_only":True,"game_source_read":False,"p10_p19_read":False,
                  "independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,"owner_score_claim":False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(s,sort_keys=True))
if __name__=='__main__': main()
