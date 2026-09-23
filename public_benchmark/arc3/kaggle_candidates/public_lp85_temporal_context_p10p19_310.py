#!/usr/bin/env python3
"""R310: frozen lp85 temporal-context p10-p19 public-development gate.

The exact mechanism ACTION_REGION4 + H3 stable period/velocity + exact base
pre-value guard was frozen before p5-p9 in source commit
f28dd34c1e787df90d77e06083a5063bbc453e7e.

R310 keeps that mechanism unchanged. R300 structural templates are fit on p0-p4
only. The frozen causal mechanism is replayed on p10-p19; history may update only
from earlier outcomes inside each evaluated trace. p5-p9 are not used for fitting
or changing the mechanism in this run.

Truth boundary: reused public-development evidence, source-assisted by the prior
decision to advance after p5-p9. Not independent hidden generalization, solver
promotion, Kaggle execution, submission, or score.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_lp85_seeded_structural_residual_gate_300 as r300
import public_lp85_temporal_residual_context_diag_302 as r302

TARGET_GAME="lp85-305b61c3"
CTX_MODE="ACTION_REGION4"
HISTORY_MODE="H3_STABLE_PERIOD_VELOCITY"
FREEZE_SOURCE="f28dd34c1e787df90d77e06083a5063bbc453e7e"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    tr=sorted(a.train,key=r246.pnum); ev=sorted(a.eval,key=r246.pnum)
    if [r246.pnum(p) for p in tr]!=list(range(5)):
        raise SystemExit("train must be exact p0-p4")
    if [r246.pnum(p) for p in ev]!=list(range(10,20)):
        raise SystemExit("eval must be exact p10-p19")
    if any(r246.game_id(p)!=TARGET_GAME for p in tr+ev):
        raise SystemExit("exact lp85 target required")

    train_traces=[r278.annotated_rows([p]) for p in tr]
    train_rows=[r for trace in train_traces for r in trace]
    templates,fit=r300.fit_templates(train_rows,train_traces)
    eval_traces=[r278.annotated_rows([p]) for p in ev]
    total,per=r302.run_mode(eval_traces,templates,CTX_MODE,HISTORY_MODE)

    pred=int(total.get("predicted_changes",0))
    false=int(total.get("false_changes",0))
    gain=int(total.get("error_reduction_vs_r300_base",0))
    exact=int(total.get("exact_frame_delta_vs_r300_base",0))
    if pred>0 and false==0 and gain>0:
        verdict="P10P19_FROZEN_CAUSAL_ZERO_FALSE_GAIN"
    elif gain>0:
        verdict="P10P19_FROZEN_CAUSAL_GAIN_UNSAFE"
    else:
        verdict="P10P19_FROZEN_CAUSAL_NO_SIGNAL"

    out={
      "schema":"deus/arc3-r310-lp85-temporal-context-p10p19/1",
      "rung":310,"game":TARGET_GAME,
      "frozen_mechanism":{
        "context":CTX_MODE,"history":HISTORY_MODE,
        "structural_fit_ps":[0,1,2,3,4],
        "freeze_source":FREEZE_SOURCE,
        "selection_changed_after_p5p9":False,
        "selection_changed_after_p10p19":False,
      },
      "lineage":{
        "cross_trace_p0p4_holdout_run":35827088771,
        "cross_trace_holdout_result":"1432 true changes / 0 false / +1432 error reduction / exact-frame delta0",
        "p5p9_replay_run":35827317202,
        "p5p9_result":"1652 true changes / 0 false / +1652 error reduction / exact-frame delta0",
      },
      "protocol":{
        "structural_fit":"p0-p4 only",
        "p5_p9_used_for_fit":False,
        "evaluation":"p10-p19 reused public development",
        "same_trace_past_outcome_adaptation":True,
        "p10_p19_updates_selector":False,
        "p10_p19_updates_mechanism":False,
        "promotion_scope":"causal residual primitive only",
      },
      "fit_gate":fit,"evaluation_total":total,"per_eval_trace":per,
      "delta":{"error_reduction_vs_r300_base":gain,"exact_frame_delta_vs_r300_base":exact},
      "verdict":verdict,
      "truth":{
        "public_trace_only":True,"source_assisted_progression":True,
        "reused_public_development_holdout":True,
        "independent_hidden_generalization_claim":False,
        "whole_game_policy_claim":False,"solver_promotion":False,
        "kaggle_execution":False,"competition_submission":False,
        "owner_score_claim":False,"submission_quota_spent_by_r310":False
      }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"evaluation_total":total,"delta":out["delta"]},sort_keys=True))

if __name__=="__main__": main()
