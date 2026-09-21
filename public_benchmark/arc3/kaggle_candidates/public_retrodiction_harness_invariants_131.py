#!/usr/bin/env python3
"""Rung 131: CPU-verifiable clean-room retrodiction harness invariants.

This rung does not call an LLM or Kaggle. It implements only a generic verifier:
a proposed deterministic visible-state transition hypothesis may be promoted by the
harness only if it retrodicts the complete recorded history exactly. The harness also
flags observational aliasing when the same visible state + action has multiple observed
next states, because a visible-only deterministic hypothesis is then underspecified.

Architecture motivation is source-level only: ARC Prize's public community leaderboard
summarizes Retrodict as recording frames and checking hypotheses against history. No
upstream implementation is imported or copied.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

RUNG = 131
Grid = list[list[int]]
Transition = dict[str, Any]


def stable(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(x: Any) -> str:
    return hashlib.sha256(stable(x).encode("utf-8")).hexdigest()


def key(state: Grid, action: str) -> str:
    return digest({"state": state, "action": action})


def move_right(state: Grid, action: str) -> Grid:
    out = copy.deepcopy(state)
    if action != "RIGHT":
        return out
    coords = [(x, y) for y, row in enumerate(state) for x, v in enumerate(row) if v == 1]
    if len(coords) != 1:
        return out
    x, y = coords[0]
    if x + 1 >= len(state[y]) or state[y][x + 1] != 0:
        return out
    out[y][x] = 0
    out[y][x + 1] = 1
    return out


def noop(state: Grid, action: str) -> Grid:
    return copy.deepcopy(state)


def replay(history: list[Transition], hypothesis: Callable[[Grid, str], Grid]) -> dict[str, Any]:
    contradictions: list[dict[str, Any]] = []
    for i, t in enumerate(history):
        predicted = hypothesis(t["state"], t["action"])
        if predicted != t["next_state"]:
            contradictions.append({
                "index": i,
                "transition_id": t["id"],
                "expected_digest": digest(t["next_state"]),
                "predicted_digest": digest(predicted),
            })
    return {
        "history_len": len(history),
        "matched": len(history) - len(contradictions),
        "contradictions": contradictions,
        "accept": len(history) > 0 and not contradictions,
    }


def aliasing(history: list[Transition]) -> dict[str, Any]:
    seen: dict[str, set[str]] = {}
    ids: dict[str, list[str]] = {}
    for t in history:
        k = key(t["state"], t["action"])
        seen.setdefault(k, set()).add(digest(t["next_state"]))
        ids.setdefault(k, []).append(t["id"])
    conflicts = [
        {"visible_state_action_digest": k, "distinct_next_states": len(v), "transition_ids": ids[k]}
        for k, v in sorted(seen.items()) if len(v) > 1
    ]
    return {
        "conflict_count": len(conflicts),
        "visible_only_deterministic_model_identifiable": len(conflicts) == 0,
        "conflicts": conflicts,
    }


def lookup_hypothesis(mapping: dict[str, Grid]) -> Callable[[Grid, str], Grid]:
    def h(state: Grid, action: str) -> Grid:
        return copy.deepcopy(mapping.get(key(state, action), state))
    return h


def base_history() -> list[Transition]:
    states = [
        [[1,0,0,0],[0,0,0,0]],
        [[0,1,0,0],[0,0,0,0]],
        [[0,0,1,0],[0,0,0,0]],
        [[0,0,0,1],[0,0,0,0]],
    ]
    return [
        {"id": f"t{i}", "state": states[i], "action": "RIGHT", "next_state": states[i+1]}
        for i in range(3)
    ]


def mutation_suite(history: list[Transition]) -> dict[str, Any]:
    # Correct hypothesis must fail every trace whose recorded outcome is corrupted once.
    rejected = 0
    cases: list[dict[str, Any]] = []
    for i in range(len(history)):
        mutant = copy.deepcopy(history)
        mutant[i]["next_state"] = copy.deepcopy(mutant[i]["state"])
        verdict = replay(mutant, move_right)
        cases.append({"mutated_index": i, "accept": verdict["accept"], "contradictions": len(verdict["contradictions"])})
        rejected += int(not verdict["accept"])
    return {"cases": cases, "rejected": rejected, "total": len(cases), "all_rejected": rejected == len(cases)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, default=Path("public-retrodiction-harness-invariants-131.json"))
    args = ap.parse_args()

    history = base_history()
    correct = replay(history, move_right)
    wrong = replay(history, noop)

    last = history[-1]
    last_only = lookup_hypothesis({key(last["state"], last["action"]): last["next_state"]})
    last_only_full = replay(history, last_only)
    last_only_suffix = replay([last], last_only)

    ambiguous = copy.deepcopy(history[:1])
    conflict = copy.deepcopy(history[0])
    conflict["id"] = "t0-conflict"
    conflict["next_state"] = [[1,0,0,0],[0,0,0,0]]
    ambiguous.append(conflict)
    ambiguity = aliasing(ambiguous)

    mutations = mutation_suite(history)

    invariants = {
        "correct_full_history_accepts": correct["accept"] is True,
        "wrong_hypothesis_rejected": wrong["accept"] is False,
        "suffix_fit_does_not_override_full_history": last_only_suffix["accept"] is True and last_only_full["accept"] is False,
        "observational_aliasing_detected": ambiguity["conflict_count"] == 1 and ambiguity["visible_only_deterministic_model_identifiable"] is False,
        "single_outcome_mutations_rejected": mutations["all_rejected"] is True,
    }
    all_pass = all(invariants.values())

    receipt = {
        "schema": "deus/arc3-public-retrodiction-harness-invariants/1",
        "rung": RUNG,
        "execution_class": "CPU_DETERMINISTIC_HARNESS_ONLY",
        "source_grounding": {
            "clean_room_implementation": True,
            "upstream_code_imported": False,
            "upstream_code_copied": False,
            "official_arc_community_leaderboard": "https://arcprize.org/leaderboard/community",
            "public_retrodict_repo": "https://github.com/EtchingShin/Retrodict",
            "principle_only": "record observed history and reject hypotheses contradicted by any recorded transition",
        },
        "history_digest": digest(history),
        "tests": {
            "correct": correct,
            "wrong": wrong,
            "last_only_suffix": last_only_suffix,
            "last_only_full": last_only_full,
            "ambiguity": ambiguity,
            "mutations": mutations,
        },
        "invariants": invariants,
        "all_invariants_pass": all_pass,
        "promotion_gate": "HARNESS_INVARIANTS_VERIFIED" if all_pass else "HARNESS_INVARIANTS_FAILED",
        "truth": {
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "public_game_execution": False,
            "kaggle_data_read": False,
            "kaggle_execution": False,
            "kaggle_output_claim": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
            "independent_generalization_claim": False,
            "award_or_settlement_claim": False,
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"promotion_gate": receipt["promotion_gate"], "invariants": invariants, "truth": receipt["truth"]}, indent=2, sort_keys=True))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
