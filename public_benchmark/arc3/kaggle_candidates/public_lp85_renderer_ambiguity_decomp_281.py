#!/usr/bin/env python3
"""R281: decompose why the frozen lp85 region state cannot render exact frames.

R279 verified that lp85 canon_regions_ui is a strong frozen state representation.
R280 then found zero usable exact-frame renderer keys on p0-p4: every region key
with cross-state support was ambiguous when mapped directly to a full canonical
raw after-frame.

R281 is a p0-p9-only diagnostic. It does NOT alter the R279 representation and
does NOT read p10-p19. For the same frozen before-key, it measures determinism
of multiple target factorizations:
  - full canonical raw/masked next state;
  - coarse/fine structural next-state targets;
  - full/interior/UI cell-delta operators.

The purpose is to choose the next materially different renderer family rather
than retuning thresholds on the failed R280 full-frame table.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278
import public_lp85_region_exact_frame_gate_280 as r280

RUNG = 281
GAME = "lp85-305b61c3"
MODE = "canon_regions_ui"
SENTINEL = r268.SENTINEL
MIN_SUPPORT = 2


def canon_raw(board: list[list[int]], action: str):
    return r275.canon_board(board, action, use_ui_mask=False)


def canon_masked(board: list[list[int]], action: str):
    return r275.canon_board(board, action, use_ui_mask=True)


def changed_cells(before, after, selector: Callable[[int, int], bool] | None = None):
    out = []
    h = min(len(before), len(after))
    w = min(len(before[0]), len(after[0])) if h else 0
    for rr in range(h):
        for cc in range(w):
            if selector is not None and not selector(rr, cc):
                continue
            if before[rr][cc] != after[rr][cc]:
                out.append((rr, cc, int(after[rr][cc])))
    return tuple(out)


def targets(r: dict[str, Any]) -> dict[str, Any]:
    a = r["action"]
    rb = canon_raw(r["before"], a)
    ra = canon_raw(r["after"], a)
    mb = canon_masked(r["before"], a)
    ma = canon_masked(r["after"], a)

    ui = {
        (rr, cc)
        for rr, row in enumerate(mb)
        for cc, v in enumerate(row)
        if int(v) == SENTINEL
    }
    is_ui = lambda rr, cc: (rr, cc) in ui
    is_interior = lambda rr, cc: (rr, cc) not in ui

    return {
        "raw_after_exact": r246.digest(ra),
        "masked_after_exact": r246.digest(ma),
        "regions8_after": r274.dig(r246.regions(ma, G=8)),
        "regions16_after": r274.dig(r246.regions(ma, G=16)),
        "nodes_coarse_after": r274.dig(r274.desc(ma, "nodes_coarse")),
        "nodes_exact_after": r274.dig(r274.desc(ma, "nodes_exact")),
        "raw_delta": changed_cells(rb, ra),
        "interior_delta": changed_cells(rb, ra, is_interior),
        "ui_delta": changed_cells(rb, ra, is_ui),
        "masked_delta": changed_cells(mb, ma),
    }


def fit_target(rows: list[dict[str, Any]], target_name: str):
    obs = defaultdict(Counter)
    prestates = defaultdict(set)
    exemplar = {}
    for r in rows:
        k = r280.candidate_key(r)
        payload = targets(r)[target_name]
        token = r246.stable(payload)
        obs[k][token] += 1
        prestates[k].add(r["before_digest"])
        exemplar[(k, token)] = payload

    table = {}
    for k, c in obs.items():
        if len(c) == 1 and len(prestates[k]) >= MIN_SUPPORT:
            token = next(iter(c))
            table[k] = exemplar[(k, token)]

    meta = {
        "observed_keys": len(obs),
        "deterministic_keys": sum(len(c) == 1 for c in obs.values()),
        "ambiguous_keys": sum(len(c) > 1 for c in obs.values()),
        "support_ge2_keys": sum(len(v) >= MIN_SUPPORT for v in prestates.values()),
        "usable_keys": len(table),
        "ambiguous_support_ge2_keys": sum(
            len(obs[k]) > 1 and len(prestates[k]) >= MIN_SUPPORT for k in obs
        ),
    }
    return table, meta


def evaluate_target(rows: list[dict[str, Any]], target_name: str, table):
    s = Counter()
    for r in rows:
        s["transitions"] += 1
        k = r280.candidate_key(r)
        pred = table.get(k)
        if pred is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        actual = targets(r)[target_name]
        s["correct" if pred == actual else "wrong"] += 1
    p = s["predictions"]
    return {
        **dict(s),
        "accuracy": round(s["correct"] / p, 6) if p else None,
        "coverage": round(p / s["transitions"], 6) if s["transitions"] else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    ps = sorted(a.input, key=r246.pnum)
    if not ps or any(r246.game_id(p) != GAME for p in ps):
        raise SystemExit(f"exact {GAME} traces required")
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise SystemExit(f"exact p0-p9 required; got {nums}")

    train = r278.annotated_rows(ps[:5])
    val = r278.annotated_rows(ps[5:10])

    target_names = (
        "raw_after_exact",
        "masked_after_exact",
        "regions8_after",
        "regions16_after",
        "nodes_coarse_after",
        "nodes_exact_after",
        "raw_delta",
        "interior_delta",
        "ui_delta",
        "masked_delta",
    )

    results = {}
    signals = []
    for name in target_names:
        tab, meta = fit_target(train, name)
        ev = evaluate_target(val, name, tab)
        results[name] = {"fit": meta, "validation": ev}
        if int(ev.get("predictions", 0)) > 0 and int(ev.get("wrong", 0)) == 0:
            signals.append({
                "target": name,
                "fit": meta,
                "validation": ev,
            })

    # Prefer executable delta operators over state-only descriptors when equal.
    priority = {
        "interior_delta": 0,
        "masked_delta": 1,
        "ui_delta": 2,
        "raw_delta": 3,
        "masked_after_exact": 4,
        "nodes_exact_after": 5,
        "regions16_after": 6,
        "regions8_after": 7,
        "nodes_coarse_after": 8,
        "raw_after_exact": 9,
    }
    ranked = sorted(
        signals,
        key=lambda x: (
            -int(x["validation"].get("correct", 0)),
            priority.get(x["target"], 99),
            -int(x["fit"].get("usable_keys", 0)),
        ),
    )

    out = {
        "schema": "deus/arc3-r281-lp85-renderer-ambiguity-decomp/1",
        "rung": RUNG,
        "lineage": {
            "r279_run": 35818105348,
            "r280_run": 35818287350,
            "r280_verdict": "NO_RENDERER_SIGNAL_P5P9",
            "r280_fit_p0_p4": {
                "observed_keys": 39,
                "support_ge2_keys": 15,
                "usable_keys": 0,
                "ambiguous_keys": 15,
            },
            "frozen_game": GAME,
            "frozen_representation": MODE,
        },
        "protocol": {
            "fit": "p0-p4",
            "diagnostic": "p5-p9",
            "p10_p19_staged_or_read": False,
            "representation_retuned": False,
            "threshold_retuned": False,
            "promotion_in_r281": False,
        },
        "targets": results,
        "zero_wrong_signals": ranked,
        "best_next_target": ranked[0]["target"] if ranked else None,
        "verdict": "TARGET_FACTORIZATION_SIGNAL" if ranked else "NO_FACTORIZATION_SIGNAL",
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "p10_p19_read": False,
            "diagnostic_only": True,
            "independent_hidden_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent_by_r281": False,
            "solver_promotion": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": out["verdict"],
        "best_next_target": out["best_next_target"],
        "signals": ranked,
        "raw_full": results["raw_after_exact"],
        "masked_full": results["masked_after_exact"],
        "interior_delta": results["interior_delta"],
        "ui_delta": results["ui_delta"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
