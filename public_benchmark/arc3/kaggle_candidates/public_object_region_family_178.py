#!/usr/bin/env python3
"""R178 child-lane: object/region overlay state families, one family per shard.

This file is designed for scatter/reduce execution. Each invocation evaluates
exactly one prior-only representation family over the same pinned public ARC3
traces. The workflow fans families out to independent CPU runners and reduces
only typed receipts.

The current target frame is never used to form the current prediction. It is
used only for scoring and post-prediction learning. This is source-assisted
public replay, not independent ARC-AGI-3 generalization and not a Kaggle score.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_fullboard_translation_program_160 as r160
import public_dense_scroll_renderer_audit_167 as r167
import public_world_overlay_renderer_172 as r172
import public_residual_family_sweep_175 as r175
import public_temporal_path_patch_177 as r177

RUNG = 178
MIN_PRIOR_FRAME_OK = 2
FAMILIES = (
    "component",
    "component_prev",
    "component_run",
    "component_phase",
    "region_patch",
    "region_prev",
    "hybrid",
)

def region_band(i: int, n: int) -> int:
    # coordinate-shared coarse regions; deliberately not an absolute pixel mask
    if i < n // 4: return 0
    if i < n // 2: return 1
    if i < (3 * n) // 4: return 2
    return 3

def feature(
    family: str,
    action: str,
    before,
    r: int,
    c: int,
    sr: int,
    sc: int,
    comps,
    prev_action: str,
    prior_same_run: int,
    action_index: int,
):
    fixed, world = before[r][c], before[sr][sc]
    comp_here = comps[(r, c)]
    comp_src = comps[(sr, sc)]
    patch_here = r175.local_eq_signature(before, r, c)
    patch_src = r175.local_eq_signature(before, sr, sc)
    rb = region_band(r, len(before))
    cb = region_band(c, len(before[0]))
    runb = r177.run_bucket(prior_same_run)

    base_pair = (action, fixed, world)
    if family == "component":
        return base_pair + (comp_here, comp_src)
    if family == "component_prev":
        return base_pair + (comp_here, comp_src, prev_action)
    if family == "component_run":
        return base_pair + (comp_here, comp_src, runb)
    if family == "component_phase":
        return base_pair + (comp_here, comp_src, action_index % 2, action_index % 3)
    if family == "region_patch":
        return base_pair + (rb, cb, patch_here, patch_src)
    if family == "region_prev":
        return base_pair + (rb, cb, prev_action, patch_here, patch_src)
    if family == "hybrid":
        return base_pair + (
            comp_here, comp_src, rb, cb, patch_here, patch_src,
            prev_action, runb, action_index % 2, action_index % 3,
        )
    raise ValueError(family)

def unique_label(counter: Counter[str]) -> str | None:
    if len(counter) != 1:
        return None
    lab, n = next(iter(counter.items()))
    return lab if n >= 1 else None

def render(before, shift, action, family, labels, recent_masks, prev_action, prior_same_run, action_index):
    dr, dc = shift
    h, w = len(before), len(before[0])
    out = [row[:] for row in before]  # preserves incoming boundary
    comps = r175.component_descriptors(before)
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world = before[r][c], before[sr][sc]
            if fixed == world:
                out[r][c] = fixed
                continue
            key = feature(
                family, action, before, r, c, sr, sc, comps,
                prev_action, prior_same_run, action_index,
            )
            lab = unique_label(labels[key])
            if lab is None:
                lab = "fixed" if (recent_masks[action] and (r, c) in recent_masks[action][-1]) else "world"
            out[r][c] = fixed if lab == "fixed" else world
    return out

def learn(before, after, shift, action, family, labels, prev_action, prior_same_run, action_index):
    dr, dc = shift
    h, w = len(before), len(before[0])
    comps = r175.component_descriptors(before)
    for r in range(h):
        for c in range(w):
            sr, sc = r - dr, c - dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world, actual = before[r][c], before[sr][sc], after[r][c]
            if fixed == world:
                continue
            if actual == fixed and actual != world:
                lab = "fixed"
            elif actual == world and actual != fixed:
                lab = "world"
            else:
                # Dynamic/other cells are intentionally not mislabeled as fixed/world.
                continue
            key = feature(
                family, action, before, r, c, sr, sc, comps,
                prev_action, prior_same_run, action_index,
            )
            labels[key][lab] += 1

def audit_trace(events: list[dict[str, Any]], family: str) -> dict[str, Any]:
    exact = defaultdict(Counter)
    shifts = defaultdict(Counter)
    recent_masks = defaultdict(list)
    labels = defaultdict(Counter)
    shadow = defaultdict(Counter)
    stats = Counter()
    pre = events[0]
    prev_action = "START"
    prior_same_run = 0
    action_index = 0

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if len(before) != len(after) or len(before[0]) != len(after[0]):
            continue

        run_before = prior_same_run if action == prev_action else 0
        ek = r160.context_exact(before, action)
        prog = r175.exact_prog(exact[ek], 1) if ek in exact else None
        pred_exact = r160.apply_program(before, prog) if prog is not None else None
        sh = r172.stable_shift(shifts[action]) if action in r172.CAMERA_ACTIONS else None

        if pred_exact is None and sh is not None:
            pred = render(before, sh, action, family, labels, recent_masks, prev_action, run_before, action_index)
            err = r175.score_frame(pred, after)
            stats["raw"] += 1
            stats["cell_errors"] += err
            stats["raw_correct" if err == 0 else "raw_wrong"] += 1
            if err <= 4: stats["near4"] += 1
            if err <= 16: stats["near16"] += 1
            q = shadow[action]["ok"] >= MIN_PRIOR_FRAME_OK and shadow[action]["wrong"] == 0
            if q:
                stats["qualified"] += 1
                stats["qualified_correct" if err == 0 else "qualified_wrong"] += 1
            shadow[action]["ok" if err == 0 else "wrong"] += 1

        # Post-outcome learning only.
        exact[ek][r160.program(before, after)] += 1
        if action in r172.CAMERA_ACTIONS:
            changed = sum(
                before[r][c] != after[r][c]
                for r in range(len(before))
                for c in range(len(before[0]))
            )
            if changed:
                b = r167.best_nonzero_shift(before, after)
                if float(b["valid_match_fraction"]) >= r172.MIN_TRANSITION_FIT:
                    obs = (int(b["dr"]), int(b["dc"]))
                    shifts[action][obs] += 1
                    learn(before, after, obs, action, family, labels, prev_action, run_before, action_index)
                    recent_masks[action].append(r175.fixed_mask_from_transition(before, after, obs))
                    if len(recent_masks[action]) > 3:
                        recent_masks[action] = recent_masks[action][-3:]

        if action == prev_action:
            prior_same_run = run_before + 1
        else:
            prior_same_run = 1
        prev_action = action
        action_index += 1

    out = {k: int(stats[k]) for k in (
        "raw", "raw_correct", "raw_wrong", "near4", "near16", "cell_errors",
        "qualified", "qualified_correct", "qualified_wrong",
    )}
    out["raw_accuracy"] = round(out["raw_correct"] / out["raw"], 6) if out["raw"] else None
    out["mean_cell_errors"] = round(out["cell_errors"] / out["raw"], 3) if out["raw"] else None
    out["qualified_accuracy"] = round(out["qualified_correct"] / out["qualified"], 6) if out["qualified"] else None
    return out

def run(paths: list[Path], family: str) -> dict[str, Any]:
    if family not in FAMILIES:
        raise ValueError(f"family must be one of {FAMILIES}")
    parts = [audit_trace(base.load_events(p), family) for p in paths]
    d = {k: sum(p[k] for p in parts) for k in (
        "raw", "raw_correct", "raw_wrong", "near4", "near16", "cell_errors",
        "qualified", "qualified_correct", "qualified_wrong",
    )}
    d["per_trace_raw_correct"] = [p["raw_correct"] for p in parts]
    d["per_trace_raw_wrong"] = [p["raw_wrong"] for p in parts]
    d["per_trace_qualified_correct"] = [p["qualified_correct"] for p in parts]
    d["per_trace_qualified_wrong"] = [p["qualified_wrong"] for p in parts]
    d["raw_accuracy"] = round(d["raw_correct"] / d["raw"], 6) if d["raw"] else None
    d["mean_cell_errors"] = round(d["cell_errors"] / d["raw"], 3) if d["raw"] else None
    d["qualified_accuracy"] = round(d["qualified_correct"] / d["qualified"], 6) if d["qualified"] else None
    d["strict_p0_p10_gain"] = bool(
        len(parts) >= 2 and d["qualified_wrong"] == 0
        and d["per_trace_qualified_correct"][0] > 0
        and d["per_trace_qualified_correct"][1] > 0
    )
    gate = "ZERO_ERROR_P0_P10_OBJECT_REGION_GAIN" if d["strict_p0_p10_gain"] else "NO_STRICT_PREQUENTIAL_OBJECT_REGION_GAIN"
    return {
        "schema": "deus/arc3-public-object-region-family/1",
        "rung": RUNG,
        "family": family,
        "execution_class": "CPU_PUBLIC_TRACE_PREQUENTIAL_OBJECT_REGION_STATE_SHARD",
        "logical_compile": {
            "logical_namespace_ceiling": 1000000000000,
            "materialized_hot_shards": len(FAMILIES),
            "this_shard": family,
            "physical_worker_claim": False,
        },
        "representation_change_from_rung177": {
            "changed": True,
            "change": "replace purely local temporal patch context with object/component or coarse-region shared state; retain prior-only recent-mask fallback",
        },
        "aggregate": d,
        "diagnostic_gate": gate,
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_sequence_replay": True,
            "current_prediction_uses_preaction_and_prior_history_only": True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning": True,
            "independent_generalization_claim": False,
            "kaggle_execution": False,
            "submission_quota_spent": False,
            "owner_score_claim": False,
            "logical_supercell_is_not_physical_worker_count": True,
        },
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=FAMILIES)
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if not a.input:
        raise SystemExit("input required")
    d = run(a.input, a.family)
    s = json.dumps(d, indent=2, sort_keys=True) + "\n"
    a.output.write_text(s, encoding="utf-8")
    print(json.dumps({
        "rung": RUNG, "family": a.family, "gate": d["diagnostic_gate"],
        "aggregate": d["aggregate"], "truth": "PREQUENTIAL_PUBLIC_SOURCE_ASSISTED_ONLY",
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
