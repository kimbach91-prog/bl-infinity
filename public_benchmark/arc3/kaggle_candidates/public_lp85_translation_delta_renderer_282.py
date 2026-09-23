#!/usr/bin/env python3
"""R282: lp85 translation-normalized action-canonical raw-delta renderer.

R281 identified the smallest discriminating renderer hypothesis after R280's
NO_EXACT_FRAME_SIGNAL: some repeated R278 representation keys have a stable
translation-normalized pixel delta even when exact next frames differ.

Protocol:
* exact game lp85-305b61c3
* frozen representation key: R278 canon_regions_ui
* fit p0-p4 only, diagnostic p5-p9 only
* p10-p19 are not staged/read
* exact visible-state/action baseline has precedence
* candidate key must have one exact normalized canonical-raw delta and >=2
  distinct raw prestates in fit
* render by scanning the current action-canonical raw frame for anchors whose
  expected-before pixels exactly match the learned normalized delta pattern;
  predict only when exactly one anchor matches
* inverse-rotate to raw coordinates and score exact full frame
* no threshold retuning; any candidate mismatch rejects the mechanism

PUBLIC_OFFLINE only; no hidden/Kaggle inference.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG=282
TARGET_GAME="lp85-305b61c3"
MODE="canon_regions_ui"
MIN_DISTINCT_PRESTATES=2
DIRS={"UP","DOWN","LEFT","RIGHT"}


def exact_key(r:dict[str,Any])->str:
    return r246.digest({"before":r["before"],"action":r["action"]})


def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r246.digest(r["after"]); obs[k][d]+=1; frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=frame[(k,d)]
    return out


def canon_raw(board,action):
    return r275.canon_board(board,action,use_ui_mask=False)


def inverse_canon(board,action):
    a=str(action or "").upper()
    if a=="UP": return [list(row) for row in board]
    if a=="DOWN": return r275.rot_180(board)
    if a=="LEFT": return r275.rot_ccw(board)
    if a=="RIGHT": return r275.rot_cw(board)
    return [list(row) for row in board]


def norm_delta(before,after):
    if len(before)!=len(after) or len(before[0])!=len(after[0]): return None
    ds=[(y,x,int(before[y][x]),int(after[y][x])) for y in range(len(before)) for x in range(len(before[0])) if before[y][x]!=after[y][x]]
    if not ds: return (0,0,())
    y0=min(y for y,_,_,_ in ds); x0=min(x for _,x,_,_ in ds)
    y1=max(y for y,_,_,_ in ds); x1=max(x for _,x,_,_ in ds)
    return (y1-y0+1,x1-x0+1,tuple(sorted((y-y0,x-x0,b,a) for y,x,b,a in ds)))


def cand_key(r):
    return r278.before_key(r,MODE)


def fit_candidate(rows):
    obs=defaultdict(Counter); prestates=defaultdict(set)
    for r in rows:
        b=canon_raw(r["before"],r["action"]); a=canon_raw(r["after"],r["action"])
        pat=norm_delta(b,a)
        if pat is None: continue
        k=cand_key(r); obs[k][r246.digest(pat)]+=1; prestates[k].add(r246.digest(r["before"]))
    # retain concrete pattern from one representative only after proving digest uniqueness
    concrete={}
    for r in rows:
        k=cand_key(r)
        if k not in obs or len(obs[k])!=1 or len(prestates[k])<MIN_DISTINCT_PRESTATES: continue
        pat=norm_delta(canon_raw(r["before"],r["action"]),canon_raw(r["after"],r["action"]))
        if pat is not None and r246.digest(pat)==next(iter(obs[k])): concrete[k]=pat
    meta={"keys":len(obs),"deterministic_delta_keys":sum(len(v)==1 for v in obs.values()),"eligible_keys":len(concrete),"min_distinct_prestates":MIN_DISTINCT_PRESTATES}
    return concrete,meta


def matching_anchors(board,pat):
    bh,bw,cells=pat
    if bh==0 and bw==0 and not cells: return [(0,0)]
    h,w=len(board),len(board[0]); out=[]
    for ay in range(0,h-bh+1):
        for ax in range(0,w-bw+1):
            ok=True
            for dy,dx,bv,av in cells:
                if int(board[ay+dy][ax+dx])!=int(bv): ok=False; break
            if ok: out.append((ay,ax))
    return out


def render(row,pattern):
    cb=canon_raw(row["before"],row["action"])
    anchors=matching_anchors(cb,pattern)
    if len(anchors)!=1: return None,len(anchors)
    ay,ax=anchors[0]; out=[list(z) for z in cb]
    for dy,dx,bv,av in pattern[2]: out[ay+dy][ax+dx]=int(av)
    return inverse_canon(out,row["action"]),1


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if {r246.game_id(p) for p in ps}!={TARGET_GAME} or [r246.pnum(p) for p in ps]!=list(range(10)):
        raise SystemExit('exact lp85 p0-p9 required')
    fit_rows=r278.annotated_rows(ps[:5]); diag_rows=r278.annotated_rows(ps[5:])
    exact=fit_exact(fit_rows); cand,fitmeta=fit_candidate(fit_rows)
    s=Counter(); examples=[]
    for r in diag_rows:
        s['transitions']+=1
        if exact_key(r) in exact:
            s['baseline_predictions']+=1; continue
        s['baseline_abstain']+=1
        pat=cand.get(cand_key(r))
        if pat is None:
            s['candidate_no_rule']+=1; continue
        pred,nanchors=render(r,pat)
        if pred is None:
            s['candidate_anchor_abstain']+=1
            if nanchors==0:s['anchor_zero']+=1
            elif nanchors>1:s['anchor_multiple']+=1
            continue
        s['candidate_predictions']+=1; ok=pred==r['after']; s['candidate_correct' if ok else 'candidate_wrong']+=1
        if len(examples)<30: examples.append({'trace':r.get('trace'),'action':r['action'],'correct':ok})
    p=s['candidate_predictions']; opp=s['baseline_abstain']
    verdict='PASS_ZERO_WRONG_EXACT_FRAME_SIGNAL' if p>0 and s['candidate_wrong']==0 else ('NO_EXACT_FRAME_SIGNAL' if p==0 else 'REJECT_EXACT_FRAME_MISMATCH')
    diagnostic={**dict(s),'candidate_accuracy':round(s['candidate_correct']/p,6) if p else None,'incremental_coverage':round(p/opp,6) if opp else 0.0,'examples':examples}
    out={'schema':'deus/arc3-r282-lp85-translation-delta-renderer/1','rung':RUNG,'frozen_candidate':{'game':TARGET_GAME,'representation_key':MODE,'renderer':'translation-normalized action-canonical raw pixel delta'},
         'lineage':{'r280':'NO_EXACT_FRAME_SIGNAL direct frame map','r281':'TRY_TRANSLATION_NORMALIZED_CANON_RAW_DELTA','repair':'change renderer representation; no support/accuracy threshold relaxation'},
         'protocol':{'fit':'p0-p4 only','diagnostic':'p5-p9 only','p10_p19_staged_or_read':False,'exact_baseline_precedence':True,'unique_anchor_required':True,'min_distinct_prestates':MIN_DISTINCT_PRESTATES,'exact_full_frame_scoring':True},
         'fit':{'exact_baseline_keys':len(exact),**fitmeta},'diagnostic':diagnostic,'verdict':verdict,
         'truth':{'public_trace_only':True,'source_free_runtime_logic':True,'p10_p19_read':False,'independent_hidden_generalization_claim':False,'kaggle_execution':False,'competition_submission':False,'owner_score_claim':False,'submission_quota_spent_by_r282':False}}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'fit':out['fit'],'diagnostic':{k:diagnostic.get(k) for k in ('transitions','baseline_predictions','baseline_abstain','candidate_no_rule','candidate_anchor_abstain','anchor_zero','anchor_multiple','candidate_predictions','candidate_correct','candidate_wrong','candidate_accuracy','incremental_coverage')}},sort_keys=True))
if __name__=='__main__': main()
