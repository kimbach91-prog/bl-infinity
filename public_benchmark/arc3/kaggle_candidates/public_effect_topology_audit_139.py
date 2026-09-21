#!/usr/bin/env python3
"""Rung 139: effect-topology diagnostic on pinned public ARC-AGI-3 traces.

Rung 138 established that strict single-object pure translations do not occur in
the pinned AR25 trace set. Before inventing another executor, this rung measures
what the observed effects actually look like: changed-cell magnitude, connected
change regions, bounding-box extent, border concentration, palette changes, and
repeated action/effect signatures.

This is a diagnostic representation audit only. It does not predict hidden
outcomes and makes no solver/model/GPU/Kaggle/leaderboard claim.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from statistics import median
from typing import Any

import public_executable_world_model_134 as base

RUNG = 139
Grid = list[list[int]]


def diff_cells(a: Grid, b: Grid) -> list[tuple[int, int]]:
    if not base.same_shape(a, b):
        return []
    return [(r, c) for r in range(len(a)) for c in range(len(a[0])) if a[r][c] != b[r][c]]


def mask_components(cells: list[tuple[int, int]]) -> int:
    remaining = set(cells)
    n = 0
    while remaining:
        n += 1
        start = remaining.pop()
        q = deque([start])
        while q:
            r, c = q.popleft()
            for nb in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if nb in remaining:
                    remaining.remove(nb)
                    q.append(nb)
    return n


def bucket_frac(x: float) -> str:
    if x == 0:
        return "0"
    if x <= 0.001:
        return "<=0.1%"
    if x <= 0.01:
        return "0.1-1%"
    if x <= 0.05:
        return "1-5%"
    if x <= 0.25:
        return "5-25%"
    if x <= 0.5:
        return "25-50%"
    return ">50%"


def bucket_components(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 8:
        return "4-8"
    return ">8"


def analyze_transition(before: Grid, after: Grid, action: str) -> dict[str, Any]:
    if not base.same_shape(before, after):
        return {"same_shape": False, "action": action}
    h, w = len(before), len(before[0])
    total = h * w
    diff = diff_cells(before, after)
    changed = len(diff)
    frac = changed / total
    comps = mask_components(diff)
    if diff:
        r0 = min(r for r, _ in diff); r1 = max(r for r, _ in diff)
        c0 = min(c for _, c in diff); c1 = max(c for _, c in diff)
        bbox_area = (r1-r0+1) * (c1-c0+1)
        bbox_frac = bbox_area / total
    else:
        bbox_frac = 0.0
    # Outer 10% band, minimum one cell. This is only a location diagnostic, not
    # a semantic claim that the band is HUD.
    br = max(1, round(h * 0.10)); bc = max(1, round(w * 0.10))
    border_changed = sum(1 for r, c in diff if r < br or r >= h-br or c < bc or c >= w-bc)
    border_ratio = border_changed / changed if changed else 0.0
    before_colors = set(v for row in before for v in row)
    after_colors = set(v for row in after for v in row)
    global_t = base.detect_global_translation(before, after)
    single_t = base.detect_single_component_translation(before, after)
    signature = {
        "action": action,
        "changed_fraction_bucket": bucket_frac(frac),
        "diff_components_bucket": bucket_components(comps),
        "bbox_fraction_bucket": bucket_frac(bbox_frac),
        "border_majority": border_ratio >= 0.5,
        "palette_changed": before_colors != after_colors,
    }
    return {
        "same_shape": True,
        "action": action,
        "h": h,
        "w": w,
        "changed_cells": changed,
        "changed_fraction": frac,
        "diff_components": comps,
        "bbox_fraction": bbox_frac,
        "border_changed_ratio": border_ratio,
        "palette_changed": before_colors != after_colors,
        "global_translation_detected": global_t is not None,
        "single_component_translation_detected": single_t is not None,
        "signature": signature,
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    same = [r for r in records if r.get("same_shape")]
    n = len(records)
    changed_counts = [int(r["changed_cells"]) for r in same]
    changed_fracs = [float(r["changed_fraction"]) for r in same]
    comp_counts = [int(r["diff_components"]) for r in same]
    bbox_fracs = [float(r["bbox_fraction"]) for r in same]
    border_ratios = [float(r["border_changed_ratio"]) for r in same if int(r["changed_cells"]) > 0]
    sigs = Counter(base.stable(r["signature"]) for r in same)
    actions: dict[str, dict[str, Any]] = {}
    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in same:
        by_action[str(r["action"])].append(r)
    for action, rows in sorted(by_action.items()):
        c = [int(r["changed_cells"]) for r in rows]
        f = [float(r["changed_fraction"]) for r in rows]
        k = [int(r["diff_components"]) for r in rows]
        actions[action] = {
            "transitions": len(rows),
            "identity": sum(x == 0 for x in c),
            "changed_cells_median": median(c) if c else None,
            "changed_fraction_median": median(f) if f else None,
            "diff_components_median": median(k) if k else None,
            "border_majority_effects": sum(float(r["border_changed_ratio"]) >= 0.5 for r in rows if int(r["changed_cells"]) > 0),
            "palette_changed": sum(bool(r["palette_changed"]) for r in rows),
        }
    top_signatures = []
    for raw, count in sigs.most_common(12):
        top_signatures.append({"count": count, "signature": json.loads(raw)})
    return {
        "transitions": n,
        "same_shape": len(same),
        "shape_changed": n - len(same),
        "identity_transitions": sum(x == 0 for x in changed_counts),
        "nonidentity_transitions": sum(x > 0 for x in changed_counts),
        "changed_cells_min": min(changed_counts) if changed_counts else None,
        "changed_cells_median": median(changed_counts) if changed_counts else None,
        "changed_cells_max": max(changed_counts) if changed_counts else None,
        "changed_fraction_median": median(changed_fracs) if changed_fracs else None,
        "changed_fraction_buckets": dict(sorted(Counter(bucket_frac(x) for x in changed_fracs).items())),
        "diff_components_median": median(comp_counts) if comp_counts else None,
        "diff_components_buckets": dict(sorted(Counter(bucket_components(x) for x in comp_counts).items())),
        "bbox_fraction_median": median(bbox_fracs) if bbox_fracs else None,
        "bbox_fraction_buckets": dict(sorted(Counter(bucket_frac(x) for x in bbox_fracs).items())),
        "border_changed_ratio_median_nonidentity": median(border_ratios) if border_ratios else None,
        "border_majority_effects": sum(x >= 0.5 for x in border_ratios),
        "palette_changed_transitions": sum(bool(r["palette_changed"]) for r in same),
        "global_translation_detected": sum(bool(r["global_translation_detected"]) for r in same),
        "single_component_translation_detected": sum(bool(r["single_component_translation_detected"]) for r in same),
        "unique_effect_signatures": len(sigs),
        "top_effect_signatures": top_signatures,
        "actions": actions,
    }


def run(paths: list[Path]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for path in paths:
        events = base.load_events(path)
        pre = events[0]
        local: list[dict[str, Any]] = []
        for event in events[1:]:
            if event.get("type") != "action":
                pre = event
                continue
            before = base.as_grid(pre["board"])
            after = base.as_grid(event["board"])
            rec = analyze_transition(before, after, base.action_name(event))
            records.append(rec); local.append(rec)
            pre = event
        traces.append({"path": str(path), "transitions": len(local), "summary": summarize(local)})
    agg = summarize(records)
    return {
        "schema": "deus/arc3-public-effect-topology-audit/1",
        "rung": RUNG,
        "execution_class": "CPU_PUBLIC_TRACE_EFFECT_TOPOLOGY_DIAGNOSTIC",
        "representation_change_from_rung138": {
            "changed": True,
            "change": "stop assuming a one-object translation mechanism and measure full rendered before/after change topology before selecting the next executable representation"
        },
        "source_grounding": {
            "public_trace_repo": base.TUFA_REPO,
            "public_trace_commit": base.TUFA_COMMIT,
            "clean_room_implementation": True,
        },
        "traces": traces,
        "aggregate": agg,
        "diagnostic_gate": "EFFECT_TOPOLOGY_CHARACTERIZED",
        "promotion": {"candidate_model_promotion": False, "kaggle_packaging": False},
        "truth": {
            "public_trace_only": True,
            "source_assisted_replay": True,
            "diagnostic_only": True,
            "independent_generalization_claim": False,
            "solver_behavior_gain_claim": False,
            "model_execution": False,
            "gpu_execution": False,
            "kaggle_execution": False,
            "kaggle_submission_attempted": False,
            "submission_quota_spent": False,
            "leaderboard_score_claim": False,
            "owner_score_claim": False,
        },
    }


def self_test() -> dict[str, Any]:
    a = [[0]*8 for _ in range(6)]
    b = [row[:] for row in a]
    a[2][2] = 1; b[2][3] = 1
    r = analyze_transition(a, b, "RIGHT")
    ok = r["changed_cells"] == 2 and r["diff_components"] == 2 and r["same_shape"] is True
    return {"schema":"deus/arc3-public-effect-topology-selftest/1","rung":RUNG,"passed":ok,"record":r}


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,action="append",default=[]); ap.add_argument("--output",type=Path); ap.add_argument("--self-test",action="store_true"); args=ap.parse_args()
    if args.self_test:
        result=self_test(); code=0 if result["passed"] else 2
    else:
        if not args.input: raise SystemExit("at least one --input is required")
        result=run(args.input); code=0
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.write_text(text,encoding="utf-8")
    print(text,end=""); return code

if __name__ == "__main__":
    raise SystemExit(main())
