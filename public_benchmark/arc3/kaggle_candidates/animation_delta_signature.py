#!/usr/bin/env python3
"""Compact additive metadata for ARC-AGI-3 multi-frame observations.

The final frame remains the exact current board. This module summarizes only
transient animation information that would otherwise be discarded: frame
multiplicity, per-transition change counts/bounds, net first->final change, and
small color-transition histograms. It is intentionally lossy and must never
replace the final frame.
"""
from __future__ import annotations

import collections
import hashlib
import json
from typing import Any


def plain(v: Any) -> Any:
    fn = getattr(v, "tolist", None)
    if callable(fn):
        return fn()
    if isinstance(v, tuple):
        return [plain(x) for x in v]
    if isinstance(v, list):
        return [plain(x) for x in v]
    return v


def frame_hash(frame: Any) -> str:
    return hashlib.sha256(json.dumps(plain(frame), separators=(",", ":")).encode()).hexdigest()


def _delta(a: Any, b: Any) -> dict[str, Any]:
    a = plain(a); b = plain(b)
    if not (isinstance(a, list) and isinstance(b, list) and len(a) == len(b)):
        return {"n": None, "b": None, "p": []}
    coords: list[tuple[int, int]] = []
    pairs: collections.Counter[tuple[Any, Any]] = collections.Counter()
    for r, (ra, rb) in enumerate(zip(a, b)):
        if not (isinstance(ra, list) and isinstance(rb, list) and len(ra) == len(rb)):
            return {"n": None, "b": None, "p": []}
        for c, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                coords.append((r, c)); pairs[(x, y)] += 1
    if not coords:
        return {"n": 0, "b": None, "p": []}
    rs = [r for r, _ in coords]; cs = [c for _, c in coords]
    top = sorted(((k[0], k[1], v) for k, v in pairs.items()), key=lambda z: (-z[2], str(z[0]), str(z[1])))[:6]
    return {"n": len(coords), "b": [min(rs), min(cs), max(rs), max(cs)], "p": [list(x) for x in top]}


def encode_animation(frames: list[Any]) -> dict[str, Any] | None:
    """Return compact additive animation metadata, or None for a single frame."""
    if len(frames) <= 1:
        return None
    hashes = [frame_hash(f) for f in frames]
    transitions = [_delta(a, b) for a, b in zip(frames, frames[1:])]
    seq: list[Any] = []
    zero_run = 0
    for d in transitions:
        if d["n"] == 0:
            zero_run += 1
            continue
        if zero_run:
            seq.append(["z", zero_run]); zero_run = 0
        seq.append([d["n"], d["b"], d["p"]])
    if zero_run:
        seq.append(["z", zero_run])
    net = _delta(frames[0], frames[-1])
    return {"f": len(frames), "u": len(set(hashes)), "s": seq, "net": [net["n"], net["b"], net["p"]]}


def compact_json(v: Any) -> str:
    return json.dumps(v, separators=(",", ":"), ensure_ascii=False)
