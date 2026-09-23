#!/usr/bin/env python3
"""R273T: lean target-family test of factorized core + UI residual.

This is a bounded discriminator for the R270-clean/R272-exact-renderer-miss
families. It uses only public traces. p0-p4 fit -> p5-p9 zero-wrong selection ->
p0-p9 refit -> p10-p19 frozen evaluation. Exact raw state/action baseline has
precedence. No hidden/Kaggle state is read and no submission is made.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268

MIN_DISTINCT_CORES = 2


def prepare_rows(paths: list[Path]) -> list[dict[str, Any]]:
    out = []
    for p in paths:
        ev = r246.load_events(p)
        pre = ev[0]
        for e in ev[1:]:
            if e.get("type") != "action":
                pre = e
                continue
            before = [[int(v) for v in row] for row in pre["board"]]
            after = [[int(v) for v in row] for row in e["board"]]
            if before and after and len(before) == len(after) and len(before[0]) == len(after[0]):
                a = r246.action_name(e)
                out.append({
                    "trace": p.name,
                    "action": a,
                    "before": before,
                    "after": after,
                    "exact_key": r246.digest({"b": before, "a": a}),
                    "after_digest": r246.digest(after),
                })
            pre = e
    return out


def ui_positions(h: int, w: int) -> list[tuple[int,int]]:
    return [(r,c) for r in range(h) for c in range(w)
            if c == 0 or c == w-1 or r in {0,1,h-1}]


def ui_values(board):
    h,w=len(board),len(board[0])
    return tuple(int(board[r][c]) for r,c in ui_positions(h,w))


def core(board):
    return r268.masked(board)


def core_digest(board): return r246.digest(core(board))
def ui_digest(board): return r246.digest(ui_values(board))


def fit_exact(rs):
    obs=defaultdict(Counter); frames={}
    for r in rs:
        obs[r["exact_key"]][r["after_digest"]]+=1
        frames[(r["exact_key"],r["after_digest"])]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=frames[(k,d)]
    return out


def fit_factor(rs):
    cobs=defaultdict(Counter); cframe={}
    uobs=defaultdict(Counter); uframe={}; usupport=defaultdict(set)
    for r in rs:
        ck=(core_digest(r["before"]),r["action"])
        ca=core(r["after"]); cd=r246.digest(ca)
        cobs[ck][cd]+=1; cframe[(ck,cd)]=ca
        uk=(ui_digest(r["before"]),r["action"])
        ua=ui_values(r["after"]); ud=r246.digest(ua)
        uobs[uk][ud]+=1; uframe[(uk,ud)]=ua
        usupport[uk].add(core_digest(r["before"]))
    ct={}
    for k,c in cobs.items():
        if len(c)==1:
            d=next(iter(c)); ct[k]=cframe[(k,d)]
    ut={}; low=amb=0
    for k,c in uobs.items():
        if len(c)!=1:
            amb+=1; continue
        if len(usupport[k]) < MIN_DISTINCT_CORES:
            low+=1; continue
        d=next(iter(c)); ut[k]=uframe[(k,d)]
    return ct,ut,{"core_keys":len(ct),"ui_keys":len(ut),"ui_low_support":low,"ui_ambiguous":amb}


def compose(ca,ua):
    out=[row[:] for row in ca]; pos=ui_positions(len(out),len(out[0]))
    if len(pos)!=len(ua): return None
    for (r,c),v in zip(pos,ua): out[r][c]=int(v)
    return out


def eval_added(rs, exact, ct, ut):
    s=Counter(); examples=[]
    for r in rs:
        s["transitions"]+=1
        if r["exact_key"] in exact:
            s["baseline_predictions"]+=1; continue
        s["baseline_abstain"]+=1
        ca=ct.get((core_digest(r["before"]),r["action"]))
        ua=ut.get((ui_digest(r["before"]),r["action"]))
        if ca is None or ua is None:
            s["candidate_abstain"]+=1; continue
        pred=compose(ca,ua)
        if pred is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        ok=pred==r["after"]
        s["candidate_correct" if ok else "candidate_wrong"]+=1
        if len(examples)<12: examples.append({"trace":r["trace"],"action":r["action"],"correct":ok})
    p=s["candidate_predictions"]; opp=s["baseline_abstain"]
    return {**dict(s),"accuracy":round(s["candidate_correct"]/p,6) if p else None,
            "coverage":round(p/opp,6) if opp else 0.0,"examples":examples}


def evaluate(paths):
    ps=sorted(paths,key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise ValueError(f"need p0..p19, got {nums}")
    parts=[prepare_rows([p]) for p in ps]
    tr=sum(parts[:5],[]); va=sum(parts[5:10],[]); fit=sum(parts[:10],[]); ho=sum(parts[10:],[])
    ex0=fit_exact(tr); ct0,ut0,d0=fit_factor(tr); val=eval_added(va,ex0,ct0,ut0)
    selected=val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0
    ex=fit_exact(fit); ct,ut,d=fit_factor(fit)
    held=eval_added(ho,ex,ct,ut) if selected else {"transitions":len(ho),"candidate_predictions":0,"candidate_correct":0,"candidate_wrong":0,"accuracy":None,"coverage":0.0}
    promote=bool(selected and held.get("candidate_predictions",0)>0 and held.get("candidate_wrong",0)==0)
    return {"selected":selected,"selection_p5_p9":val,"fit_p0_p4":d0,"refit_p0_p9":d,"heldout_p10_p19":held,"promote_representation":promote}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,action='append',default=[]); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    games={g:evaluate(ps) for g,ps in sorted(by.items())}
    agg=Counter(); promoted=[]; selected=[]
    for g,x in games.items():
        if x['selected']: selected.append(g)
        if x['promote_representation']: promoted.append(g)
        h=x['heldout_p10_p19']
        for k in ('transitions','baseline_predictions','baseline_abstain','candidate_predictions','candidate_correct','candidate_wrong','candidate_abstain'):
            agg[k]+=int(h.get(k,0) or 0)
    p=agg['candidate_predictions']; opp=agg['baseline_abstain']
    result={
      'schema':'deus/arc3-r273t-factorized-ui-target4/1',
      'protocol':{'fit':'p0-p4','selection':'p5-p9 zero-wrong positive incremental','refit':'p0-p9','frozen_eval':'p10-p19','exact_baseline_precedence':True,'ui_min_distinct_cores':MIN_DISTINCT_CORES},
      'games':games,
      'aggregate':{**dict(agg),'game_count':len(games),'selected_games':selected,'promoted_games':promoted,'accuracy':round(agg['candidate_correct']/p,6) if p else None,'coverage':round(p/opp,6) if opp else 0.0},
      'truth':{'public_trace_only':True,'game_source_read':False,'heldout_updates_model':False,'kaggle_execution':False,'competition_submission':False,'submission_quota_spent':False,'owner_score_claim':False}
    }
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result['aggregate'],sort_keys=True))

if __name__=='__main__': main()
