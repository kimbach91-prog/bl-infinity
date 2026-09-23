#!/usr/bin/env python3
"""R273: factorized gameplay-core + UI-residual exact-frame gate.

Falsifier-driven hypothesis:
- R270/R271 showed that removing the static engine/UI border can make next
  normalized states deterministic across many public games.
- R272 exact-frame reconstruction still covers only a small fraction of
  baseline abstentions because a masked-state key throws away the border that
  must be rendered back.
- Instead of mapping masked gameplay state directly to a whole exact next
  frame, factor the transition into two train-side mechanisms:
    (1) masked gameplay core + action -> masked next core;
    (2) current UI border + action -> next UI border.
  The UI table is accepted only when its output is deterministic and the same
  UI transition was observed under >=2 distinct gameplay cores.

Protocol per game:
  p0-p4 fit; p5-p9 select only if incremental exact-frame predictions are
  positive and ZERO wrong; p0-p9 refit; p10-p19 frozen evaluation.
Exact visible-state/action baseline always has precedence.

This is PUBLIC_OFFLINE reused public-development evidence only. It is not a
Kaggle/hidden score and does not spend submission quota.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_ui_mask_markov_diag_268 as r268

RUNG = 273
MIN_DISTINCT_CORES = 2


def rows(paths: list[Path]) -> list[dict[str, Any]]:
    return [r for p in paths for r in r251.prepare_rows([p])]


def exact_key(r: dict[str, Any]) -> str:
    return r246.digest({"before": r["before"], "action": r["action"]})


def ui_positions(h: int, w: int) -> list[tuple[int, int]]:
    out = []
    for rr in range(h):
        for cc in range(w):
            if cc == 0 or cc == w - 1 or rr in {0, 1, h - 1}:
                out.append((rr, cc))
    return out


def ui_values(board: list[list[int]]) -> tuple[int, ...]:
    h, w = len(board), len(board[0])
    return tuple(int(board[r][c]) for r, c in ui_positions(h, w))


def core_board(board: list[list[int]]) -> list[list[int]]:
    return r268.masked(board)


def core_digest(board: list[list[int]]) -> str:
    return r246.digest(core_board(board))


def ui_digest(board: list[list[int]]) -> str:
    return r246.digest(ui_values(board))


def fit_exact(rs: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
    obs: dict[str, Counter] = defaultdict(Counter)
    frame: dict[tuple[str, str], list[list[int]]] = {}
    for r in rs:
        k = exact_key(r)
        d = r246.digest(r["after"])
        obs[k][d] += 1
        frame[(k, d)] = r["after"]
    out = {}
    for k, c in obs.items():
        if len(c) == 1:
            d = next(iter(c))
            out[k] = frame[(k, d)]
    return out


def fit_factorized(rs: list[dict[str, Any]]) -> tuple[dict, dict, dict[str, int]]:
    core_obs: dict[tuple[str, str], Counter] = defaultdict(Counter)
    core_frame: dict[tuple[tuple[str, str], str], list[list[int]]] = {}
    ui_obs: dict[tuple[str, str], Counter] = defaultdict(Counter)
    ui_frame: dict[tuple[tuple[str, str], str], tuple[int, ...]] = {}
    ui_core_support: dict[tuple[str, str], set[str]] = defaultdict(set)

    for r in rs:
        ck = (core_digest(r["before"]), r["action"])
        ca = core_board(r["after"])
        cad = r246.digest(ca)
        core_obs[ck][cad] += 1
        core_frame[(ck, cad)] = ca

        uk = (ui_digest(r["before"]), r["action"])
        ua = ui_values(r["after"])
        uad = r246.digest(ua)
        ui_obs[uk][uad] += 1
        ui_frame[(uk, uad)] = ua
        ui_core_support[uk].add(core_digest(r["before"]))

    core_tab = {}
    for k, c in core_obs.items():
        if len(c) == 1:
            d = next(iter(c))
            core_tab[k] = core_frame[(k, d)]

    ui_tab = {}
    rejected_low_support = 0
    rejected_ambiguous = 0
    for k, c in ui_obs.items():
        if len(c) != 1:
            rejected_ambiguous += 1
            continue
        if len(ui_core_support[k]) < MIN_DISTINCT_CORES:
            rejected_low_support += 1
            continue
        d = next(iter(c))
        ui_tab[k] = ui_frame[(k, d)]

    diag = {
        "core_keys": len(core_tab),
        "ui_keys": len(ui_tab),
        "ui_rejected_low_core_support": rejected_low_support,
        "ui_rejected_ambiguous": rejected_ambiguous,
    }
    return core_tab, ui_tab, diag


def compose(core_after: list[list[int]], ui_after: tuple[int, ...]) -> list[list[int]]:
    out = [row[:] for row in core_after]
    h, w = len(out), len(out[0])
    pos = ui_positions(h, w)
    if len(pos) != len(ui_after):
        raise ValueError("UI shape mismatch")
    for (r, c), v in zip(pos, ui_after):
        out[r][c] = int(v)
    return out


def evaluate_incremental(rs: list[dict[str, Any]], exact: dict, core_tab: dict, ui_tab: dict) -> dict[str, Any]:
    s = Counter()
    examples = []
    for r in rs:
        s["transitions"] += 1
        if exact_key(r) in exact:
            s["baseline_predictions"] += 1
            continue
        s["baseline_abstain"] += 1
        ck = (core_digest(r["before"]), r["action"])
        uk = (ui_digest(r["before"]), r["action"])
        ca = core_tab.get(ck)
        ua = ui_tab.get(uk)
        if ca is None or ua is None:
            s["candidate_abstain"] += 1
            continue
        pred = compose(ca, ua)
        s["candidate_predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 20:
            examples.append({"trace": r.get("trace"), "action": r["action"], "correct": ok})
    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "candidate_accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "incremental_coverage": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise ValueError(f"exact p0..p19 required, got {nums}")

    parts = [rows([p]) for p in ps]
    tr = [r for x in parts[:5] for r in x]
    va = [r for x in parts[5:10] for r in x]
    fit = [r for x in parts[:10] for r in x]
    ho = [r for x in parts[10:] for r in x]

    tr_exact = fit_exact(tr)
    tr_core, tr_ui, train_diag = fit_factorized(tr)
    val = evaluate_incremental(va, tr_exact, tr_core, tr_ui)
    selected = bool(
        val.get("candidate_predictions", 0) > 0
        and val.get("candidate_correct", 0) > 0
        and val.get("candidate_wrong", 0) == 0
    )

    fit_exact_tab = fit_exact(fit)
    fit_core, fit_ui, refit_diag = fit_factorized(fit)
    held = evaluate_incremental(ho, fit_exact_tab, fit_core, fit_ui) if selected else {
        "transitions": len(ho),
        "baseline_predictions": sum(exact_key(r) in fit_exact_tab for r in ho),
        "baseline_abstain": sum(exact_key(r) not in fit_exact_tab for r in ho),
        "candidate_predictions": 0,
        "candidate_correct": 0,
        "candidate_wrong": 0,
        "candidate_abstain": sum(exact_key(r) not in fit_exact_tab for r in ho),
        "candidate_accuracy": None,
        "incremental_coverage": 0.0,
        "examples": [],
    }
    promote = bool(
        selected
        and held.get("candidate_predictions", 0) > 0
        and held.get("candidate_correct", 0) > 0
        and held.get("candidate_wrong", 0) == 0
    )
    return {
        "selection": {"selected": selected, "p5_p9": val, "p0_p4_fit": train_diag},
        "refit": refit_diag,
        "heldout": held,
        "exact_frame_promoted": promote,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by: dict[str, list[Path]] = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}

    agg = Counter()
    promoted = []
    selected = []
    for g, x in games.items():
        if x["selection"]["selected"]:
            selected.append(g)
        if x["exact_frame_promoted"]:
            promoted.append(g)
        h = x["heldout"]
        for k in (
            "transitions", "baseline_predictions", "baseline_abstain",
            "candidate_predictions", "candidate_correct", "candidate_wrong", "candidate_abstain",
        ):
            agg[k] += int(h.get(k, 0) or 0)
    p = agg["candidate_predictions"]
    opp = agg["baseline_abstain"]
    aggregate = {
        **dict(agg),
        "game_count": len(games),
        "selected_count": len(selected),
        "selected_games": selected,
        "promoted_count": len(promoted),
        "promoted_games": promoted,
        "candidate_accuracy": round(agg["candidate_correct"] / p, 6) if p else None,
        "incremental_coverage": round(p / opp, 6) if opp else 0.0,
    }

    out = {
        "schema": "deus/arc3-r273-factorized-ui-residual/1",
        "rung": RUNG,
        "hypothesis": "factor exact rendering into deterministic masked gameplay-core transition plus cross-core deterministic UI-border transition",
        "protocol": {
            "selection": "p0-p4 fit / p5-p9 zero-wrong incremental exact-frame gate",
            "refit": "p0-p9",
            "frozen_eval": "p10-p19",
            "exact_baseline_precedence": True,
            "ui_min_distinct_gameplay_cores": MIN_DISTINCT_CORES,
        },
        "games": games,
        "aggregate": aggregate,
        "promotion": {
            "representation_candidate": bool(promoted),
            "solver_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "selection_uses_p0_p9_only": True,
            "p10_p19_never_updates_selection_or_model": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"aggregate": aggregate, "promotion": out["promotion"]}, sort_keys=True))


if __name__ == "__main__":
    main()
