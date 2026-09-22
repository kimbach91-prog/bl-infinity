#!/usr/bin/env python3
"""R211: ft09 ring-2 relational selector, derived from R210 structural falsifier.

R210 showed the sole R209/eight-neighbor error (p13 step79) differs from its
training reference by two 6x6 macro tiles at relative offsets N2 and NE2 while
the clicked tile and ring-1 context are unchanged. R211 therefore adds exactly
the radius-2 macro ring to the frozen pre-action key; no broader feature sweep.
p0-p9 fit only, p10-p19 frozen evaluation only.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
import public_ft09_macro_neighbor_rule_207 as r207
RUNG=211; GAME='ft09-0d8bbf25'

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name); return int(m.group(1)) if m else -1

def sample(board,r,c):
 return board[r][c] if 0<=r<len(board) and 0<=c<len(board[0]) else -1

def ring2(board,bb):
 r0,c0,r1,c1,_=bb; cr=(r0+r1)//2; cc=(c0+c1)//2
 out=[]
 for dr in (-16,-8,0,8,16):
  for dc in (-16,-8,0,8,16):
   if max(abs(dr),abs(dc))!=16: continue
   out.append(sample(board,cr+dr,cc+dc))
 return tuple(out)

def rows(path):
 ev=base.load_events(path); pre=ev[0]; step=0
 for e in ev[1:]:
  if e.get('type')!='action': pre=e; continue
  before=base.as_grid(pre['board']); after=base.as_grid(e['board']); a=base.action_name(e); pre=e; step+=1
  if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE': continue
  click=c191.parse_mouse(a)
  if click is None: continue
  rr,cc=click; h,w=len(before),len(before[0]); rr=max(0,min(h-1,rr)); cc=max(0,min(w-1,cc)); bb=r207.comp_bbox(before,rr,cc)
  if bb[4]!=36 or (bb[2]-bb[0]+1,bb[3]-bb[1]+1)!=(6,6): continue
  ctx=r207.macro_context(before,bb); cur=ctx['current']; target=r207.dominant_target(before,after,bb)
  yield {'trace':path.name,'p':pnum(path),'step':step,'current':cur,'target':target,'changed':target!=cur,
         'base':(cur,ctx['four'],ctx['global_core_counts_bucket']),'ring2':ring2(before,bb)}

def fit(rs,keyfn):
 obs=defaultdict(Counter)
 for r in rs:
  if r['changed']: obs[repr(keyfn(r))][r['target']]+=1
 return {k:next(iter(c)) for k,c in obs.items() if len(c)==1},obs

def eval_(rs,tab,keyfn):
 s=Counter(); mistakes=[]
 for r in rs:
  s['eligible']+=1; pred=tab.get(repr(keyfn(r)))
  if pred is None: s['abstain']+=1; continue
  s['predictions']+=1
  if pred==r['target']: s['correct']+=1
  else:
   s['wrong']+=1
   if len(mistakes)<20: mistakes.append({**r,'pred':pred})
 p=s['predictions']; return {**dict(s),'accuracy':round(s['correct']/p,6) if p else None,'coverage':round(p/s['eligible'],6) if s['eligible'] else 0.0},mistakes

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(20)): raise ValueError('exact p0..p19 required')
 tr=[r for p in ps[:10] for r in rows(p)]; he=[r for p in ps[10:] for r in rows(p)]
 basefn=lambda r:r['base']; ringfn=lambda r:(r['base'],r['ring2'])
 bt,bobs=fit(tr,basefn); rt,robs=fit(tr,ringfn)
 bm,bmist=eval_(he,bt,basefn); rm,rmist=eval_(he,rt,ringfn)
 gate=bool(rm.get('predictions',0)>=100 and rm.get('wrong',0)==0 and (rm.get('accuracy') or 0)>=0.99)
 return {'schema':'deus/arc3-ft09-ring2-relational-gate/1','rung':RUNG,'game':GAME,
   'derivation':'R210 p13s79 structural residual at N2 and NE2; add exactly radius-2 macro ring',
   'train':{'base_values':len(bobs),'ring2_values':len(robs),'ring2_deterministic_values':len(rt)},
   'heldout':{'base':bm,'ring2':rm,'base_mistakes':bmist,'ring2_mistakes':rmist},
   'mechanism_gate_pass':gate,
   'promotion':{'mechanism_gate':gate,'solver_promotion':False,'kaggle_packaging':False,'reason':'target-color mechanism only; full-frame renderer and policy remain unresolved'},
   'truth':{'public_trace_only':True,'iterative_public_heldout_research':True,'heldout_never_updates_model':True,'independent_generalization_claim':False,'pre_action_selector_only':True,'full_frame_solver_claim':False,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); d=run(a.input); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n'); print(json.dumps({'heldout':d['heldout'],'gate':d['mechanism_gate_pass'],'promotion':d['promotion']},sort_keys=True))
if __name__=='__main__': main()
