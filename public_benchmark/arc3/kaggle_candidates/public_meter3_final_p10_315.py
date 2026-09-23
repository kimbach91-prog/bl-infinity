#!/usr/bin/env python3
"""R315: clean final p10-p19 audit for the three frozen meter signals.

Selector history (all public-development):
- R307 p0-p4 five-fold LOTO froze meter as zero-wrong for ls20/sb26/sp80.
- R308 kept the selector unchanged and replayed p5-p9:
    ls20 3/3, sb26 4/4, sp80 20/20, all zero-wrong.
R315 performs the final audit only after that barrier. It deliberately fits the
exact baseline and meter->exact-next-frame table on p0-p4 ONLY, not p5-p9, then
evaluates p10-p19. Thus the final audit cannot tune the selector or model.

This is reused public-development evidence, not independent hidden/Kaggle
performance. No solver promotion is implied by a scoped zero-wrong result.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG=315
MODE="meter"
GAMES={"ls20-9607627b","sb26-7fbdac44","sp80-589a99af"}
MIN_PRESTATES=2
MIN_TRACES=2


def exact_key(r): return r246.digest({"b":r["before"],"a":r["action"]})
def abs_key(r): return r246.stable((r["before_features"][MODE],r["action"]))


def fit_exact(rows):
    obs=defaultdict(Counter); frame={}
    for r in rows:
        k=exact_key(r); d=r["after_digest"]; obs[k][d]+=1; frame[(k,d)]=r["after"]
    out={}
    for k,c in obs.items():
        if len(c)==1:
            d=next(iter(c)); out[k]=frame[(k,d)]
    return out


def fit_meter(rows):
    obs=defaultdict(Counter); prestates=defaultdict(set); traces=defaultdict(set); frame={}
    for r in rows:
        k=abs_key(r); d=r["after_digest"]
        obs[k][d]+=1; prestates[k].add(r["before_digest"]); traces[k].add(r["trace"]); frame[(k,d)]=r["after"]
    tab={}
    for k,c in obs.items():
        if len(c)!=1 or len(prestates[k])<MIN_PRESTATES or len(traces[k])<MIN_TRACES: continue
        d=next(iter(c)); tab[k]=frame[(k,d)]
    return tab,{"observed_keys":len(obs),"safe_keys":len(tab)}


def evaluate(rows,exact,tab):
    s=Counter()
    for r in rows:
        s["transitions"]+=1
        if exact_key(r) in exact:
            s["exact_baseline"]+=1; continue
        s["baseline_abstain"]+=1
        pred=tab.get(abs_key(r))
        if pred is None:
            s["candidate_abstain"]+=1; continue
        s["candidate_predictions"]+=1
        s["candidate_correct" if pred==r["after"] else "candidate_wrong"]+=1
    p=s["candidate_predictions"]
    s["accuracy"]=round(s["candidate_correct"]/p,6) if p else None
    return dict(s)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    tr_by=defaultdict(list); ev_by=defaultdict(list)
    for p in a.train: tr_by[r246.game_id(p)].append(p)
    for p in a.eval: ev_by[r246.game_id(p)].append(p)
    if set(tr_by)!=GAMES or set(ev_by)!=GAMES:
        raise SystemExit(f"exact frozen games required; train={sorted(tr_by)} eval={sorted(ev_by)}")

    games={}; pass_games=[]
    agg=Counter()
    for g in sorted(GAMES):
        tps=sorted(tr_by[g],key=r246.pnum); eps=sorted(ev_by[g],key=r246.pnum)
        if [r246.pnum(p) for p in tps]!=list(range(5)): raise SystemExit(f"{g}: train must be p0-p4")
        if [r246.pnum(p) for p in eps]!=list(range(10,20)): raise SystemExit(f"{g}: eval must be p10-p19")
        train=[r for p in tps for r in r251.prepare_rows([p])]
        final=[r for p in eps for r in r251.prepare_rows([p])]
        exact=fit_exact(train); meter,fit=fit_meter(train); val=evaluate(final,exact,meter)
        gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
        if gate: pass_games.append(g)
        games[g]={"fit":fit,"final_p10_p19":val,"gate_pass":gate}
        for k in ("transitions","exact_baseline","baseline_abstain","candidate_predictions","candidate_correct","candidate_wrong"):
            agg[k]+=int(val.get(k,0) or 0)
    p=agg["candidate_predictions"]
    aggregate={**dict(agg),"accuracy":round(agg["candidate_correct"]/p,6) if p else None}
    verdict="FINAL_METER_ZERO_WRONG_SIGNAL" if len(pass_games)==len(GAMES) else ("PARTIAL_FINAL_METER_SIGNAL" if pass_games else "NO_PROMOTION")
    out={
      "schema":"deus/arc3-r315-meter3-final-p10/1","rung":RUNG,
      "lineage":{
        "r307_run":35827692947,
        "r308_run":35827840654,
        "frozen_games":sorted(GAMES),
        "frozen_mode":MODE,
        "selector_frozen_before_p5_p9":True,
        "p5_p9_replay_zero_wrong":{"ls20":"3/3","sb26":"4/4","sp80":"20/20"}
      },
      "protocol":{
        "selector":"frozen before R308 p5-p9",
        "model_fit":"p0-p4 only",
        "final_audit":"p10-p19 only",
        "p5_p9_staged_or_read_by_r315":False,
        "p10_p19_updates_selector":False,
        "p10_p19_updates_model":False,
        "no_retune_after_final_audit":True
      },
      "games":games,"aggregate":aggregate,"pass_games":pass_games,"verdict":verdict,
      "truth":{
        "public_trace_only":True,"source_free_runtime_logic":True,
        "reused_public_development_final_audit":True,
        "independent_hidden_generalization_claim":False,
        "whole_game_policy_claim":False,"solver_promotion":False,
        "kaggle_execution":False,"competition_submission":False,
        "submission_quota_spent_by_r315":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"pass_games":pass_games,"aggregate":aggregate,"games":games},sort_keys=True))

if __name__=="__main__": main()
