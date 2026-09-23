#!/usr/bin/env python3
"""R306: cn04 frozen graph_exact reused-public p10-p19 representation gate.

Selector identity is inherited from the immutable R305 source commit
9bd5223a309d41174ffb194b898af987f928dc58, which was fixed before p5-p9 replay.
R306 refits the already-frozen graph_exact representation on p0-p9 and evaluates
p10-p19 without updating selector, representation, or model.

This is PUBLIC_OFFLINE reused-public-development evidence only.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_exact_topology_loto_303 as r303

RUNG=306
GAME="cn04-2fe56bfb"
MODE="graph_exact"
BASELINE="nodes_coarse"
FREEZE_SOURCE="9bd5223a309d41174ffb194b898af987f928dc58"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")

    fit_traces=[r278.annotated_rows([p]) for p in ps[:10]]
    hold=[r for p in ps[10:] for r in r278.annotated_rows([p])]
    ctab,cfit=r303.fit(fit_traces,MODE); btab,bfit=r303.fit(fit_traces,BASELINE)
    cand=r303.evaluate(hold,ctab,MODE); base=r303.evaluate(hold,btab,BASELINE)
    passed=bool(cand.get("predictions",0)>0 and cand.get("wrong",0)==0 and cand.get("correct",0)>base.get("correct",0))
    verdict="PROMOTE_FROZEN_GRAPH_EXACT_REPRESENTATION" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r306-cn04-graph-exact-frozen-p10p19/1","rung":RUNG,"game":GAME,
      "frozen_selector":{"mode":MODE,"baseline":BASELINE,"freeze_source":FREEZE_SOURCE},
      "lineage":{"r303":"p0-p4 LOTO graph_exact 57/57 zero wrong","r305":"p5-p9 frozen replay 100/100 zero wrong vs baseline22 correct/8 wrong"},
      "protocol":{"selector_frozen_before_p5_p9":True,"refit":"p0-p9 only","evaluation":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_representation":False,"p10_p19_updates_model":False,"promotion_scope":"representation primitive only"},
      "candidate_fit":cfit,"baseline_fit":bfit,"candidate":cand,"baseline":base,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r306":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"candidate":cand,"baseline":base},sort_keys=True))
if __name__=="__main__": main()
