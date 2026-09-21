#!/usr/bin/env python3
"""Rung 154: coarsened, reliability-gated temporal residual state machine.

Rung153 established that temporal placement transforms can be predicted with zero
observed errors on p11, but its keys were too specific to recur on p0/p10. This is a
representation repair, not a retry: coarsen the temporal state to action + predicted
semantic + recent semantic phase and optional previous placement velocity, while
requiring prior transform support before emitting a prediction.

Prediction remains strictly prequential. Current residual target is revealed only
after the prediction decision is locked. Current outcome is still used to isolate
and score the residual, so this remains public/source-assisted diagnostic evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_residual_history_state_machine_audit_153 as r153
import public_residual_placement_reconstruction_audit_150 as r150

RUNG = 154
MIN_SUPPORT = 2


def reliable(counter: Counter[str]) -> str | None:
    if len(counter) != 1:
        return None
    value, n = next(iter(counter.items()))
    return value if n >= MIN_SUPPORT else None


def coarse_motion(prev2, prev1) -> list[int] | None:
    m = r153.prev_motion(prev2, prev1)
    if m is None:
        return None
    def q(x: int) -> int:
        return -1 if x < 0 else (1 if x > 0 else 0)
    return [q(m[0]), q(m[1])]


def keys_for(action: str, sem: str, p2sem: str, p1sem: str, prev2, prev1) -> dict[str, str]:
    motion = coarse_motion(prev2, prev1)
    return {
        "action_sem_prev1sem": base.stable({"a": action, "sem": sem, "p1": p1sem}),
        "action_sem_phase2": base.stable({"a": action, "sem": sem, "p2": p2sem, "p1": p1sem}),
        "action_sem_prev1sem_motion_sign": base.stable({"a": action, "sem": sem, "p1": p1sem, "m": motion}),
        "action_sem_phase2_motion_sign": base.stable({"a": action, "sem": sem, "p2": p2sem, "p1": p1sem, "m": motion}),
    }

REPS = tuple(keys_for("RIGHT", "x", "y", "z", [(0,0,0,0)], [(0,0,0,0)]).keys())


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_bank: dict[str, Counter[str]] = defaultdict(Counter)
    transform_banks: dict[str, dict[str, Counter[str]]] = {r: defaultdict(Counter) for r in REPS}
    stats = {r: {
        "semantic_predictions": 0, "semantic_correct": 0, "semantic_wrong": 0,
        "placement_predictions": 0, "placement_correct": 0, "placement_wrong": 0,
        "placement_unseen_or_low_support": 0, "placement_conflict": 0, "placement_invalid_apply": 0,
    } for r in REPS}
    eligible = 0
    prev2_sem = prev1_sem = None
    prev2_edits = prev1_edits = None
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e; continue
        before = base.as_grid(pre["board"]); after = base.as_grid(e["board"]); action = base.action_name(e); pre = e
        detail = r150.residual_edits(before, after, action)
        if detail is None:
            continue
        edits, target_sem = detail; eligible += 1
        ctx = r153.semantic_context(before, action, prev2_sem, prev1_sem)
        sem_pred = r153.unique(semantic_bank[ctx]) if ctx is not None and ctx in semantic_bank else None
        history_ready = sem_pred is not None and prev2_sem is not None and prev1_sem is not None and prev2_edits is not None and prev1_edits is not None

        if history_ready:
            ks = keys_for(action, sem_pred, prev2_sem, prev1_sem, prev2_edits, prev1_edits)
            for rep in REPS:
                s = stats[rep]
                s["semantic_predictions"] += 1
                if sem_pred == target_sem: s["semantic_correct"] += 1
                else: s["semantic_wrong"] += 1
                counter = transform_banks[rep].get(ks[rep])
                if not counter:
                    s["placement_unseen_or_low_support"] += 1; continue
                pred_t = reliable(counter)
                if pred_t is None:
                    if len(counter) > 1: s["placement_conflict"] += 1
                    else: s["placement_unseen_or_low_support"] += 1
                    continue
                pred = r153.apply_transform(before, prev1_edits, pred_t)
                if pred is None:
                    s["placement_invalid_apply"] += 1; continue
                s["placement_predictions"] += 1
                if pred == sorted(edits): s["placement_correct"] += 1
                else: s["placement_wrong"] += 1

        if ctx is not None:
            semantic_bank[ctx][target_sem] += 1
        if prev2_sem is not None and prev1_sem is not None and prev2_edits is not None and prev1_edits is not None:
            true_keys = keys_for(action, target_sem, prev2_sem, prev1_sem, prev2_edits, prev1_edits)
            true_t = r153.transform_from_prev(prev1_edits, edits)
            for rep in REPS:
                transform_banks[rep][true_keys[rep]][true_t] += 1
        prev2_sem, prev1_sem = prev1_sem, target_sem
        prev2_edits, prev1_edits = prev1_edits, edits

    for rep, s in stats.items():
        s["semantic_accuracy"] = round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None
        s["placement_accuracy"] = round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None
        s["placement_coverage_of_eligible"] = round(s["placement_predictions"] / eligible, 6) if eligible else 0.0
        s["strict_zero_error_placement"] = bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0)
        s["transform_contexts_final"] = len(transform_banks[rep])
        s["transform_conflicted_contexts_final"] = sum(len(c) > 1 for c in transform_banks[rep].values())
    return {"eligible_transitions": eligible, "representations": stats}


def aggregate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = sum(p["eligible_transitions"] for p in parts); out = {}; hard = []
    for rep in REPS:
        keys = ("semantic_predictions","semantic_correct","semantic_wrong","placement_predictions","placement_correct","placement_wrong","placement_unseen_or_low_support","placement_conflict","placement_invalid_apply")
        s = {k: sum(p["representations"][rep][k] for p in parts) for k in keys}
        pp = [p["representations"][rep]["placement_predictions"] for p in parts]
        pc = [p["representations"][rep]["placement_correct"] for p in parts]
        pw = [p["representations"][rep]["placement_wrong"] for p in parts]
        sw = [p["representations"][rep]["semantic_wrong"] for p in parts]
        s.update({
            "semantic_accuracy": round(s["semantic_correct"] / s["semantic_predictions"], 6) if s["semantic_predictions"] else None,
            "placement_accuracy": round(s["placement_correct"] / s["placement_predictions"], 6) if s["placement_predictions"] else None,
            "placement_coverage_of_eligible": round(s["placement_predictions"] / eligible, 6) if eligible else 0.0,
            "strict_zero_error_placement": bool(s["placement_predictions"] and s["placement_wrong"] == 0 and s["semantic_wrong"] == 0),
            "per_trace_placement_predictions": pp, "per_trace_placement_correct": pc,
            "per_trace_placement_wrong": pw, "per_trace_semantic_wrong": sw,
        })
        out[rep] = s
        if len(pp) >= 2 and pp[0] > 0 and pp[1] > 0 and pw[0] == 0 and pw[1] == 0 and sw[0] == 0 and sw[1] == 0:
            hard.append((pp[0] + pp[1], rep))
    return {"trace_count": len(parts), "eligible_transitions": eligible, "representations": out, "best_zero_error_p0_p10_coarse_history": max(hard)[1] if hard else None, "per_trace": parts}


def run(paths: list[Path]) -> dict[str, Any]:
    parts=[]; traces=[]
    for p in paths:
        a=audit_trace(base.load_events(p)); parts.append(a); traces.append({"path":str(p),"audit":a})
    return {
        "schema":"deus/arc3-public-residual-coarse-history-state-machine-audit/1","rung":RUNG,
        "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_COARSE_GLOBAL_HISTORY_RESIDUAL_STATE_MACHINE_DIAGNOSTIC",
        "representation_change_from_rung153":{"changed":True,"change":"coarsen temporal keys that were all unseen on p0/p10 and require at least two identical prior transforms before prediction"},
        "parameters":{"min_support":MIN_SUPPORT},
        "source_grounding":{"public_trace_repo":base.TUFA_REPO,"public_trace_commit":base.TUFA_COMMIT,"clean_room_implementation":True},
        "traces":traces,"aggregate":aggregate(parts),"diagnostic_gate":"COARSE_GLOBAL_HISTORY_RESIDUAL_STATE_MACHINE_CHARACTERIZED",
        "promotion":{"candidate_model_promotion":False,"kaggle_packaging":False},
        "truth":{"public_trace_only":True,"source_assisted_replay":True,"diagnostic_only":True,"current_preaction_and_past_history_only_for_prediction":True,"current_targets_ingested_after_prediction":True,"current_outcome_used_for_residual_isolation_and_scoring":True,"hard_trace_gate_requires_p0_and_p10_nonzero_zero_error_coverage":True,"full_frame_prediction_claim":False,"independent_generalization_claim":False,"solver_behavior_gain_claim":False,"model_execution":False,"gpu_execution":False,"kaggle_execution":False,"kaggle_submission_attempted":False,"submission_quota_spent":False,"leaderboard_score_claim":False,"owner_score_claim":False}
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); args=ap.parse_args()
    if not args.input: raise SystemExit("at least one --input is required")
    d=run(args.input); text=json.dumps(d,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.write_text(text,encoding="utf-8")
    print(text,end=""); return 0
if __name__=="__main__": raise SystemExit(main())
