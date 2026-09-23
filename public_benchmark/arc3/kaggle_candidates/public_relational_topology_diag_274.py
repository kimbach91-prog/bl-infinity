#!/usr/bin/env python3
"""R274 translation-invariant relational-topology diagnostic for the 11 R268 non-signal games.

Falsifier-driven change from R273: R273 encoded absolute component bounding boxes and produced
NO_SIGNAL. R274 removes absolute screen position and represents component shape/type plus pairwise
relative topology. Protocol is p0-p4 fit -> p5-p9 diagnostic only; p10-p19 are not staged/read.
This is PUBLIC_OFFLINE research only and cannot imply Kaggle/hidden performance.
"""
from __future__ import annotations
import argparse, hashlib, json, math
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

def sgn(v:float)->int: return (v>0)-(v<0)
def dbin(v:float, span:int)->int:
    q=abs(v)/max(1,span)
    return 0 if q<0.08 else 1 if q<0.20 else 2 if q<0.40 else 3

def extract(board:list[list[int]], drop_edgebars:bool):
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
        hh=y1-y0+1; ww=x1-x0+1; n=len(cells)
        edge=(y0==0 or x0==0 or y1==h-1 or x1==w-1)
        longbar=(hh==1 and ww>=0.6*w) or (ww==1 and hh>=0.6*h)
        if drop_edgebars and edge and (longbar or n>=max(h,w)): continue
        local=sorted((yy-y0,xx-x0) for yy,xx in cells)
        exact=(int(c),n,hh,ww,dig(local)[:10])
        area_bucket=min(7,int(math.log2(max(1,n))))
        fill_bucket=min(4,int(round(4*n/max(1,hh*ww))))
        aspect=-1 if ww<hh else 1 if ww>hh else 0
        coarse=(int(c),area_bucket,aspect,fill_bucket)
        cy=sum(ys)/n; cx=sum(xs)/n
        out.append({'exact':exact,'coarse':coarse,'cy':cy,'cx':cx})
    return out,h,w

def desc(board,mode):
    drop=mode.endswith('_noedge')
    objs,h,w=extract(board,drop)
    coarse='coarse' in mode
    sig=lambda o:o['coarse'] if coarse else o['exact']
    nodes=sorted(sig(o) for o in objs)
    if mode.startswith('nodes_'): return ('nodes',tuple(nodes))
    edges=[]
    for i in range(len(objs)):
      for j in range(i+1,len(objs)):
        a,b=objs[i],objs[j]; sa,sb=sig(a),sig(b)
        dy=b['cy']-a['cy']; dx=b['cx']-a['cx']
        if sa<sb:
          rel=(sgn(dy),sgn(dx),dbin(dy,h),dbin(dx,w)); lo,hi=sa,sb
        elif sb<sa:
          rel=(-sgn(dy),-sgn(dx),dbin(dy,h),dbin(dx,w)); lo,hi=sb,sa
        else:
          rel=(abs(sgn(dy)),abs(sgn(dx)),dbin(dy,h),dbin(dx,w)); lo=hi=sa
        edges.append((lo,hi,rel))
    return ('graph',tuple(nodes),tuple(sorted(edges)))

def key(board,mode):
    if mode=='raw': return r268.state_key(board,'raw')
    return dig(desc(board,mode))

def fit(rows,mode):
    obs=defaultdict(Counter); counts=Counter()
    for r in rows:
      k=(key(r['before'],mode),r['action']); obs[k][key(r['after'],mode)]+=1; counts[k]+=1
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    return tab, {'keys':len(obs),'deterministic':len(tab),'ambiguous':sum(len(v)>1 for v in obs.values()),'repeat_keys':sum(n>=2 for n in counts.values()),'repeat_observations':sum(n for n in counts.values() if n>=2)}

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
    modes=('raw','nodes_coarse','graph_coarse','graph_coarse_noedge','graph_exact_noedge')
    games={}; signals=[]
    for g,ps in sorted(by.items()):
      ps=sorted(ps,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
      if nums!=list(range(10)): raise SystemExit(f'{g}: exact p0-p9 required, got {nums}')
      tr=r268.rows(ps[:5]); va=r268.rows(ps[5:]); mm={}
      for m in modes:
        tab,fs=fit(tr,m); mm[m]={'fit':fs,'validation':ev(va,tab,m)}
      raw=mm['raw']['validation']; candidates=[]
      for m in modes[1:]:
        v=mm[m]['validation']
        if int(v.get('wrong',0))==0 and int(v.get('correct',0))>int(raw.get('correct',0)): candidates.append(m)
      if candidates:
        best=max(candidates,key=lambda m:(int(mm[m]['validation'].get('correct',0)),int(mm[m]['fit'].get('repeat_keys',0))))
        signals.append({'game':g,'mode':best,'raw':raw,'candidate':mm[best]['validation'],'fit':mm[best]['fit']})
      games[g]={'modes':mm,'diagnostic_signal_modes':candidates}
    out={'schema':'deus/arc3-r274-relational-topology-diagnostic/1','rung':274,
         'representation_delta':'translation-invariant component type/shape multiset plus canonical pairwise relative topology; removes R273 absolute bbox dependence',
         'protocol':{'fit':'p0-p4','diagnostic':'p5-p9','p10_p19_staged_or_read':False,'promotion_in_r274':False},
         'unresolved_games':sorted(by),'signals':signals,'games':games,'verdict':'DIAGNOSTIC_SIGNAL' if signals else 'NO_SIGNAL',
         'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r274':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'signal_count':len(signals),'signals':signals,'verdict':out['verdict']},sort_keys=True))
if __name__=='__main__': main()
