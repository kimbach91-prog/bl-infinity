#!/usr/bin/env python3
"""R207: ft09 macro-tile relational target-color diagnostic, p0-p9 only.

R206 established that 674 dominant click effects are exact 6x6 solid-color tile
changes. This diagnostic tests whether the next tile color is selected by a
pre-action macro-grid relation (neighbors/global tile-color state/position),
rather than memorizing raw pixels. No p10-p19 outcomes are read.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
RUNG=207;GAME='ft09-0d8bbf25';CORE=(8,9,12)

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def comp_bbox(board,r,c):
 h,w=len(board),len(board[0]);v=board[r][c];q=[(r,c)];seen={(r,c)}
 for rr,cc in q:
  for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
   nr,nc=rr+dr,cc+dc
   if 0<=nr<h and 0<=nc<w and (nr,nc) not in seen and board[nr][nc]==v:
    seen.add((nr,nc));q.append((nr,nc))
 rs=[x for x,y in seen];cs=[y for x,y in seen]
 return min(rs),min(cs),max(rs),max(cs),len(seen)

def dominant_target(before,after,bb):
 r0,c0,r1,c1,_=bb;vals=Counter(after[r][c] for r in range(r0,r1+1) for c in range(c0,c1+1));return vals.most_common(1)[0][0]

def sample(board,r,c):
 h,w=len(board),len(board[0]);return board[r][c] if 0<=r<h and 0<=c<w else -1

def macro_context(board,bb):
 r0,c0,r1,c1,_=bb;cr=(r0+r1)//2;cc=(c0+c1)//2;cur=board[cr][cc]
 # 8-pixel pitch inferred from 6x6 components separated by 2 cells.
 neigh={name:sample(board,cr+dr,cc+dc) for name,(dr,dc) in {
  'N':(-8,0),'S':(8,0),'W':(0,-8),'E':(0,8),
  'NW':(-8,-8),'NE':(-8,8),'SW':(8,-8),'SE':(8,8)}.items()}
 four=(neigh['N'],neigh['E'],neigh['S'],neigh['W']);eight=tuple(neigh[x] for x in ('N','NE','E','SE','S','SW','W','NW'))
 core_counts=Counter(v for v in four if v in CORE);board_counts=Counter(v for row in board for v in row if v in CORE)
 return {
  'current':cur,'four':four,'eight':eight,
  'four_multiset':tuple(sorted(four)),
  'core_neighbor_counts':tuple(core_counts[k] for k in CORE),
  'global_core_counts_bucket':tuple(board_counts[k]//36 for k in CORE),
  'macro_pos':(r0//8,c0//8),'macro_parity':((r0//8)%2,(c0//8)%2),
 }

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(10)):raise ValueError('exact p0..p9 only')
 obs=defaultdict(lambda:defaultdict(Counter));stats=Counter();hyp=Counter();examples=[]
 prev_target=None
 for path in ps:
  ev=base.load_events(path);pre=ev[0];prev_target=None;step=0
  for e in ev[1:]:
   if e.get('type')!='action':pre=e;continue
   before=base.as_grid(pre['board']);after=base.as_grid(e['board']);a=base.action_name(e);pre=e;step+=1
   if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':continue
   click=c191.parse_mouse(a)
   if click is None:continue
   r,c=click;h,w=len(before),len(before[0]);r=max(0,min(h-1,r));c=max(0,min(w-1,c))
   bb=comp_bbox(before,r,c)
   if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6):continue
   target=dominant_target(before,after,bb);ctx=macro_context(before,bb);cur=ctx['current']
   if target==cur:continue
   stats['examples']+=1
   keys={
    'current':(cur,),
    'current_pos':(cur,ctx['macro_pos']),
    'current_parity':(cur,ctx['macro_parity']),
    'current_four':(cur,ctx['four']),
    'current_four_multiset':(cur,ctx['four_multiset']),
    'current_neighbor_counts':(cur,ctx['core_neighbor_counts']),
    'current_eight':(cur,ctx['eight']),
    'current_global_counts':(cur,ctx['global_core_counts_bucket']),
    'current_four_global':(cur,ctx['four'],ctx['global_core_counts_bucket']),
    'current_prev_target':(cur,prev_target),
   }
   for fam,k in keys.items():obs[fam][repr(k)][target]+=1
   # Simple causal candidates.
   core4=[v for v in ctx['four'] if v in CORE]
   if core4:
    mc=Counter(core4).most_common()
    if target==mc[0][0]:hyp['target_is_neighbor_mode']+=1
    if target in core4:hyp['target_in_four_neighbors']+=1
   others=[x for x in CORE if x!=cur]
   if len(others)==2:
    if target==others[0]:hyp['target_is_first_other']+=1
    if target==others[1]:hyp['target_is_second_other']+=1
   if prev_target is not None and target==prev_target:hyp['target_equals_prev_target']+=1
   if len(examples)<60:examples.append({'trace':path.name,'step':step,'current':cur,'target':target,'macro_pos':list(ctx['macro_pos']),'four':list(ctx['four']),'eight':list(ctx['eight']),'global_core_tiles':list(ctx['global_core_counts_bucket']),'prev_target':prev_target})
   prev_target=target
 summary={}
 for fam,vals in obs.items():
  total=sum(sum(c.values()) for c in vals.values());det=sum(sum(c.values()) for c in vals.values() if len(c)==1);conf=sum(1 for c in vals.values() if len(c)>1)
  summary[fam]={'examples':total,'deterministic_examples':det,'deterministic_fraction':round(det/total,6) if total else 0,'values':len(vals),'conflicted_values':conf,'top_values':[{'key':k,'targets':dict(c)} for k,c in sorted(vals.items(),key=lambda kv:-sum(kv[1].values()))[:15]]}
 return {'schema':'deus/arc3-ft09-macro-neighbor-rule/1','rung':RUNG,'game':GAME,'scope':'p0-p9_outcome_assisted_relational_diagnostic_only','stats':dict(stats),'selector_summary':summary,'hypothesis_hits':dict(hyp),'examples':examples,'truth':{'uses_only_p0_p9':True,'p10_p19_read':False,'outcome_assisted':True,'diagnostic_only':True,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'stats':d['stats'],'selectors':{k:{x:v[x] for x in ('deterministic_fraction','deterministic_examples','examples','values','conflicted_values')} for k,v in d['selector_summary'].items()},'hypothesis_hits':d['hypothesis_hits']},sort_keys=True))
if __name__=='__main__':main()
