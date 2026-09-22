#!/usr/bin/env python3
"""R210: structural board-diff diagnostic for the exact two R208/R209 mistakes.

The R209 feature family failed to eliminate both mistakes. This rung changes
representation to direct structural residuals: for each frozen heldout base-key
mistake, compare its pre-action board against the p0-p9 training reference
boards sharing the same frozen base key. No predictor is changed and p10-p19
never update any model.
"""
from __future__ import annotations
import argparse,json,re,hashlib
from collections import Counter,defaultdict,deque
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_macro_neighbor_rule_207 as r207

RUNG=210; GAME='ft09-0d8bbf25'
def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def bsig(b): return hashlib.sha256(json.dumps(b,separators=(',',':')).encode()).hexdigest()[:16]

def recs(path):
 ev=base.load_events(path); pre=ev[0]; step=0
 for e in ev[1:]:
  if e.get('type')!='action': pre=e; continue
  before=base.as_grid(pre['board']); after=base.as_grid(e['board']); a=base.action_name(e); pre=e; step+=1
  if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE': continue
  click=c191.parse_mouse(a)
  if click is None: continue
  rr,cc=click; h,w=len(before),len(before[0]); rr=max(0,min(h-1,rr)); cc=max(0,min(w-1,cc))
  bb=r207.comp_bbox(before,rr,cc)
  if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6): continue
  ctx=r207.macro_context(before,bb); cur=ctx['current']; target=r207.dominant_target(before,after,bb)
  key=(cur,ctx['four'],ctx['global_core_counts_bucket'])
  yield {'p':pnum(path),'trace':path.name,'step':step,'board':before,'board_sig':bsig(before),'target':target,'current':cur,'changed':target!=cur,'base':key,'click':(rr,cc),'click_bbox':bb}

def components(mask):
 pts=set(mask); out=[]
 while pts:
  start=next(iter(pts)); q=[start]; pts.remove(start); comp=[start]
  for r,c in q:
   for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
    z=(r+dr,c+dc)
    if z in pts: pts.remove(z); q.append(z); comp.append(z)
  out.append(comp)
 return sorted(out,key=len,reverse=True)

def diff(a,b,click_bbox):
 h,w=len(a),len(a[0]); cells=[]; pairs=Counter(); rows=Counter(); cols=Counter()
 for r in range(h):
  for c in range(w):
   if a[r][c]!=b[r][c]:
    cells.append((r,c)); pairs[(a[r][c],b[r][c])]+=1; rows[r]+=1; cols[c]+=1
 if cells:
  rs=[x for x,y in cells]; cs=[y for x,y in cells]; bbox=(min(rs),min(cs),max(rs),max(cs))
 else:bbox=None
 comps=components(cells)
 r0,c0,r1,c1,_=click_bbox
 inside=sum(r0<=r<=r1 and c0<=c<=c1 for r,c in cells)
 bottom4=sum(r>=h-4 for r,c in cells); bottom8=sum(r>=h-8 for r,c in cells)
 return {'count':len(cells),'bbox':bbox,'pair_counts':{f'{x}->{y}':n for (x,y),n in pairs.most_common()},
         'top_rows':rows.most_common(12),'top_cols':cols.most_common(12),
         'component_sizes':[len(x) for x in comps[:20]],'inside_clicked_bbox':inside,
         'outside_clicked_bbox':len(cells)-inside,'bottom4':bottom4,'bottom8':bottom8,
         'sample_cells':[{'r':r,'c':c,'train':a[r][c],'heldout':b[r][c]} for r,c in cells[:120]]}

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
 train=[r for p in ps[:10] for r in recs(p)]; held=[r for p in ps[10:] for r in recs(p)]
 obs=defaultdict(Counter)
 for r in train:
  if r['changed']: obs[repr(r['base'])][r['target']]+=1
 table={k:next(iter(c)) for k,c in obs.items() if len(c)==1}
 mistakes=[]
 for r in held:
  k=repr(r['base']); pred=table.get(k)
  if pred is not None and pred!=r['target']:
   refs=[x for x in train if repr(x['base'])==k]
   groups={}
   for x in refs: groups.setdefault(x['board_sig'],x)
   comparisons=[]
   for sig,x in groups.items():
    comparisons.append({'train_board_sig':sig,'train_occurrences':[(z['p'],z['step'],z['target']) for z in refs if z['board_sig']==sig],
                        'structural_diff':diff(x['board'],r['board'],r['click_bbox'])})
   mistakes.append({'heldout':{'p':r['p'],'step':r['step'],'trace':r['trace'],'board_sig':r['board_sig'],'pred':pred,'target':r['target'],'base_key':k,'click':r['click'],'click_bbox':r['click_bbox']},'comparisons':comparisons})
 return {'schema':'deus/arc3-ft09-mismatch-boarddiff/1','rung':RUNG,'game':GAME,'mistake_count':len(mistakes),'mistakes':mistakes,
         'verdict':{'base_mistakes_reproduced':len(mistakes)==2,'diagnostic_only':True,'solver_promotion':False,'kaggle_packaging':False},
         'truth':{'public_trace_only':True,'iterative_public_heldout_research':True,'heldout_never_updates_model':True,'independent_generalization_claim':False,'full_frame_solver_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n'); print(json.dumps({'mistake_count':d['mistake_count'],'summaries':[{'heldout':x['heldout'],'diffs':[c['structural_diff']['count'] for c in x['comparisons']]} for x in d['mistakes']]},sort_keys=True))
if __name__=='__main__': main()
