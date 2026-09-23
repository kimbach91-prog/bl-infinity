#!/usr/bin/env python3
"""R275 action-canonicalized topology diagnostic for the 11 unresolved public games.

R274 removed absolute position but fit each action label separately and found NO_SIGNAL.
R275 uses directional actions as spatial symmetry operators: transitions are rotated into
a common UP-oriented frame and pooled under MOVE. Protocol is p0-p4 fit -> p5-p9
only; p10-p19 are not staged/read. PUBLIC_OFFLINE only.
"""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274

SIGNAL14={'ar25-0c556536','ft09-0d8bbf25','ka59-38d34dbb','lf52-271a04aa','lp85-305b61c3','r11l-495a7899','re86-8af5384d','s5i5-18d95033','su15-1944f8ab','tn36-ef4dde99','tr87-cd924810','tu93-0768757b','vc33-5430563c','wa30-ee6fef47'}
DIRS={'UP','DOWN','LEFT','RIGHT'}
KEY_CACHE={}

def rot_cw(b): return [list(row) for row in zip(*b[::-1])]
def rot_ccw(b): return [list(row) for row in zip(*b)][::-1]
def rot_180(b): return [list(reversed(row)) for row in reversed(b)]

def canon_board(board, action, use_ui_mask=False):
    b=[list(map(int,row)) for row in board]
    if use_ui_mask: b=r268.masked(b)
    a=str(action).upper()
    if a=='UP': return b
    if a=='DOWN': return rot_180(b)
    if a=='LEFT': return rot_cw(b)
    if a=='RIGHT': return rot_ccw(b)
    return b

def action_class(action):
    a=str(action).upper(); return 'MOVE' if a in DIRS else a

def key(board, action, mode):
    frozen=tuple(tuple(map(int,row)) for row in board); a=str(action).upper(); ck=(frozen,a,mode)
    if ck in KEY_CACHE: return KEY_CACHE[ck]
    if mode=='raw': out=(r246.digest(board),a)
    else:
        use_ui=mode.endswith('_ui'); b=canon_board(board,a,use_ui); base=mode[:-3] if use_ui else mode
        if base=='canon_raw': d=r246.digest(b)
        elif base=='canon_nodes': d=r274.dig(r274.desc(b,'nodes_coarse'))
        elif base=='canon_graph': d=r274.dig(r274.desc(b,'graph_coarse_noedge'))
        else: raise KeyError(mode)
        out=(d,action_class(a))
    KEY_CACHE[ck]=out; return out

def fit(rows,mode):
    obs=defaultdict(Counter); counts=Counter()
    for r in rows:
        k=key(r['before'],r['action'],mode); n=key(r['after'],r['action'],mode)[0]
        obs[k][n]+=1; counts[k]+=1
    tab={k:next(iter(v)) for k,v in obs.items() if len(v)==1}
    return tab,{'keys':len(obs),'deterministic':len(tab),'ambiguous':sum(len(v)>1 for v in obs.values()),'repeat_keys':sum(n>=2 for n in counts.values()),'repeat_observations':sum(n for n in counts.values() if n>=2)}

def evaluate(rows,tab,mode):
    s=Counter()
    for r in rows:
        s['transitions']+=1; k=key(r['before'],r['action'],mode); pred=tab.get(k)
        if pred is None: s['abstain']+=1; continue
        s['predictions']+=1; actual=key(r['after'],r['action'],mode)[0]
        s['correct' if pred==actual else 'wrong']+=1
    p=s['predictions']; s['accuracy']=round(s['correct']/p,6) if p else None
    return dict(s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if len(by)!=11 or set(by)&SIGNAL14: raise SystemExit(f'exact unresolved11 required, got {sorted(by)}')
    modes=('raw','canon_raw','canon_raw_ui','canon_nodes','canon_nodes_ui','canon_graph','canon_graph_ui')
    games={}; signals=[]
    for g,ps in sorted(by.items()):
        ps=sorted(ps,key=r246.pnum); nums=[r246.pnum(p) for p in ps]
        if nums!=list(range(10)): raise SystemExit(f'{g}: exact p0-p9 required, got {nums}')
        tr=r268.rows(ps[:5]); va=r268.rows(ps[5:]); mm={}
        for m in modes:
            tab,fs=fit(tr,m); mm[m]={'fit':fs,'validation':evaluate(va,tab,m)}
        raw=mm['raw']['validation']; candidates=[]
        for m in modes[1:]:
            v=mm[m]['validation']
            if int(v.get('wrong',0))==0 and int(v.get('correct',0))>int(raw.get('correct',0)): candidates.append(m)
        if candidates:
            best=max(candidates,key=lambda m:(int(mm[m]['validation'].get('correct',0)),int(mm[m]['fit'].get('repeat_keys',0)),-int(mm[m]['fit'].get('ambiguous',0))))
            signals.append({'game':g,'mode':best,'raw':raw,'candidate':mm[best]['validation'],'fit':mm[best]['fit']})
        games[g]={'modes':mm,'diagnostic_signal_modes':candidates}
    out={'schema':'deus/arc3-r275-action-canonical-topology-diagnostic/1','rung':275,'representation_delta':'directional actions rotate to UP and pool as MOVE; optional static UI mask; topology evaluated in action-aligned frame','lineage':{'r273':'absolute object state NO_SIGNAL','r274':'translation-invariant topology NO_SIGNAL','repair':'action symmetry transform + directional pooling; no threshold retune'},'protocol':{'fit':'p0-p4','diagnostic':'p5-p9','p10_p19_staged_or_read':False,'promotion_in_r275':False},'unresolved_games':sorted(by),'signals':signals,'games':games,'verdict':'DIAGNOSTIC_SIGNAL' if signals else 'NO_SIGNAL','truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent_by_r275':False}}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'signal_count':len(signals),'signals':signals,'verdict':out['verdict']},sort_keys=True))
if __name__=='__main__': main()
