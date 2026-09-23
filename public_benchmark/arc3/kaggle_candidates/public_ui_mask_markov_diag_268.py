#!/usr/bin/env python3
"""R268: source-free static UI-mask Markov diagnostic over public ARC-AGI-3 traces.

Public source grounding: shloksah/arc-agi-3-agent FrugalExplorer at commit
7dccef15650fa00ef1db1c21cc7279adcf4a9e2a masks the outer ring plus row 1
before state hashing to suppress engine step/timer UI churn. R268 independently
tests only that representation idea against the pinned Tufa public traces.

Protocol:
  * p0-p4 fit raw-state and static-UI-masked state/action next-state tables;
  * p5-p9 evaluate state-key prediction coverage/accuracy;
  * p10-p19 are NOT read;
  * this is a representation diagnostic, not a full-frame solver or score.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG = 268
SENTINEL = 16
SOURCE_REF = "shloksah/arc-agi-3-agent@7dccef15650fa00ef1db1c21cc7279adcf4a9e2a:core/frugal_explorer.py"


def masked(board: list[list[int]]) -> list[list[int]]:
    x = [list(map(int, row)) for row in board]
    if not x or not x[0]:
        return x
    h, w = len(x), len(x[0])
    for r in range(h):
        x[r][0] = SENTINEL
        if w > 1:
            x[r][w - 1] = SENTINEL
    for r in {0, 1, h - 1}:
        if 0 <= r < h:
            for c in range(w):
                x[r][c] = SENTINEL
    return x


def rows(paths: list[Path]):
    return [r for p in paths for r in r251.prepare_rows([p])]


def state_key(board, mode: str) -> str:
    return r246.digest(masked(board) if mode == "ui_mask" else board)


def fit_table(rs, mode: str):
    obs = defaultdict(Counter)
    before_states = set()
    for r in rs:
        b = state_key(r["before"], mode)
        n = state_key(r["after"], mode)
        before_states.add(b)
        obs[(b, r["action"])][n] += 1
    table = {}
    ambiguous = 0
    for k, c in obs.items():
        if len(c) == 1:
            table[k] = next(iter(c))
        else:
            ambiguous += 1
    return table, {
        "unique_before_states": len(before_states),
        "state_action_keys": len(obs),
        "deterministic_keys": len(table),
        "ambiguous_keys": ambiguous,
        "deterministic_fraction": round(len(table) / len(obs), 6) if obs else 0.0,
    }


def evaluate(rs, table, mode: str):
    s = Counter()
    for r in rs:
        s["transitions"] += 1
        k = (state_key(r["before"], mode), r["action"])
        pred = table.get(k)
        if pred is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        ok = pred == state_key(r["after"], mode)
        s["correct" if ok else "wrong"] += 1
    p = s["predictions"]
    return {
        **dict(s),
        "accuracy": round(s["correct"] / p, 6) if p else None,
        "coverage": round(p / s["transitions"], 6) if s["transitions"] else 0.0,
    }


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise ValueError(f"exact p0..p9 required, got {nums}")
    tr = rows(ps[:5])
    va = rows(ps[5:])
    out = {}
    for mode in ("raw", "ui_mask"):
        table, fit = fit_table(tr, mode)
        out[mode] = {"fit": fit, "validation": evaluate(va, table, mode)}
    rv, mv = out["raw"]["validation"], out["ui_mask"]["validation"]
    out["delta"] = {
        "correct": int(mv.get("correct", 0)) - int(rv.get("correct", 0)),
        "wrong": int(mv.get("wrong", 0)) - int(rv.get("wrong", 0)),
        "predictions": int(mv.get("predictions", 0)) - int(rv.get("predictions", 0)),
        "unique_train_states": out["ui_mask"]["fit"]["unique_before_states"] - out["raw"]["fit"]["unique_before_states"],
    }
    out["signal"] = bool(
        out["delta"]["correct"] > 0
        and int(mv.get("wrong", 0)) <= int(rv.get("wrong", 0))
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}
    signal_games = [g for g, x in games.items() if x["signal"]]
    aggregate = Counter()
    for x in games.values():
        for mode in ("raw", "ui_mask"):
            v = x[mode]["validation"]
            for k in ("transitions", "predictions", "correct", "wrong", "abstain"):
                aggregate[f"{mode}_{k}"] += int(v.get(k, 0) or 0)
    raw_p = aggregate["raw_predictions"]
    mask_p = aggregate["ui_mask_predictions"]
    agg = dict(aggregate)
    agg["raw_accuracy"] = round(aggregate["raw_correct"] / raw_p, 6) if raw_p else None
    agg["ui_mask_accuracy"] = round(aggregate["ui_mask_correct"] / mask_p, 6) if mask_p else None
    agg["correct_delta"] = aggregate["ui_mask_correct"] - aggregate["raw_correct"]
    agg["wrong_delta"] = aggregate["ui_mask_wrong"] - aggregate["raw_wrong"]
    out = {
        "schema": "deus/arc3-r268-ui-mask-markov-diagnostic/1",
        "rung": RUNG,
        "source_grounding": {
            "reference": SOURCE_REF,
            "idea": "freeze/remove engine UI border pixels from state hashing",
            "implementation": "independent diagnostic implementation; no upstream runtime/score imported",
        },
        "protocol": {
            "fit": "p0-p4",
            "diagnostic_eval": "p5-p9",
            "p10_p19_read": False,
            "metric": "next normalized-state-key prediction, not full-frame rendering",
            "promotion": False,
        },
        "aggregate": agg,
        "signal_games": signal_games,
        "games": games,
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "p10_p19_read": False,
            "source_assisted_idea": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"aggregate": agg, "signal_games": signal_games}, sort_keys=True))


if __name__ == "__main__":
    main()
