#!/usr/bin/env python3
"""R282: finer structural representation diagnostic for the remaining first-subset games.

R278 tested action-canonical coarse object/region/phase representations on
dc22, ft09, lp85, tr87, wa30 and found a clean new signal only for lp85.
R279 promoted lp85's region representation; R280/R281 then showed that exact
raw rendering still aliases fine/UI state. R282 therefore moves the OTHER FOUR
games to a materially finer structural family instead of retuning R278.

Targets:
  dc22, ft09, tr87, wa30

New candidates:
  - action-canonical exact component type/shape;
  - 16x16 coarse region field;
  - exact components + 16x16 regions;
  - same composite + past-only phase token;
  - action-canonical exact relational graph with edge-bar suppression.

Protocol: p0-p4 fit -> p5-p9 diagnostic only. p10-p19 are not staged/read.
No solver promotion or Kaggle claim occurs in R282.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_ui_mask_markov_diag_268 as r268
import public_relational_topology_diag_274 as r274
import public_action_canonical_topology_diag_275 as r275
import public_object_region_phase_diag_278 as r278

RUNG = 282
TARGET_PREFIXES = ("dc22", "ft09", "tr87", "wa30")
CONTROL_MODES = ("ui_mask", "canon_nodes_ui", "canon_regions_ui")
NEW_MODES = (
    "canon_nodes_exact_ui",
    "canon_regions16_ui",
    "canon_nodes_exact_regions16_ui",
    "canon_nodes_exact_regions16_phase_ui",
    "canon_graph_exact_noedge_ui",
)
ALL_MODES = CONTROL_MODES + NEW_MODES


def canon(board: list[list[int]], action: str):
    return r275.canon_board(board, action, use_ui_mask=True)


def rep_state(board: list[list[int]], action: str, mode: str, phase):
    a = str(action or "").upper()
    if mode in ("ui_mask", "canon_nodes_ui", "canon_regions_ui"):
        return r278.rep_state(board, a, mode, phase)

    b = canon(board, a)
    if mode == "canon_nodes_exact_ui":
        payload = ("nodes_exact", r274.desc(b, "nodes_exact"))
    elif mode == "canon_regions16_ui":
        payload = ("regions16", r246.regions(b, G=16))
    elif mode == "canon_nodes_exact_regions16_ui":
        payload = (
            "nodes_exact_regions16",
            r274.desc(b, "nodes_exact"),
            r246.regions(b, G=16),
        )
    elif mode == "canon_nodes_exact_regions16_phase_ui":
        payload = (
            "nodes_exact_regions16",
            r274.desc(b, "nodes_exact"),
            r246.regions(b, G=16),
            "phase",
            phase,
        )
    elif mode == "canon_graph_exact_noedge_ui":
        payload = ("graph_exact_noedge", r274.desc(b, "graph_exact_noedge"))
    else:
        raise KeyError(mode)
    return r274.dig(payload)


def action_class(action: str, mode: str) -> str:
    if mode == "ui_mask":
        return str(action or "").upper()
    return r275.action_class(action)


def before_key(r: dict[str, Any], mode: str):
    return (
        rep_state(r["before"], r["action"], mode, r["phase_before"]),
        action_class(r["action"], mode),
    )


def after_key(r: dict[str, Any], mode: str):
    return rep_state(r["after"], r["action"], mode, r["phase_after"])


def fit(rows: list[dict[str, Any]], mode: str):
    obs = defaultdict(Counter)
    counts = Counter()
    for r in rows:
        k = before_key(r, mode)
        n = after_key(r, mode)
        obs[k][n] += 1
        counts[k] += 1
    tab = {k: next(iter(v)) for k, v in obs.items() if len(v) == 1}
    return tab, {
        "keys": len(obs),
        "deterministic": len(tab),
        "ambiguous": sum(len(v) > 1 for v in obs.values()),
        "repeat_keys": sum(n >= 2 for n in counts.values()),
        "repeat_observations": sum(n for n in counts.values() if n >= 2),
    }


def evaluate(rows: list[dict[str, Any]], tab, mode: str):
    s = Counter()
    for r in rows:
        s["transitions"] += 1
        pred = tab.get(before_key(r, mode))
        if pred is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        actual = after_key(r, mode)
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

    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)

    resolved = {}
    for prefix in TARGET_PREFIXES:
        matches = sorted(g for g in by if g.startswith(prefix + "-") or g == prefix)
        if len(matches) != 1:
            raise SystemExit(f"{prefix}: expected exactly one game, got {matches}")
        resolved[prefix] = matches[0]
    if set(by) != set(resolved.values()):
        raise SystemExit(f"exact remaining first-subset four required, got {sorted(by)}")

    games = {}
    signals = []
    for prefix in TARGET_PREFIXES:
        g = resolved[prefix]
        ps = sorted(by[g], key=r246.pnum)
        nums = [r246.pnum(p) for p in ps]
        if nums != list(range(10)):
            raise SystemExit(f"{g}: exact p0-p9 required, got {nums}")

        train = r278.annotated_rows(ps[:5])
        val = r278.annotated_rows(ps[5:])
        modes = {}
        for mode in ALL_MODES:
            tab, fs = fit(train, mode)
            modes[mode] = {"fit": fs, "validation": evaluate(val, tab, mode)}

        best_control_correct = max(
            int(modes[m]["validation"].get("correct", 0)) for m in CONTROL_MODES
        )
        candidates = []
        for mode in NEW_MODES:
            v = modes[mode]["validation"]
            if (
                int(v.get("predictions", 0)) > 0
                and int(v.get("wrong", 0)) == 0
                and int(v.get("correct", 0)) > best_control_correct
            ):
                candidates.append(mode)

        if candidates:
            best = max(
                candidates,
                key=lambda m: (
                    int(modes[m]["validation"].get("correct", 0)),
                    int(modes[m]["fit"].get("repeat_keys", 0)),
                    -int(modes[m]["fit"].get("ambiguous", 0)),
                ),
            )
            signals.append({
                "prefix": prefix,
                "game": g,
                "mode": best,
                "candidate": modes[best]["validation"],
                "fit": modes[best]["fit"],
                "controls": {m: modes[m]["validation"] for m in CONTROL_MODES},
            })

        games[g] = {
            "prefix": prefix,
            "best_control_correct": best_control_correct,
            "diagnostic_signal_modes": candidates,
            "modes": modes,
        }

    out = {
        "schema": "deus/arc3-r282-fine-structure-first4-diagnostic/1",
        "rung": RUNG,
        "lineage": {
            "r278_run": 35817707053,
            "r279_run": 35818105348,
            "r280_run": 35818287350,
            "r281_run": 35818473648,
            "lp85_removed_after_representation_promotion": True,
        },
        "representation_delta": {
            "from": "R278 coarse nodes / region8 / phase",
            "to": "exact component shape, region16, exact-node+region16 composite, causal phase, exact relational graph",
            "ui_mask_retuned": False,
        },
        "protocol": {
            "fit": "p0-p4",
            "diagnostic": "p5-p9",
            "p10_p19_staged_or_read": False,
            "candidate_rule": "predictions>0, wrong=0, correct>best frozen control correct",
            "promotion_in_r282": False,
        },
        "target_prefixes": list(TARGET_PREFIXES),
        "resolved_games": resolved,
        "controls": list(CONTROL_MODES),
        "new_modes": list(NEW_MODES),
        "games": games,
        "signals": signals,
        "verdict": "DIAGNOSTIC_SIGNAL" if signals else "NO_SIGNAL",
        "truth": {
            "public_trace_only": True,
            "source_free_runtime_logic": True,
            "past_only_phase_features": True,
            "p10_p19_read": False,
            "independent_hidden_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent_by_r282": False,
            "solver_promotion": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": out["verdict"],
        "signal_count": len(signals),
        "signals": signals,
        "resolved_games": resolved,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
