#!/usr/bin/env python3
"""R181M worker: evaluate one frozen R180 pipeline trajectory.

Imports the frozen per-trajectory evaluator from R181. This worker exists only
to parallelize the same R181 heldout stress; it does not change architecture.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import public_executable_world_model_134 as base
import public_ar25_all20_frozen_pipeline_181 as r181

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    pid=r181.path_id(a.input)
    d=r181.audit_trace(base.load_events(a.input))
    d.update({
        "schema":"deus/arc3-ar25-r181m-path/1",
        "rung":"181M",
        "path":pid,
        "file":a.input.name,
        "split":"selection" if pid in r181.SELECTION_PATHS else "heldout_same_game",
        "truth":{
            "architecture_frozen_from_r180":True,
            "preaction_prior_history_only":True,
            "current_outcome_postscore_learning_only":True,
            "kaggle_execution":False,
            "submission_quota_spent":False
        }
    })
    s=json.dumps(d,indent=2,sort_keys=True)+"\n"
    print(s,end="")
    a.output.write_text(s,encoding="utf-8")
if __name__=="__main__":
    main()
