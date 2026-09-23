#!/usr/bin/env python3
"""R311: frozen source-assisted p5-p9 replay for the R310 sc25 regions signal.

R310 used p0-p4 outer LOTO with a nested training-only per-key reliability gate
and found regions = 7/7 zero-wrong incremental exact-frame predictions.
R311 freezes:
  mode=regions
  nested per-key trust: >=2 nested predictions, zero nested wrong
before staging p5-p9. It rebuilds trusted keys using p0-p4 only, refits the
regions->exact-next-frame table on p0-p4, gives exact baseline precedence, and
replays p5-p9. p10-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_sc25_nested_exactframe_loto_310 as r310

RUNG=311
GAME="sc25-635fd71a"
MODE="regions"


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit("exact p0-p9 required")

    train_traces=[r251.prepare_rows([p]) for p in ps[:5]]
    train=[r for tr in train_traces for r in tr]
    replay=[r for p in ps[5:] for r in r251.prepare_rows([p])]

    trusted,nested=r310.nested_trusted(train_traces,MODE)
    exact=r310.fit_exact(train)
    tab=r310.fit_abs(train,MODE)
    val=r310.evaluate(replay,exact,tab,trusted,MODE)
    gate=bool(val.get("candidate_predictions",0)>0 and val.get("candidate_wrong",0)==0 and val.get("candidate_correct",0)>0)
    verdict="SOURCE_ASSISTED_REGIONS_ZERO_WRONG_SIGNAL" if gate else "NO_PROMOTION"

    out={
      "schema":"deus/arc3-r311-sc25-frozen-regions-replay/1","rung":RUNG,"game":GAME,
      "lineage":{"r310_run":35828083267,"r310_head":"f8c4d3d41497cce36f1302510b529ceb8b0ee514","mode_frozen_before_p5_p9":MODE,"nested_reliability_rule_frozen":True},
      "mechanism":{"mode":MODE,"nested_min_predictions":r310.MIN_NESTED_PRED,"nested_zero_wrong_required":True,"exact_baseline_precedence":True},
      "protocol":{"fit_and_trust":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"p5_p9_updates_trust":False,"p5_p9_updates_model":False,"promotion_scope":"exact-frame residual primitive only"},
      "trusted_keys":len(trusted),
      "nested_predictions":sum(v["predictions"] for v in nested.values()),
      "nested_wrong":sum(v["wrong"] for v in nested.values()),
      "source_assisted_p5_p9":val,"gate_pass":gate,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r311":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"trusted_keys":len(trusted),"source_assisted_p5_p9":val},sort_keys=True))

if __name__=="__main__": main()
