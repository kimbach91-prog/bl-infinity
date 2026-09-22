#!/usr/bin/env python3
"""R251: semantics-preserving performance repair of timed-out R247.

R247's representation was not falsified: GitHub cancelled it at its 45-minute
wallclock limit while recomputing the same six fit_lens tables once for every
action.  R251 keeps the exact R247 protocol and frozen boundary, but builds each
lens table once per game, partitions train/validation rows once by action, and
reuses those immutable objects.  No rule, threshold, selection signal, heldout
outcome, or score is changed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG = 251


def partition(rows):
    out = defaultdict(list)
    for row in rows:
        out[row["action"]].append(row)
    return out


def select_per_action(train, val):
    exact = r246.fit_exact(train)
    train_by_action = partition(train)
    val_by_action = partition(val)
    all_actions = sorted(set(train_by_action) | set(val_by_action))

    # R247 timeout repair: each expensive global lens table is identical for
    # every action, so compute it once and reuse it.
    lens_tabs = {name: r246.fit_lens(train, name) for name in r246.LENS_NAMES}
    selected = {}
    diagnostic = {}
    for action in all_actions:
        cand = {}
        action_train = train_by_action.get(action, [])
        action_val = val_by_action.get(action, [])
        for name in r246.LENS_NAMES:
            tab = lens_tabs[name]
            met = r246.eval_added(action_val, exact, tab, name)
            cand[name] = {
                "keys": len(tab),
                "fidelity": round(r246.markov_fidelity(action_train, name), 6),
                "validation": met,
            }
        zero = [
            name for name in r246.LENS_NAMES
            if cand[name]["validation"].get("candidate_predictions", 0) > 0
            and cand[name]["validation"].get("candidate_wrong", 0) == 0
        ]
        if zero:
            zero.sort(key=lambda name: (
                -cand[name]["validation"].get("candidate_correct", 0),
                -cand[name]["fidelity"],
                r246.LENS_NAMES.index(name),
            ))
            selected[action] = zero[0]
        diagnostic[action] = cand
    return selected, diagnostic


def evaluate_game(paths):
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"{r246.game_id(ps[0])}: exact p0..p19 required, got {nums}")

    tr = r246.transitions(ps[:5])
    va = r246.transitions(ps[5:10])
    fit = r246.transitions(ps[:10])
    ho = r246.transitions(ps[10:])
    selected, diag = select_per_action(tr, va)
    exact = r246.fit_exact(fit)
    tabs = {name: r246.fit_lens(fit, name) for name in set(selected.values())}

    s = Counter()
    examples = []
    by_action = defaultdict(Counter)
    for row in ho:
        s["transitions"] += 1
        if r246.exact_key(row) in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        action = row["action"]
        name = selected.get(action)
        if name is None:
            s["candidate_abstain"] += 1
            continue
        k = r246.stable((r246.lens(name, row["before"]), action))
        pred = tabs[name].get(k)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        by_action[action]["predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        by_action[action]["correct" if ok else "wrong"] += 1
        if len(examples) < 30:
            examples.append({"trace": row["trace"], "action": action, "lens": name, "correct": ok})

    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    held = {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "by_action": {a: dict(v) for a, v in by_action.items()},
        "examples": examples,
    }
    gain = bool(p > 0 and s["candidate_wrong"] == 0)
    return {
        "selected_by_action": selected,
        "selection_diagnostic": diag,
        "refit": {"exact_keys": len(exact), "selected_action_count": len(selected)},
        "heldout": held,
        "gain": gain,
    }


def run(paths):
    by = defaultdict(list)
    for path in paths:
        by[r246.game_id(path)].append(path)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}
    agg = Counter()
    gain_games = []
    for g, result in games.items():
        h = result["heldout"]
        for k in (
            "transitions", "exact_baseline", "baseline_abstain",
            "candidate_predictions", "candidate_correct", "candidate_wrong",
        ):
            agg[k] += int(h.get(k, 0) or 0)
        if result["gain"]:
            gain_games.append(g)
    p = agg["candidate_predictions"]
    opp = agg["baseline_abstain"]
    aggregate = {
        **dict(agg),
        "candidate_accuracy": round(agg["candidate_correct"] / p, 6) if p else None,
        "candidate_coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "gain_games": gain_games,
        "gain_game_count": len(gain_games),
        "game_count": len(games),
    }
    nondominated = bool(p > 0 and agg["candidate_wrong"] == 0 and agg["candidate_correct"] > 0)
    return {
        "schema": "deus/arc3-r251-action-conditional-markov-gate/1",
        "rung": RUNG,
        "lineage": {
            "r246": "run35763149532/artifact10712160802",
            "r247": "run35774094523/job106902767529/CANCELLED_TIMEOUT_NO_ARTIFACT",
            "repair": "memoize identical lens fits once per game; semantics unchanged",
        },
        "protocol": {
            "select": "p0-p4 fit / p5-p9 per-action zero-wrong validation",
            "refit": "p0-p9",
            "frozen_eval": "p10-p19",
            "exact_baseline_precedence": True,
        },
        "games": games,
        "aggregate": aggregate,
        "non_dominated_source_side_gain": nondominated,
        "promotion": {
            "integration_candidate": nondominated,
            "solver_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "selection_uses_p0_p9_only": True,
            "p10_p19_never_updates_selection_or_model": True,
            "r246_wrong_locations_not_encoded_as_rules": True,
            "r247_semantics_preserved": True,
            "repair_is_runtime_implementation_only": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run(args.input)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "aggregate": result["aggregate"],
        "gain": result["non_dominated_source_side_gain"],
        "sc25": result["games"].get("sc25-635fd71a", {}).get("heldout"),
        "selected_sc25": result["games"].get("sc25-635fd71a", {}).get("selected_by_action"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
