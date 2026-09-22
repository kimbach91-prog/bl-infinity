#!/usr/bin/env python3
"""R262: source-free visible-state phase diagnostic for g50t.

R258 falsified short action-history as a useful conditioner for g50t delta
classes. R254 falsified static action+single-component anchoring. R262 therefore
tests whether coarse *current visible-state* descriptors separate latent phases.
It predicts only normalized transition-delta signatures, not full frames.

p0-p4 fit, p5-p9 validation. Diagnostic only; no p10-p19, game source, Kaggle
runtime/score, hidden outcome, or promotion.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict, deque
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246

MODES=("action","hist4","components","border","quadrants","hist4_components")

def stable(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]

def delta_sig(before,after):
    ch=[]
    for r in range(len(before)):
        for c in range(len(before[0])):
            b=int(before[r][c]); a=int(after[r][c])
            if b!=a: ch.append((r,c,b,a))
    if not ch:return "IDENTITY",0
    r0=min(x[0] for x in ch); c0=min(x[1] for x in ch); r1=max(x[0] for x in ch); c1=max(x[1] for x in ch)
    norm=tuple(sorted((r-r0,c-c0,b,a) for r,c,b,a in ch))
    return stable(((r1-r0+1,c1-c0+1),norm)),len(ch)

def hist(board,bucket=4):
    c=Counter(int(v) for row in board for v in row)
    return tuple(sorted((k,n//bucket) for k,n in c.items()))

def comps(board):
    h=len(board); w=len(board[0]); seen=set(); out=Counter()
    for r in range(h):
        for c in range(w):
            if (r,c) in seen: continue
            col=int(board[r][c]); q=deque([(r,c)]); seen.add((r,c)); n=0
            while q:
                rr,cc=q.popleft(); n+=1
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and int(board[nr][nc])==col:
                        seen.add((nr,nc)); q.append((nr,nc))
            ab="1" if n==1 else "2-4" if n<=4 else "5-16" if n<=16 else "17+"
            out[(col,ab)]+=1
    return tuple(sorted(((k[0],k[1],v) for k,v in out.items())))

def border(board):
    h=len(board); w=len(board[0]); c=Counter()
    for col in range(w): c[int(board[0][col])]+=1; c[int(board[h-1][col])]+=1
    for r in range(1,h-1): c[int(board[r][0])]+=1; c[int(board[r][w-1])]+=1
    return tuple(sorted((k,n//2) for k,n in c.items()))

def quadrants(board):
    h=len(board); w=len(board[0]); out=[]
    cuts=[(0,h//2,0,w//2),(0,h//2,w//2,w),(h//2,h,0,w//2),(h//2,h,w//2,w)]
    for r0,r1,c0,c1 in cuts:
        c=Counter(int(board[r][cc]) for r in range(r0,r1) for cc in range(c0,c1))
        out.append(tuple(sorted((k,n//4) for k,n in c.items())))
    return tuple(out)

def descriptor(board,mode):
    if mode=='action': return None
    if mode=='hist4': return hist(board,4)
    if mode=='components': return comps(board)
    if mode=='border': return border(board)
    if mode=='quadrants': return quadrants(board)
    if mode=='hist4_components': return (hist(board,4),comps(board))
    raise KeyError(mode)

def extract(paths):
    out=[]
    for p in sorted(paths,key=r246.pnum):
        ev=r246.load_events(p); pre=ev[0]
        for e in ev[1:]:
            if e.get('type')!='action': pre=e; continue
            b=[[int(v) for v in row] for row in pre['board']]; a=[[int(v) for v in row] for row in e['board']]
            if len(b)==len(a) and len(b[0])==len(a[0]):
                ds,n=delta_sig(b,a); out.append({'trace':p.name,'action':r246.action_name(e),'board':b,'delta_sig':ds,'changed':n})
            pre=e
    return out

def key(r,mode):
    d=descriptor(r['board'],mode)
    return (r['action'],) if d is None else (r['action'],stable(d))

def fit(rows,mode):
    obs=defaultdict(Counter); traces=defaultdict(lambda:defaultdict(set))
    for r in rows:
        if r['changed']==0: continue
        k=key(r,mode); s=r['delta_sig']; obs[k][s]+=1; traces[k][s].add(r['trace'])
    model={}
    for k,c in obs.items():
        s,_=sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))[0]
        if len(traces[k][s])>=2:model[k]=s
    return model

def evaluate(rows,model,mode):
    s=Counter(); by=defaultdict(Counter)
    for r in rows:
        if r['changed']==0: s['identity_skipped']+=1; continue
        s['nonidentity']+=1; by[r['action']]['nonidentity']+=1; k=key(r,mode)
        if k not in model: s['abstain']+=1; by[r['action']]['abstain']+=1; continue
        s['predictions']+=1; by[r['action']]['predictions']+=1; ok=(model[k]==r['delta_sig'])
        s['correct' if ok else 'wrong']+=1; by[r['action']]['correct' if ok else 'wrong']+=1
    n=s['predictions']; opp=s['nonidentity']
    return {**dict(s),'accuracy':round(s['correct']/n,6) if n else None,'coverage':round(n/opp,6) if opp else 0.0,
            'correct_coverage':round(s['correct']/opp,6) if opp else 0.0,'by_action':{a:dict(v) for a,v in sorted(by.items())}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise ValueError(f'exact p0..p9 required, got {nums}')
    tr=extract(ps[:5]); va=extract(ps[5:]); modes={}
    for mode in MODES:
        m=fit(tr,mode); modes[mode]={'model_size':len(m),'validation':evaluate(va,m,mode)}
    base=modes['action']['validation']['correct_coverage']
    for mode in MODES:modes[mode]['correct_coverage_delta_vs_action']=round(modes[mode]['validation']['correct_coverage']-base,6)
    best=max(MODES,key=lambda m:(modes[m]['validation']['correct_coverage'],modes[m]['validation']['accuracy'] or 0,m))
    out={'schema':'deus/arc3-r262-visible-state-phase-diagnostic/1','rung':262,
         'protocol':{'fit':'p0-p4','validation':'p5-p9','min_modal_trace_support':2,'promotion':False},
         'modes':modes,'best_mode':best,
         'truth':{'public_trace_only':True,'game_source_read':False,'p10_p19_read':False,'independent_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'best_mode':best,'modes':{m:modes[m]['validation'] for m in MODES}},sort_keys=True))
if __name__=='__main__':main()
