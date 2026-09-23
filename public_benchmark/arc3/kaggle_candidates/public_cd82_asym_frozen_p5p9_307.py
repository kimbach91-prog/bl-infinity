#!/usr/bin/env python3
"""R307: frozen cd82 exact_nodes_to_coarse p5-p9 gate.

R304 selected exact_nodes_to_coarse on p0-p4 five-fold LOTO:
139/139 correct, 0 wrong versus coarse baseline 163 correct / 9 wrong.
This source freezes the exact game+mode before p5-p9 staging.

p5-p9 replay is public-development/source-assisted evidence only; p10-p19 are
forbidden in R307.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=307
GAME="cd82-fb555c5d"
MODE="exact_nodes_to_coarse"
BASELINE="coarse_to_coarse"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f"exact p0-p9 required, got {nums}")
    train=[r278.annotated_rows([p]) for p in ps[:5]]
    val=[r for p in ps[5:] for r in r278.annotated_rows([p])]
    ctab,cfit=r304.fit(train,MODE); btab,bfit=r304.fit(train,BASELINE)
    cand=r304.evaluate(val,ctab,MODE); base=r304.evaluate(val,btab,BASELINE)
    passed=bool(cand.get("predictions",0)>0 and cand.get("wrong",0)==0 and cand.get("correct",0)>=int(0.75*base.get("correct",0)) and cand.get("wrong",0)<base.get("wrong",0))
    verdict="FROZEN_ASYMMETRIC_P5P9_SIGNAL" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r307-cd82-asym-frozen-p5p9/1","rung":RUNG,"game":GAME,
      "frozen_selector":{"mode":MODE,"baseline":BASELINE},
      "lineage":{"r304_run":35826885553,"r304_job":107070470643,"r304_loto":"exact_nodes_to_coarse 139/139 zero wrong; coarse 163 correct 9 wrong"},
      "protocol":{"fit":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"selector_frozen_before_replay":True,"p5_p9_updates_selector":False,"p5_p9_updates_representation":False,"p5_p9_updates_model":False,"promotion_scope":"representation primitive only"},
      "candidate_fit":cfit,"baseline_fit":bfit,"candidate":cand,"baseline":base,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r307":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"candidate":cand,"baseline":base},sort_keys=True))
if __name__=="__main__": main()
