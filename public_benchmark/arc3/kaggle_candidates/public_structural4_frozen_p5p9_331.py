#!/usr/bin/env python3
"""R331: frozen p5-p9 replay for four new R329 zero-false fixed-method signals.

R329 froze the R327 structural method across all 25 games on p0-p4 only and
found zero-false signals on dc22, tn36, tr87, s5i5, wa30. TR87 already passed
the unchanged method on p5-p9 in R328, so R331 evaluates the remaining four:
  dc22-fdcac232, tn36-ef4dde99, s5i5-18d95033, wa30-ee6fef47.

For each game, fit the exact frozen R327 method on p0-p4 and replay p5-p9
unchanged. No representation selection or threshold changes occur. p10-p19 are
not staged/read. This is source-assisted public-development stability evidence,
not hidden/Kaggle evidence or whole-game solver promotion.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_tr87_wa30_region_context_loto_321 as r321
import public_tr87_seeded_structural_loto_327 as r327

RUNG=331
GAMES={
  "dc22-fdcac232",
  "tn36-ef4dde99",
  "s5i5-18d95033",
  "wa30-ee6fef47",
}
BASE_MODE="delta"
GRID=8
FREEZE_SOURCE="8d54bd197ae805a306493d5630c11268fcbe1ef9"
SELECTOR_SOURCE="b3bef4979c940f010227632c215bce5767e5315a"


def one_game(paths):
    g=r246.game_id(paths[0])
    train=[r302.augment_trace(p) for p in paths[:5]]
    replay=[r302.augment_trace(p) for p in paths[5:]]
    prepared_train=[r321.prep(t,BASE_MODE,GRID) for t in train]
    prepared_replay=[x for t in replay for x in r321.prep(t,BASE_MODE,GRID)]
    templates,fit=r327.fit_templates(prepared_train)
    val=r327.evaluate(prepared_replay,templates)
    zero=bool(
      val.get("predicted_changes",0)>0
      and val.get("false_changes",0)==0
      and val.get("pixel_gain",0)>0
    )
    return {
      "fit":fit,
      "source_assisted_p5_p9":val,
      "gate_pass":zero,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by)!=GAMES:
        raise SystemExit(f"exact frozen games required; got {sorted(by)}")
    games={}; passed=[]
    for g in sorted(GAMES):
        ps=sorted(by[g],key=r246.pnum)
        if [r246.pnum(p) for p in ps]!=list(range(10)):
            raise SystemExit(f"{g}: exact p0-p9 required")
        result=one_game(ps)
        games[g]=result
        if result["gate_pass"]:
            passed.append(g)
    verdict="FROZEN_STRUCTURAL_MULTI_GAME_STABILITY_SIGNAL" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r331-structural4-frozen-p5p9/1",
      "rung":RUNG,
      "freeze":{
        "method_source":FREEZE_SOURCE,
        "selector_source":SELECTOR_SOURCE,
        "method":"R327 fixed delta+region8 seeded structural templates",
        "games":sorted(GAMES),
        "games_selected_from_r329_p0_p4_only":True,
        "representation_changed_after_selection":False,
        "threshold_changed_after_selection":False,
      },
      "protocol":{
        "fit":"p0-p4 only",
        "source_assisted_replay":"p5-p9 only",
        "p10_p19_staged_or_read":False,
        "p5_p9_updates_selector":False,
        "p5_p9_updates_model_family":False,
      },
      "games":games,
      "pass_games":passed,
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
    print(json.dumps({"verdict":verdict,"pass_games":passed,"games":games},sort_keys=True))

if __name__=="__main__":
    main()
