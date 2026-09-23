#!/usr/bin/env python3
"""R316: clean final p10-p19 audit for frozen cd82 selective backoff.

Frozen lineage:
- R304 p0-p4 LOTO: exact_nodes_to_coarse = 139/139 zero wrong.
- R309 repaired p0-p4 nested selective backoff = 141/141 zero wrong.
- R313 source-assisted p5-p9 replay = ensemble 259/259 zero wrong.

R316 rebuilds the exact route, nested-trusted coarse keys, and both transition
tables from p0-p4 ONLY. It does not stage p5-p9. The final p10-p19 audit cannot
update selector, trust, representation, or model.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_cd82_selective_backoff_loto_309 as r309

RUNG=316
GAME=r309.GAME


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    tps=sorted(a.train,key=r246.pnum); eps=sorted(a.eval,key=r246.pnum)
    if not tps or any(r246.game_id(p)!=GAME for p in tps+eps):
        raise SystemExit("exact cd82 traces required")
    if [r246.pnum(p) for p in tps]!=list(range(5)): raise SystemExit("train must be p0-p4")
    if [r246.pnum(p) for p in eps]!=list(range(10,20)): raise SystemExit("eval must be p10-p19")

    train_traces=[r278.annotated_rows([p]) for p in tps]
    train=[r for tr in train_traces for r in tr]
    final=[r for p in eps for r in r278.annotated_rows([p])]

    trusted,nested=r309.nested_trust(train_traces)
    etab,efit=r309.fit_raw(train,r309.EXACT)
    ctab,cfit=r309.fit_raw(train,r309.COARSE)
    exact,ensemble=r309.eval_outer(final,etab,ctab,trusted)

    gate=bool(
        ensemble.get("predictions",0)>0
        and ensemble.get("wrong",0)==0
        and ensemble.get("correct",0)>=exact.get("correct",0)
    )
    verdict="FINAL_CD82_SELECTIVE_BACKOFF_ZERO_WRONG" if gate else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r316-cd82-final-p10/1","rung":RUNG,"game":GAME,
      "lineage":{
        "r309_run":35828232358,
        "r313_run":35828457543,
        "mechanism_frozen_before_p5_p9":True,
        "p5_p9_replay":"ensemble 259/259 zero wrong"
      },
      "mechanism":{
        "precedence":r309.EXACT,
        "backoff":r309.COARSE,
        "nested_min_predictions":r309.MIN_NESTED_PRED,
        "nested_zero_wrong_required":True
      },
      "protocol":{
        "fit_and_trust":"p0-p4 only",
        "final_audit":"p10-p19 only",
        "p5_p9_staged_or_read_by_r316":False,
        "p10_p19_updates_selector":False,
        "p10_p19_updates_trust":False,
        "p10_p19_updates_model":False,
        "no_retune_after_final_audit":True
      },
      "trusted_coarse_keys":len(trusted),
      "nested_predictions":sum(v["predictions"] for v in nested.values()),
      "nested_wrong":sum(v["wrong"] for v in nested.values()),
      "exact_fit":efit,"coarse_fit":cfit,
      "exact_only_final":exact,"ensemble_final":ensemble,
      "gate_pass":gate,"verdict":verdict,
      "truth":{
        "public_trace_only":True,"source_free_runtime_logic":True,
        "reused_public_development_final_audit":True,
        "independent_hidden_generalization_claim":False,
        "whole_game_policy_claim":False,"solver_promotion":False,
        "kaggle_execution":False,"competition_submission":False,
        "submission_quota_spent_by_r316":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"trusted_coarse_keys":len(trusted),"exact_only":exact,"ensemble":ensemble},sort_keys=True))

if __name__=="__main__": main()
