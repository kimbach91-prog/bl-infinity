#!/usr/bin/env python3
"""R313: frozen source-assisted replay for the R309 cd82 selective backoff.

R309 p0-p4 outer LOTO, after a harness-only trace-group repair, verified:
  exact_nodes_to_coarse: 139/139 zero wrong
  exact + nested-trusted coarse backoff: 141/141 zero wrong
R313 freezes the exact precedence and nested reliability rule before p5-p9.
Trusted coarse keys and both tables are rebuilt from p0-p4 only, then p5-p9 is
replayed source-assisted. p10-p19 are forbidden.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_cd82_selective_backoff_loto_309 as r309

RUNG=313
GAME=r309.GAME


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    by=defaultdict(list)
    for p in a.input: by[r246.game_id(p)].append(p)
    if set(by)!={GAME}: raise SystemExit(f"exact {GAME} required, got {sorted(by)}")
    ps=sorted(by[GAME],key=r246.pnum)
    if [r246.pnum(p) for p in ps]!=list(range(10)): raise SystemExit("exact p0-p9 required")

    train_traces=[r278.annotated_rows([p]) for p in ps[:5]]
    train=[r for tr in train_traces for r in tr]
    replay=[r for p in ps[5:] for r in r278.annotated_rows([p])]

    trusted,nested=r309.nested_trust(train_traces)
    etab,efit=r309.fit_raw(train,r309.EXACT)
    ctab,cfit=r309.fit_raw(train,r309.COARSE)
    exact,ensemble=r309.eval_outer(replay,etab,ctab,trusted)

    gate=bool(ensemble.get("predictions",0)>0 and ensemble.get("wrong",0)==0 and ensemble.get("correct",0)>=exact.get("correct",0))
    verdict="SOURCE_ASSISTED_SELECTIVE_BACKOFF_ZERO_WRONG" if gate else "NO_PROMOTION"
    out={
      "schema":"deus/arc3-r313-cd82-frozen-selective-replay/1","rung":RUNG,"game":GAME,
      "lineage":{"r309_run":35828232358,"r309_head":"b8e41b58e4e68735db8baa232bbd675c565e31b0","mechanism_frozen_before_p5_p9":True},
      "mechanism":{"precedence":r309.EXACT,"backoff":r309.COARSE,"nested_min_predictions":r309.MIN_NESTED_PRED,"nested_zero_wrong_required":True},
      "protocol":{"fit_and_trust":"p0-p4 only","source_assisted_replay":"p5-p9 only","p10_p19_staged_or_read":False,"p5_p9_updates_trust":False,"p5_p9_updates_model":False,"promotion_scope":"coarse representation transition primitive only"},
      "trusted_coarse_keys":len(trusted),
      "nested_predictions":sum(v["predictions"] for v in nested.values()),
      "nested_wrong":sum(v["wrong"] for v in nested.values()),
      "exact_fit":efit,"coarse_fit":cfit,
      "exact_only_p5_p9":exact,"ensemble_p5_p9":ensemble,
      "gate_pass":gate,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_replay_is_source_assisted":True,"p10_p19_read":False,"independent_hidden_generalization_claim":False,"whole_game_policy_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r313":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"trusted_coarse_keys":len(trusted),"exact_only":exact,"ensemble":ensemble},sort_keys=True))

if __name__=="__main__": main()
