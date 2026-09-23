#!/usr/bin/env python3
"""R286: frozen lp85 canon_regions_ui -> exact next-frame adapter.

Purpose: perform the smallest falsifying test after R279. Keep the R279
representation fixed (lp85 + canon_regions_ui) and ask whether that abstract
state/action key can safely emit an EXACT visible next frame when the exact
visible-state baseline abstains.

Protocol:
- candidate identity is fixed in this source before p10-p19 are staged by the
  separate workflow;
- fit on public p0-p9 only;
- candidate table keeps only abstract keys mapping to one exact next-frame
  digest with support from >=2 distinct exact pre-states;
- frozen evaluation on reused public-development p10-p19;
- exact visible-state/action baseline has precedence;
- promotion requires added predictions > 0 and wrong == 0.

Truth boundary: this is PUBLIC_OFFLINE source-free runtime logic over public
traces. It is not hidden generalization, Kaggle execution, a competition
submission, an owner leaderboard score, or a whole-game/action-policy claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278

RUNG = 286
TARGET_GAME = "lp85-305b61c3"
FROZEN_MODE = "canon_regions_ui"
PARENT_R279_RUN = 35818709235
MIN_DISTINCT_PRESTATES = 2


def fit_exact_frame_adapter(rows: list[dict[str, Any]]):
    obs = defaultdict(Counter)
    prestates = defaultdict(set)
    examples: dict[tuple[Any, str], list[list[int]]] = {}
    for r in rows:
        k = r278.before_key(r, FROZEN_MODE)
        d = r246.digest(r["after"])
        obs[k][d] += 1
        prestates[k].add(r246.digest(r["before"]))
        examples[(k, d)] = r["after"]

    tab = {}
    for k, outcomes in obs.items():
        if len(outcomes) != 1:
            continue
        if len(prestates[k]) < MIN_DISTINCT_PRESTATES:
            continue
        d = next(iter(outcomes))
        tab[k] = examples[(k, d)]

    return tab, {
        "abstract_keys_seen": len(obs),
        "safe_exact_frame_keys": len(tab),
        "ambiguous_exact_frame_keys": sum(len(v) > 1 for v in obs.values()),
        "keys_below_distinct_prestate_support": sum(
            len(v) == 1 and len(prestates[k]) < MIN_DISTINCT_PRESTATES
            for k, v in obs.items()
        ),
        "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
    }


def evaluate_added(rows: list[dict[str, Any]], exact_baseline, adapter):
    s = Counter()
    examples = []
    for r in rows:
        s["transitions"] += 1
        if r246.exact_key(r) in exact_baseline:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        pred = adapter.get(r278.before_key(r, FROZEN_MODE))
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == r["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 30:
            examples.append({
                "trace": r.get("trace"),
                "pnum": r.get("pnum"),
                "trace_row": r.get("trace_row"),
                "action": r.get("action"),
                "correct": ok,
            })

    p = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "candidate_accuracy": round(s["candidate_correct"] / p, 6) if p else None,
        "coverage_of_baseline_abstain": round(p / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by_game: dict[str, list[Path]] = defaultdict(list)
    for p in a.input:
        by_game[r246.game_id(p)].append(p)
    if set(by_game) != {TARGET_GAME}:
        raise SystemExit(f"exact frozen target {TARGET_GAME} required, got {sorted(by_game)}")

    ps = sorted(by_game[TARGET_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise SystemExit(f"exact p0-p19 required, got {nums}")

    fit_rows = r278.annotated_rows(ps[:10])
    gate_rows = r278.annotated_rows(ps[10:])
    exact_baseline = r246.fit_exact(fit_rows)
    adapter, fit_stats = fit_exact_frame_adapter(fit_rows)
    gate = evaluate_added(gate_rows, exact_baseline, adapter)

    preds = int(gate.get("candidate_predictions", 0) or 0)
    wrong = int(gate.get("candidate_wrong", 0) or 0)
    correct = int(gate.get("candidate_correct", 0) or 0)
    if preds > 0 and wrong == 0 and correct > 0:
        verdict = "PASS_ZERO_WRONG_EXACT_FRAME_GAIN"
    elif preds == 0:
        verdict = "NO_SIGNAL"
    else:
        verdict = "REJECT_MISMATCH"

    out = {
        "schema": "deus/arc3-r286-lp85-canon-regions-exact-frame-adapter/1",
        "rung": RUNG,
        "frozen_candidate": {
            "game": TARGET_GAME,
            "mode": FROZEN_MODE,
            "selected_by": "R278 diagnostic -> R279 frozen representation-state gate",
            "parent_r279_run": PARENT_R279_RUN,
            "min_distinct_prestates": MIN_DISTINCT_PRESTATES,
        },
        "protocol": {
            "candidate_selection_in_r286": False,
            "fit": "p0-p9 public traces only",
            "frozen_gate": "p10-p19 reused public-development traces",
            "baseline": "exact visible-state/action -> exact next frame",
            "candidate": "frozen canon_regions_ui/action -> unique exact next frame with >=2 distinct exact pre-states",
            "baseline_precedence": True,
            "threshold_retuning_on_gate": False,
            "metric": "incremental exact next-frame predictions over exact baseline",
        },
        "fit": {
            "exact_baseline_keys": len(exact_baseline),
            **fit_stats,
        },
        "gate": gate,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "reused_public_development_p10_p19": True,
            "independent_hidden_generalization_claim": False,
            "whole_game_policy_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r286": False,
            "solver_promotion_beyond_public_offline": False,
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "fit": out["fit"], "gate": gate}, sort_keys=True))


if __name__ == "__main__":
    main()
