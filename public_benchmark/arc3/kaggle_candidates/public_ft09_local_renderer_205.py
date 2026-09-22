#!/usr/bin/env python3
"""R205: executable ft09 local-renderer candidate after R203/R204.

R204 showed a dominant local 6x6-ish click effect plus optional bottom HUD delta.
R205 isolates the local-only subset: learn deterministic pre-action local-patch ->
post-action local-patch programs only from contexts whose observed outcome has no
changes outside the local radius. p0-p4 fit, p5-p9 select, p0-p9 refit,
p10-p19 frozen public-heldout evaluation. Because earlier ft09 heldout aggregate
feedback exists, this is iterative public-heldout research, not independent
generalization and never a Kaggle score.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
RUNG=205;GAME='ft09-0d8bbf25'
RADII=(3,4);SUPPORTS=(1,2);FAMILIES=('local','local_pos','local_hud')

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def patch(board,r,c,rad):
 h,w=len(board),len(board[0]);out=[]
 for dr in range(-rad,rad+1):
  row=[]
  for dc in range(-rad,rad+1):
   rr,cc=r+dr,c+dc;row.append(board[rr][cc] if 0<=rr<h and 0<=cc<w else -1)
  out.append(tuple(row))
 return tuple(out)

def hud_sig(board):
 h,w=len(board),len(board[0]);rows=[]
 for r in range(max(0,h-4),h):
  cnt=Counter(board[r]);rows.append(tuple(sorted(cnt.items())))
 return tuple(rows)

def collect(paths):
 out=[]
 for path in sorted(paths,key=pnum):
  ev=base.load_events(path);pre=ev[0]
  for e in ev[1:]:
   if e.get('type')!='action':pre=e;continue
   before=base.as_grid(pre['board']);after=base.as_grid(e['board']);a=base.action_name(e);pre=e
   if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':continue
   click=c191.parse_mouse(a)
   if click is None:continue
   out.append({'trace':path.name,'before':before,'after':after,'click':tuple(click),'action':a})
 return out

def key(row,fam,rad):
 r,c=row['click'];k=(patch(row['before'],r,c,rad),)
 if fam=='local_pos':k+=(r//8,c//8)
 elif fam=='local_hud':k+=(hud_sig(row['before']),)
 return k

def fit(rows,fam,rad,support):
 obs=defaultdict(lambda:{'targets':set(),'outside':set(),'traces':set(),'states':set(),'before_patch':None})
 for row in rows:
  r,c=row['click'];bp=patch(row['before'],r,c,rad);ap=patch(row['after'],r,c,rad)
  changed=[(rr,cc) for rr in range(len(row['before'])) for cc in range(len(row['before'][0])) if row['before'][rr][cc]!=row['after'][rr][cc]]
  outside=any(max(abs(rr-r),abs(cc-c))>rad for rr,cc in changed)
  o=obs[key(row,fam,rad)];o['targets'].add(ap);o['outside'].add(outside);o['traces'].add(row['trace']);o['states'].add(base.digest(row['before']));o['before_patch']=bp
 model={}
 for k,o in obs.items():
  if len(o['targets'])!=1 or o['outside']!={False}:continue
  if len(o['traces'])<support or len(o['states'])<support:continue
  target=next(iter(o['targets']))
  if target==o['before_patch']:continue
  model[k]=target
 return model

def apply(before,click,rad,target):
 out=[row[:] for row in before];h,w=len(out),len(out[0]);r,c=click
 for i,dr in enumerate(range(-rad,rad+1)):
  for j,dc in enumerate(range(-rad,rad+1)):
   rr,cc=r+dr,c+dc
   if 0<=rr<h and 0<=cc<w and target[i][j]!=-1:out[rr][cc]=target[i][j]
 return out

def evaluate(model,rows,fam,rad):
 s=Counter();by_trace=defaultdict(Counter)
 for row in rows:
  s['transitions']+=1;bt=by_trace[row['trace']];bt['transitions']+=1
  k=key(row,fam,rad)
  if k not in model:s['abstain']+=1;bt['abstain']+=1;continue
  pred=apply(row['before'],row['click'],rad,model[k]);s['predictions']+=1;bt['predictions']+=1
  ok=pred==row['after'];s['correct' if ok else 'wrong']+=1;bt['correct' if ok else 'wrong']+=1
 def pack(c):
  d={x:int(c[x]) for x in ('transitions','predictions','correct','wrong','abstain')};d['accuracy']=round(d['correct']/d['predictions'],6) if d['predictions'] else None;d['coverage']=round(d['predictions']/d['transitions'],6) if d['transitions'] else 0.;return d
 return {'all':pack(s),'by_trace':{k:pack(v) for k,v in sorted(by_trace.items())}}

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(20)):raise ValueError('exact p0..p19 required')
 tr=collect(ps[:5]);va=collect(ps[5:10]);ft=collect(ps[:10]);ho=collect(ps[10:])
 configs={}
 for fam in FAMILIES:
  for rad in RADII:
   for sup in SUPPORTS:
    m=fit(tr,fam,rad,sup);v=evaluate(m,va,fam,rad)['all'];configs[f'{fam}|r{rad}|s{sup}']={'family':fam,'radius':rad,'support':sup,'model_keys':len(m),'validation':v}
 def rank(it):
  name,c=it;v=c['validation'];u=v['correct']-10*v['wrong'];return (-u,v['wrong'],-v['correct'],-v['coverage'],name)
 name,cfg=sorted(configs.items(),key=rank)[0];m=fit(ft,cfg['family'],cfg['radius'],cfg['support']);held=evaluate(m,ho,cfg['family'],cfg['radius'])
 return {'schema':'deus/arc3-ft09-local-renderer/1','rung':RUNG,'game':GAME,'protocol':{'train':'p0-p4','validation':'p5-p9','refit':'p0-p9','heldout':'p10-p19','heldout_learning':False},'inner':{'configs':configs,'selected':name},'heldout':held,'promotion':{'solver_promotion':False,'kaggle_packaging':False},'truth':{'public_trace_only':True,'iterative_public_heldout_research':True,'independent_generalization_claim':False,'pre_action_lookup_only':True,'heldout_never_updates_model':True,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'selected':d['inner']['selected'],'heldout':d['heldout']['all']},sort_keys=True))
if __name__=='__main__':main()
