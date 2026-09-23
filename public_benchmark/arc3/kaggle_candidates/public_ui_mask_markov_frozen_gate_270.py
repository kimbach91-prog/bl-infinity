#!/usr/bin/env python3
"""R270: frozen static-UI-mask Markov representation gate on public p10-p19.

The candidate set is frozen from the prior R268 p0-p4 fit / p5-p9 diagnostic
before this program reads any p10-p19 trace. R270 does not re-select games,
thresholds, masks, or model rules from p10-p19. It compares the frozen static
UI-mask representation with the raw-state representation using the same
p0-p4 action-conditional transition table protocol.

Truth boundary:
  * public ARC-AGI-3 traces only;
  * source-assisted representation idea, independently implemented;
  * p0-p4 fit, p10-p19 frozen public holdout evaluation;
  * p5-p9 are not read by R270 (they were used by prior R268 to freeze set);
  * no model update or selector retune on p10-p19;
  * representation/state-key gate only, not full-frame solver or Kaggle score.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268

RUNG = 270
R268_ARTIFACT_ID = 10726568095
R268_HEAD = "b0ede7e3a2aec847675e6de5bafb7ecfcefe6e91"
FROZEN_GAMES = (
    "ar25-0c556536",
    "ft09-0d8bbf25",
    "ka59-38d34dbb",
    "lf52-271a04aa",
    "lp85-305b61c3",
    "r11l-495a7899",
    "re86-8af5384d",
    "s5i5-18d95033",
    "su15-1944f8ab",
    "tn36-ef4dde99",
    "tr87-cd924810",
    "tu93-0768757b",
    "vc33-5430563c",
    "wa30-ee6fef47",
)
EXPECTED_PNUMS = tuple(range(5)) + tuple(range(10, 20))


def evaluate_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = tuple(r246.pnum(p) for p in ps)
    if nums != EXPECTED_PNUMS:
        raise ValueError(f"exact p0-p4+p10-p19 required, got {nums}")
    fit_paths = [p for p in ps if r246.pnum(p) <= 4]
    holdout_paths = [p for p in ps if r246.pnum(p) >= 10]
    tr = r268.rows(fit_paths)
    va = r268.rows(holdout_paths)
    out: dict[str, Any] = {}
    for mode in ("raw", "ui_mask"):
        table, fit = r268.fit_table(tr, mode)
        out[mode] = {
            "fit": fit,
            "holdout": r268.evaluate(va, table, mode),
        }
    rv = out["raw"]["holdout"]
    mv = out["ui_mask"]["holdout"]
    out["delta"] = {
        "correct": int(mv.get("correct", 0)) - int(rv.get("correct", 0)),
        "wrong": int(mv.get("wrong", 0)) - int(rv.get("wrong", 0)),
        "predictions": int(mv.get("predictions", 0)) - int(rv.get("predictions", 0)),
    }
    out["game_gate"] = bool(
        int(mv.get("wrong", 0)) == 0
        and int(mv.get("correct", 0)) > int(rv.get("correct", 0))
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by: dict[str, list[Path]] = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    if set(by) != set(FROZEN_GAMES):
        raise SystemExit(
            f"input games must equal frozen set; missing={sorted(set(FROZEN_GAMES)-set(by))} "
            f"extra={sorted(set(by)-set(FROZEN_GAMES))}"
        )

    games = {g: evaluate_game(by[g]) for g in FROZEN_GAMES}
    aggregate = Counter()
    for x in games.values():
        for mode in ("raw", "ui_mask"):
            v = x[mode]["holdout"]
            for k in ("transitions", "predictions", "correct", "wrong", "abstain"):
                aggregate[f"{mode}_{k}"] += int(v.get(k, 0) or 0)

    raw_p = aggregate["raw_predictions"]
    mask_p = aggregate["ui_mask_predictions"]
    agg = dict(aggregate)
    agg["raw_accuracy"] = round(aggregate["raw_correct"] / raw_p, 6) if raw_p else None
    agg["ui_mask_accuracy"] = round(aggregate["ui_mask_correct"] / mask_p, 6) if mask_p else None
    agg["correct_delta"] = aggregate["ui_mask_correct"] - aggregate["raw_correct"]
    agg["wrong_delta"] = aggregate["ui_mask_wrong"] - aggregate["raw_wrong"]
    promoted_games = [g for g, x in games.items() if x["game_gate"]]

    promote = bool(
        aggregate["ui_mask_wrong"] == 0
        and aggregate["ui_mask_correct"] > aggregate["raw_correct"]
        and promoted_games
    )
    verdict = "PROMOTE_REPRESENTATION_GATE" if promote else "NO_PROMOTION"

    out = {
        "schema": "deus/arc3-r270-ui-mask-frozen-public-holdout/1",
        "rung": RUNG,
        "frozen_from": {
            "rung": 268,
            "head": R268_HEAD,
            "artifact_id": R268_ARTIFACT_ID,
            "selection_rule": "R268 p5-p9: ui_mask wrong == 0 and correct_delta > 0",
            "games": list(FROZEN_GAMES),
        },
        "protocol": {
            "fit": "p0-p4",
            "selector_freeze_source": "prior R268 p5-p9 diagnostic only",
            "r270_p5_p9_read": False,
            "holdout_eval": "p10-p19",
            "p10_p19_model_update": False,
            "p10_p19_selector_retune": False,
            "metric": "next normalized-state-key prediction under matched raw vs static-ui-mask representations",
            "promotion_rule": "aggregate ui_mask wrong == 0 AND ui_mask correct > raw correct",
        },
        "aggregate": agg,
        "promoted_games": promoted_games,
        "games": games,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_assisted_representation_idea": True,
            "independent_generalization_claim": False,
            "full_frame_solver_claim": False,
            "hidden_kaggle_score_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "aggregate": agg,
        "promoted_games": promoted_games,
        "verdict": verdict,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
