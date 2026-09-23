#!/usr/bin/env python3
"""R283: lp85 UI-masked world-delta diagnostic after R282 NO_SIGNAL.

R281 found more deterministic repeated keys when the translation-normalized
delta is measured on the action-canonical UI-masked frame (7 keys vs 3 raw).
R282 then showed the raw-delta rules do not recur on p5-p9. R283 changes the
mechanism representation, not thresholds: isolate the non-UI world transition
and test whether its normalized delta recurs and renders the exact MASKED next
state. This is deliberately not a full-frame claim; a positive result would
unlock a separate UI reconstruction test.

Protocol: lp85 only; p0-p4 fit; p5-p9 diagnostic; p10-p19 not staged/read;
exact baseline precedence; >=2 distinct raw prestates; unique anchor; exact
masked-state scoring; any wrong rejects the world-delta mechanism.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG=283; GAME='lp85-305b61c3'; MODE='canon_regions_ui'; MIN_PRE=2

def exact_mask_key(r): return r246.digest({'before':r268.masked(r['before']),'action':r['action']})
def canon_mask(b,a): return r275.canon_board(b,a,use_ui_mask=True)
def key(r): return r278.before_key(r,MODE)

def delta(b,a):
    ds=[(y,x,int(b[y][x]),int(a[y][x])) for y in range(len(b)) for x in range(len(b[0])) if b[y][x]!=a[y][x]]
    if not ds:return (0,0,())
    y0=min(y for y,_,_,_ in ds);x0=min(x for _,x,_,_ in ds);y1=max(y for y,_,_,_ in ds);x1=max(x for _,x,_,_ in ds)
    return (y1-y0+1,x1-x0+1,tuple(sorted((y-y0,x-x0,bv,av) for y,x,bv,av in ds)))

def fit_exact(rs):
    obs=defaultdict(Counter)
    for r in rs:obs[exact_mask_key(r)][r246.digest(r268.masked(r['after']))]+=1
    return {k:next(iter(v)) for k,v in obs.items() if len(v)==1}

def fit(rs):
    obs=defaultdict(Counter);pre=defaultdict(set);concrete={}
    for r in rs:
        p=delta(canon_mask(r['before'],r['action']),canon_mask(r['after'],r['action']));k=key(r);d=r246.digest(p)
        obs[k][d]+=1;pre[k].add(r246.digest(r['before']));concrete[(k,d)]=p
    rules={k:concrete[(k,next(iter(v)))] for k,v in obs.items() if len(v)==1 and len(pre[k])>=MIN_PRE}
    return rules,{'keys':len(obs),'deterministic_delta_keys':sum(len(v)==1 for v in obs.values()),'eligible_keys':len(rules)}
def anchors(board,p):
    bh,bw,cells=p
    if not cells:return [(0,0)]
    h,w=len(board),len(board[0]);out=[]
    for ay in range(h-bh+1):
      for ax in range(w-bw+1):
        if all(int(board[ay+dy][ax+dx])==int(bv) for dy,dx,bv,av in cells):out.append((ay,ax))
    return out

def render(r,p):
    b=canon_mask(r['before'],r['action']);aa=anchors(b,p)
    if len(aa)!=1:return None,len(aa)
    ay,ax=aa[0];o=[list(z) for z in b]
    for dy,dx,bv,av in p[2]:o[ay+dy][ax+dx]=int(av)
    # compare in canonical masked space, avoiding inverse-rotation ambiguity
    return o,1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,action='append',default=[]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if {r246.game_id(p) for p in ps}!={GAME} or [r246.pnum(p) for p in ps]!=list(range(10)):raise SystemExit('exact lp85 p0-p9 required')
    tr=r278.annotated_rows(ps[:5]);va=r278.annotated_rows(ps[5:]);ex=fit_exact(tr);rules,fm=fit(tr);s=Counter();examples=[]
    for r in va:
      s['transitions']+=1
      if exact_mask_key(r) in ex:s['baseline_predictions']+=1;continue
      s['baseline_abstain']+=1;p=rules.get(key(r))
      if p is None:s['candidate_no_rule']+=1;continue
      pred,n=render(r,p)
      if pred is None:
        s['anchor_abstain']+=1;s['anchor_zero' if n==0 else 'anchor_multiple']+=1;continue
      s['candidate_predictions']+=1;actual=canon_mask(r['after'],r['action']);ok=pred==actual;s['candidate_correct' if ok else 'candidate_wrong']+=1
      if len(examples)<30:examples.append({'trace':r.get('trace'),'action':r['action'],'correct':ok})
    p=s['candidate_predictions'];opp=s['baseline_abstain'];v='PASS_ZERO_WRONG_MASKED_WORLD_SIGNAL' if p and s['candidate_wrong']==0 else ('NO_MASKED_WORLD_SIGNAL' if not p else 'REJECT_MASKED_WORLD_MISMATCH')
    diag={**dict(s),'accuracy':round(s['candidate_correct']/p,6) if p else None,'incremental_coverage':round(p/opp,6) if opp else 0.0,'examples':examples}
    out={'schema':'deus/arc3-r283-lp85-masked-world-delta/1','rung':RUNG,'lineage':{'r281':'norm_canon_ui_delta deterministic on 7 repeated fit keys','r282':'raw delta rules NO_SIGNAL on p5-p9','repair':'separate world delta from UI instead of relaxing thresholds'},'protocol':{'fit':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'metric':'exact action-canonical UI-masked next-state rendering','full_frame_claim':False,'exact_baseline_precedence':True,'unique_anchor_required':True},'fit':{'baseline_keys':len(ex),**fm},'diagnostic':diag,'verdict':v,'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'full_frame_result':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r283':False}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps({'verdict':v,'fit':out['fit'],'diagnostic':{k:diag.get(k) for k in ('transitions','baseline_predictions','baseline_abstain','candidate_no_rule','anchor_abstain','anchor_zero','anchor_multiple','candidate_predictions','candidate_correct','candidate_wrong','accuracy','incremental_coverage')}},sort_keys=True))
if __name__=='__main__':main()
