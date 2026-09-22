#!/usr/bin/env python3
"""R204: ft09 p0-p9 click-local + bottom-HUD decomposition diagnostic.

Follows R203, which found most non-identity MOUSE transitions change ~36-38
cells with no viewport shift. This diagnostic tests the discriminating
hypothesis that each transition decomposes into a clicked-tile/local effect plus
a bottom HUD/timer effect. p10-p19 are never read.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
RUNG=204;GAME='ft09-0d8bbf25'

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(10)):raise ValueError('exact p0..p9 only')
 total=Counter();decomp4=Counter();decomp8=Counter();rows=Counter();local_offsets=Counter();bottom_cols=Counter();pairs_local=Counter();pairs_bottom=Counter();pairs_other=Counter();examples=[]
 for path in ps:
  ev=base.load_events(path);pre=ev[0];step=0
  for e in ev[1:]:
   if e.get('type')!='action':pre=e;continue
   before=base.as_grid(pre['board']);after=base.as_grid(e['board']);a=base.action_name(e);pre=e;step+=1
   if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':continue
   h,w=len(before),len(before[0]);click=c191.parse_mouse(a)
   changed=[(r,c) for r in range(h) for c in range(w) if before[r][c]!=after[r][c]]
   total['mouse']+=1
   if not changed:total['identity']+=1;continue
   total['changed']+=1
   if click is None:total['no_click']+=1;continue
   cr,cc=click
   local={(r,c) for r,c in changed if max(abs(r-cr),abs(c-cc))<=4}
   b4={(r,c) for r,c in changed if r>=h-4}
   b8={(r,c) for r,c in changed if r>=h-8}
   other4=set(changed)-local-b4;other8=set(changed)-local-b8
   decomp4[(len(changed),len(local),len(b4),len(other4))]+=1
   decomp8[(len(changed),len(local),len(b8),len(other8))]+=1
   if not other4:total['explained_local_plus_bottom4']+=1
   if not other8:total['explained_local_plus_bottom8']+=1
   for r,c in changed:
    rows[r]+=1
    if (r,c) in local:
     local_offsets[(r-cr,c-cc)]+=1;pairs_local[(before[r][c],after[r][c])]+=1
    elif r>=h-8:
     bottom_cols[c]+=1;pairs_bottom[(before[r][c],after[r][c])]+=1
    else:pairs_other[(before[r][c],after[r][c])]+=1
   if len(examples)<30:
    examples.append({'trace':path.name,'step':step,'click':[cr,cc],'changed':len(changed),'local_r4':len(local),'bottom4':len(b4),'bottom8':len(b8),'other4':len(other4),'other8':len(other8),'other8_cells':sorted([list(x) for x in other8])[:20]})
 def top(c,n=30):return [[list(k) if isinstance(k,tuple) else k,v] for k,v in c.most_common(n)]
 return {'schema':'deus/arc3-ft09-click-hud-decomposition/1','rung':RUNG,'game':GAME,'scope':'p0-p9_outcome_assisted_mechanism_research_only','totals':dict(total),'decomp_bottom4_top':top(decomp4),'decomp_bottom8_top':top(decomp8),'changed_rows_top':rows.most_common(30),'local_relative_offsets_top':top(local_offsets),'bottom_columns_top':bottom_cols.most_common(30),'local_value_transforms_top':top(pairs_local),'bottom_value_transforms_top':top(pairs_bottom),'other_value_transforms_top':top(pairs_other),'examples':examples,'truth':{'uses_only_p0_p9':True,'p10_p19_read':False,'outcome_assisted':True,'diagnostic_only':True,'kaggle_execution':False,'submission_quota_spent':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'totals':d['totals'],'decomp8':d['decomp_bottom8_top'][:8]},sort_keys=True))
if __name__=='__main__':main()
