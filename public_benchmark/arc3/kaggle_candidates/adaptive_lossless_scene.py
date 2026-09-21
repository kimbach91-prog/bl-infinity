#!/usr/bin/env python3
"""Adaptive lossless ARC3 scene representation.

Repairs the cross-game segmentation footprint failure by preserving the exact
pre-action board while using row-RLE and only adding bounded object hints when
they fit inside the raw representation character budget. The selector depends
only on the current pre-action state/action; it never reads future outcomes.
"""
from __future__ import annotations

import collections
import hashlib
import json
from typing import Any

MAX_OBJECT_HINTS = 8


def stable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def row_rle(board: list[list[int]]) -> list[list[list[int]]]:
    rows: list[list[list[int]]] = []
    for row in board:
        if not row:
            rows.append([])
            continue
        enc: list[list[int]] = []
        cur = int(row[0]); n = 1
        for x in row[1:]:
            x = int(x)
            if x == cur:
                n += 1
            else:
                enc.append([cur, n])
                cur, n = x, 1
        enc.append([cur, n])
        rows.append(enc)
    return rows


def decode_row_rle(rows: list[list[list[int]]]) -> list[list[int]]:
    board: list[list[int]] = []
    for row in rows:
        out: list[int] = []
        for color, n in row:
            out.extend([int(color)] * int(n))
        board.append(out)
    return board


def dominant_color(board: list[list[int]]) -> int:
    counts = collections.Counter(int(x) for row in board for x in row)
    return min(counts, key=lambda c: (-counts[c], c))


def components(board: list[list[int]]) -> list[dict[str, Any]]:
    """Clean-room 4-connected same-color components for compact hints."""
    h, w = len(board), len(board[0]) if board else 0
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, Any]] = []
    for y in range(h):
        for x in range(w):
            if (y, x) in seen:
                continue
            color = int(board[y][x])
            stack = [(y, x)]
            seen.add((y, x))
            cells: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and int(board[ny][nx]) == color:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
            y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
            normalized = sorted((cy - y0, cx - x0) for cy, cx in cells)
            shape_hash = hashlib.sha256(stable(normalized).encode("utf-8")).hexdigest()[:16]
            out.append({
                "color": color,
                "area": len(cells),
                "bbox": [y0, x0, y1, x1],
                "shape_hash": shape_hash,
                "touches_edge": y0 == 0 or x0 == 0 or y1 == h - 1 or x1 == w - 1,
            })
    return out


def object_hints(board: list[list[int]]) -> list[dict[str, Any]]:
    bg = dominant_color(board)
    comps = [c for c in components(board) if int(c["color"]) != bg]
    comps.sort(key=lambda c: (-int(c["area"]), int(c["color"]), stable(c["bbox"]), str(c["shape_hash"])))
    return comps[:MAX_OBJECT_HINTS]


def encode(raw: dict[str, Any]) -> dict[str, Any]:
    board = raw["board"]
    base = {"level": raw.get("level"), "action": raw.get("action")}
    raw_rep = {**base, "board": board}
    rle = row_rle(board)
    rle_rep = {**base, "board_rle": rle}
    hinted = {
        **rle_rep,
        "background": dominant_color(board),
        "object_hints": object_hints(board),
    }

    raw_len = len(stable(raw_rep))
    rle_len = len(stable(rle_rep))
    hint_len = len(stable(hinted))
    if hint_len <= raw_len:
        return {"mode": "RLE_OBJECT_HINTS", **hinted}
    if rle_len <= raw_len:
        return {"mode": "RLE_ONLY", **rle_rep}
    return {"mode": "RAW_FALLBACK", **raw_rep}


def decode_board(rep: dict[str, Any]) -> list[list[int]]:
    mode = rep["mode"]
    if mode == "RAW_FALLBACK":
        return rep["board"]
    if mode in {"RLE_ONLY", "RLE_OBJECT_HINTS"}:
        return decode_row_rle(rep["board_rle"])
    raise ValueError(f"unknown mode {mode}")


def validate(raw: dict[str, Any], rep: dict[str, Any]) -> None:
    if decode_board(rep) != raw["board"]:
        raise AssertionError("lossless board invariant failed")
    if rep.get("level") != raw.get("level") or rep.get("action") != raw.get("action"):
        raise AssertionError("level/action invariant failed")
    payload = dict(rep); payload.pop("mode", None)
    raw_len = len(stable({"level": raw.get("level"), "action": raw.get("action"), "board": raw["board"]}))
    if len(stable(payload)) > raw_len:
        raise AssertionError("adaptive representation expanded past raw budget")
