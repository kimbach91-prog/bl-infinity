#!/usr/bin/env python3
"""R203: ft09 p0-p9 outcome-assisted effect taxonomy for mechanism selection.

This is deliberately NOT a heldout evaluator. It inspects only public p0-p9
outcomes to characterize the remaining non-identity mechanism after R202.
No p10-p19 file is accepted. The result is source-assisted research and cannot
be promoted as independent generalization or Kaggle evidence.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191

RUNG=203;GAME='ft09-0d8bbf25'

def pnum(p:Path):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def bbox(cells):
 if not cells:return None
 rs=[r for r,c in cells];cs=[c for r,c in cells]
 return [min(rs),min(cs),max(rs),max(cs)]

def click_dist_stats(changed,click):
 if click is None or not changed:return None
 r0,c0=click;ds=[max(abs(r-r0),abs(c-c0)) for r,c in changed]
 return {'max_cheb':max(ds),'within1':sum(d<=1 for d in ds),'within2':sum(d<=2 for d in ds),'within4':sum(d<=4 for d in ds)}

def effect_class(before,after,action):
 h,w=len(before),len(before[0]);changed=[];pairs=Counter()
 for r in range(h):
  for c in range(w):
   if before[r][c]!=after[r][c]:
    changed.append((r,c));pairs[(before[r][c],after[r][c])]+=1
 if not changed:return 'identity',changed,pairs,None
 click=c191.parse_mouse(action)
 if click is not None:
  cr,cc=click;ds=[max(abs(r-cr),abs(c-cc)) for r,c in changed]
  if max(ds)<=1:return 'click_local_r1',changed,pairs,click
  if max(ds)<=2:return 'click_local_r2',changed,pairs,click
  if max(ds)<=4:return 'click_local_r4',changed,pairs,click
 border=sum(r<2 or c<2 or r>=h-2 or c>=w-2 for r,c in changed)
 if border==len(changed):return 'border_only',changed,pairs,click
 density=len(changed)/(h*w)
 if density>=0.25:return 'global_dense',changed,pairs,click
 if len(changed)<=16:return 'sparse_nonlocal',changed,pairs,click
 return 'regional_or_medium',changed,pairs,click

def best_shift(before,after,limit=2):
 h,w=len(before),len(before[0]);best=None
 for dr in range(-limit,limit+1):
  for dc in range(-limit,limit+1):
   mism=0;n=0
   for r in range(h):
    rr=r+dr
    if not 0<=rr<h:continue
    for c in range(w):
     cc=c+dc
     if not 0<=cc<w:continue
     n+=1;mism+=before[r][c]!=after[rr][cc]
   key=(mism/max(1,n),mism,-n,dr,dc)
   if best is None or key<best[0]:best=(key,{'dr':dr,'dc':dc,'mismatch_rate':round(mism/max(1,n),6),'mismatches':mism,'compared':n})
 return best[1]

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(10)):raise ValueError('R203 accepts exact p0..p9 only')
 classes=Counter();by_action=defaultdict(Counter);changed_hist=Counter();pair_counts=Counter();click_max=Counter();shift_counts=Counter();examples=[]
 total=0;changed_total=0
 for p in ps:
  ev=base.load_events(p);pre=ev[0]
  for e in ev[1:]:
   if e.get('type')!='action':pre=e;continue
   before=base.as_grid(pre['board']);after=base.as_grid(e['board']);a=base.action_name(e);pre=e
   if not base.same_shape(before,after):continue
   total+=1;cl,chg,pairs,click=effect_class(before,after,a);classes[cl]+=1;by_action[c191.action_class(a)][cl]+=1
   if chg:
    changed_total+=1;changed_hist[min(len(chg),256)]+=1;pair_counts.update(pairs)
    cds=click_dist_stats(chg,click)
    if cds:click_max[min(cds['max_cheb'],32)]+=1
    if cl in ('global_dense','regional_or_medium','border_only'):
     s=best_shift(before,after);shift_counts[(s['dr'],s['dc'],round(s['mismatch_rate'],2))]+=1
    if len(examples)<25:examples.append({'trace':p.name,'action_class':c191.action_class(a),'class':cl,'changed':len(chg),'bbox':bbox(chg),'click':list(click) if click else None})
 return {
  'schema':'deus/arc3-ft09-effect-taxonomy/1','rung':RUNG,'game':GAME,
  'scope':'p0-p9_outcome_assisted_mechanism_research_only',
  'totals':{'transitions':total,'nonidentity':changed_total,'identity':classes['identity']},
  'classes':dict(classes),'by_action':{k:dict(v) for k,v in sorted(by_action.items())},
  'changed_count_hist_top':changed_hist.most_common(20),
  'top_value_transforms':[[list(k),v] for k,v in pair_counts.most_common(20)],
  'click_max_distance_hist':click_max.most_common(20),
  'best_shift_signature_top':[[list(k),v] for k,v in shift_counts.most_common(20)],
  'examples':examples,
  'truth':{'uses_only_p0_p9':True,'p10_p19_read':False,'outcome_assisted':True,'diagnostic_only':True,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'classes':d['classes'],'by_action':d['by_action'],'totals':d['totals']},sort_keys=True))
if __name__=='__main__':main()
