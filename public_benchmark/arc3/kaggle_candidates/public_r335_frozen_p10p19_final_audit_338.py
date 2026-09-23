#!/usr/bin/env python3
"""R338: one-shot no-retune source-free p10-p19 final public audit for frozen R336/R335.

Fit uses exact public p0-p4 only. Evaluation uses exact p10-p19 only.
The parser, representation, action learner, support threshold, and ambiguity policy
are imported unchanged from the frozen R336 semantic-equivalence candidate.
Public p5-p9 are intentionally not staged or read by this audit.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path

import public_r335_sourcefree_p0p4_falsifier_336 as r336
import public_sourcefree_markov_fidelity_adapter_246 as r246

SCHEMA="deus/arc3-r338-r335-frozen-p10p19-final-audit/1"
IDEMPOTENCY="R338-R335-FROZEN-P10P19-20260923-001"

def _ordered(paths, expected):
    ps=sorted(paths,key=r246.pnum)
    got=[r246.pnum(p) for p in ps]
    if got!=list(expected):
        raise SystemExit(f"expected traces {list(expected)}, got {got}")
    return ps

def evaluate(fit_paths, eval_paths):
    fit=_ordered(fit_paths, range(5))
    eva=_ordered(eval_paths, range(10,20))

    train=[row for p in fit for row in r336.event_rows(p)]
    edit_map,move_map,fitstats=r336.fit_model(train)

    total=Counter()
    bytrace=[]
    for p in eva:
        tm=Counter()
        for row in r336.event_rows(p):
            if row["before"] is not None:
                tm["parsed_before"]+=1
            if row["after"] is not None:
                tm["parsed_after"]+=1
                if row["after"]["answer"]==row["after"]["target"]:
                    tm["target_match_after"]+=1
                    if (
                        row["reward"]>0
                        or row["level_after"]>row["level_before"]
                        or "FINISHED" in row["state_after"].upper()
                    ):
                        tm["target_match_reward_or_level"]+=1

            pred=r336.predict(row,edit_map,move_map)
            if pred is None:
                tm["abstain"]+=1
            else:
                tm["predicted"]+=1
                if pred==r336.actual_tuple(row["after"]):
                    tm["correct"]+=1
                else:
                    tm["wrong"]+=1

        bytrace.append({"trace":r246.pnum(p),"metrics":dict(tm)})
        for k,v in tm.items():
            total[k]+=v

    if total["predicted"]>0 and total["wrong"]==0:
        verdict="FROZEN_P10P19_SOURCEFREE_ZERO_WRONG"
    elif total["wrong"]>0:
        verdict="FROZEN_P10P19_SOURCEFREE_FALSIFIED"
    else:
        verdict="FROZEN_P10P19_SOURCEFREE_NO_SIGNAL"

    return {
        "schema":SCHEMA,
        "idempotency_key":IDEMPOTENCY,
        "protocol":{
            "fit":"public p0-p4 only",
            "eval":"public p10-p19 only",
            "candidate_semantics":"frozen R336/R335 semantic-equivalence",
            "retuning_after_eval":False,
            "game_id_branching":False,
            "ambiguity_policy":"abstain",
            "p5_p9_staged_or_read":False,
            "one_shot_final_public_audit":True,
        },
        "fit":{"edit_rules":len(edit_map),"move_rules":len(move_map),**fitstats},
        "metrics":dict(total),
        "by_trace":bytrace,
        "verdict":verdict,
        "truth":{
            "source_free_runtime_logic":True,
            "public_offline_only":True,
            "game_source_read":False,
            "independent_hidden_generalization_claim":False,
            "provider_execution":False,
            "kaggle_submission":False,
            "whole_game_solver_promotion":False,
            "candidate_mutated_after_final_audit":False,
        },
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fit",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    d=evaluate(a.fit,a.eval)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":d["verdict"],
        "fit":d["fit"],
        "metrics":d["metrics"],
        "by_trace":d["by_trace"],
    },sort_keys=True))

if __name__=="__main__":
    main()
