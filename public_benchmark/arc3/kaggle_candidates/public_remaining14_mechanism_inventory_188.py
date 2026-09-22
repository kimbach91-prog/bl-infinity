#!/usr/bin/env python3
"""R188: mechanism inventory for the 14 public ARC-AGI-3 families uncovered by R184.

R184's frozen R180-derived camera/world-overlay path emitted on only 11/25
public game families. The 14 remaining families are not treated as "unsolved
because impossible"; they are a representation gap.

This diagnostic classifies every observed public transition in those families
using prefix-independent structural detectors only:
  * identity
  * R134 executable rules (global translation, single component translation,
    deterministic color map)
  * local patch rewrite eligibility (R136)
  * dense approximate viewport shift fit in any direction
  * changed-cell / bbox scale
  * action inventory

Outcome is used only to characterize the already-observed transition. This rung
does not claim prediction, hidden generalization, Kaggle execution, or score.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import public_executable_world_model_134 as base
import public_dense_scroll_renderer_audit_167 as r167
import public_local_transition_program_prequential_136 as r136

RUNG = 188
TARGET_GAMES = (
    "bp35-0a0ad940",
    "ft09-0d8bbf25",
    "g50t-5849a774",
    "lf52-271a04aa",
    "lp85-305b61c3",
    "ls20-9607627b",
    "m0r0-492f87ba",
    "r11l-495a7899",
    "s5i5-18d95033",
    "sb26-7fbdac44",
    "su15-1944f8ab",
    "tn36-ef4dde99",
    "tr87-cd924810",
    "vc33-5430563c",
)


def parse_id(path: Path) -> tuple[str, str]:
    m = re.match(r"(.+)_p(\d+)_events\.jsonl$", path.name)
    if not m:
        return path.stem, "unknown"
    return m.group(1), f"p{m.group(2)}"


def diff_bbox(before, after):
    h, w = len(before), len(before[0])
    pts = [(r, c) for r in range(h) for c in range(w) if before[r][c] != after[r][c]]
    if not pts:
        return None
    r0, r1 = min(r for r, _ in pts), max(r for r, _ in pts)
    c0, c1 = min(c for _, c in pts), max(c for _, c in pts)
    return (r0, c0, r1, c1)


def size_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 4:
        return "2_4"
    if n <= 16:
        return "5_16"
    if n <= 64:
        return "17_64"
    if n <= 256:
        return "65_256"
    return "257_plus"


def action_class(action: str) -> str:
    if action.startswith("MOUSE("):
        return "MOUSE"
    return action or "UNKNOWN"


def audit_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    c = Counter()
    actions = Counter()
    rule_kinds = Counter()
    shift_vectors = Counter()
    by_action: dict[str, Counter] = defaultdict(Counter)
    pre = events[0]

    for e in events[1:]:
        if e.get("type") != "action":
            pre = e
            continue
        before = base.as_grid(pre["board"])
        after = base.as_grid(e["board"])
        action = base.action_name(e)
        pre = e
        if not base.same_shape(before, after):
            c["shape_change"] += 1
            continue

        c["transitions"] += 1
        actions[action_class(action)] += 1
        ac = by_action[action_class(action)]
        ac["transitions"] += 1

        changed = sum(
            before[r][cc] != after[r][cc]
            for r in range(len(before))
            for cc in range(len(before[0]))
        )
        c[f"changed_bucket:{size_bucket(changed)}"] += 1
        ac[f"changed_bucket:{size_bucket(changed)}"] += 1

        if changed == 0:
            c["identity"] += 1
            ac["identity"] += 1
        else:
            bbox = diff_bbox(before, after)
            if bbox is not None:
                r0, c0, r1, c1 = bbox
                bh, bw = r1 - r0 + 1, c1 - c0 + 1
                area = bh * bw
                c["bbox_area_total"] += area
                c["bbox_height_total"] += bh
                c["bbox_width_total"] += bw
                if bh == len(before) and bw == len(before[0]):
                    c["whole_board_bbox"] += 1

        rules = base.infer_rules(before, after)
        kinds = sorted({str(x["kind"]) for x in rules})
        if kinds:
            c["r134_rule_covered"] += 1
            ac["r134_rule_covered"] += 1
            for kind in kinds:
                rule_kinds[kind] += 1
                ac[f"rule:{kind}"] += 1

        if r136.infer_local_program(before, after) is not None:
            c["local_patch_eligible"] += 1
            ac["local_patch_eligible"] += 1

        if changed:
            best = r167.best_nonzero_shift(before, after)
            fit = float(best["valid_match_fraction"])
            if fit >= 0.98:
                c["shift_fit_098"] += 1
                ac["shift_fit_098"] += 1
                shift_vectors[f"{int(best['dr'])},{int(best['dc'])}"] += 1
            elif fit >= 0.90:
                c["shift_fit_090"] += 1
                ac["shift_fit_090"] += 1

    n = int(c["transitions"])
    out = {
        "transitions": n,
        "identity": int(c["identity"]),
        "shape_change": int(c["shape_change"]),
        "r134_rule_covered": int(c["r134_rule_covered"]),
        "local_patch_eligible": int(c["local_patch_eligible"]),
        "shift_fit_098": int(c["shift_fit_098"]),
        "shift_fit_090": int(c["shift_fit_090"]),
        "whole_board_bbox": int(c["whole_board_bbox"]),
        "actions": dict(actions),
        "rule_kinds": dict(rule_kinds),
        "shift_vectors": dict(shift_vectors),
        "changed_buckets": {
            k.split(":",1)[1]: int(v)
            for k,v in c.items() if k.startswith("changed_bucket:")
        },
        "by_action": {k: dict(v) for k,v in sorted(by_action.items())},
    }
    for key in ("identity","r134_rule_covered","local_patch_eligible","shift_fit_098"):
        out[key + "_fraction"] = round(out[key] / n, 6) if n else None
    if n:
        out["mean_bbox_area"] = round(int(c["bbox_area_total"]) / max(1, n - out["identity"]), 3)
    else:
        out["mean_bbox_area"] = None
    return out


def merge(parts: list[dict[str, Any]]) -> dict[str, Any]:
    scalar = Counter()
    actions = Counter()
    rule_kinds = Counter()
    shift_vectors = Counter()
    changed = Counter()
    by_action: dict[str, Counter] = defaultdict(Counter)

    for p in parts:
        for k in ("transitions","identity","shape_change","r134_rule_covered",
                  "local_patch_eligible","shift_fit_098","shift_fit_090","whole_board_bbox"):
            scalar[k] += int(p.get(k,0))
        actions.update(p.get("actions",{}))
        rule_kinds.update(p.get("rule_kinds",{}))
        shift_vectors.update(p.get("shift_vectors",{}))
        changed.update(p.get("changed_buckets",{}))
        for a, vals in p.get("by_action",{}).items():
            by_action[a].update(vals)

    n = scalar["transitions"]
    out = {
        **{k:int(v) for k,v in scalar.items()},
        "actions": dict(actions),
        "rule_kinds": dict(rule_kinds),
        "shift_vectors": dict(shift_vectors),
        "changed_buckets": dict(changed),
        "by_action": {k: dict(v) for k,v in sorted(by_action.items())},
    }
    for key in ("identity","r134_rule_covered","local_patch_eligible","shift_fit_098"):
        out[key + "_fraction"] = round(out.get(key,0) / n, 6) if n else None
    return out


def run(game: str, paths: list[Path]) -> dict[str, Any]:
    parts = []
    for p in sorted(paths, key=lambda x: x.name):
        g, path = parse_id(p)
        if g != game:
            raise ValueError(f"input {p.name} does not match --game {game}")
        parts.append({"path":path,"file":p.name,"metrics":audit_trace(base.load_events(p))})
    agg = merge([x["metrics"] for x in parts])
    return {
        "schema":"deus/arc3-remaining14-mechanism-inventory/1",
        "rung":RUNG,
        "game":game,
        "trace_count":len(parts),
        "aggregate":agg,
        "per_trace":parts,
        "diagnostic_gate":"MECHANISM_INVENTORY_COMPLETE",
        "truth":{
            "public_trace_only":True,
            "outcome_assisted_characterization_only":True,
            "prediction_claim":False,
            "independent_generalization_claim":False,
            "kaggle_execution":False,
            "submission_quota_spent":False,
            "owner_score_claim":False,
        },
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--game",required=True)
    ap.add_argument("--input",type=Path,action="append",default=[])
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.game not in TARGET_GAMES:
        raise SystemExit(f"game not in remaining14 target set: {a.game}")
    if not a.input:
        raise SystemExit("input required")
    d=run(a.game,a.input)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"rung":RUNG,"game":a.game,"aggregate":d["aggregate"]},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
