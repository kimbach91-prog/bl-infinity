#!/usr/bin/env python3
"""R314: sharded execution wrapper for R302 residual4 p0-p4 LOTO modes.

This does not change R302 semantics. It runs exactly one (game,mode) pair so the
12 public p0-p4 checks can use separate runners instead of one long multi-mode
job. The purpose is runtime resilience/resource parallelism, not a new solver.

No p5-p19 traces are staged/read.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302

RUNG=314
ALLOWED=r302.ALLOWED
MODES=("spatial","phase","delta")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--game",required=True)
    ap.add_argument("--mode",choices=MODES,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.game not in ALLOWED: raise SystemExit(f"game not allowed: {a.game}")
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={a.game}: raise SystemExit(f"exact game required, got {sorted(by)}")
    ps=sorted(by[a.game],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact p0-p4 required")
    traces=[r302.augment_trace(p) for p in ps]
    total,folds=r302.run_loto(traces,a.mode)
    if total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0:
        verdict="ZERO_FALSE_LOTO_SIGNAL"
    elif total.get("pixel_gain",0)>0:
        verdict="LOTO_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="NO_SIGNAL"
    out={
      "schema":"deus/arc3-r314-residual4-mode-shard/1",
      "rung":RUNG,"game":a.game,"mode":a.mode,
      "lineage":{"r302":"semantic-identical single-mode shard; runtime parallelization only"},
      "protocol":{"data":"p0-p4 only","evaluation":"5-fold leave-one-trace-out","p5_p9_staged_or_read":False,"p10_p19_staged_or_read":False,"promotion_in_r314":False},
      "loto":total,"folds":folds,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"runtime_shard_only":True,"p5_p9_read":False,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r314":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"mode":a.mode,"verdict":verdict,"loto":total},sort_keys=True))
if __name__=="__main__": main()
