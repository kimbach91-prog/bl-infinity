#!/usr/bin/env python3
"""R329: fixed R327 structural method across all 25 public ARC3 games, p0-p4 only.

The method is frozen before this cross-game sweep:
- action-canonical static-UI-masked world
- previous-transition binary delta local state
- fixed coarse region8 token
- seed reliability: deterministic non-identity rule present in every training trace
- structural expansion: one exact connected residual template per seed key,
  identical across every training trace, component size 2..64
- before-value guard and conflicting-cell discard
- identity fallback

Each game is evaluated by five-fold leave-one-trace-out using only p0-p4.
There is no per-game representation selection and no p5-p19 read. The purpose is
method generality/falsification, not hidden/Kaggle evidence or solver promotion.
"""
from __future__ import annotations

import argparse,json
from collections import Counter
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327

RUNG=329
BASE_MODE="delta"
GRID=8
MAX_COMPONENT=64

def run_game(paths):
    game=r246.game_id(paths[0])
    traces=[r302.augment_trace(p) for p in paths]
    prepared=[r321.prep(t,BASE_MODE,GRID) for t in traces]
    total=Counter(); folds=[]
    for held in range(5):
        train=[prepared[i] for i in range(5) if i!=held]
        templates,fit=r327.fit_templates(train)
        ev=r327.evaluate(prepared[held],templates)
        folds.append({"held_trace":held,"fit":fit,"eval":ev})
        for k,v in ev.items():
            if isinstance(v,int):
                total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    total=dict(total)
    if total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0 and total.get("exact_frame_gain",0)>0:
        verdict="FIXED_STRUCTURAL_ZERO_FALSE_EXACTFRAME_SIGNAL"
    elif total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0:
        verdict="FIXED_STRUCTURAL_ZERO_FALSE_PIXEL_SIGNAL"
    elif total.get("pixel_gain",0)>0:
        verdict="FIXED_STRUCTURAL_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="FIXED_STRUCTURAL_NO_SIGNAL"
    return {
      "game":game,
      "loto":total,
      "folds":folds,
      "verdict":verdict,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--game",required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    ps=sorted(a.input,key=r246.pnum)
    if not ps or any(r246.game_id(p)!=a.game for p in ps):
        raise SystemExit(f"exact game required: {a.game}")
    if [r246.pnum(p) for p in ps]!=list(range(5)):
        raise SystemExit("exact p0-p4 required")

    result=run_game(ps)
    out={
      "schema":"deus/arc3-r329-structural25-fixed-method-loto/1",
      "rung":RUNG,
      "game":a.game,
      "freeze":{
        "method_source":"R327 source commit 8d54bd197ae805a306493d5630c11268fcbe1ef9",
        "base_mode":BASE_MODE,
        "grid":GRID,
        "max_component":MAX_COMPONENT,
        "per_game_method_selection":False,
      },
      "protocol":{
        "data":"public p0-p4 only",
        "evaluation":"5-fold leave-one-trace-out",
        "p5_p9_staged_or_read":False,
        "p10_p19_staged_or_read":False,
        "cross_game_hyperparameter_retune":False,
      },
      **result,
      "truth":{
        "public_trace_only":True,
        "source_free_runtime_logic":True,
        "p5_p9_read":False,
        "p10_p19_read":False,
        "independent_hidden_generalization_claim":False,
        "whole_game_solver_promotion":False,
        "kaggle_execution":False,
        "competition_submission":False,
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":a.game,"verdict":out["verdict"],"loto":out["loto"]},sort_keys=True))

if __name__=="__main__":
    main()
