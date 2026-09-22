#!/usr/bin/env python3
"""R252: source-free relative local-operator gate for R251 no-gain families.

Falsifier from R251:
- re86 has only six actions and near-perfect structural/composite Markov fidelity,
  yet R251 produces zero transferable exact-next-frame predictions.
- This suggests the state abstraction can be Markov while the *absolute output
  frame* is trace-specific.

R252 changes representation rather than thresholds: learn an action-conditioned
local transition operator (cell neighborhood -> next center value), optionally
conditioned on the previous action. The operator is applied to the current
frame, so the prediction is relative to the observed state rather than an
absolute memorized next frame.

Protocol:
  p0-p4  fit local rules
  p5-p9  select per-action representation only if added full-frame predictions
         are >0 and ZERO wrong
  p0-p9  refit selected rules
  p10-p19 frozen public-development evaluation
Exact visible-state/action lookup retains precedence.

No game source, upstream replay bank beyond the pinned public traces, upstream
score, Kaggle runtime, or hidden outcomes are read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_action_conditional_markov_gate_251 as r251
import public_sourcefree_markov_fidelity_adapter_246 as r246

RUNG = 252
MIN_TRANSITION_SUPPORT = 2
BASE_REPS = ("cross1", "cross2", "count1")
VARIANTS = tuple(
    f"{rep}{'_prev' if prev else ''}{'_id' if ident else '_strict'}"
    for rep in BASE_REPS for prev in (False, True) for ident in (False, True)
)
SENTINEL = -1


def prepare_history_rows(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        rows = r251.prepare_rows([p])
        prev_action = "START"
        for step, r in enumerate(rows):
            x = dict(r)
            x["prev_action"] = prev_action
            x["step"] = step
            x["transition_id"] = f"{p.name}#{step}"
            out.append(x)
            prev_action = r["action"]
    return out


def at(board: list[list[int]], rr: int, cc: int) -> int:
    if rr < 0 or cc < 0 or rr >= len(board) or cc >= len(board[0]):
        return SENTINEL
    return int(board[rr][cc])


def local_feature(board: list[list[int]], r: int, c: int, rep: str) -> Any:
    if rep == "cross1":
        return (
            at(board, r, c),
            at(board, r - 1, c), at(board, r + 1, c),
            at(board, r, c - 1), at(board, r, c + 1),
        )
    if rep == "cross2":
        return (
            at(board, r, c),
            at(board, r - 1, c), at(board, r + 1, c),
            at(board, r, c - 1), at(board, r, c + 1),
            at(board, r - 2, c), at(board, r + 2, c),
            at(board, r, c - 2), at(board, r, c + 2),
        )
    if rep == "count1":
        center = at(board, r, c)
        vals = [
            at(board, r + dr, c + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if not (dr == 0 and dc == 0)
        ]
        return (center, tuple(sorted(Counter(vals).items())))
    raise KeyError(rep)


def parse_variant(name: str) -> tuple[str, bool, bool]:
    ident = name.endswith("_id")
    stem = name[:-3] if ident else name[:-7]
    prev = stem.endswith("_prev")
    if prev:
        stem = stem[:-5]
    if stem not in BASE_REPS:
        raise KeyError(name)
    return stem, prev, ident


def cell_key(row: dict[str, Any], r: int, c: int, variant: str) -> str:
    rep, use_prev, _ = parse_variant(variant)
    k = [row["action"]]
    if use_prev:
        k.append(row["prev_action"])
    k.append(local_feature(row["before"], r, c, rep))
    return r246.stable(k)


def fit_rules(rows: list[dict[str, Any]], variant: str) -> dict[str, int]:
    obs: dict[str, Counter] = defaultdict(Counter)
    support: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        b = row["before"]
        a = row["after"]
        h, w = len(b), len(b[0])
        tid = row["transition_id"]
        for r in range(h):
            for c in range(w):
                k = cell_key(row, r, c, variant)
                obs[k][int(a[r][c])] += 1
                support[k].add(tid)
    rules: dict[str, int] = {}
    for k, counts in obs.items():
        if len(counts) == 1 and len(support[k]) >= MIN_TRANSITION_SUPPORT:
            rules[k] = int(next(iter(counts)))
    return rules


def predict(row: dict[str, Any], rules: dict[str, int], variant: str) -> list[list[int]] | None:
    _, _, identity_fallback = parse_variant(variant)
    b = row["before"]
    h, w = len(b), len(b[0])
    out = [list(map(int, rr)) for rr in b]
    for r in range(h):
        for c in range(w):
            k = cell_key(row, r, c, variant)
            if k in rules:
                out[r][c] = rules[k]
            elif identity_fallback:
                out[r][c] = int(b[r][c])
            else:
                return None
    return out


def fit_exact(rows: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
    return r251.fit_exact(rows)


def eval_rows(rows: list[dict[str, Any]], exact: dict, rules: dict[str, int], variant: str) -> dict[str, Any]:
    s = Counter()
    examples = []
    for row in rows:
        s["transitions"] += 1
        if row["exact_key"] in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        pred = predict(row, rules, variant)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 20:
            examples.append({
                "trace": row["trace"], "step": row["step"],
                "action": row["action"], "prev_action": row["prev_action"],
                "correct": ok,
            })
    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"{r246.game_id(ps[0])}: exact p0..p19 required, got {nums}")

    parts = [prepare_history_rows([p]) for p in ps]
    tr = [r for part in parts[:5] for r in part]
    va = [r for part in parts[5:10] for r in part]
    fit = [r for part in parts[:10] for r in part]
    ho = [r for part in parts[10:] for r in part]

    train_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    val_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fit_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in tr: train_by_action[r["action"]].append(r)
    for r in va: val_by_action[r["action"]].append(r)
    for r in fit: fit_by_action[r["action"]].append(r)

    exact_tr = fit_exact(tr)
    selected: dict[str, str] = {}
    diagnostics: dict[str, Any] = {}
    all_actions = sorted(set(train_by_action) | set(val_by_action))

    for action in all_actions:
        cand: dict[str, Any] = {}
        train_rows = train_by_action.get(action, [])
        val_rows = val_by_action.get(action, [])
        for variant in VARIANTS:
            rules = fit_rules(train_rows, variant)
            met = eval_rows(val_rows, exact_tr, rules, variant)
            cand[variant] = {"rule_count": len(rules), "validation": met}
        zero = [
            v for v in VARIANTS
            if cand[v]["validation"].get("candidate_predictions", 0) > 0
            and cand[v]["validation"].get("candidate_wrong", 0) == 0
        ]
        if zero:
            zero.sort(key=lambda v: (
                -cand[v]["validation"].get("candidate_correct", 0),
                -cand[v]["validation"].get("candidate_predictions", 0),
                VARIANTS.index(v),
            ))
            selected[action] = zero[0]
        diagnostics[action] = cand

    exact_fit = fit_exact(fit)
    refit_rules: dict[tuple[str, str], dict[str, int]] = {}
    for action, variant in selected.items():
        refit_rules[(action, variant)] = fit_rules(fit_by_action.get(action, []), variant)

    s = Counter()
    by_action: dict[str, Counter] = defaultdict(Counter)
    examples = []
    for row in ho:
        s["transitions"] += 1
        if row["exact_key"] in exact_fit:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        variant = selected.get(row["action"])
        if variant is None:
            s["candidate_abstain"] += 1
            continue
        pred = predict(row, refit_rules[(row["action"], variant)], variant)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        by_action[row["action"]]["predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        by_action[row["action"]]["correct" if ok else "wrong"] += 1
        if len(examples) < 30:
            examples.append({
                "trace": row["trace"], "step": row["step"],
                "action": row["action"], "prev_action": row["prev_action"],
                "variant": variant, "correct": ok,
            })
    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    held = {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "by_action": {a: dict(v) for a, v in by_action.items()},
        "examples": examples,
    }
    gain = bool(p > 0 and s["candidate_wrong"] == 0 and s["candidate_correct"] > 0)
    return {
        "selected_by_action": selected,
        "selection_diagnostic": diagnostics,
        "refit": {
            "exact_keys": len(exact_fit),
            "selected_action_count": len(selected),
            "rule_count_total": sum(len(v) for v in refit_rules.values()),
        },
        "heldout": held,
        "gain": gain,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    by: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        by[r246.game_id(p)].append(p)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}
    agg = Counter()
    gains = []
    for g, x in games.items():
        h = x["heldout"]
        for k in (
            "transitions", "exact_baseline", "baseline_abstain",
            "candidate_predictions", "candidate_correct", "candidate_wrong",
        ):
            agg[k] += int(h.get(k, 0) or 0)
        if x["gain"]:
            gains.append(g)
    p = agg["candidate_predictions"]
    opp = agg["baseline_abstain"]
    aggregate = {
        **dict(agg),
        "candidate_accuracy": round(agg["candidate_correct"] / p, 6) if p else None,
        "candidate_coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "gain_games": gains, "gain_game_count": len(gains), "game_count": len(games),
    }
    nondominated = bool(p > 0 and agg["candidate_wrong"] == 0 and agg["candidate_correct"] > 0)
    return {
        "schema": "deus/arc3-r252-relative-local-operator/1",
        "rung": RUNG,
        "lineage": {
            "r251": "run35795562246/artifact10724065280",
            "falsifier": "re86 structural Markov fidelity near 1.0 but R251 transferable absolute-output prediction count zero",
            "repair": "relative local transition operator; no threshold retune",
        },
        "protocol": {
            "select": "p0-p4 fit / p5-p9 per-action zero-wrong full-frame validation",
            "refit": "p0-p9",
            "frozen_eval": "p10-p19",
            "exact_baseline_precedence": True,
            "candidate": "action-conditioned local cell operator applied to current frame",
            "variants": list(VARIANTS),
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
            "p10_p19_status": "PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
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
        "selected": {g: x["selected_by_action"] for g, x in d["games"].items()},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
