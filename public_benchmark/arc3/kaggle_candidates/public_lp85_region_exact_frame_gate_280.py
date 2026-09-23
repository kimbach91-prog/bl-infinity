#!/usr/bin/env python3
"""R280: conservative exact-frame renderer gate for the frozen lp85 region representation.

Lineage:
- R278 selected lp85-305b61c3 / canon_regions_ui using p0-p4 -> p5-p9 only.
- R279 froze that selector before p10-p19 and promoted the representation:
  632/632 correct state-representation predictions, zero wrong.

R280 asks the stricter question: can that frozen representation add exact raw
next-frame predictions beyond the exact visible-state/action baseline?

Renderer semantics are fixed before heldout:
- directional actions are canonicalized to UP;
- candidate key is the frozen canon_regions_ui state + action class;
- target is the FULL RAW after-frame canonicalized by the same action;
- a candidate key is usable only if it maps to exactly one canonical raw frame
  and has support from >=2 distinct raw pre-state digests;
- prediction is inverse-rotated back to the original action orientation;
- exact visible-state/action baseline always has precedence.

Protocol:
  p0-p4 fit -> p5-p9 renderer diagnostic.
  Only if diagnostic has >=1 incremental exact-frame prediction and zero wrong:
  refit unchanged renderer on p0-p9 -> frozen p10-p19 evaluation.

PUBLIC_OFFLINE reused development only. No hidden/Kaggle claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG = 280
GAME = "lp85-305b61c3"
MODE = "canon_regions_ui"
MIN_PRESTATE_SUPPORT = 2


def exact_key(r: dict[str, Any]) -> str:
    return r246.digest({"before": r["before"], "action": r["action"]})


def fit_exact(rows: list[dict[str, Any]]):
    obs = defaultdict(Counter)
    frame = {}
    for r in rows:
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


def canon_raw(board: list[list[int]], action: str) -> list[list[int]]:
    return r275.canon_board(board, action, use_ui_mask=False)


def inverse_canon(board: list[list[int]], action: str) -> list[list[int]]:
    a = str(action or "").upper()
    if a == "UP":
        return [list(row) for row in board]
    if a == "DOWN":
        return r275.rot_180(board)
    if a == "LEFT":
        return r275.rot_ccw(board)
    if a == "RIGHT":
        return r275.rot_cw(board)
    return [list(row) for row in board]


def candidate_key(r: dict[str, Any]):
    # R278's frozen mode ignores phase but still uses its exact action-canonical
    # region representation and MOVE pooling.
    return r278.before_key(r, MODE)


def fit_candidate(rows: list[dict[str, Any]]):
    obs = defaultdict(Counter)
    prestates = defaultdict(set)
    frame = {}
    for r in rows:
        k = candidate_key(r)
        target = canon_raw(r["after"], r["action"])
        d = r246.digest(target)
        obs[k][d] += 1
        prestates[k].add(r["before_digest"])
        frame[(k, d)] = target

    out = {}
    support = {}
    ambiguous = 0
    for k, c in obs.items():
        if len(c) != 1:
            ambiguous += 1
            continue
        if len(prestates[k]) < MIN_PRESTATE_SUPPORT:
            continue
        d = next(iter(c))
        out[k] = frame[(k, d)]
        support[k] = len(prestates[k])

    return out, {
        "observed_keys": len(obs),
        "usable_keys": len(out),
        "ambiguous_keys": ambiguous,
        "min_distinct_raw_prestates": MIN_PRESTATE_SUPPORT,
        "support_ge2_keys": sum(len(v) >= MIN_PRESTATE_SUPPORT for v in prestates.values()),
    }, support


def evaluate(rows: list[dict[str, Any]], exact, candidate):
    s = Counter()
    examples = []
    for r in rows:
        s["transitions"] += 1
        if exact_key(r) in exact:
            s["baseline_predictions"] += 1
            continue

        s["baseline_abstain"] += 1
        canon_pred = candidate.get(candidate_key(r))
        if canon_pred is None:
            s["candidate_abstain"] += 1
            continue

        pred = inverse_canon(canon_pred, r["action"])
        s["candidate_predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 30:
            examples.append({
                "trace": r["trace"],
                "pnum": r["pnum"],
                "trace_row": r["trace_row"],
                "action": r["action"],
                "correct": ok,
            })

    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "candidate_accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "incremental_coverage": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
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
    if nums != list(range(20)):
        raise SystemExit(f"exact p0-p19 required, got {nums}")

    parts = [r278.annotated_rows([p]) for p in ps]
    tr = [r for part in parts[:5] for r in part]
    va = [r for part in parts[5:10] for r in part]
    fit = [r for part in parts[:10] for r in part]
    hold = [r for part in parts[10:] for r in part]

    exact_tr = fit_exact(tr)
    cand_tr, cand_tr_meta, _ = fit_candidate(tr)
    diagnostic = evaluate(va, exact_tr, cand_tr)
    diagnostic_pass = bool(
        int(diagnostic.get("candidate_predictions", 0)) > 0
        and int(diagnostic.get("candidate_wrong", 0)) == 0
    )

    heldout = None
    fit_meta = None
    promoted = False
    if diagnostic_pass:
        exact_fit = fit_exact(fit)
        cand_fit, fit_meta, _ = fit_candidate(fit)
        heldout = evaluate(hold, exact_fit, cand_fit)
        promoted = bool(
            int(heldout.get("candidate_predictions", 0)) > 0
            and int(heldout.get("candidate_wrong", 0)) == 0
        )

    if promoted:
        verdict = "PROMOTE_INCREMENTAL_EXACT_FRAME_RENDERER"
    elif diagnostic_pass:
        verdict = "NO_PROMOTION_FROZEN_HELDOUT"
    else:
        verdict = "NO_RENDERER_SIGNAL_P5P9"

    out = {
        "schema": "deus/arc3-r280-lp85-region-exact-frame-gate/1",
        "rung": RUNG,
        "lineage": {
            "r278_run": 35817707053,
            "r279_run": 35818105348,
            "r279_head": "f6993abf2c739113b5b76151637b725085f94b60",
            "r279_artifact": 10731339197,
            "frozen_game": GAME,
            "frozen_representation": MODE,
            "r279_representation_promoted": True,
        },
        "renderer": {
            "candidate_key": "frozen canon_regions_ui before-state + action class",
            "target": "full raw after-frame in action-canonical orientation",
            "inverse_rotation_to_original_frame": True,
            "exact_baseline_precedence": True,
            "min_distinct_raw_prestates": MIN_PRESTATE_SUPPORT,
        },
        "protocol": {
            "renderer_diagnostic_fit": "p0-p4",
            "renderer_diagnostic_eval": "p5-p9",
            "diagnostic_pass_rule": "incremental exact-frame predictions>0 and wrong=0",
            "refit_after_diagnostic_pass": "p0-p9 with unchanged renderer semantics",
            "frozen_eval": "p10-p19 reused public-development",
            "p10_p19_updates_renderer": False,
            "p10_p19_updates_representation": False,
            "p10_p19_updates_model": False,
        },
        "fit_p0_p4": cand_tr_meta,
        "diagnostic_p5_p9": diagnostic,
        "diagnostic_pass": diagnostic_pass,
        "fit_p0_p9": fit_meta,
        "heldout_p10_p19": heldout,
        "exact_frame_promoted": promoted,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "reused_public_development_holdout": True,
            "representation_frozen_before_r280": True,
            "renderer_semantics_fixed_before_p10_p19": True,
            "independent_hidden_generalization_claim": False,
            "full_game_policy_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent_by_r280": False,
        },
    }

    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "diagnostic": diagnostic,
        "heldout": heldout,
        "fit_p0_p4": cand_tr_meta,
        "fit_p0_p9": fit_meta,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
