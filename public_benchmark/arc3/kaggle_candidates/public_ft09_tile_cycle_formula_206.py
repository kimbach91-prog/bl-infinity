#!/usr/bin/env python3
"""R206: ft09 tile-cycle formula diagnostic on public p0-p9 only.

R204 found a dominant 36-cell click-local effect. This diagnostic asks the
smallest causal question: is that 36-cell renderer a 6x6 tile-wide color
permutation, and which pre-action observable selects the permutation direction?
No p10-p19 file is accepted; outcome use is diagnostic/source-assisted only.
"""
from __future__ import annotations
import argparse,json,re,itertools
from collections import Counter,defaultdict
from pathlib import Path
import public_executable_world_model_134 as base
import public_v5_canonical_patch_router_191 as c191
RUNG=206;GAME='ft09-0d8bbf25'; CORE=(8,9,12)

def pnum(p):
 m=re.search(r'_p(\d+)_events\.jsonl$',p.name);return int(m.group(1)) if m else -1

def bbox(cells):
 rs=[r for r,c in cells];cs=[c for r,c in cells];return (min(rs),min(cs),max(rs),max(cs))

def permutation_label(pairs):
 # Require every changed core-color cell to obey one bijection on CORE.
 observed={}
 for a,b in pairs:
  if a in CORE and b in CORE:
   if a in observed and observed[a]!=b:return 'CONFLICT'
   observed[a]=b
  elif a!=b:
   return 'NONCORE'
 if not observed:return 'NONE'
 if any(k not in observed for k in CORE):return 'PARTIAL:'+','.join(f'{k}>{observed[k]}' for k in sorted(observed))
 vals=tuple(observed[k] for k in CORE)
 if len(set(vals))<3:return 'NONBIJECTIVE:'+str(vals)
 return 'PERM:'+','.join(f'{k}>{observed[k]}' for k in CORE)

def hud_signature(board):
 # pre-action bottom row summary only, color-aware because HUD colors are semantic here
 h=len(board);out=[]
 for r in range(max(0,h-3),h):out.append(tuple(Counter(board[r]).most_common()))
 return tuple(out)

def run(paths):
 ps=sorted(paths,key=pnum)
 if [pnum(x) for x in ps]!=list(range(10)):raise ValueError('exact p0..p9 only')
 stats=Counter();bbox_rel=Counter();dims=Counter();perm=Counter();selector=defaultdict(Counter);click_pre=Counter();click_mod=Counter();examples=[]
 for path in ps:
  ev=base.load_events(path);pre=ev[0];step=0
  for e in ev[1:]:
   if e.get('type')!='action':pre=e;continue
   before=base.as_grid(pre['board']);after=base.as_grid(e['board']);a=base.action_name(e);pre=e;step+=1
   if not base.same_shape(before,after) or c191.action_class(a)!='MOUSE':continue
   click=c191.parse_mouse(a)
   if click is None:continue
   cr,cc=click;h,w=len(before),len(before[0]);changed=[(r,c) for r in range(h) for c in range(w) if before[r][c]!=after[r][c]]
   if not changed:stats['identity']+=1;continue
   local=[(r,c) for r,c in changed if max(abs(r-cr),abs(c-cc))<=4]
   if len(local)!=36:continue
   stats['local36']+=1
   bb=bbox(local);r0,c0,r1,c1=bb;dims[(r1-r0+1,c1-c0+1)]+=1;bbox_rel[(r0-cr,c0-cc,r1-cr,c1-cc)]+=1
   pairs=[(before[r][c],after[r][c]) for r,c in local];lab=permutation_label(pairs);perm[lab]+=1
   precol=before[cr][cc] if 0<=cr<h and 0<=cc<w else -1;click_pre[(precol,lab)]+=1;click_mod[(cr%8,cc%8,lab)]+=1
   # Candidate pre-action selectors: clicked color, click grid residue, coarse tile index parity, and HUD signature hash.
   selectors={
    'clicked_color':str(precol),
    'residue8':f'{cr%8},{cc%8}',
    'tile_parity':f'{(cr//8)%2},{(cc//8)%2}',
    'clicked+parity':f'{precol}|{(cr//8)%2},{(cc//8)%2}',
    'clicked+residue':f'{precol}|{cr%8},{cc%8}',
    'hud_counts':repr(hud_signature(before)),
   }
   for fam,val in selectors.items():selector[(fam,val)][lab]+=1
   if len(examples)<40:examples.append({'trace':path.name,'step':step,'click':[cr,cc],'pre_clicked_color':precol,'bbox':[r0,c0,r1,c1],'bbox_rel':[r0-cr,c0-cc,r1-cr,c1-cc],'perm':lab,'changed_total':len(changed),'outside_local36':len(changed)-36})
 # For each selector family, measure how many local36 examples belong to values with deterministic permutation label.
 family_summary={}
 for fam in ('clicked_color','residue8','tile_parity','clicked+parity','clicked+residue','hud_counts'):
  vals=[(val,c) for (f,val),c in selector.items() if f==fam]
  det=sum(sum(c.values()) for val,c in vals if len(c)==1)
  total=sum(sum(c.values()) for val,c in vals)
  conflicts=sum(1 for val,c in vals if len(c)>1)
  family_summary[fam]={'examples':total,'deterministic_examples':det,'deterministic_fraction':round(det/total,6) if total else 0,'values':len(vals),'conflicted_values':conflicts,'top_values':[{'value':val,'labels':dict(c)} for val,c in sorted(vals,key=lambda x:-sum(x[1].values()))[:12]]}
 return {'schema':'deus/arc3-ft09-tile-cycle-formula/1','rung':RUNG,'game':GAME,'scope':'p0-p9_outcome_assisted_formula_diagnostic_only','stats':dict(stats),'local36_dimensions':[[list(k),v] for k,v in dims.most_common(20)],'local36_bbox_relative':[[list(k),v] for k,v in bbox_rel.most_common(20)],'permutation_labels':dict(perm),'selector_summary':family_summary,'clicked_color_labels':[[list(k),v] for k,v in click_pre.most_common(30)],'click_residue_labels':[[list(k),v] for k,v in click_mod.most_common(30)],'examples':examples,'truth':{'uses_only_p0_p9':True,'p10_p19_read':False,'outcome_assisted':True,'diagnostic_only':True,'kaggle_execution':False,'submission_quota_spent':False,'owner_score_claim':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();d=run(a.input);a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'stats':d['stats'],'dims':d['local36_dimensions'][:5],'perms':d['permutation_labels'],'selectors':{k:{x:v[x] for x in ('examples','deterministic_examples','deterministic_fraction','values','conflicted_values')} for k,v in d['selector_summary'].items()}},sort_keys=True))
if __name__=='__main__':main()
