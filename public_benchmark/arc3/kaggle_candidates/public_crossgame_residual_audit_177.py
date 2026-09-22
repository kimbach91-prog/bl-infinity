#!/usr/bin/env python3
"""R177: broad public cross-game audit of the R175 best residual renderer.

Run patch_recent1_s2 unchanged across every pinned public event trace selected by
its workflow matrix. Each trace learns only from its own PRIOR history; no state
is transferred across players or games. The purpose is breadth/generalization
measurement, not tuning.

This remains source-assisted public replay. It is not hidden ARC-AGI-3
evaluation, not a Kaggle execution, and not a leaderboard score.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path

import public_executable_world_model_134 as base
import public_heldout_confidence_gate_176 as r176

RUNG=177
CANDIDATE=r176.CANDIDATE


def summarize(path:Path):
    rs=r176.records(base.load_events(path))
    c=Counter()
    per_action={}
    for r in rs:
        c["opportunities"]+=1
        c["exact" if r["correct"] else "wrong"]+=1
        c["near4"]+=int(r["cell_errors"]<=4)
        c["near16"]+=int(r["cell_errors"]<=16)
        c["cell_errors"]+=int(r["cell_errors"])
        a=per_action.setdefault(r["action"],Counter())
        a["opportunities"]+=1
        a["exact" if r["correct"] else "wrong"]+=1
        a["near4"]+=int(r["cell_errors"]<=4)
        a["near16"]+=int(r["cell_errors"]<=16)
        a["cell_errors"]+=int(r["cell_errors"])
    out={k:int(c[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    out["raw_accuracy"]=round(out["exact"]/out["opportunities"],6) if out["opportunities"] else None
    out["mean_cell_errors"]=round(out["cell_errors"]/out["opportunities"],3) if out["opportunities"] else None
    out["per_action"]={}
    for a,x in sorted(per_action.items()):
        d={k:int(x[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
        d["raw_accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
        out["per_action"][a]=d
    out["trace"]=path.name
    return out


def run(game:str,paths:list[Path]):
    parts=[summarize(p) for p in paths]
    agg=Counter()
    for p in parts:
        for k in ("opportunities","exact","wrong","near4","near16","cell_errors"):
            agg[k]+=int(p[k])
    d={k:int(agg[k]) for k in ("opportunities","exact","wrong","near4","near16","cell_errors")}
    d["raw_accuracy"]=round(d["exact"]/d["opportunities"],6) if d["opportunities"] else None
    d["mean_cell_errors"]=round(d["cell_errors"]/d["opportunities"],3) if d["opportunities"] else None
    return {
      "schema":"deus/arc3-public-crossgame-residual-audit/1",
      "rung":RUNG,
      "game":game,
      "candidate":CANDIDATE,
      "trace_count":len(parts),
      "aggregate":d,
      "per_trace":parts,
      "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
      "diagnostic_gate":"PUBLIC_GAME_AUDIT_COMPLETE",
      "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
      "truth":{"public_trace_only":True,"source_assisted_sequence_replay":True,"trace_local_prior_only_learning":True,"cross_trace_state_transfer":False,"current_prediction_uses_preaction_and_prior_history_only":True,"current_outcome_used_only_for_scoring_and_post_prediction_learning":True,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"gpu_execution":False,"kaggle_execution":False,"submission_quota_spent":False,"owner_score_claim":False},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--input",type=Path,action="append",default=[]);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    if not a.input:raise SystemExit("input required")
    d=run(a.game,a.input);s=json.dumps(d,indent=2,sort_keys=True)+"\n";print(json.dumps({"rung":RUNG,"game":a.game,"trace_count":d["trace_count"],"aggregate":d["aggregate"],"truth":"PUBLIC_SOURCE_ASSISTED_ONLY"},sort_keys=True))
    a.output.write_text(s,encoding="utf-8")


if __name__=="__main__":main()
