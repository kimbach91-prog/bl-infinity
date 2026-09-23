#!/usr/bin/env python3
"""R287: lp85 action-canonical exact-frame diagnostic.

R279 proved that canon_regions_ui predicts the next *abstract* representation state.
R286 then showed that mapping the pooled/action-canonical key directly to an exact
screen frame has no safe held-out overlap. That direct renderer ignored a crucial
symmetry fact: LEFT/RIGHT/DOWN observations are pooled only after rotating the
screen into the same UP-oriented coordinate frame.

This diagnostic changes only that discriminating mechanism. It predicts the exact
next RAW frame in the common action-canonical coordinate system. A later frozen
adapter can inverse-rotate that frame back to provider coordinates.

Protocol: p0-p4 fit -> p5-p9 diagnostic only. p10-p19 are forbidden here.
PUBLIC_OFFLINE/source-free runtime logic only; no solver/Kaggle/hidden claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278
import public_action_canonical_topology_diag_275 as r275

RUNG = 287
TARGET_GAME = "lp85-305b61c3"
MODE = "canon_regions_ui"
MIN_DISTINCT_PRESTATES = 2


def canonical_raw(board: list[list[int]], action: str) -> list[list[int]]:
    return r275.canon_board(board, action, use_ui_mask=False)


def fit(rows: list[dict[str, Any]]):
    obs = defaultdict(Counter)
    raw_pre = defaultdict(set)
    examples: dict[tuple[Any, str], list[list[int]]] = {}
    for r in rows:
        k = r278.before_key(r, MODE)
        out = canonical_raw(r["after"], r["action"])
        d = r246.digest(out)
        obs[k][d] += 1
        raw_pre[k].add(r246.digest(r["before"]))
        examples[(k, d)] = out

    table = {}
    for k, vv in obs.items():
        if len(vv) != 1:
            continue
        if len(raw_pre[k]) < MIN_DISTINCT_PRESTATES:
            continue
        d = next(iter(vv))
        table[k] = examples[(k, d)]

    return table, {
        "keys": len(obs),
        "ambiguous_canonical_exact_frame_keys": sum(len(v) > 1 for v in obs.values()),
        "unique_keys": sum(len(v) == 1 for v in obs.values()),
        "eligible_keys": len(table),
        "below_distinct_prestate_support": sum(
            len(v) == 1 and len(raw_pre[k]) < MIN_DISTINCT_PRESTATES
            for k, v in obs.items()
        ),
    }


def exact_baseline(rows: list[dict[str, Any]]):
    obs = defaultdict(Counter)
    for r in rows:
        k = r246.exact_key(r)
        obs[k][r246.digest(r["after"])] += 1
    return {k for k, v in obs.items() if len(v) == 1}


def evaluate(rows: list[dict[str, Any]], table, baseline):
    s = Counter()
    examples = []
    for r in rows:
        s["transitions"] += 1
        if r246.exact_key(r) in baseline:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        pred = table.get(r278.before_key(r, MODE))
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        actual = canonical_raw(r["after"], r["action"])
        ok = pred == actual
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 30:
            examples.append({
                "pnum": r.get("pnum"),
                "trace_row": r.get("trace_row"),
                "action": r.get("action"),
                "correct": ok,
            })
    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "incremental_coverage": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by) != {TARGET_GAME}:
        raise SystemExit(f"exact target {TARGET_GAME} required, got {sorted(by)}")
    ps = sorted(by[TARGET_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise SystemExit(f"exact p0-p9 required, got {nums}")

    train = r278.annotated_rows(ps[:5])
    val = r278.annotated_rows(ps[5:])
    table, fs = fit(train)
    baseline = exact_baseline(train)
    diagnostic = evaluate(val, table, baseline)

    p = int(diagnostic.get("candidate_predictions", 0) or 0)
    w = int(diagnostic.get("candidate_wrong", 0) or 0)
    c = int(diagnostic.get("candidate_correct", 0) or 0)
    verdict = "DIAGNOSTIC_SIGNAL" if p > 0 and w == 0 and c > 0 else ("NO_SIGNAL" if p == 0 else "REJECT_MISMATCH")

    out = {
        "schema": "deus/arc3-r287-lp85-action-canonical-exact-frame-diagnostic/1",
        "rung": RUNG,
        "lineage": {
            "r279": "canon_regions_ui predicts abstract next representation state",
            "r286": "direct pooled key -> original exact frame NO_SIGNAL",
            "r283": "masked-world delta NO_MASKED_WORLD_SIGNAL",
            "repair": "preserve action symmetry through output by predicting exact RAW next frame in canonical UP-oriented coordinates",
        },
        "candidate": {
            "game": TARGET_GAME,
            "mode": MODE,
            "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
            "output_space": "exact raw next frame after action-canonical rotation; no UI masking",
        },
        "protocol": {
            "fit": "p0-p4 only",
            "diagnostic": "p5-p9 only",
            "p10_p19_staged_or_read": False,
            "exact_visible_state_action_baseline_precedence": True,
            "selection_or_threshold_retune_on_p5_p9": False,
            "promotion_in_r287": False,
            "next_if_signal": "freeze exact mechanism before p10-p19; refit p0-p9; inverse-rotate prediction and require zero-wrong exact original-frame gain",
        },
        "fit": {"exact_baseline_keys": len(baseline), **fs},
        "diagnostic": diagnostic,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p10_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "whole_game_policy_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r287": False,
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "fit": out["fit"], "diagnostic": diagnostic}, sort_keys=True))


if __name__ == "__main__":
    main()
