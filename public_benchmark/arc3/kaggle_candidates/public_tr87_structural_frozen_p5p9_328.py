#!/usr/bin/env python3
"""R328: frozen p5-p9 replay for the R327 TR87 structural residual candidate.

Candidate identity was fixed by R327 source commit
8d54bd197ae805a306493d5630c11268fcbe1ef9 using p0-p4 LOTO only.
R328 refits the exact same structural-template family on p0-p4 and evaluates
p5-p9 unchanged. No representation or threshold selection occurs here.

Because p5-p9 were previously used elsewhere in the project, this is
source-assisted public-development stability evidence only. p10-p19 are not
staged/read by this rung.
"""
from __future__ import annotations

import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327

RUNG=328
GAME=r327.GAME
BASE_MODE=r327.BASE_MODE
GRID=r327.GRID
FREEZE_COMMIT="8d54bd197ae805a306493d5630c11268fcbe1ef9"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)):
        raise SystemExit("exact p0-p9 required")

    train=[r302.augment_trace(p) for p in ps[:5]]
    replay=[r302.augment_trace(p) for p in ps[5:]]
    prepared_train=[r321.prep(t,BASE_MODE,GRID) for t in train]
    prepared_replay=[x for t in replay for x in r321.prep(t,BASE_MODE,GRID)]

    templates,fit=r327.fit_templates(prepared_train)
    val=r327.evaluate(prepared_replay,templates)

    gate=bool(
        val.get("predicted_changes",0)>0
        and val.get("false_changes",0)==0
        and val.get("pixel_gain",0)>0
        and val.get("exact_frame_gain",0)>0
    )
    verdict="FROZEN_STRUCTURAL_P5P9_ZERO_FALSE_PASS" if gate else "FROZEN_STRUCTURAL_P5P9_NO_PROMOTION"

    out={
      "schema":"deus/arc3-r328-tr87-structural-frozen-p5p9/1",
      "rung":RUNG,
      "game":GAME,
      "freeze_commit":FREEZE_COMMIT,
      "candidate":{
        "seed":"R323 unanimous delta+region8",
        "structural_expansion":"R327 connected residual template",
        "representation_changed_after_r327":False,
        "threshold_changed_after_r327":False,
      },
      "protocol":{
        "fit":"p0-p4 only",
        "source_assisted_replay":"p5-p9 only",
        "p10_p19_staged_or_read":False,
        "p5_p9_updates_selector":False,
        "p5_p9_updates_model_family":False,
      },
      "fit":fit,
      "source_assisted_p5_p9":val,
      "gate_pass":gate,
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_replay_is_source_assisted":True,
        "p10_p19_read":False,
        "independent_hidden_generalization_claim":False,
        "whole_game_solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"gate_pass":gate,"replay":val},sort_keys=True))

if __name__=="__main__":
    main()
