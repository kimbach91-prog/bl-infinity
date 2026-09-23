#!/usr/bin/env python3
"""R309: source-assisted cd82 coarse action-canonical p10-p19 gate.

R307 p5-p9 replay showed the predeclared coarse_to_coarse action-canonical
representation at 255/255 correct while exact_nodes_to_coarse had 247/247.
R309 freezes coarse_to_coarse after that public-development observation, refits
on p0-p9, and evaluates p10-p19. This is explicitly source-assisted selector
development, not independent generalization.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_subset4_asymmetric_alias_loto_304 as r304

RUNG=309
GAME="cd82-fb555c5d"
MODE="coarse_to_coarse"
ALT="exact_nodes_to_coarse"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum); nums=[r246.pnum(p) for p in ps]
    if nums!=list(range(20)): raise SystemExit(f"exact p0-p19 required, got {nums}")
    fit=[r278.annotated_rows([p]) for p in ps[:10]]
    hold=[r for p in ps[10:] for r in r278.annotated_rows([p])]
    ctab,cfit=r304.fit(fit,MODE); atab,afit=r304.fit(fit,ALT)
    cand=r304.evaluate(hold,ctab,MODE); alt=r304.evaluate(hold,atab,ALT)
    passed=bool(cand.get("predictions",0)>0 and cand.get("wrong",0)==0 and cand.get("correct",0)>=alt.get("correct",0))
    verdict="SOURCE_ASSISTED_COARSE_ZERO_WRONG_SIGNAL" if passed else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r309-cd82-coarse-actioncanon-p10p19/1","rung":RUNG,"game":GAME,
      "selector":{"mode":MODE,"alternative":ALT,"selected_after_r307_p5_p9":True},
      "lineage":{"r304":"p0-p4 LOTO exact_nodes_to_coarse 139/139 vs coarse 163 correct/9 wrong","r307":"p5-p9 coarse 255/255; exact_nodes_to_coarse247/247; original asymmetric candidate not promoted"},
      "protocol":{"selector_source_assisted_by_p5_p9":True,"refit":"p0-p9","evaluation":"p10-p19 reused public development","p10_p19_updates_selector":False,"p10_p19_updates_representation":False,"p10_p19_updates_model":False,"promotion_scope":"source-assisted public representation signal only"},
      "candidate_fit":cfit,"alternative_fit":afit,"candidate":cand,"alternative":alt,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"selector_is_source_assisted":True,"reused_public_development_holdout":True,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r309":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"candidate":cand,"alternative":alt},sort_keys=True))
if __name__=="__main__": main()
