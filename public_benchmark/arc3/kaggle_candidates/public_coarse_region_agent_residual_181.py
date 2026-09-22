#!/usr/bin/env python3
"""R181: optimized coarse-region + agent-relative executable residual roles.

This is the representation-changing successor to R179/R180A after:
- R179 found no nonempty p11 zero-error abstention gate for frozen R178; and
- R180A third-stage residual caching produced only diagnostic raw gain.

R181 predicts residuals as executable ROLES (KEEP/FIXED/WORLD/BG/SET), replacing
absolute-coordinate lookup with normalized coarse regions and pre-action
small-component agent-relative geometry. Structural variants can share evidence
across literal color IDs. All features for the current frame are precomputed
from the pre-action board; current outcome is used only for scoring and then
post-prediction learning.

This is public source-assisted prequential replay, not independent ARC-AGI-3
generalization and not a Kaggle score/submission.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175

RUNG = 181
Grid = list[list[int]]
SUPPORTS = (1, 2, 3)
FAMILIES = (
    "region_role",
    "region_local_role",
    "agent_role",
    "region_agent_role",
    "region_agent_prev_role",
    "struct_region_agent_role",
    "struct_region_agent_prev_role",
)
MIN_PRIOR_FRAME_OK = 2


def run_bucket(n: int) -> int:
    return 0 if n <= 0 else 1 if n == 1 else 2 if n == 2 else 3


def coarse(i: int, n: int, bins: int = 4) -> int:
    if n <= 1:
        return 0
    return min(bins - 1, (i * bins) // n)


def dominant(g: Grid) -> int:
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def sbucket(n: int) -> int:
    if n <= 1: return 1
    if n <= 2: return 2
    if n <= 4: return 4
    if n <= 8: return 8
    return 16


def dbucket(d: float) -> int:
    ad = abs(d)
    mag = 0 if ad < 0.75 else 1 if ad < 2.0 else 2 if ad < 4.0 else 3
    return -mag if d < 0 else mag


def small_components(g: Grid, bg: int) -> list[dict[str, Any]]:
    h, w = len(g), len(g[0])
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, Any]] = []
    for r0 in range(h):
        for c0 in range(w):
            if (r0, c0) in seen:
                continue
            val = g[r0][c0]
            q = deque([(r0, c0)])
            seen.add((r0, c0))
            cells: list[tuple[int, int]] = []
            while q:
                r, c = q.popleft(); cells.append((r, c))
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and (rr, cc) not in seen and g[rr][cc] == val:
                        seen.add((rr, cc)); q.append((rr, cc))
            if val == bg or len(cells) > 16:
                continue
            cr = sum(r for r, _ in cells) / len(cells)
            cc = sum(c for _, c in cells) / len(cells)
            touch = int(any(r in (0, h-1) or c in (0, w-1) for r, c in cells))
            out.append({"value": val, "size": len(cells), "cr": cr, "cc": cc, "touch": touch, "cells": set(cells)})
    return out


def agent_feature(anchors: list[dict[str, Any]], g: Grid, r: int, c: int) -> tuple[Any, ...]:
    if not anchors:
        return ("none",)
    a = min(anchors, key=lambda x: abs(r - x["cr"]) + abs(c - x["cc"]))
    v = g[r][c]
    return (
        "anchor", sbucket(int(a["size"])), int(a["touch"]),
        int(v == a["value"]), int((r, c) in a["cells"]),
        dbucket(r - float(a["cr"])), dbucket(c - float(a["cc"])),
    )


def structural_core(action: str, fixed: int, pred: int, world: int, bg: int) -> tuple[Any, ...]:
    return (
        action, int(fixed == world), int(pred == fixed), int(pred == world),
        int(fixed == bg), int(world == bg), int(pred == bg),
    )


def literal_core(action: str, pred: int, fixed: int, world: int) -> tuple[Any, ...]:
    return (action, pred, fixed, world)


def role_label(pred: int, fixed: int, world: int, bg: int, actual: int) -> str:
    if actual == pred: return "KEEP"
    if actual == fixed: return "FIXED"
    if actual == world: return "WORLD"
    if actual == bg: return "BG"
    return f"SET:{actual}"


def apply_role(pred: int, fixed: int, world: int, bg: int, lab: str | None) -> int:
    if lab is None or lab == "KEEP": return pred
    if lab == "FIXED": return fixed
    if lab == "WORLD": return world
    if lab == "BG": return bg
    if lab.startswith("SET:"): return int(lab.split(":", 1)[1])
    return pred


def unique(bank: Counter[str], support: int) -> str | None:
    if len(bank) != 1:
        return None
    k, n = next(iter(bank.items()))
    return k if n >= support else None


def names() -> list[str]:
    return [f"{fam}_s{s}" for fam in FAMILIES for s in SUPPORTS]


def precompute_frame_features(
    before: Grid,
    base_pred: Grid,
    action: str,
    shift: tuple[int, int],
    prev_action: str,
    prior_same_run: int,
) -> dict[str, list[list[tuple[Any, ...]]]]:
    """Compute each family key exactly once per current cell."""
    h, w = len(before), len(before[0]); dr, dc = shift
    bg = dominant(before)
    anchors = small_components(before, bg)
    local_before = [[r175.local_eq_signature(before, r, c) for c in range(w)] for r in range(h)]
    local_pred = [[r175.local_eq_signature(base_pred, r, c) for c in range(w)] for r in range(h)]
    out = {fam: [[()] * w for _ in range(h)] for fam in FAMILIES}
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            fixed = before[r][c]
            world = before[sr][sc] if 0 <= sr < h and 0 <= sc < w else fixed
            pv = base_pred[r][c]
            reg = (coarse(r, h), coarse(c, w), r175.band(r, h), r175.band(c, w))
            ag = agent_feature(anchors, before, r, c)
            literal = literal_core(action, pv, fixed, world)
            structural = structural_core(action, fixed, pv, world, bg)
            out["region_role"][r][c] = literal + reg
            out["region_local_role"][r][c] = literal + reg + (local_before[r][c], local_pred[r][c])
            out["agent_role"][r][c] = literal + ag
            out["region_agent_role"][r][c] = literal + reg + ag
            out["region_agent_prev_role"][r][c] = literal + reg + ag + (prev_action, run_bucket(prior_same_run))
            out["struct_region_agent_role"][r][c] = structural + reg + ag
            out["struct_region_agent_prev_role"][r][c] = structural + reg + ag + (prev_action, run_bucket(prior_same_run))
    return out


def render_all(
    before: Grid,
    base_pred: Grid,
    shift: tuple[int, int],
    features,
    caches,
) -> dict[str, Grid]:
    h, w = len(before), len(before[0]); dr, dc = shift; bg = dominant(before)
    outs = {n: [row[:] for row in base_pred] for n in names()}
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            fixed = before[r][c]
            world = before[sr][sc] if 0 <= sr < h and 0 <= sc < w else fixed
            pv = base_pred[r][c]
            for fam in FAMILIES:
                bank = caches[fam][features[fam][r][c]]
                for s in SUPPORTS:
                    lab = unique(bank, s)
                    outs[f"{fam}_s{s}"][r][c] = apply_role(pv, fixed, world, bg, lab)
    return outs


def learn_roles(before: Grid, base_pred: Grid, after: Grid, shift: tuple[int, int], features, caches) -> None:
    h, w = len(before), len(before[0]); dr, dc = shift; bg = dominant(before)
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            fixed = before[r][c]
            world = before[sr][sc] if 0 <= sr < h and 0 <= sc < w else fixed
            lab = role_label(base_pred[r][c], fixed, world, bg, after[r][c])
            for fam in FAMILIES:
                caches[fam][features[fam][r][c]][lab] += 1


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    exact = defaultdict(Counter); shifts = defaultdict(Counter); recent_masks = defaultdict(list)
    base_labels = {f: defaultdict(Counter) for f in r175.MORPH_FAMILIES}
    caches = {f: defaultdict(Counter) for f in FAMILIES}
    shadow = defaultdict(Counter); stats = defaultdict(Counter); base_stats = Counter()
    pre = events[0]; prev_action = "START"; prior_same_run = 0

    for e in events[1:]:
        if e.get("type") != "action": pre = e; continue
        before = base.as_grid(pre["board"]); after = base.as_grid(e["board"]); action = base.action_name(e); pre = e
        if len(before) != len(after) or len(before[0]) != len(after[0]): continue
        run_before = prior_same_run if action == prev_action else 0
        ek = r160.context_exact(before, action)
        prog = r175.exact_prog(exact[ek], 1) if ek in exact else None
        pred_exact = r160.apply_program(before, prog) if prog is not None else None
        sh = r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None
        frame_features = None; base_pred = None

        if pred_exact is None and sh is not None:
            comps = r175.component_descriptors(before)
            base_pred = r175.render_candidate(before, sh, action, "patch_recent1_s2", recent_masks, base_labels, comps)
            berr = r175.score_frame(base_pred, after)
            base_stats["raw"] += 1; base_stats["cell_errors"] += berr
            base_stats["raw_correct" if berr == 0 else "raw_wrong"] += 1
            if berr <= 4: base_stats["near4"] += 1
            if berr <= 16: base_stats["near16"] += 1

            frame_features = precompute_frame_features(before, base_pred, action, sh, prev_action, run_before)
            preds = render_all(before, base_pred, sh, frame_features, caches)
            for name, pred in preds.items():
                err = r175.score_frame(pred, after); c = stats[name]
                c["raw"] += 1; c["cell_errors"] += err
                c["raw_correct" if err == 0 else "raw_wrong"] += 1
                if err <= 4: c["near4"] += 1
                if err <= 16: c["near16"] += 1
                q = shadow[(name, action)]["ok"] >= MIN_PRIOR_FRAME_OK and shadow[(name, action)]["wrong"] == 0
                if q:
                    c["qualified"] += 1
                    c["qualified_correct" if err == 0 else "qualified_wrong"] += 1
                shadow[(name, action)]["ok" if err == 0 else "wrong"] += 1

        # Current outcome enters every cache only AFTER all current predictions are frozen/scored.
        exact[ek][r160.program(before, after)] += 1
        if action in r172.CAMERA_ACTIONS:
            changed = sum(before[r][c] != after[r][c] for r in range(len(before)) for c in range(len(before[0])))
            if changed:
                b = r167.best_nonzero_shift(before, after)
                if float(b["valid_match_fraction"]) >= r172.MIN_TRANSITION_FIT:
                    obs = (int(b["dr"]), int(b["dc"])); shifts[action][obs] += 1
                    comps = r175.component_descriptors(before)
                    r175.learn_morph(before, after, obs, action, base_labels, comps)
                    recent_masks[action].append(r175.fixed_mask_from_transition(before, after, obs))
                    if len(recent_masks[action]) > 3: recent_masks[action] = recent_masks[action][-3:]
                    if base_pred is not None and frame_features is not None and obs == sh:
                        learn_roles(before, base_pred, after, obs, frame_features, caches)

        prior_same_run = run_before + 1 if action == prev_action else 1
        prev_action = action

    def pack(c: Counter) -> dict[str, Any]:
        d = {k: int(c[k]) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
        d["raw_accuracy"] = round(d["raw_correct"] / d["raw"], 6) if d["raw"] else None
        d["mean_cell_errors"] = round(d["cell_errors"] / d["raw"], 3) if d["raw"] else None
        d["qualified_accuracy"] = round(d["qualified_correct"] / d["qualified"], 6) if d["qualified"] else None
        return d
    return {"base": pack(base_stats), "candidates": {n: pack(stats[n]) for n in names()}}


def run(paths: list[Path]) -> dict[str, Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    agg: dict[str, Any] = {}
    for n in names():
        d = {k: sum(p["candidates"][n][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors","qualified","qualified_correct","qualified_wrong")}
        d["per_trace_raw_correct"] = [p["candidates"][n]["raw_correct"] for p in parts]
        d["per_trace_raw_wrong"] = [p["candidates"][n]["raw_wrong"] for p in parts]
        d["per_trace_qualified_correct"] = [p["candidates"][n]["qualified_correct"] for p in parts]
        d["per_trace_qualified_wrong"] = [p["candidates"][n]["qualified_wrong"] for p in parts]
        d["raw_accuracy"] = round(d["raw_correct"] / d["raw"], 6) if d["raw"] else None
        d["mean_cell_errors"] = round(d["cell_errors"] / d["raw"], 3) if d["raw"] else None
        d["qualified_accuracy"] = round(d["qualified_correct"] / d["qualified"], 6) if d["qualified"] else None
        d["strict_p0_p10_gain"] = bool(len(parts) >= 2 and d["qualified_wrong"] == 0 and d["per_trace_qualified_correct"][0] > 0 and d["per_trace_qualified_correct"][1] > 0)
        agg[n] = d

    baseagg = {k: sum(p["base"][k] for p in parts) for k in ("raw","raw_correct","raw_wrong","near4","near16","cell_errors")}
    baseagg["raw_accuracy"] = round(baseagg["raw_correct"] / baseagg["raw"], 6) if baseagg["raw"] else None
    ranked = sorted(names(), key=lambda n: (-agg[n]["raw_correct"], -agg[n]["near4"], agg[n]["cell_errors"], n))
    strict = [n for n in names() if agg[n]["strict_p0_p10_gain"]]
    return {
        "schema": "deus/arc3-public-coarse-region-agent-residual/2",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_COARSE_REGION_AGENT_ROLE_RESIDUAL_SWEEP_OPTIMIZED",
        "representation_change_from_rung180a": {
            "changed": True,
            "change": "replace repeated local residual SET cache with executable role outputs plus normalized coarse-region and pre-action agent-relative geometry; precompute current features once per frame",
        },
        "aggregate": {
            "base_patch_recent1_s2": baseagg,
            "candidates": agg,
            "ranking": ranked,
            "best_diagnostic_candidate": ranked[0] if ranked else None,
            "strict_p0_p10_candidates": strict,
            "per_trace": parts,
        },
        "diagnostic_gate": "ZERO_ERROR_P0_P10_COARSE_AGENT_ROLE_GAIN" if strict else "NO_STRICT_PREQUENTIAL_COARSE_AGENT_ROLE_GAIN",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_sequence_replay": True,
            "current_prediction_uses_preaction_and_prior_history_only": True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning": True,
            "representation_changed_from_rung180a": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--input", type=Path, action="append", default=[]); ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if not a.input: raise SystemExit("input required")
    d = run(a.input); s = json.dumps(d, indent=2, sort_keys=True) + "\n"; print(s, end="")
    if a.output: a.output.write_text(s, encoding="utf-8")


if __name__ == "__main__": main()
