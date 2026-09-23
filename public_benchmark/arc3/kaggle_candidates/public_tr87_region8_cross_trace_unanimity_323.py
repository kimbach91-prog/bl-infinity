#!/usr/bin/env python3
"""R323: bounded falsifier for TR87 region8 false changes.

Hypothesis: R321's remaining false changes come from change rules that are
locally deterministic but not supported across every independent training
trace. Keep the exact R321 region8 representation and change only the
reliability mechanism: a rule must be observed with one pooled outcome in all
four training traces of each p0-p4 LOTO fold.

No p5-p19 traces are staged/read. This is PUBLIC_OFFLINE representation/
reliability research only, not whole-game or Kaggle promotion.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_residual4_local_causal_loto_302 as r302
import public_residual4_mode_shard_314 as r314
import public_tr87_wa30_region_context_loto_321 as r321

RUNG = 323
GAME = "tr87-cd924810"
BASE_MODE = "delta"
GRID = 8


def fit_unanimous(prepared_traces):
    outcomes = defaultdict(Counter)
    support = defaultdict(set)
    for ti, tr in enumerate(prepared_traces):
        for row in tr:
            b, a, keys = row["b"], row["a"], row["keys"]
            h = len(b); w = len(b[0]) if h else 0
            for rr in range(h):
                for cc in range(w):
                    k = keys[rr][cc]
                    outcomes[k][int(a[rr][cc])] += 1
                    support[k].add(ti)
    rules = {}
    ntr = len(prepared_traces)
    for k, out in outcomes.items():
        if len(out) != 1 or len(support[k]) != ntr:
            continue
        pred = int(next(iter(out)))
        center = int(k[0][len(k[0]) // 2])
        if pred != center:
            rules[k] = pred
    return rules, {
        "keys": len(outcomes),
        "all_trace_supported_keys": sum(len(support[k]) == ntr for k in outcomes),
        "change_rules": len(rules),
        "required_trace_support": ntr,
    }


def run_loto(traces):
    prepared = [r321.prep(t, BASE_MODE, GRID) for t in traces]
    total = Counter(); folds = []
    for held in range(5):
        train = [prepared[i] for i in range(5) if i != held]
        rules, fit = fit_unanimous(train)
        ev = r314._evaluate(prepared[held], rules)
        folds.append({"held_trace": held, "fit": fit, "eval": ev})
        for k, v in ev.items():
            if isinstance(v, int):
                total[k] += v
    total["pixel_gain"] = total["identity_errors"] - total["candidate_errors"]
    total["exact_frame_gain"] = total["candidate_exact_frames"] - total["identity_exact_frames"]
    return dict(total), folds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    ps = sorted(a.input, key=r246.pnum)
    if any(r246.game_id(p) != GAME for p in ps) or [r246.pnum(p) for p in ps] != list(range(5)):
        raise SystemExit("exact TR87 p0-p4 required")
    traces = [r302.augment_trace(p) for p in ps]
    total, folds = run_loto(traces)
    if total.get("predicted_changes", 0) > 0 and total.get("false_changes", 0) == 0 and total.get("pixel_gain", 0) > 0 and total.get("exact_frame_gain", 0) >= 0:
        verdict = "UNANIMOUS_ZERO_FALSE_LOTO_SIGNAL"
    elif total.get("pixel_gain", 0) > 0:
        verdict = "UNANIMOUS_GAIN_WITH_FALSE_CHANGE"
    else:
        verdict = "UNANIMOUS_NO_SIGNAL"
    out = {
        "schema": "deus/arc3-r323-tr87-region8-cross-trace-unanimity/1",
        "rung": RUNG,
        "game": GAME,
        "base_mode": BASE_MODE,
        "grid": GRID,
        "hypothesis": "R321 false changes are caused by change rules not invariant across all independent training traces",
        "protocol": {
            "data": "public p0-p4 only",
            "evaluation": "5-fold leave-one-trace-out",
            "representation": "unchanged R321 delta+region8",
            "mechanism_delta": "require deterministic change rule support in all four training traces per fold",
            "p5_p9_staged_or_read": False,
            "p10_p19_staged_or_read": False,
        },
        "loto": total,
        "folds": folds,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p5_p9_read": False,
            "p10_p19_read": False,
            "whole_game_solver_promotion": False,
            "kaggle_execution": False,
            "competition_submission": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "loto": total}, sort_keys=True))


if __name__ == "__main__":
    main()
