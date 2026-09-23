#!/usr/bin/env python3
"""R266: source-free contextual object-interaction residual gate for re86.

R264 verified that post-transport residuals concentrate in object-relative
coordinates; R265 showed that generic action/object-local sparse corrections
still do not generalize. R266 therefore conditions residual repair on the
moved object's persistent identity/orientation plus its source/destination
local interaction context (contact/occlusion/background topology).

Protocol:
  p0-p4 fit contextual local residual rules
  p5-p9 select per action only when added predictions >0 and ZERO wrong
  p0-p9 refit selected variant
  p10-p19 frozen reused public-development evaluation

Exact visible-state/action lookup retains precedence. No game source, hidden
state, Kaggle score, leaderboard information, or competition outcome is read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251
import public_component_delta_operator_254 as r254
import public_selective_object_transport_257 as r257

RUNG = 266
MAX_AREA = 13
MIN_FRAC = 0.80
MIN_SUPPORT = 3

# (mode, context padding, edit radius, minimum distinct trace support)
VARIANTS = tuple(
    (mode, pad, edit_radius, support)
    for mode in ("dest_coarse", "source_dest_coarse", "source_dest_color")
    for pad in (1, 2, 3)
    for edit_radius in (8, 12)
    for support in (2, 3)
)


def prep(path: Path) -> list[dict[str, Any]]:
    out = []
    for i, row in enumerate(r251.prepare_rows([path])):
        x = dict(row)
        x["transition_id"] = f"{path.name}#{i}"
        out.append(x)
    return out


def fit_base(rows: list[dict[str, Any]]):
    return r257.learn(rows, MAX_AREA, MIN_FRAC, MIN_SUPPORT)


def movable_components(board: list[list[int]], model):
    vector, movable = model
    if not vector or not movable:
        return []
    dr, dc = vector
    h, w = len(board), len(board[0])
    comps = []
    for c in r254.components(board):
        if c["area"] > MAX_AREA or r257.cls(c) not in movable:
            continue
        if c["r0"] + dr < 0 or c["c0"] + dc < 0:
            continue
        if c["r1"] + dr >= h or c["c1"] + dc >= w:
            continue
        comps.append(c)
    return comps


def local_signature(
    board: list[list[int]],
    comp: dict[str, Any],
    *,
    dest_vector: tuple[int, int] | None,
    pad: int,
    color_sensitive: bool,
):
    bg = int(r246.bg(board))
    dr, dc = dest_vector or (0, 0)
    r0, r1 = comp["r0"] + dr, comp["r1"] + dr
    c0, c1 = comp["c0"] + dc, comp["c1"] + dc
    own = {(comp["r0"] + rr + dr, comp["c0"] + cc + dc) for rr, cc in comp["shape"]}
    h, w = len(board), len(board[0])
    sig = []
    for rr in range(r0 - pad, r1 + pad + 1):
        row = []
        for cc in range(c0 - pad, c1 + pad + 1):
            if not (0 <= rr < h and 0 <= cc < w):
                row.append(("OOB",))
            elif (rr, cc) in own:
                row.append(("SELF",))
            else:
                v = int(board[rr][cc])
                if color_sensitive:
                    row.append(("C", v))
                else:
                    row.append(("BG",) if v == bg else ("OTHER",))
        sig.append(tuple(row))
    return tuple(sig)


def context_key(row, comp, base, model, mode: str, pad: int):
    vector, _ = model
    cls = r257.cls(comp)
    color_sensitive = mode == "source_dest_color"
    dest_sig = local_signature(
        base, comp, dest_vector=vector, pad=pad, color_sensitive=color_sensitive
    )
    if mode == "dest_coarse":
        src_sig = None
    else:
        src_sig = local_signature(
            row["before"], comp, dest_vector=None, pad=pad, color_sensitive=color_sensitive
        )
    dr, dc = vector
    h, w = len(row["before"]), len(row["before"][0])
    edge = (
        min(comp["r0"], 6),
        min(comp["c0"], 6),
        min(h - 1 - comp["r1"], 6),
        min(w - 1 - comp["c1"], 6),
        int(dr),
        int(dc),
    )
    return r246.stable((row["action"], cls, src_sig, dest_sig, edge))


def assign_residuals(base, actual, comps, vector):
    dr, dc = vector
    assigned = defaultdict(list)
    for rr in range(len(base)):
        for cc in range(len(base[0])):
            if int(base[rr][cc]) == int(actual[rr][cc]):
                continue
            ranked = []
            for i, c in enumerate(comps):
                r0, c0 = c["r0"] + dr, c["c0"] + dc
                cr = (r0 + c["r1"] + dr) / 2.0
                co = (c0 + c["c1"] + dc) / 2.0
                ranked.append((abs(rr - cr) + abs(cc - co), i, r0, c0))
            if not ranked:
                return None
            _, i, r0, c0 = min(ranked)
            assigned[i].append((rr - r0, cc - c0, int(actual[rr][cc])))
    return assigned


def fit_rules(rows, model, mode: str, pad: int, edit_radius: int, support: int):
    observations = defaultdict(Counter)
    traces = defaultdict(lambda: defaultdict(set))
    for row in rows:
        base = r257.render(row["before"], model[0], model[1], MAX_AREA)
        comps = movable_components(row["before"], model)
        if base is None or not comps:
            continue
        assigned = assign_residuals(base, row["after"], comps, model[0])
        if assigned is None:
            continue
        for i, comp in enumerate(comps):
            edits = assigned.get(i, [])
            if not edits:
                continue
            if any(abs(orr) > edit_radius or abs(occ) > edit_radius for orr, occ, _ in edits):
                continue
            outcome = tuple(sorted((int(orr), int(occ), int(v)) for orr, occ, v in edits))
            key = context_key(row, comp, base, model, mode, pad)
            observations[key][outcome] += 1
            traces[key][outcome].add(row["trace"])
    rules = {}
    for key, counts in observations.items():
        if len(counts) != 1:
            continue
        outcome = next(iter(counts))
        if len(traces[key][outcome]) >= support:
            rules[key] = outcome
    return rules


def apply(row, model, rules, mode: str, pad: int):
    base = r257.render(row["before"], model[0], model[1], MAX_AREA)
    comps = movable_components(row["before"], model)
    if base is None or not comps:
        return None
    dr, dc = model[0]
    proposals = defaultdict(set)
    matched_rules = 0
    for comp in comps:
        key = context_key(row, comp, base, model, mode, pad)
        outcome = rules.get(key)
        if outcome is None:
            continue
        matched_rules += 1
        r0, c0 = comp["r0"] + dr, comp["c0"] + dc
        for orr, occ, value in outcome:
            rr, cc = r0 + orr, c0 + occ
            if not (0 <= rr < len(base) and 0 <= cc < len(base[0])):
                return None
            proposals[(rr, cc)].add(int(value))
    if matched_rules == 0 or any(len(v) != 1 for v in proposals.values()):
        return None
    out = [r[:] for r in base]
    for (rr, cc), values in proposals.items():
        out[rr][cc] = next(iter(values))
    return out


def evaluate(rows, exact, model, rules, mode: str, pad: int):
    s = Counter()
    examples = []
    for row in rows:
        s["transitions"] += 1
        if row["exact_key"] in exact:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        pred = apply(row, model, rules, mode, pad)
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        if len(examples) < 20:
            examples.append({"trace": row["trace"], "action": row["action"], "correct": ok})
    n = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    return {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / n, 6) if n else None,
        "coverage_of_baseline_abstain": round(n / opp, 6) if opp else 0.0,
        "examples": examples,
    }


def evaluate_game(paths: list[Path]):
    ps = sorted(paths, key=r246.pnum)
    if [r246.pnum(p) for p in ps] != list(range(20)):
        raise ValueError("exact p0..p19 required")
    parts = [prep(p) for p in ps]
    tr = [r for part in parts[:5] for r in part]
    va = [r for part in parts[5:10] for r in part]
    fit = [r for part in parts[:10] for r in part]
    ho = [r for part in parts[10:] for r in part]

    tr_by = defaultdict(list)
    va_by = defaultdict(list)
    fit_by = defaultdict(list)
    for r in tr:
        tr_by[r["action"]].append(r)
    for r in va:
        va_by[r["action"]].append(r)
    for r in fit:
        fit_by[r["action"]].append(r)

    exact_tr = r251.fit_exact(tr)
    selected = {}
    diagnostics = {}
    for action in sorted(set(tr_by) | set(va_by)):
        base = fit_base(tr_by[action])
        candidates = {}
        for mode, pad, edit_radius, support in VARIANTS:
            rules = fit_rules(tr_by[action], base, mode, pad, edit_radius, support)
            met = evaluate(va_by[action], exact_tr, base, rules, mode, pad)
            key = f"{mode}_p{pad}_e{edit_radius}_s{support}"
            candidates[key] = {
                "mode": mode,
                "pad": pad,
                "edit_radius": edit_radius,
                "support": support,
                "rule_count": len(rules),
                "base_vector": list(base[0]) if base and base[0] else None,
                "validation": met,
            }
        zero = [
            k for k, v in candidates.items()
            if v["validation"].get("candidate_correct", 0) > 0
            and v["validation"].get("candidate_wrong", 0) == 0
        ]
        if zero:
            zero.sort(
                key=lambda k: (
                    -candidates[k]["validation"].get("candidate_correct", 0),
                    -candidates[k]["validation"].get("candidate_predictions", 0),
                    candidates[k]["rule_count"],
                    k,
                )
            )
            selected[action] = zero[0]
        diagnostics[action] = candidates

    exact_fit = r251.fit_exact(fit)
    refit = {}
    for action, key in selected.items():
        spec = diagnostics[action][key]
        base = fit_base(fit_by[action])
        rules = fit_rules(
            fit_by[action],
            base,
            spec["mode"],
            spec["pad"],
            spec["edit_radius"],
            spec["support"],
        )
        refit[action] = (base, rules, spec)

    s = Counter()
    by_action = defaultdict(Counter)
    examples = []
    for row in ho:
        s["transitions"] += 1
        if row["exact_key"] in exact_fit:
            s["exact_baseline"] += 1
            continue
        s["baseline_abstain"] += 1
        pack = refit.get(row["action"])
        if pack is None:
            s["candidate_abstain"] += 1
            continue
        base, rules, spec = pack
        pred = apply(row, base, rules, spec["mode"], spec["pad"])
        if pred is None:
            s["candidate_abstain"] += 1
            continue
        s["candidate_predictions"] += 1
        by_action[row["action"]]["predictions"] += 1
        ok = pred == row["after"]
        s["candidate_correct" if ok else "candidate_wrong"] += 1
        by_action[row["action"]]["correct" if ok else "wrong"] += 1
        if len(examples) < 30:
            examples.append(
                {
                    "trace": row["trace"],
                    "action": row["action"],
                    "variant": selected[row["action"]],
                    "correct": ok,
                }
            )

    n = s["candidate_predictions"]
    opp = s["baseline_abstain"]
    held = {
        **dict(s),
        "accuracy": round(s["candidate_correct"] / n, 6) if n else None,
        "coverage_of_baseline_abstain": round(n / opp, 6) if opp else 0.0,
        "by_action": {a: dict(v) for a, v in by_action.items()},
        "examples": examples,
    }
    gain = bool(n > 0 and s["candidate_wrong"] == 0 and s["candidate_correct"] > 0)
    return {
        "selected_by_action": selected,
        "selection_diagnostic": diagnostics,
        "heldout": held,
        "gain": gain,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    by = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    games = {g: evaluate_game(ps) for g, ps in sorted(by.items())}
    agg = Counter()
    gain_games = []
    for g, x in games.items():
        h = x["heldout"]
        for k in (
            "transitions",
            "exact_baseline",
            "baseline_abstain",
            "candidate_predictions",
            "candidate_correct",
            "candidate_wrong",
        ):
            agg[k] += int(h.get(k, 0) or 0)
        if x["gain"]:
            gain_games.append(g)
    n = agg["candidate_predictions"]
    opp = agg["baseline_abstain"]
    aggregate = {
        **dict(agg),
        "candidate_accuracy": round(agg["candidate_correct"] / n, 6) if n else None,
        "candidate_coverage_of_baseline_abstain": round(n / opp, 6) if opp else 0.0,
        "gain_games": gain_games,
        "gain_game_count": len(gain_games),
        "game_count": len(games),
    }
    nd = bool(n > 0 and agg["candidate_wrong"] == 0 and agg["candidate_correct"] > 0)
    out = {
        "schema": "deus/arc3-r266-contextual-object-interaction-gate/1",
        "rung": RUNG,
        "lineage": {
            "r264": "object-relative residual concentration verified",
            "r265": "generic object-local residual correction NO_PROMOTION",
            "repair": "persistent object identity/orientation plus source/destination contact-occlusion context",
        },
        "protocol": {
            "select": "p0-p4 fit / p5-p9 per-action zero-wrong validation",
            "refit": "p0-p9",
            "frozen_eval": "p10-p19",
            "exact_baseline_precedence": True,
        },
        "games": games,
        "aggregate": aggregate,
        "non_dominated_source_side_gain": nd,
        "promotion": {
            "integration_candidate": nd,
            "solver_promotion": False,
            "kaggle_packaging": False,
        },
        "truth": {
            "public_trace_only": True,
            "game_source_read": False,
            "selection_uses_p0_p9_only": True,
            "p10_p19_never_updates_selection_or_model": True,
            "p10_p19_status": "PUBLIC_DEVELOPMENT_REUSED_NOT_INDEPENDENT_HELDOUT",
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "competition_submission": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "aggregate": aggregate,
                "gain": nd,
                "selected": {g: x["selected_by_action"] for g, x in games.items()},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
