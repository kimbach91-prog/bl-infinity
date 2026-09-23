#!/usr/bin/env python3
"""R284: source-free translation-invariant local object-delta diagnostic.

Purpose
-------
Repair the R273 absolute-object NO_SIGNAL falsifier by changing representation,
not thresholds: learn exact local transition deltas relative to a connected
component anchor, then test only on p5-p9 after fitting p0-p4.

Protocol
--------
* Public traces only; no game source and no score/leaderboard inputs.
* Fit: p0-p4 only.
* Diagnostic: p5-p9 only. p10-p19 are neither required nor read.
* A learned rule must be deterministic, have >=2 supporting transitions and
  occur at >=2 distinct absolute anchor locations (translation evidence).
* Prediction requires exactly one matching anchor and exact applicability of
  every learned before-cell. Otherwise abstain.
* Exact full-frame scoring. Any wrong prediction rejects the mechanism.

This is PUBLIC_OFFLINE mechanism evidence only, never Kaggle/hidden evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import public_sourcefree_markov_fidelity_adapter_246 as r246
import public_action_conditional_markov_gate_251 as r251

RUNG = 284
MIN_SUPPORT = 2
MAX_DIFF = 64
MAX_LOCAL_MARGIN = 4


def dominant_bg(board: list[list[int]]) -> int:
    c = Counter(v for row in board for v in row)
    return c.most_common(1)[0][0]


def components(board: list[list[int]]) -> list[dict[str, Any]]:
    h, w = len(board), len(board[0])
    bg = dominant_bg(board)
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, Any]] = []
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or board[y][x] == bg:
                continue
            q = deque([(y, x)])
            seen.add((y, x))
            cells: list[tuple[int, int, int]] = []
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx, int(board[cy][cx])))
                for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and board[ny][nx] != bg:
                        seen.add((ny, nx)); q.append((ny, nx))
            y0 = min(y for y,_,_ in cells); x0 = min(x for _,x,_ in cells)
            y1 = max(y for y,_,_ in cells); x1 = max(x for _,x,_ in cells)
            norm = tuple(sorted((y-y0, x-x0, v) for y,x,v in cells))
            sig = (y1-y0+1, x1-x0+1, len(cells), norm)
            out.append({"bbox": (y0,x0,y1,x1), "anchor": (y0,x0), "cells": cells, "sig": sig})
    return out


def diff_cells(before: list[list[int]], after: list[list[int]]) -> list[tuple[int,int,int,int]]:
    if len(before) != len(after) or len(before[0]) != len(after[0]):
        return []
    return [(y,x,int(before[y][x]),int(after[y][x]))
            for y in range(len(before)) for x in range(len(before[0]))
            if before[y][x] != after[y][x]]


def bbox_distance(c: dict[str, Any], y: int, x: int) -> int:
    y0,x0,y1,x1 = c["bbox"]
    dy = 0 if y0 <= y <= y1 else min(abs(y-y0), abs(y-y1))
    dx = 0 if x0 <= x <= x1 else min(abs(x-x0), abs(x-x1))
    return dy + dx


def choose_anchor(before: list[list[int]], diffs: list[tuple[int,int,int,int]]) -> dict[str, Any] | None:
    comps = components(before)
    if not comps or not diffs:
        return None
    ranked = []
    for c in comps:
        near = sum(bbox_distance(c,y,x) <= 1 for y,x,_,_ in diffs)
        total_d = sum(bbox_distance(c,y,x) for y,x,_,_ in diffs)
        ranked.append((-near, total_d, -len(c["cells"]), c))
    ranked.sort(key=lambda z: z[:3])
    c = ranked[0][3]
    if max(bbox_distance(c,y,x) for y,x,_,_ in diffs) > MAX_LOCAL_MARGIN:
        return None
    return c


def rule_observation(r: dict[str, Any]) -> tuple[Any, Any, tuple[int,int]] | None:
    b, a = r["before"], r["after"]
    ds = diff_cells(b, a)
    if not ds or len(ds) > MAX_DIFF:
        return None
    c = choose_anchor(b, ds)
    if c is None:
        return None
    ay, ax = c["anchor"]
    # Include both expected before value and exact replacement value so a rule
    # cannot silently apply to a different local state.
    delta = tuple(sorted((y-ay, x-ax, bv, av) for y,x,bv,av in ds))
    key = (r["action"], c["sig"])
    return key, delta, (ay, ax)


def fit_rules(rows: list[dict[str, Any]]) -> tuple[dict[Any, Any], dict[str, Any]]:
    obs: dict[Any, Counter] = defaultdict(Counter)
    anchors: dict[tuple[Any, Any], set[tuple[int,int]]] = defaultdict(set)
    usable = 0
    for r in rows:
        o = rule_observation(r)
        if o is None:
            continue
        usable += 1
        key, delta, anchor = o
        obs[key][delta] += 1
        anchors[(key, delta)].add(anchor)
    rules: dict[Any, Any] = {}
    for key, ctr in obs.items():
        if len(ctr) != 1:
            continue
        delta, support = ctr.most_common(1)[0]
        if support < MIN_SUPPORT or len(anchors[(key, delta)]) < 2:
            continue
        rules[key] = delta
    return rules, {"fit_rows": len(rows), "usable_local_transitions": usable, "learned_rules": len(rules)}


def predict(row: dict[str, Any], rules: dict[Any, Any]) -> list[list[int]] | None:
    board = row["before"]
    matches: list[tuple[dict[str, Any], Any]] = []
    for c in components(board):
        key = (row["action"], c["sig"])
        if key in rules:
            matches.append((c, rules[key]))
    if len(matches) != 1:
        return None
    c, delta = matches[0]
    ay, ax = c["anchor"]
    h, w = len(board), len(board[0])
    out = [list(r) for r in board]
    for dy, dx, before_v, after_v in delta:
        y, x = ay + dy, ax + dx
        if not (0 <= y < h and 0 <= x < w) or int(out[y][x]) != int(before_v):
            return None
    for dy, dx, before_v, after_v in delta:
        out[ay+dy][ax+dx] = int(after_v)
    return out


def eval_game(paths: list[Path]) -> dict[str, Any]:
    ps = sorted(paths, key=r246.pnum)
    nums = [r246.pnum(p) for p in ps]
    if nums != list(range(10)):
        raise ValueError(f"exact p0..p9 required, got {nums}")
    train = [r for p in ps[:5] for r in r251.prepare_rows([p])]
    val = [r for p in ps[5:10] for r in r251.prepare_rows([p])]
    rules, fit = fit_rules(train)
    s = Counter(); examples=[]
    for r in val:
        s["transitions"] += 1
        pred = predict(r, rules)
        if pred is None:
            s["abstain"] += 1
            continue
        s["predictions"] += 1
        ok = pred == r["after"]
        s["correct" if ok else "wrong"] += 1
        if len(examples) < 20:
            examples.append({"trace": r["trace"], "action": r["action"], "correct": ok})
    p=s["predictions"]
    verdict = "PASS_ZERO_WRONG_SIGNAL" if p > 0 and s["wrong"] == 0 else ("NO_SIGNAL" if p == 0 else "REJECT_MISMATCH")
    return {"fit": fit, "diagnostic": {**dict(s), "accuracy": round(s["correct"]/p,6) if p else None, "examples":examples}, "verdict": verdict}


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a=ap.parse_args()
    by: dict[str,list[Path]] = defaultdict(list)
    for p in a.input:
        by[r246.game_id(p)].append(p)
    games={g:eval_game(ps) for g,ps in sorted(by.items())}
    agg=Counter()
    for x in games.values():
        d=x["diagnostic"]
        for k in ("transitions","predictions","correct","wrong","abstain"):
            agg[k]+=int(d.get(k,0) or 0)
    p=agg["predictions"]
    verdict = "PASS_ZERO_WRONG_SIGNAL" if p>0 and agg["wrong"]==0 else ("NO_SIGNAL" if p==0 else "REJECT_MISMATCH")
    out={
      "schema":"deus/arc3-r284-relational-local-delta/1",
      "rung":RUNG,
      "protocol":{"fit":"p0-p4 only","diagnostic":"p5-p9 only","p10_p19_staged":False,
                  "representation":"translation-invariant connected-component anchored exact local delta",
                  "min_support":MIN_SUPPORT,"min_distinct_absolute_anchors":2,"exact_full_frame_scoring":True},
      "games":games,
      "aggregate":{**dict(agg),"accuracy":round(agg["correct"]/p,6) if p else None,"verdict":verdict},
      "truth":{"public_trace_only":True,"game_source_read":False,"source_free":True,"p10_p19_read":False,
               "independent_generalization_claim":False,"kaggle_execution":False,"competition_submission":False,
               "owner_score_claim":False,"submission_quota_spent":False}
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out["aggregate"],sort_keys=True))

if __name__=="__main__":
    main()
