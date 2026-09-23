#!/usr/bin/env python3
"""R273 public object-state diagnostic on the 11 R268 UI-mask non-signal games.

Grounding idea: AnubhavBharadwaaj/arc-agi-3-release@0164696f30bae31d4bd755381eb1d5fd8db937e3
solvers/representation.py (MIT-0) argues for typed connected components before
reasoning. This is an independent minimal implementation for state-key fidelity.

Protocol: p0-p4 fit -> p5-p9 diagnostic only. p10-p19 are not staged/read.
No promotion occurs in R273; any signal must be frozen and separately tested.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268

SIGNAL14={
'ar25-0c556536','ft09-0d8bbf25','ka59-38d34dbb','lf52-271a04aa','lp85-305b61c3',
'r11l-495a7899','re86-8af5384d','s5i5-18d95033','su15-1944f8ab','tn36-ef4dde99',
'tr87-cd924810','tu93-0768757b','vc33-5430563c','wa30-ee6fef47'}

def dig(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def comps(board:list[list[int]], drop_edgebars:bool)->list[tuple]:
    h=len(board); w=len(board[0]); cnt=Counter(v for row in board for v in row); bg=cnt.most_common(1)[0][0]
    seen=set(); out=[]
    for y in range(h):
      for x in range(w):
        c=board[y][x]
        if c==bg or (y,x) in seen: continue
        q=deque([(y,x)]); seen.add((y,x)); cells=[]
        while q:
          a,b=q.popleft(); cells.append((a,b))
          for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=a+dy,b+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and board[ny][nx]==c:
              seen.add((ny,nx)); q.append((ny,nx))
        ys=[p[0] for p in cells]; xs=[p[1] for p in cells]; y0,x0,y1,x1=min(ys),min(xs),max(ys),max(xs)
        edge=(y0==0 or x0==0 or y1==h-1 or x1==w-1)
        longbar=((y1-y0)==0 and (x1-x0+1)>=0.6*w) or ((x1-x0)==0 and (y1-y0+1)>=0.6*h)
        if drop_edgebars and edge and (longbar or len(cells)>=max(h,w)): continue
        local=sorted((yy-y0,xx-x0) for yy,xx in cells)
        out.append((int(c),len(cells),(y0,x0,y1,x1),dig(local)[:12]))
    return sorted(out)

def key(board,mode):
    if mode=='raw': return r268.state_key(board,'raw')
    if mode=='obj_abs': return dig(comps(board,False))
    if mode=='obj_noedgebar': return dig(comps(board,True))
    raise KeyError(mode)

def fit(rows,mode):
    obs=defaultdict(Counter)
    for r in rows: obs[(key(r['before'],mode),r['action'])][key(r['after'],mode)]+=1
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    return tab, {'keys':len(obs),'deterministic':len(tab),'ambiguous':sum(len(v)>1 for v in obs.values())}

def ev(rows,tab,mode):
    s=Counter()
    for r in rows:
      s['transitions']+=1; p=tab.get((key(r['before'],mode),r['action']))
      if p is None: s['abstain']+=1; continue
      s['predictions']+=1
      if p==key(r['after'],mode): s['correct']+=1
      else: s['wrong']+=1
    s['accuracy']=round(s['correct']/s['predictions'],6) if s['predictions'] else None
    return dict(s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if len(by)!=11 or set(by)&SIGNAL14: raise SystemExit(f'exact unresolved11 required, got {sorted(by)}')
    games={}; signals=[]
    for g,ps in sorted(by.items()):
      ps=sorted(ps,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
      if nums!=list(range(10)): raise SystemExit(f'{g}: exact p0-p9 required, got {nums}')
      tr=r268.rows(ps[:5]); va=r268.rows(ps[5:]); modes={}
      for m in ('raw','obj_abs','obj_noedgebar'):
        tab,fs=fit(tr,m); modes[m]={'fit':fs,'validation':ev(va,tab,m)}
      raw=modes['raw']['validation']; candidates=[]
      for m in ('obj_abs','obj_noedgebar'):
        v=modes[m]['validation']
        if int(v.get('wrong',0))==0 and int(v.get('correct',0))>int(raw.get('correct',0)): candidates.append(m)
      if candidates:
        best=max(candidates,key=lambda m:int(modes[m]['validation'].get('correct',0))); signals.append({'game':g,'mode':best,'raw':raw,'candidate':modes[best]['validation']})
      games[g]={'modes':modes,'diagnostic_signal_modes':candidates}
    out={'schema':'deus/arc3-r273-object-state-diagnostic/1','rung':273,'source_grounding':{'repo':'AnubhavBharadwaaj/arc-agi-3-release','commit':'0164696f30bae31d4bd755381eb1d5fd8db937e3','file':'solvers/representation.py','license':'MIT-0','use':'conceptual grounding; independent implementation'},'protocol':{'fit':'p0-p4','diagnostic':'p5-p9','p10_p19_staged_or_read':False,'promotion_in_r273':False},'unresolved_games':sorted(by),'signals':signals,'games':games,'verdict':'DIAGNOSTIC_SIGNAL' if signals else 'NO_SIGNAL','truth':{'public_trace_only':True,'source_assisted_representation_idea':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r273':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'signal_count':len(signals),'signals':signals,'verdict':out['verdict']},sort_keys=True))
if __name__=='__main__': main()
