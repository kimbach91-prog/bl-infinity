#!/usr/bin/env python3
"""Adaptive lossless ARC3 scene representation.

Repairs the cross-game segmentation footprint failure by preserving the exact
pre-action board while using row-RLE and only adding bounded object hints when
they fit inside the raw representation character budget. The selector depends
only on the current pre-action state/action; it never reads future outcomes.
"""
from __future__ import annotations

import collections
import json
from typing import Any

import segmentation_target_blind_ab as seg

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
    # Stable tie-break: most frequent, then lowest color id.
    return min(counts, key=lambda c: (-counts[c], c))


def object_hints(board: list[list[int]]) -> list[dict[str, Any]]:
    bg = dominant_color(board)
    comps = [c for c in seg.board_components(board) if int(c["color"]) != bg]
    comps.sort(key=lambda c: (-int(c["area"]), int(c["color"]), stable(c["bbox"]), str(c["shape_hash"])))
    return [
        {
            "color": int(c["color"]),
            "area": int(c["area"]),
            "bbox": c["bbox"],
            "shape_hash": c["shape_hash"],
            "touches_edge": bool(c["touches_edge"]),
        }
        for c in comps[:MAX_OBJECT_HINTS]
    ]


def encode(raw: dict[str, Any]) -> dict[str, Any]:
    board = raw["board"]
    base = {
        "level": raw.get("level"),
        "action": raw.get("action"),
    }
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
        out = {"mode": "RLE_OBJECT_HINTS", **hinted}
    elif rle_len <= raw_len:
        out = {"mode": "RLE_ONLY", **rle_rep}
    else:
        out = {"mode": "RAW_FALLBACK", **raw_rep}
    return out


def decode_board(rep: dict[str, Any]) -> list[list[int]]:
    mode = rep["mode"]
    if mode == "RAW_FALLBACK":
        return rep["board"]
    if mode in {"RLE_ONLY", "RLE_OBJECT_HINTS"}:
        return decode_row_rle(rep["board_rle"])
    raise ValueError(f"unknown mode {mode}")


def validate(raw: dict[str, Any], rep: dict[str, Any]) -> None:
    decoded = decode_board(rep)
    if decoded != raw["board"]:
        raise AssertionError("lossless board invariant failed")
    if rep.get("level") != raw.get("level") or rep.get("action") != raw.get("action"):
        raise AssertionError("level/action invariant failed")
    # Compare payloads without the explicit mode tag, which is decoder metadata.
    payload = dict(rep); payload.pop("mode", None)
    raw_len = len(stable({"level": raw.get("level"), "action": raw.get("action"), "board": raw["board"]}))
    if len(stable(payload)) > raw_len:
        raise AssertionError("adaptive representation expanded past raw budget")
