#!/usr/bin/env python3
"""R305: frozen cn04 graph_exact p5-p9 representation gate.

R303 selected cn04 graph_exact using p0-p4-only five-fold LOTO:
57/57 correct, 0 wrong versus coarse 12 correct / 7 wrong.
R305 freezes game+mode before staging p5-p9, fits only p0-p4, then replays
p5-p9 without updating selector, representation, or model.

Because p5-p9 are reused public-development traces elsewhere in the project,
this is source-assisted PUBLIC_OFFLINE evidence, not independent generalization.
p10-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_exact_topology_loto_303 as r303

RUNG=305
GAME="cn04-2fe56bfb"
MODE="graph_exact"
BASELINE="nodes_coarse"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum)
    nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(10)): raise SystemExit(f"exact p0-p9 required, got {nums}")

    train=[r278.annotated_rows([p]) for p in ps[:5]]
    val=[r for p in ps[5:] for r in r278.annotated_rows([p])]

    ctab,cfit=r303.fit(train,MODE)
    btab,bfit=r303.fit(train,BASELINE)
    cand=r303.evaluate(val,ctab,MODE)
    base=r303.evaluate(val,btab,BASELINE)

    gate=bool(
        cand.get("predictions",0)>0
        and cand.get("wrong",0)==0
        and cand.get("correct",0)>base.get("correct",0)
    )
    verdict="FROZEN_GRAPH_EXACT_P5P9_SIGNAL" if gate else "NO_PROMOTION"

    out={
      "schema":"deus/arc3-r305-cn04-graph-exact-frozen-p5p9/1",
      "rung":RUNG,
      "game":GAME,
      "frozen_selector":{"mode":MODE,"baseline":BASELINE},
      "lineage":{"r303_run":35826664764,"r303_job":107069791316,"r303_loto":"graph_exact 57/57 zero wrong; coarse 12 correct 7 wrong"},
      "protocol":{
        "fit":"p0-p4 only",
        "source_assisted_replay":"p5-p9 only",
        "p10_p19_staged_or_read":False,
        "selector_frozen_before_replay":True,
        "p5_p9_updates_selector":False,
        "p5_p9_updates_representation":False,
        "p5_p9_updates_model":False,
        "promotion_scope":"representation primitive only",
      },
      "candidate_fit":cfit,
      "baseline_fit":bfit,
      "candidate":cand,
      "baseline":base,
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_replay_is_source_assisted":True,
        "p10_p19_read":False,
        "independent_hidden_generalization_claim":False,
        "whole_game_policy_claim":False,
        "solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
        "submission_quota_spent_by_r305":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"candidate":cand,"baseline":base},sort_keys=True))

if __name__=="__main__": main()
