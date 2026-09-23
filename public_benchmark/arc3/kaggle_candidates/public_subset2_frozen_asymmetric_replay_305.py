#!/usr/bin/env python3
"""R305: frozen source-assisted replay for the two R304 asymmetric alias signals.

R304 used p0-p4 five-fold LOTO only and nominated:
- cd82-fb555c5d -> exact_nodes_to_coarse
- cn04-2fe56bfb -> exact_graph_to_coarse

R305 freezes those exact game/mode pairs before any p5-p9 staging. It fits only
p0-p4 and replays p5-p9. p10-p19 are forbidden. Because earlier project work has
already touched p5-p9 for these games, this is source-assisted public-development
stability evidence, not independent generalization, hidden/Kaggle evidence, or
whole-game policy proof.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=305
FROZEN={
    "cd82-fb555c5d":"exact_nodes_to_coarse",
    "cn04-2fe56bfb":"exact_graph_to_coarse",
}
BASELINE="coarse_to_coarse"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    by=defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by)!=set(FROZEN):
        raise SystemExit(f"exact frozen games required: {sorted(FROZEN)}; got {sorted(by)}")

    games={}
    pass_games=[]
    for g in sorted(FROZEN):
        ps=sorted(by[g],key=r246.pnum)
        nums=[r246.pnum(p) for p in ps]
        if nums!=list(range(10)):
            raise SystemExit(f"{g}: exact p0-p9 required, got {nums}")
        train_traces=[r278.annotated_rows([p]) for p in ps[:5]]
        replay=[r for p in ps[5:] for r in r278.annotated_rows([p])]

        mode=FROZEN[g]
        ctab,cfit=r304.fit(train_traces,mode)
        btab,bfit=r304.fit(train_traces,BASELINE)
        cand=r304.evaluate(replay,ctab,mode)
        base=r304.evaluate(replay,btab,BASELINE)

        # Source-assisted replay promotion is intentionally strict: zero wrong,
        # nonzero predictions, and strictly more correct predictions than the
        # coarse baseline on the same p5-p9 replay.
        gate=bool(
            int(cand.get("predictions",0))>0
            and int(cand.get("wrong",0))==0
            and int(cand.get("correct",0))>int(base.get("correct",0))
        )
        if gate: pass_games.append(g)
        games[g]={
            "frozen_mode":mode,
            "fit":cfit,
            "baseline_fit":bfit,
            "source_assisted_p5_p9":cand,
            "baseline_p5_p9":base,
            "gate_pass":gate,
        }

    verdict="SOURCE_ASSISTED_STABILITY_SIGNAL" if pass_games else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r305-subset2-frozen-asymmetric-replay/1",
      "rung":RUNG,
      "lineage":{
        "r304_run":35826885553,
        "r304_head":"1706acd2bee3387c95a50c71d5a21abaac4ffae1",
        "candidate_pairs_frozen_before_p5_p9":True,
      },
      "frozen_candidates":FROZEN,
      "protocol":{
        "selector":"R304 p0-p4 LOTO only",
        "fit":"p0-p4 only",
        "source_assisted_replay":"p5-p9 only",
        "p10_p19_staged_or_read":False,
        "p5_p9_updates_selector":False,
        "p5_p9_updates_model":False,
        "promotion_scope":"representation primitive only",
      },
      "games":games,
      "pass_games":pass_games,
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
    print(json.dumps({"verdict":verdict,"pass_games":pass_games,"games":games},sort_keys=True))

if __name__=="__main__":
    main()
