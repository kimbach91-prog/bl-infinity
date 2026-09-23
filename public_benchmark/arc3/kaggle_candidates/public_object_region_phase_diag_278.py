#!/usr/bin/env python3
"""R278: object/region/phase diagnostic for the first five R272M residual games.

Goal:
- leave the frozen R272 exact-frame stack untouched;
- do not retune the static UI mask;
- test a materially different causal representation on the first residual subset:
  dc22, ft09, lp85, tr87, wa30.

Representation changes:
1) rotate directional actions into the same UP-oriented frame (R275 symmetry);
2) combine translation-invariant connected-component type/shape with an 8x8
   coarse region field;
3) optionally add a causal phase token derived only from PAST actions:
   relative previous direction + capped previous-action run length.

Protocol is fit p0-p4 -> diagnostic p5-p9 only. p10-p19 must not be staged/read.
This run may nominate a representation for a later frozen gate; it cannot promote
a solver or make a Kaggle/hidden-performance claim.
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

RUNG = 278
TARGET_PREFIXES = ("dc22", "ft09", "lp85", "tr87", "wa30")
DIR_ORDER = ("UP", "RIGHT", "DOWN", "LEFT")
NEW_MODES = (
    "canon_regions_ui",
    "canon_regions_phase_ui",
    "canon_nodes_regions_ui",
    "canon_nodes_regions_phase_ui",
)
CONTROL_MODES = ("ui_mask", "canon_nodes_ui")
ALL_MODES = CONTROL_MODES + NEW_MODES


def _action(a: Any) -> str:
    return str(a or "").upper()


def relative_prev(prev_action: str | None, current_action: str) -> str:
    """Express the previous direction relative to the current direction.

    This is strictly causal: only the already-observed previous action is used.
    """
    cur = _action(current_action)
    if prev_action is None:
        return "START"
    prev = _action(prev_action)
    if cur not in DIR_ORDER:
        return "PREV_" + (prev if prev else "NONE")
    if prev not in DIR_ORDER:
        return "PREV_NONDIR_" + (prev if prev else "NONE")
    d = (DIR_ORDER.index(prev) - DIR_ORDER.index(cur)) % 4
    return ("SAME", "PREV_RIGHT", "OPPOSITE", "PREV_LEFT")[d]


def annotated_rows(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(paths, key=r246.pnum):
        prev: str | None = None
        prev_run = 0
        for idx, r in enumerate(r268.rows([p])):
            rr = dict(r)
            rr["trace_row"] = idx
            rr["pnum"] = r246.pnum(p)
            rr["phase_before"] = (relative_prev(prev, r["action"]), min(prev_run, 3))
            cur = _action(r["action"])
            if prev is not None and cur == _action(prev):
                run_after = prev_run + 1
            else:
                run_after = 1
            rr["phase_after"] = ("SAME", min(run_after, 3))
            out.append(rr)
            prev = cur
            prev_run = run_after
    return out


def canon(board: list[list[int]], action: str) -> list[list[int]]:
    return r275.canon_board(board, action, use_ui_mask=True)


def regions_desc(board: list[list[int]], action: str):
    return r246.regions(canon(board, action), G=8)


def nodes_desc(board: list[list[int]], action: str):
    return r274.desc(canon(board, action), "nodes_coarse")


def rep_state(board: list[list[int]], action: str, mode: str, phase):
    a = _action(action)
    if mode == "ui_mask":
        return r268.state_key(board, "ui_mask")
    if mode == "canon_nodes_ui":
        return r274.dig(nodes_desc(board, a))

    reg = regions_desc(board, a)
    if mode == "canon_regions_ui":
        payload = ("regions8", reg)
    elif mode == "canon_regions_phase_ui":
        payload = ("regions8", reg, "phase", phase)
    elif mode == "canon_nodes_regions_ui":
        payload = ("nodes_regions", nodes_desc(board, a), reg)
    elif mode == "canon_nodes_regions_phase_ui":
        payload = ("nodes_regions", nodes_desc(board, a), reg, "phase", phase)
    else:
        raise KeyError(mode)
    return r274.dig(payload)


def action_class(action: str, mode: str) -> str:
    # Preserve R268's raw action labels for the UI-mask control.
    # New action-canonical modes pool directions as MOVE after rotation.
    if mode == "ui_mask":
        return _action(action)
    return r275.action_class(action)


def before_key(r: dict[str, Any], mode: str):
    return (
        rep_state(r["before"], r["action"], mode, r["phase_before"]),
        action_class(r["action"], mode),
    )


def after_key(r: dict[str, Any], mode: str):
    # The next phase token is known immediately after applying the current action.
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

    by: dict[str, list[Path]] = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)

    resolved_prefixes = {}
    for prefix in TARGET_PREFIXES:
        matches = sorted(g for g in by if g.startswith(prefix + "-") or g == prefix)
        if len(matches) != 1:
            raise SystemExit(f"{prefix}: expected exactly one game, got {matches}")
        resolved_prefixes[prefix] = matches[0]

    if set(by) != set(resolved_prefixes.values()):
        raise SystemExit(f"exact first residual five required, got {sorted(by)}")

    games = {}
    signals = []
    for prefix in TARGET_PREFIXES:
        g = resolved_prefixes[prefix]
        ps = sorted(by[g], key=r246.pnum)
        nums = [r246.pnum(p) for p in ps]
        if nums != list(range(10)):
            raise SystemExit(f"{g}: exact p0-p9 required, got {nums}")

        train = annotated_rows(ps[:5])
        val = annotated_rows(ps[5:])
        modes = {}
        for mode in ALL_MODES:
            tab, fs = fit(train, mode)
            modes[mode] = {"fit": fs, "validation": evaluate(val, tab, mode)}

        best_control_correct = max(int(modes[m]["validation"].get("correct", 0)) for m in CONTROL_MODES)
        best_control_wrong = min(int(modes[m]["validation"].get("wrong", 0)) for m in CONTROL_MODES)

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
                "game": g,
                "prefix": prefix,
                "mode": best,
                "candidate": modes[best]["validation"],
                "fit": modes[best]["fit"],
                "control_ui_mask": modes["ui_mask"]["validation"],
                "control_canon_nodes_ui": modes["canon_nodes_ui"]["validation"],
            })

        games[g] = {
            "prefix": prefix,
            "controls": list(CONTROL_MODES),
            "new_modes": list(NEW_MODES),
            "best_control_correct": best_control_correct,
            "best_control_wrong": best_control_wrong,
            "diagnostic_signal_modes": candidates,
            "modes": modes,
        }

    out = {
        "schema": "deus/arc3-r278-object-region-phase-diagnostic/1",
        "rung": RUNG,
        "objective": "first R272M residual five: test object+region+causal-phase representations without UI-mask retuning",
        "representation_delta": {
            "action_canonicalization": "directional actions rotate to UP and pool as MOVE",
            "object": "translation-invariant nodes_coarse from R274",
            "region": "8x8 coarse region field on action-canonical UI-masked board",
            "phase": "previous-action relation to current action + capped previous-action run length; past-only",
            "controls": list(CONTROL_MODES),
        },
        "protocol": {
            "fit": "p0-p4",
            "diagnostic": "p5-p9",
            "p10_p19_staged_or_read": False,
            "candidate_rule": "new mode predictions>0, wrong=0, correct>best(ui_mask,canon_nodes_ui) control correct",
            "promotion_in_r278": False,
            "next_if_signal": "freeze exact game+mode before any p10-p19 read; refit p0-p9; run separate frozen gate",
        },
        "target_prefixes": list(TARGET_PREFIXES),
        "resolved_games": resolved_prefixes,
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
            "submission_quota_spent_by_r278": False,
            "solver_promotion": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": out["verdict"],
        "signal_count": len(signals),
        "signals": signals,
        "resolved_games": resolved_prefixes,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
