#!/usr/bin/env python3
"""R280: bounded lp85 representation -> exact-frame diagnostic.

R279 established that the frozen source-free representation
`canon_regions_ui` is deterministic on reused public-development p10-p19 at
representation-state level. That is not an exact-frame result. R280 asks the
smallest next falsifying question without touching p10-p19:

Can the SAME frozen representation key learned from p0-p4 deterministically
map to an exact next visible frame on p5-p9, beyond the exact visible-state
baseline?

Protocol:
* exact game: lp85-305b61c3
* exact frozen mode: canon_regions_ui (no mode selection here)
* fit p0-p4 only; diagnostic p5-p9 only
* p10-p19 must not be staged/read
* exact visible-state/action baseline has precedence
* candidate key must map to exactly one exact next frame in fit
* candidate key must have >=2 distinct raw pre-states in fit
* promotion signal requires >=1 incremental exact-frame prediction and 0 wrong

PUBLIC_OFFLINE diagnostic only; not hidden/Kaggle evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278

RUNG = 280
TARGET_GAME = "lp85-305b61c3"
FROZEN_MODE = "canon_regions_ui"
MIN_DISTINCT_PRESTATES = 2


def exact_key(r: dict[str, Any]) -> str:
    return r246.digest({"before": r["before"], "action": r["action"]})


def fit_exact(rows: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
    obs: dict[str, Counter] = defaultdict(Counter)
    frames: dict[tuple[str, str], list[list[int]]] = {}
    for r in rows:
        k = exact_key(r)
        d = r246.digest(r["after"])
        obs[k][d] += 1
        frames[(k, d)] = r["after"]
    out = {}
    for k, ctr in obs.items():
        if len(ctr) == 1:
            d = next(iter(ctr))
            out[k] = frames[(k, d)]
    return out


def candidate_key(r: dict[str, Any]):
    return r278.before_key(r, FROZEN_MODE)


def fit_candidate(rows: list[dict[str, Any]]):
    obs: dict[Any, Counter] = defaultdict(Counter)
    prestates: dict[Any, set[str]] = defaultdict(set)
    frames: dict[tuple[Any, str], list[list[int]]] = {}
    for r in rows:
        k = candidate_key(r)
        d = r246.digest(r["after"])
        obs[k][d] += 1
        prestates[k].add(r246.digest(r["before"]))
        frames[(k, d)] = r["after"]
    out = {}
    for k, ctr in obs.items():
        if len(ctr) != 1 or len(prestates[k]) < MIN_DISTINCT_PRESTATES:
            continue
        d = next(iter(ctr))
        out[k] = frames[(k, d)]
    return out, {
        "keys": len(obs),
        "deterministic_exact_frame_keys": sum(len(v) == 1 for v in obs.values()),
        "eligible_keys": len(out),
        "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    ps = sorted(a.input, key=r246.pnum)
    games = {r246.game_id(p) for p in ps}
    nums = [r246.pnum(p) for p in ps]
    if games != {TARGET_GAME}:
        raise SystemExit(f"exact target {TARGET_GAME} required, got {sorted(games)}")
    if nums != list(range(10)):
        raise SystemExit(f"exact p0-p9 required, got {nums}")

    fit_rows = r278.annotated_rows(ps[:5])
    diag_rows = r278.annotated_rows(ps[5:])
    exact = fit_exact(fit_rows)
    cand, fit_meta = fit_candidate(fit_rows)

    s = Counter()
    examples = []
    for r in diag_rows:
        s["transitions"] += 1
        if exact_key(r) in exact:
            s["baseline_predictions"] += 1
            continue
        s["baseline_abstain"] += 1
        pred = cand.get(candidate_key(r))
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 30:
            examples.append({"trace": r.get("trace"), "action": r["action"], "correct": ok})

    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    if p > 0 and s["candidate_wrong"] == 0:
        verdict = "PASS_ZERO_WRONG_EXACT_FRAME_SIGNAL"
    elif p == 0:
        verdict = "NO_EXACT_FRAME_SIGNAL"
    else:
        verdict = "REJECT_EXACT_FRAME_MISMATCH"

    out = {
        "schema": "deus/arc3-r280-lp85-region-to-exact-frame-diagnostic/1",
        "rung": RUNG,
        "frozen_candidate": {"game": TARGET_GAME, "mode": FROZEN_MODE},
        "protocol": {
            "fit": "p0-p4 only",
            "diagnostic": "p5-p9 only",
            "p10_p19_staged_or_read": False,
            "exact_baseline_precedence": True,
            "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
            "mode_selection_in_r280": False,
            "exact_full_frame_scoring": True,
        },
        "fit": {"exact_baseline_keys": len(exact), **fit_meta},
        "diagnostic": {
            **dict(s),
            "candidate_accuracy": round(s["candidate_correct"] / p, 6) if p else None,
            "incremental_coverage": round(p / opp, 6) if opp else 0.0,
            "examples": examples,
        },
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p10_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r280": False,
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "fit": out["fit"], "diagnostic": out["diagnostic"]}, sort_keys=True))


if __name__ == "__main__":
    main()
