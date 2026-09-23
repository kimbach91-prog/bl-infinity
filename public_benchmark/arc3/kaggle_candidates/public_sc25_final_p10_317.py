#!/usr/bin/env python3
"""R317: clean final p10-p19 audit for frozen sc25 nested-regions expert.

Frozen lineage:
- R310 p0-p4 nested LOTO: regions 7/7 zero-wrong incremental exact frames.
- R311 selector/trust unchanged, p5-p9 source-assisted replay: 11/11 zero-wrong.

R317 rebuilds the exact baseline, nested trusted regions keys, and regions table
from p0-p4 ONLY, stages no p5-p9, and audits p10-p19 without updates or retune.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_sc25_nested_exactframe_loto_310 as r310

RUNG=317
GAME=r310.GAME
MODE="regions"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    tps=sorted(a.train,key=r246.pnum); eps=sorted(a.eval,key=r246.pnum)
    if not tps or any(r246.game_id(p)!=GAME for p in tps+eps): raise SystemExit("exact sc25 traces required")
    if [r246.pnum(p) for p in tps]!=list(range(5)): raise SystemExit("train must be p0-p4")
    if [r246.pnum(p) for p in eps]!=list(range(10,20)): raise SystemExit("eval must be p10-p19")

    train_traces=[r251.prepare_rows([p]) for p in tps]
    train=[r for tr in train_traces for r in tr]
    final=[r for p in eps for r in r251.prepare_rows([p])]

    trusted,nested=r310.nested_trusted(train_traces,MODE)
    exact=r310.fit_exact(train)
    tab=r310.fit_abs(train,MODE)
    val=r310.evaluate(final,exact,tab,trusted,MODE)
    gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
    verdict="FINAL_SC25_REGIONS_ZERO_WRONG" if gate else "NO_PROMOTION"

    out={
      "schema":"deus/arc3-r317-sc25-final-p10/1","rung":RUNG,"game":GAME,
      "lineage":{
        "r310_run":35828083267,
        "r311_run":35828299505,
        "mode_frozen_before_p5_p9":MODE,
        "nested_reliability_rule_frozen":True,
        "p5_p9_replay":"11/11 zero wrong"
      },
      "mechanism":{"mode":MODE,"nested_min_predictions":r310.MIN_NESTED_PRED,"nested_zero_wrong_required":True,"exact_baseline_precedence":True},
      "protocol":{
        "fit_and_trust":"p0-p4 only",
        "final_audit":"p10-p19 only",
        "p5_p9_staged_or_read_by_r317":False,
        "p10_p19_updates_selector":False,
        "p10_p19_updates_trust":False,
        "p10_p19_updates_model":False,
        "no_retune_after_final_audit":True
      },
      "trusted_keys":len(trusted),
      "nested_predictions":sum(v["predictions"] for v in nested.values()),
      "nested_wrong":sum(v["wrong"] for v in nested.values()),
      "final_p10_p19":val,"gate_pass":gate,"verdict":verdict,
      "truth":{
        "public_trace_only":True,"source_free_runtime_logic":True,
        "reused_public_development_final_audit":True,
        "independent_hidden_generalization_claim":False,
        "whole_game_policy_claim":False,"solver_promotion":False,
        "kaggle_execution":False,"competition_submission":False,
        "submission_quota_spent_by_r317":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"trusted_keys":len(trusted),"final":val},sort_keys=True))

if __name__=="__main__": main()
