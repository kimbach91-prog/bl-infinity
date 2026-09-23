#!/usr/bin/env python3
"""R312: source-assisted cn04 phase-seen reliability guard.

R308 showed both R306 graph_exact errors occur under base graph/action keys whose
current causal phase token was unseen in p0-p9; the 8x8 region discriminator was
seen and reproduced the same wrong target. R312 therefore changes only the
reliability gate: retain the frozen graph_exact transition table, but abstain
unless (base graph/action key, phase_before) was observed in p0-p9.

This hypothesis is informed by reused-public p10-p19 mismatches and is therefore
source-assisted public development, not independent generalization.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275
import public_relational_topology_diag_274 as r274
import public_subset4_exact_topology_loto_303 as r303

RUNG=312
GAME="cn04-2fe56bfb"
MODE="graph_exact"

def phase(row):
    p=row.get("phase_before",("START",0))
    if isinstance(p,list): p=tuple(p)
    return tuple(p) if isinstance(p,tuple) else (str(p),0)

def base_key(row):
    return (r274.dig(r303.state(row,"before",MODE)),r275.action_class(row["action"]))

def target(row):
    return r274.dig(r303.state(row,"after",MODE))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")
    fit_traces=[r278.annotated_rows([p]) for p in ps[:10]]
    fit=[r for tr in fit_traces for r in tr]
    hold=[r for p in ps[10:] for r in r278.annotated_rows([p])]

    tab,_=r303.fit(fit_traces,MODE)
    seen=set((base_key(r),phase(r)) for r in fit)
    base=Counter(); guarded=Counter()
    for r in hold:
        k=base_key(r); pred=tab.get(k)
        if pred is None:
            base["abstain"]+=1; guarded["abstain"]+=1; continue
        actual=target(r)
        base["predictions"]+=1; base["correct" if pred==actual else "wrong"]+=1
        if (k,phase(r)) not in seen:
            guarded["abstain"]+=1; guarded["guard_abstain"]+=1; continue
        guarded["predictions"]+=1; guarded["correct" if pred==actual else "wrong"]+=1
    for d in (base,guarded):
        p=d["predictions"]; d["accuracy"]=round(d["correct"]/p,6) if p else None
    passed=bool(guarded["predictions"]>0 and guarded["wrong"]==0 and guarded["correct"]>=int(0.8*base["correct"]))
    verdict="SOURCE_ASSISTED_PHASE_GUARD_ZERO_WRONG_SIGNAL" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r312-cn04-phase-seen-guard/1","rung":RUNG,"game":GAME,
      "lineage":{"r306":"graph_exact p10-p19 235 correct / 2 wrong","r308":"both wrong had unseen phase for frozen base key; region was seen and predicted same wrong target"},
      "mechanism":{"predictor":"unchanged frozen graph_exact table fit p0-p9","reliability_gate":"require exact (graph/action base key, phase_before) observed in p0-p9; otherwise abstain"},
      "protocol":{"fit":"p0-p9","evaluation":"p10-p19 reused public development","hypothesis_informed_by_p10_p19":True,"p10_p19_updates_table":False,"promotion_scope":"source-assisted reliability primitive only"},
      "baseline":dict(base),"guarded":dict(guarded),"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"source_assisted_by_reused_public_errors":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r312":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"baseline":dict(base),"guarded":dict(guarded)},sort_keys=True))
if __name__=="__main__": main()
