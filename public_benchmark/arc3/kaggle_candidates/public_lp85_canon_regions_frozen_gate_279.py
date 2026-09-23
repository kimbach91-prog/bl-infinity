#!/usr/bin/env python3
"""R279: frozen lp85 canon_regions_ui public-development gate.

The candidate identity is frozen in this source file BEFORE any p10-p19 trace is
staged by the separate workflow commit:
  TARGET_GAME = lp85-305b61c3
  FROZEN_MODE = canon_regions_ui

Selection evidence came from R278 on p0-p4 fit -> p5-p9 diagnostic. R279 does
not select/tune on p10-p19. It refits the already-frozen representation on
p0-p9, then evaluates only p10-p19.

Truth boundary: p10-p19 are reused public development traces, not hidden Kaggle
data and not independent generalization. Scoring is exact next representation-
state transition fidelity for the frozen 8x8 action-canonical region state,
not exact full-frame rendering.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_object_region_phase_diag_278 as r278

RUNG = 279
TARGET_GAME = "lp85-305b61c3"
FROZEN_MODE = "canon_regions_ui"
FREEZE_PARENT_R278_RUN = 35817707053
FREEZE_PARENT_R278_HEAD = "d5c082770462b62fa20909859f3e97ab6177ef7f"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    by_game: dict[str, list[Path]] = {}
    for p in a.input:
        by_game.setdefault(r246.game_id(p), []).append(p)
    if set(by_game) != {TARGET_GAME}:
        raise SystemExit(f"exact frozen target {TARGET_GAME} required, got {sorted(by_game)}")

    ps = sorted(by_game[TARGET_GAME], key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(20)):
        raise SystemExit(f"exact p0-p19 required, got {nums}")

    train = r278.annotated_rows(ps[:10])
    held = r278.annotated_rows(ps[10:])
    tab, fit_stats = r278.fit(train, FROZEN_MODE)
    score = r278.evaluate(held, tab, FROZEN_MODE)

    predictions = int(score.get("predictions", 0) or 0)
    wrong = int(score.get("wrong", 0) or 0)
    if predictions > 0 and wrong == 0:
        verdict = "PASS_ZERO_WRONG_SIGNAL"
    elif predictions == 0:
        verdict = "NO_SIGNAL"
    else:
        verdict = "REJECT_MISMATCH"

    out: dict[str, Any] = {
        "schema": "deus/arc3-r279-lp85-canon-regions-frozen-gate/1",
        "rung": RUNG,
        "frozen_candidate": {
            "game": TARGET_GAME,
            "mode": FROZEN_MODE,
            "selected_by": "R278 p0-p4 fit -> p5-p9 diagnostic only",
            "parent_run": FREEZE_PARENT_R278_RUN,
            "parent_head": FREEZE_PARENT_R278_HEAD,
        },
        "protocol": {
            "selection_in_r279": False,
            "refit": "p0-p9 after candidate freeze",
            "frozen_gate": "p10-p19 reused public-development traces",
            "metric": "exact next representation-state transition",
            "full_frame_claim": False,
            "threshold_retuning_on_gate": False,
        },
        "fit": fit_stats,
        "gate": score,
        "verdict": verdict,
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "reused_public_development_p10_p19": True,
            "independent_hidden_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "owner_score_claim": False,
            "submission_quota_spent_by_r279": False,
            "solver_promotion_beyond_public_offline": False,
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "game": TARGET_GAME,
        "mode": FROZEN_MODE,
        "verdict": verdict,
        "fit": fit_stats,
        "gate": score,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
