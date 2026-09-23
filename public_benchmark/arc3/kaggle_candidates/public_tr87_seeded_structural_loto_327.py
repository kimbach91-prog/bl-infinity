#!/usr/bin/env python3
"""R327: TR87 seeded structural-residual expansion with p0-p4 LOTO.

R323/R324/R325 established a conservative zero-false delta+region8 seed
primitive. R325 still had zero exact-frame gain on p10-p19, so R327 changes the
unit of prediction without touching later traces: in each p0-p4 outer fold,
learn a deterministic connected residual component anchored at an R323 seed.

A structural template is eligible only when:
- its seed key is an R323 unanimous change rule;
- the exact relative before->after residual component is unique;
- the same template is observed in every training trace;
- component size is 2..64 pixels;
- every expected pre-state cell matches before application.

Conflicting cell proposals are discarded. p5-p19 are never staged/read.
"""
from __future__ import annotations

import argparse,json
from collections import Counter,defaultdict,deque
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_region8_cross_trace_unanimity_323 as r323

RUNG=327
GAME="tr87-cd924810"
BASE_MODE="delta"
GRID=8
MAX_COMPONENT=64


def components(mask):
    h=len(mask); w=len(mask[0]) if h else 0
    seen=set(); comps=[]; at={}
    for r in range(h):
        for c in range(w):
            if not mask[r][c] or (r,c) in seen:
                continue
            q=deque([(r,c)]); seen.add((r,c)); pts=[]
            while q:
                rr,cc=q.popleft(); pts.append((rr,cc))
                for nr,nc in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                    if 0<=nr<h and 0<=nc<w and mask[nr][nc] and (nr,nc) not in seen:
                        seen.add((nr,nc)); q.append((nr,nc))
            idx=len(comps); comps.append(tuple(sorted(pts)))
            for p in pts: at[p]=idx
    return comps,at


def fit_templates(prepared_traces):
    seed_rules,seed_fit=r323.fit_unanimous(prepared_traces)
    obs=defaultdict(Counter); support=defaultdict(set)
    for ti,tr in enumerate(prepared_traces):
        for row in tr:
            b,a,keys=row["b"],row["a"],row["keys"]
            h=len(b); w=len(b[0]) if h else 0
            mask=[[int(b[r][c])!=int(a[r][c]) for c in range(w)] for r in range(h)]
            comps,at=components(mask)
            for r in range(h):
                for c in range(w):
                    k=keys[r][c]
                    pred=seed_rules.get(k)
                    if pred is None or int(a[r][c])!=int(pred):
                        continue
                    ci=at.get((r,c))
                    if ci is None:
                        continue
                    comp=comps[ci]
                    if not (2<=len(comp)<=MAX_COMPONENT):
                        continue
                    rel=tuple(sorted(
                        (rr-r,cc-c,int(b[rr][cc]),int(a[rr][cc]))
                        for rr,cc in comp
                    ))
                    obs[k][rel]+=1
                    support[(k,rel)].add(ti)

    ntr=len(prepared_traces); templates={}
    for k,cnt in obs.items():
        if len(cnt)!=1:
            continue
        rel=next(iter(cnt))
        if len(support[(k,rel)])!=ntr:
            continue
        templates[k]=rel
    return templates,{
      "seed_fit":seed_fit,
      "seed_rules":len(seed_rules),
      "observed_seed_keys_with_structural_component":len(obs),
      "accepted_templates":len(templates),
      "required_trace_support":ntr,
      "max_component":MAX_COMPONENT,
      "template_sizes":sorted(len(v) for v in templates.values()),
    }


def evaluate(rows,templates):
    m=Counter()
    for row in rows:
        b,a,keys=row["b"],row["a"],row["keys"]
        h=len(b); w=len(b[0]) if h else 0
        proposals=defaultdict(set)
        for r in range(h):
            for c in range(w):
                rel=templates.get(keys[r][c])
                if rel is None:
                    continue
                ok=True
                for dr,dc,before,after in rel:
                    rr,cc=r+dr,c+dc
                    if not (0<=rr<h and 0<=cc<w and int(b[rr][cc])==int(before)):
                        ok=False; break
                if not ok:
                    continue
                m["template_firings"]+=1
                for dr,dc,before,after in rel:
                    proposals[(r+dr,c+dc)].add(int(after))
        pred=[list(map(int,x)) for x in b]
        for (r,c),vals in proposals.items():
            if len(vals)==1:
                pred[r][c]=next(iter(vals))
            else:
                m["conflicting_cells"]+=1

        id_err=cand_err=0
        for r in range(h):
            for c in range(w):
                bv=int(b[r][c]); av=int(a[r][c]); pv=int(pred[r][c])
                id_err += bv!=av; cand_err += pv!=av
                if pv!=bv:
                    m["predicted_changes"]+=1
                    if pv==av and bv!=av:
                        m["true_changed_correct"]+=1
                    elif pv!=av:
                        m["false_changes"]+=1
        m["frames"]+=1; m["pixels"]+=h*w
        m["identity_errors"]+=id_err; m["candidate_errors"]+=cand_err
        m["identity_exact_frames"]+=id_err==0; m["candidate_exact_frames"]+=cand_err==0
    m["pixel_gain"]=m["identity_errors"]-m["candidate_errors"]
    m["exact_frame_gain"]=m["candidate_exact_frames"]-m["identity_exact_frames"]
    return dict(m)


def run_loto(traces):
    prepared=[r321.prep(t,BASE_MODE,GRID) for t in traces]
    total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        templates,fit=fit_templates(train)
        ev=evaluate(prepared[held],templates)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total),folds


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if any(r246.game_id(p)!=GAME for p in ps) or [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact TR87 p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]
    total,folds=run_loto(traces)

    if total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0 and total.get("exact_frame_gain",0)>0:
        verdict="STRUCTURAL_ZERO_FALSE_EXACTFRAME_LOTO_SIGNAL"
    elif total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0:
        verdict="STRUCTURAL_ZERO_FALSE_PIXEL_LOTO_SIGNAL"
    elif total.get("pixel_gain",0)>0:
        verdict="STRUCTURAL_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="STRUCTURAL_NO_SIGNAL"

    out={
      "schema":"deus/arc3-r327-tr87-seeded-structural-loto/1",
      "rung":RUNG,
      "game":GAME,
      "lineage":{
        "r323":"delta+region8 unanimous zero-false p0-p4 LOTO seed",
        "r324":"frozen p5-p9 seed replay zero-false",
        "r325":"frozen p10-p19 seed audit zero-false but exact-frame gain 0",
      },
      "mechanism":{
        "seed":"R323 unanimous delta+region8 change key",
        "expansion":"connected actual residual component anchored at seed",
        "template_support":"exact same normalized template in every training trace",
        "precondition":"all relative before-values match",
        "conflict_policy":"discard conflicting cell proposals",
        "component_size":[2,MAX_COMPONENT],
      },
      "protocol":{
        "data":"public p0-p4 only",
        "evaluation":"5-fold leave-one-trace-out",
        "p5_p9_staged_or_read":False,
        "p10_p19_staged_or_read":False,
      },
      "loto":total,
      "folds":folds,
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_read":False,
        "p10_p19_read":False,
        "whole_game_solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"loto":total},sort_keys=True))

if __name__=="__main__":
    main()
