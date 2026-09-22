#!/usr/bin/env python3
"""R175: bounded residual-repair family sweep after R174 no-gain.

R173 showed R172 residuals are dominated by fixed-like cells while more than half
of wrong frames are already near-exact. R174's coordinate-shared value/band
selector did not obtain strict p0+p10 gain. This rung therefore tests the
remaining planned public residual families in ONE matched prequential sweep:

  1) recent screen-fixed masks learned from prior same-action transitions;
  2) local morphology classifiers (3x3 equality signature);
  3) connected-component morphology classifiers;
  4) hybrids that use a learned morphology label when supported and otherwise
     fall back to recent prior masks.

Every prediction is made from the current frame and PRIOR history only. The
current outcome is used only for scoring and post-prediction learning. This is
source-assisted public replay, not independent ARC-AGI-3 generalization and not
a Kaggle score/submission.
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

RUNG = 175
MIN_PRIOR_FRAME_OK = 2
CAMERA_ACTIONS = r172.CAMERA_ACTIONS
Grid = list[list[int]]

SUPPORTS = (1, 2, 3)
RECENT_VARIANTS = (
    "recent1",
    "recent2_union",
    "recent2_intersection",
    "recent3_majority",
)
MORPH_FAMILIES = ("patch", "component")
HYBRID_VARIANTS = ("patch_recent1_s2", "component_recent1_s2")


def unique(bank: Counter[str], support: int) -> str | None:
    if len(bank) != 1:
        return None
    k, n = next(iter(bank.items()))
    return k if n >= support else None


def exact_prog(bank: Counter[str], support: int = 1) -> str | None:
    return unique(bank, support)


def band(i: int, n: int) -> str:
    if i < 3:
        return "edge0"
    if i < 6:
        return "edge1"
    if i >= n - 3:
        return "edge0r"
    if i >= n - 6:
        return "edge1r"
    return "mid"


def local_eq_signature(g: Grid, r: int, c: int) -> int:
    """8-neighbor equality-to-center mask; geometry, not absolute coordinate."""
    h, w = len(g), len(g[0])
    v = g[r][c]
    bit = 0
    out = 0
    for dr, dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == v:
            out |= 1 << bit
        bit += 1
    return out


def component_descriptors(g: Grid) -> dict[tuple[int,int], tuple[int,int,int,int]]:
    """Per-cell same-value 4-connected morphology descriptor.

    Descriptor: (size_bucket, height_bucket, width_bucket, touches_edge).
    """
    h, w = len(g), len(g[0])
    seen: set[tuple[int,int]] = set()
    out: dict[tuple[int,int], tuple[int,int,int,int]] = {}

    def bucket(n: int) -> int:
        if n <= 1: return 1
        if n <= 2: return 2
        if n <= 4: return 4
        if n <= 8: return 8
        if n <= 16: return 16
        if n <= 32: return 32
        return 64

    for r0 in range(h):
        for c0 in range(w):
            if (r0, c0) in seen:
                continue
            v = g[r0][c0]
            q = deque([(r0,c0)])
            seen.add((r0,c0))
            cells: list[tuple[int,int]] = []
            rmin = rmax = r0
            cmin = cmax = c0
            touch = 0
            while q:
                r, c = q.popleft()
                cells.append((r,c))
                rmin, rmax = min(rmin,r), max(rmax,r)
                cmin, cmax = min(cmin,c), max(cmax,c)
                if r in (0,h-1) or c in (0,w-1):
                    touch = 1
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    rr, cc = r+dr, c+dc
                    if 0 <= rr < h and 0 <= cc < w and (rr,cc) not in seen and g[rr][cc] == v:
                        seen.add((rr,cc))
                        q.append((rr,cc))
            desc = (bucket(len(cells)), bucket(rmax-rmin+1), bucket(cmax-cmin+1), touch)
            for p in cells:
                out[p] = desc
    return out


def morph_feature(
    family: str,
    action: str,
    before: Grid,
    r: int,
    c: int,
    sr: int,
    sc: int,
    comps: dict[tuple[int,int], tuple[int,int,int,int]],
) -> tuple[Any, ...]:
    fixed, world = before[r][c], before[sr][sc]
    basef: tuple[Any, ...] = (action, fixed, world, band(r,len(before)), band(c,len(before[0])))
    if family == "patch":
        return basef + (local_eq_signature(before,r,c), local_eq_signature(before,sr,sc))
    if family == "component":
        return basef + (comps[(r,c)], comps[(sr,sc)])
    raise ValueError(f"unknown family {family}")


def fixed_mask_from_transition(before: Grid, after: Grid, shift: tuple[int,int]) -> set[tuple[int,int]]:
    dr, dc = shift
    h, w = len(before), len(before[0])
    out: set[tuple[int,int]] = set()
    for r in range(h):
        for c in range(w):
            sr, sc = r-dr, c-dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world, actual = before[r][c], before[sr][sc], after[r][c]
            if actual == fixed and actual != world:
                out.add((r,c))
    return out


def recent_decision(name: str, history: list[set[tuple[int,int]]], p: tuple[int,int]) -> bool:
    if not history:
        return False
    if name == "recent1":
        return p in history[-1]
    last2 = history[-2:]
    if name == "recent2_union":
        return any(p in x for x in last2)
    if name == "recent2_intersection":
        return len(last2) >= 2 and all(p in x for x in last2)
    if name == "recent3_majority":
        last3 = history[-3:]
        need = 2 if len(last3) >= 3 else len(last3)
        return len(last3) >= 2 and sum(p in x for x in last3) >= need
    raise ValueError(name)


def render_candidate(
    before: Grid,
    shift: tuple[int,int],
    action: str,
    name: str,
    recent_masks: dict[str, list[set[tuple[int,int]]]],
    labels: dict[str, dict[tuple[Any,...], Counter[str]]],
    comps: dict[tuple[int,int], tuple[int,int,int,int]],
) -> Grid:
    dr, dc = shift
    h, w = len(before), len(before[0])
    out = [row[:] for row in before]  # preserve incoming boundary by default

    for r in range(h):
        for c in range(w):
            sr, sc = r-dr, c-dc
            if not (0 <= sr < h and 0 <= sc < w):
                continue
            fixed, world = before[r][c], before[sr][sc]
            if fixed == world:
                out[r][c] = fixed
                continue

            use_fixed = False
            if name in RECENT_VARIANTS:
                use_fixed = recent_decision(name, recent_masks[action], (r,c))
            elif name.startswith("patch_s") or name.startswith("component_s"):
                family, s = name.split("_s")
                key = morph_feature(family, action, before, r,c,sr,sc,comps)
                lab = unique(labels[family][key], int(s))
                use_fixed = lab == "fixed" if lab is not None else False
            elif name == "patch_recent1_s2":
                key = morph_feature("patch", action, before, r,c,sr,sc,comps)
                lab = unique(labels["patch"][key], 2)
                use_fixed = (lab == "fixed") if lab is not None else recent_decision("recent1", recent_masks[action], (r,c))
            elif name == "component_recent1_s2":
                key = morph_feature("component", action, before, r,c,sr,sc,comps)
                lab = unique(labels["component"][key], 2)
                use_fixed = (lab == "fixed") if lab is not None else recent_decision("recent1", recent_masks[action], (r,c))
            else:
                raise ValueError(name)

            out[r][c] = fixed if use_fixed else world
    return out


def learn_morph(
    before: Grid,
    after: Grid,
    shift: tuple[int,int],
    action: str,
    labels: dict[str, dict[tuple[Any,...], Counter[str]]],
    comps: dict[tuple[int,int], tuple[int,int,int,int]],
) -> None:
    dr, dc = shift
    h, w = len(before), len(before[0])
    for r in range(h):
        for c in range(w):
            sr, sc = r-dr, c-dc
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
                continue
            for family in MORPH_FAMILIES:
                labels[family][morph_feature(family,action,before,r,c,sr,sc,comps)][lab] += 1


def candidate_names() -> list[str]:
    names = list(RECENT_VARIANTS)
    for fam in MORPH_FAMILIES:
        for s in SUPPORTS:
            names.append(f"{fam}_s{s}")
    names.extend(HYBRID_VARIANTS)
    return names


def score_frame(pred: Grid, after: Grid) -> int:
    return sum(pred[r][c] != after[r][c] for r in range(len(after)) for c in range(len(after[0])))


def audit_trace(events: list[dict[str,Any]]) -> dict[str,Any]:
    exact = defaultdict(Counter)
    shifts = defaultdict(Counter)
    recent_masks: dict[str, list[set[tuple[int,int]]]] = defaultdict(list)
    labels: dict[str, dict[tuple[Any,...], Counter[str]]] = {
        f: defaultdict(Counter) for f in MORPH_FAMILIES
    }
    shadow = defaultdict(Counter)
    stats = defaultdict(Counter)
    pre = events[0]

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

        ek = r160.context_exact(before, action)
        prog = exact_prog(exact[ek], 1) if ek in exact else None
        pred_exact = r160.apply_program(before, prog) if prog is not None else None
        sh = r172.stable_shift(shifts[action]) if action in CAMERA_ACTIONS else None

        if pred_exact is None and sh is not None:
            comps = component_descriptors(before)
            for name in candidate_names():
                pred = render_candidate(before, sh, action, name, recent_masks, labels, comps)
                err = score_frame(pred, after)
                s = stats[name]
                s["raw"] += 1
                s["cell_errors"] += err
                if err == 0:
                    s["raw_correct"] += 1
                else:
                    s["raw_wrong"] += 1
                if err <= 4:
                    s["near4"] += 1
                if err <= 16:
                    s["near16"] += 1
                q = shadow[(name,action)]["ok"] >= MIN_PRIOR_FRAME_OK and shadow[(name,action)]["wrong"] == 0
                if q:
                    s["qualified"] += 1
                    if err == 0:
                        s["qualified_correct"] += 1
                    else:
                        s["qualified_wrong"] += 1
                shadow[(name,action)]["ok" if err == 0 else "wrong"] += 1

        # Post-outcome learning only.
        exact[ek][r160.program(before,after)] += 1
        if action in CAMERA_ACTIONS:
            changed = sum(before[r][c] != after[r][c] for r in range(len(before)) for c in range(len(before[0])))
            if changed:
                b = r167.best_nonzero_shift(before,after)
                if float(b["valid_match_fraction"]) >= r172.MIN_TRANSITION_FIT:
                    obs = (int(b["dr"]), int(b["dc"]))
                    shifts[action][obs] += 1
                    comps = component_descriptors(before)
                    learn_morph(before,after,obs,action,labels,comps)
                    recent_masks[action].append(fixed_mask_from_transition(before,after,obs))
                    if len(recent_masks[action]) > 3:
                        recent_masks[action] = recent_masks[action][-3:]

    out = {}
    for name in candidate_names():
        c = stats[name]
        d = {k:int(c[k]) for k in (
            "raw","raw_correct","raw_wrong","near4","near16","cell_errors",
            "qualified","qualified_correct","qualified_wrong"
        )}
        d["raw_accuracy"] = round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
        d["mean_cell_errors"] = round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
        d["qualified_accuracy"] = round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
        out[name] = d
    return out


def run(paths: list[Path]) -> dict[str,Any]:
    parts = [audit_trace(base.load_events(p)) for p in paths]
    agg = {}
    for name in candidate_names():
        d = {k:sum(p[name][k] for p in parts) for k in (
            "raw","raw_correct","raw_wrong","near4","near16","cell_errors",
            "qualified","qualified_correct","qualified_wrong"
        )}
        d["per_trace_raw_correct"] = [p[name]["raw_correct"] for p in parts]
        d["per_trace_raw_wrong"] = [p[name]["raw_wrong"] for p in parts]
        d["per_trace_near4"] = [p[name]["near4"] for p in parts]
        d["per_trace_qualified_correct"] = [p[name]["qualified_correct"] for p in parts]
        d["per_trace_qualified_wrong"] = [p[name]["qualified_wrong"] for p in parts]
        d["raw_accuracy"] = round(d["raw_correct"]/d["raw"],6) if d["raw"] else None
        d["mean_cell_errors"] = round(d["cell_errors"]/d["raw"],3) if d["raw"] else None
        d["qualified_accuracy"] = round(d["qualified_correct"]/d["qualified"],6) if d["qualified"] else None
        d["strict_p0_p10_gain"] = bool(
            len(parts) >= 2 and d["qualified_wrong"] == 0
            and d["per_trace_qualified_correct"][0] > 0
            and d["per_trace_qualified_correct"][1] > 0
        )
        agg[name] = d

    ranked = sorted(candidate_names(), key=lambda n: (
        -agg[n]["raw_correct"],
        -agg[n]["near4"],
        agg[n]["cell_errors"],
        n,
    ))
    best = ranked[0] if ranked else None
    strict = [n for n in candidate_names() if agg[n]["strict_p0_p10_gain"]]

    return {
        "schema":"deus/arc3-public-residual-family-sweep/1",
        "rung":RUNG,
        "execution_class":"CPU_PUBLIC_TRACE_PREQUENTIAL_RESIDUAL_REPAIR_FAMILY_SWEEP",
        "representation_change_from_rung174":{
            "changed":True,
            "change":"replace value-pair/coarse-band-only selector with matched sweep of recent prior masks, local patch morphology, connected-component morphology, and morphology+recent hybrids",
        },
        "source_grounding":{
            "public_trace_repo":base.TUFA_REPO,
            "public_trace_commit":base.TUFA_COMMIT,
            "clean_room_implementation":True,
        },
        "parameters":{
            "supports":list(SUPPORTS),
            "recent_variants":list(RECENT_VARIANTS),
            "morph_families":list(MORPH_FAMILIES),
            "hybrid_variants":list(HYBRID_VARIANTS),
            "min_prior_frame_ok":MIN_PRIOR_FRAME_OK,
        },
        "aggregate":{
            "candidates":agg,
            "ranking":ranked,
            "best_diagnostic_candidate":best,
            "strict_p0_p10_candidates":strict,
            "per_trace":parts,
        },
        "diagnostic_gate":"ZERO_ERROR_P0_P10_RESIDUAL_FAMILY_GAIN" if strict else "NO_STRICT_PREQUENTIAL_RESIDUAL_FAMILY_GAIN",
        "promotion":{
            "candidate_model_promotion":False,
            "kaggle_packaging":False,
        },
        "truth":{
            "public_trace_only":True,
            "source_assisted_sequence_replay":True,
            "current_prediction_uses_preaction_and_prior_history_only":True,
            "current_outcome_used_only_for_scoring_and_post_prediction_learning":True,
            "matched_family_sweep":True,
            "independent_generalization_claim":False,
            "solver_behavior_gain_claim":False,
            "gpu_execution":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if not a.input:
        raise SystemExit("input required")
    d = run(a.input)
    s = json.dumps(d, indent=2, sort_keys=True) + "\n"
    print(s, end="")
    if a.output:
        a.output.write_text(s, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
