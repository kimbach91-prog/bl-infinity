#!/usr/bin/env python3
"""R316: frozen DC22 phase representation final audit on public p10-p19.

The phase representation was selected on R314 p0-p4 and passed R315 p5-p9
without any selector/representation update. Rules remain fit only on p0-p4.
This script evaluates p10-p19 once, with no retuning on final-audit data.
It is public-offline evidence, not Kaggle/hidden execution or a whole-game solver.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314

RUNG=316
GAME="dc22-fdcac232"
MODE="phase"
WORKFLOW_TRIGGER_REVISION=1


def _exact(paths,nums,label):
    ps=sorted(paths,key=r246.pnum)
    got=[r246.pnum(p) for p in ps]
    want=list(nums)
    if got!=want: raise SystemExit(f"{label}: exact pnums required {want}, got {got}")
    if any(r246.game_id(p)!=GAME for p in ps): raise SystemExit(f"{label}: exact game required")
    return ps


def _sum_eval(evals):
    total=Counter()
    for ev in evals:
        for k,v in ev.items():
            if isinstance(v,int): total[k]+=v
    total["pixel_gain"]=total["identity_errors"]-total["candidate_errors"]
    total["exact_frame_gain"]=total["candidate_exact_frames"]-total["identity_exact_frames"]
    return dict(total)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--train",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    train_ps=_exact(a.train,range(5),"train")
    eval_ps=_exact(a.eval,range(10,20),"eval")

    train_traces=[r302.augment_trace(p) for p in train_ps]
    eval_traces=[r302.augment_trace(p) for p in eval_ps]
    prepared_train=[r314._prepare_trace(tr,MODE) for tr in train_traces]
    rules,fit=r314._fit_rules(prepared_train)
    evals=[]
    for tr in eval_traces:
        evals.append(r314._evaluate(r314._prepare_trace(tr,MODE),rules))
    total=_sum_eval(evals)

    if total.get("predicted_changes",0)>0 and total.get("false_changes",0)==0 and total.get("pixel_gain",0)>0:
        verdict="FINAL_ZERO_FALSE_SIGNAL"
    elif total.get("pixel_gain",0)>0:
        verdict="FINAL_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict="FINAL_NO_SIGNAL"

    out={
      "schema":"deus/arc3-r316-dc22-phase-frozen-p10p19/1",
      "rung":RUNG,"game":GAME,"mode":MODE,
      "lineage":{"r314":"phase selected on p0-p4 LOTO","r315":"p5-p9 zero-false gate only; no selector/representation update","execution_representation":"row_world_key_cache_v2"},
      "protocol":{"fit":"public p0-p4 all five traces","evaluation":"public p10-p19 one-shot frozen final audit","p5_p9_staged_or_read":False,"selector_or_representation_updates_after_final_read":False,"promotion_in_r316":False},
      "fit":fit,"eval_by_trace":evals,"eval_total":total,"verdict":verdict,
      "truth":{"public_trace_only":True,"source_free_runtime_logic":True,"p5_p9_read_in_r316":False,"p10_p19_read":True,"frozen_final_audit":True,"retuned_on_final":False,"independent_hidden_generalization_claim":False,"whole_game_solver_claim":False,"solver_promotion":False,"kaggle_execution":False,"competition_submission":False,"submission_quota_spent_by_r316":False}
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"game":GAME,"mode":MODE,"verdict":verdict,"eval_total":total},sort_keys=True))

if __name__=="__main__": main()
