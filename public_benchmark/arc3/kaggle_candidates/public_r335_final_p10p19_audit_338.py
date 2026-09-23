#!/usr/bin/env python3
"""R338: one-shot final public audit for frozen R336/R335 semantic-equivalence candidate.

Fit: exact public p0-p4 only.
Final audit: exact public p10-p19 only.
p5-p9 are NOT staged/read by this audit and cannot affect fitting.
Candidate parser/representation/action learner are imported unchanged from frozen R336.
Any wrong prediction closes this frozen candidate; no post-audit retuning is permitted.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
import public_r335_sourcefree_p0p4_falsifier_336 as r336
import public_sourcefree_markov_fidelity_adapter_246 as r246

SCHEMA="deus/arc3-r338-r335-final-p10p19-audit/1"
IDEMPOTENCY="R338-R335-FINAL-P10P19-20260923-001"

def ordered(paths, expected):
    ps=sorted(paths,key=r246.pnum)
    got=[r246.pnum(p) for p in ps]
    if got!=list(expected):
        raise SystemExit(f"expected traces {list(expected)}, got {got}")
    return ps

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fit",type=Path,action="append",default=[])
    ap.add_argument("--eval",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    fit=ordered(a.fit, range(5))
    eva=ordered(a.eval, range(10,20))
    train=[row for p in fit for row in r336.event_rows(p)]
    edit_map,move_map,fitstats=r336.fit_model(train)

    total=Counter(); bytrace=[]
    for p in eva:
        m=Counter()
        for row in r336.event_rows(p):
            if row["before"] is not None: m["parsed_before"]+=1
            if row["after"] is not None:
                m["parsed_after"]+=1
                if row["after"]["answer"]==row["after"]["target"]:
                    m["target_match_after"]+=1
                    if row["reward"]>0 or row["level_after"]>row["level_before"] or "FINISHED" in row["state_after"].upper():
                        m["target_match_reward_or_level"]+=1
            pred=r336.predict(row,edit_map,move_map)
            if pred is None:
                m["abstain"]+=1
            else:
                m["predicted"]+=1
                if pred==r336.actual_tuple(row["after"]):
                    m["correct"]+=1
                else:
                    m["wrong"]+=1
        bytrace.append({"trace":r246.pnum(p),"metrics":dict(m)})
        for k,v in m.items(): total[k]+=v

    if total["predicted"]>0 and total["wrong"]==0:
        verdict="FINAL_PUBLIC_SOURCEFREE_ZERO_WRONG_PASS"
    elif total["wrong"]>0:
        verdict="FINAL_PUBLIC_SOURCEFREE_FALSIFIED"
    else:
        verdict="FINAL_PUBLIC_SOURCEFREE_NO_SIGNAL"

    out={
        "schema":SCHEMA,
        "idempotency_key":IDEMPOTENCY,
        "protocol":{
            "candidate":"frozen R336/R335 semantic-equivalence",
            "fit":"public p0-p4 only",
            "validation_prior":"R337 p5-p9 already executed separately; not read by this audit",
            "final_eval":"public p10-p19 one-shot",
            "retuning_after_final_audit":False,
            "game_id_branching":False,
            "ambiguity_policy":"abstain",
            "p5_p9_staged_or_read_by_this_audit":False,
        },
        "fit":{"edit_rules":len(edit_map),"move_rules":len(move_map),**fitstats},
        "metrics":dict(total),
        "by_trace":bytrace,
        "verdict":verdict,
        "truth":{
            "source_free_runtime_logic":True,
            "public_reused_development_final_audit":True,
            "independent_hidden_generalization_claim":False,
            "provider_execution":False,
            "kaggle_submission":False,
            "whole_game_solver_promotion":False,
            "post_audit_retune_allowed":False,
        }
    }
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":verdict,"fit":out["fit"],"metrics":dict(total),"by_trace":bytrace},sort_keys=True))

if __name__=="__main__":
    main()
