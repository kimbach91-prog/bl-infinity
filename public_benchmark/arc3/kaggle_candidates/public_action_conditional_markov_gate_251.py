#!/usr/bin/env python3
"""R251: runtime-repaired action-conditional source-free Markov gate.

This preserves R247's solver semantics but removes its timeout-causing repeated
perception/table work. The repair is harness/runtime only:
- each trace is loaded once per game;
- each before/after frame's six R246 lens values are computed once;
- exact keys and frame digests are computed once;
- p0-p4 lens tables are fit once per lens, then reused across actions.

Selection/evaluation protocol is unchanged from R247:
  p0-p4 fit, p5-p9 per-action zero-wrong selection, p0-p9 refit,
  p10-p19 frozen public-development evaluation.
No game source, upstream score, Kaggle runtime or hidden outcomes are read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG = 251


def frame_features(board: list[list[int]]) -> dict[str, Any]:
    # Directly compute the same five primitive R246 lens values once. Composite
    # is exactly the tuple used by R246.lens("composite", ...).
    p = r246.palette(board)
    m = r246.meter(board)
    s = r246.symmetry(board)
    rg = r246.regions(board)
    o = r246.object_key(board)
    return {
        "palette": p,
        "meter": m,
        "symmetry": s,
        "regions": rg,
        "objects": o,
        "composite": (p, m, s, rg, o),
    }


def prepare_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in paths:
        ev = r246.load_events(p)
        pre = ev[0]
        for e in ev[1:]:
            if e.get("type") != "action":
                pre = e
                continue
            before = [[int(v) for v in row] for row in pre["board"]]
            after = [[int(v) for v in row] for row in e["board"]]
            if len(before) == len(after) and len(before[0]) == len(after[0]):
                action = r246.action_name(e)
                before_digest = r246.digest(before)
                after_digest = r246.digest(after)
                rows.append({
                    "trace": p.name,
                    "action": action,
                    "before": before,
                    "after": after,
                    "before_digest": before_digest,
                    "after_digest": after_digest,
                    "exact_key": r246.digest({"b": before, "a": action}),
                    "before_features": frame_features(before),
                    "after_features": frame_features(after),
                })
            pre = e
    return rows


def fit_exact(rows: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
    obs: dict[str, Counter] = defaultdict(Counter)
    ex: dict[tuple[str, str], list[list[int]]] = {}
    for r in rows:
        k = r["exact_key"]
        d = r["after_digest"]
        obs[k][d] += 1
        ex[(k, d)] = r["after"]
    tab: dict[str, list[list[int]]] = {}
    for k, c in obs.items():
        if len(c) == 1:
            d = next(iter(c))
            tab[k] = ex[(k, d)]
    return tab


def fit_lens(rows: list[dict[str, Any]], name: str, min_support: int = r246.MIN_SUPPORT) -> dict[str, list[list[int]]]:
    obs: dict[str, Counter] = defaultdict(Counter)
    prestates: dict[str, set[str]] = defaultdict(set)
    ex: dict[tuple[str, str], list[list[int]]] = {}
    for r in rows:
        k = r246.stable((r["before_features"][name], r["action"]))
        d = r["after_digest"]
        obs[k][d] += 1
        prestates[k].add(r["before_digest"])
        ex[(k, d)] = r["after"]
    tab: dict[str, list[list[int]]] = {}
    for k, c in obs.items():
        if len(c) != 1 or len(prestates[k]) < min_support:
            continue
        d = next(iter(c))
        tab[k] = ex[(k, d)]
    return tab


def markov_fidelity(rows: list[dict[str, Any]], name: str) -> float:
    table: dict[tuple[str, str], set[str]] = defaultdict(set)
    keys: set[str] = set()
    for r in rows:
        sk = r246.stable(r["before_features"][name])
        nk = r246.stable(r["after_features"][name])
        keys.add(sk)
        keys.add(nk)
        table[(sk, r["action"])].add(nk)
    if len(keys) < 2 or not table:
        return 0.0
    return sum(len(v) == 1 for v in table.values()) / len(table)


def eval_added(rows: list[dict[str, Any]], exact: dict, abstract: dict, name: str) -> dict[str, Any]:
    s = Counter()
    examples = []
    for r in rows:
        s["transitions"] += 1
        if r["exact_key"] in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        k = r246.stable((r["before_features"][name], r["action"]))
        pred = abstract.get(k)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 20:
            examples.append({"trace": r["trace"], "action": r["action"], "correct": ok})
    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def select_per_action(train: list[dict[str, Any]], val: list[dict[str, Any]]):
    exact = fit_exact(train)
    selected: dict[str, str] = {}
    diagnostic: dict[str, Any] = {}
    train_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    val_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in train:
        train_by_action[r["action"]].append(r)
    for r in val:
        val_by_action[r["action"]].append(r)
    all_actions = sorted(set(train_by_action) | set(val_by_action))

    # R247 recomputed the full train table once per action. R251 computes it
    # once per lens; this is the central timeout repair and does not alter data.
    train_tables = {name: fit_lens(train, name) for name in r246.LENS_NAMES}

    for action in all_actions:
        cand: dict[str, Any] = {}
        tr_action = train_by_action.get(action, [])
        va_action = val_by_action.get(action, [])
        for name in r246.LENS_NAMES:
            tab = train_tables[name]
            met = eval_added(va_action, exact, tab, name)
            cand[name] = {
                "keys": len(tab),
                "fidelity": round(markov_fidelity(tr_action, name), 6),
                "validation": met,
            }
        zero = [
            n for n in r246.LENS_NAMES
            if cand[n]["validation"].get("candidate_predictions", 0) > 0
            and cand[n]["validation"].get("candidate_wrong", 0) == 0
        ]
        if zero:
            zero.sort(key=lambda n: (
                -cand[n]["validation"].get("candidate_correct", 0),
                -cand[n]["fidelity"],
                r246.LENS_NAMES.index(n),
            ))
            selected[action] = zero[0]
        diagnostic[action] = cand
    return selected, diagnostic


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"{r246.game_id(ps[0])}: exact p0..p19 required, got {nums}")

    # Each trace is decoded once. Preserve exact trace/action ordering.
    parts = [prepare_rows([p]) for p in ps]
    tr = [r for part in parts[:5] for r in part]
    va = [r for part in parts[5:10] for r in part]
    fit = [r for part in parts[:10] for r in part]
    ho = [r for part in parts[10:] for r in part]

    selected, diag = select_per_action(tr, va)
    exact = fit_exact(fit)
    tabs = {name: fit_lens(fit, name) for name in set(selected.values())}
    s = Counter()
    examples = []
    by_action: dict[str, Counter] = defaultdict(Counter)
    for r in ho:
        s["transitions"] += 1
        if r["exact_key"] in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        action = r["action"]
        name = selected.get(action)
        if name is None:
            s["candidate_abstain"] += 1
            continue
        k = r246.stable((r["before_features"][name], action))
        pred = tabs[name].get(k)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        by_action[action]["predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        by_action[action]["correct" if ok else "wrong"] += 1
        if len(examples) < 30:
            examples.append({"trace": r["trace"], "action": action, "lens": name, "correct": ok})
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


def run(paths: list[Path]) -> dict[str, Any]:
    by: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        by[r246.game_id(p)].append(p)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}
    agg = Counter()
    gain_games = []
    for g, x in games.items():
        h = x["heldout"]
        for k in (
            "transitions", "exact_baseline", "baseline_abstain",
            "candidate_predictions", "candidate_correct", "candidate_wrong",
        ):
            agg[k] += int(h.get(k, 0) or 0)
        if x["gain"]:
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
        "schema": "deus/arc3-r251-action-conditional-markov-optimized/1",
        "rung": RUNG,
        "lineage": {
            "r246": "run35763149532/artifact10712160802",
            "r247_timeout": "run35774094523/job106902767529",
            "r250_sc25_equivalence_anchor": "run35794677108/artifact10723667948",
            "repair": "semantic-equivalent precomputation/runtime repair; no heldout-informed selection",
        },
        "protocol": {
            "select": "p0-p4 fit / p5-p9 per-action zero-wrong validation",
            "refit": "p0-p9",
            "frozen_eval": "p10-p19",
            "exact_baseline_precedence": True,
            "semantic_target": "R247",
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
            "r250_expected_metrics_used_for_implementation_QA_only": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    d = run(a.input)
    a.output.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "aggregate": d["aggregate"],
        "gain": d["non_dominated_source_side_gain"],
        "sc25": d["games"].get("sc25-635fd71a", {}).get("heldout"),
        "selected_sc25": d["games"].get("sc25-635fd71a", {}).get("selected_by_action"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
