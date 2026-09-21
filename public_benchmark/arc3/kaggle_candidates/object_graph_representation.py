"""Clean-room object-centric state representation for ARC-AGI-3 harness experiments.

This implementation is written independently from first principles. Public research
on object-centric ARC harnesses (including the July 2026 Duck exposition) motivated
the *idea* of testing connected-component/object summaries, but that repository has
no root LICENSE file at pinned commit 0a05c529ab58121843b5aaa29a411e175d159118.
Accordingly, no upstream implementation code is copied here.

Scope: public-development representation research only. This module does not read
hidden state, does not submit to Kaggle, and makes no leaderboard-score claim.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Sequence


Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class ObjectNode:
    color: int
    area: int
    bbox: tuple[int, int, int, int]
    bbox_center_x2: tuple[int, int]
    shape_key: str
    color_shape_key: str

    def compact(self) -> dict[str, object]:
        return {
            "c": self.color,
            "a": self.area,
            "b": self.bbox,
            "p2": self.bbox_center_x2,
            "s": self.shape_key,
            "cs": self.color_shape_key,
        }


def normalize_grid(raw: Sequence[Sequence[int]]) -> Grid:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("grid must be a non-empty sequence of rows")
    width: int | None = None
    rows: list[tuple[int, ...]] = []
    for raw_row in raw:
        if not isinstance(raw_row, (list, tuple)) or not raw_row:
            raise ValueError("each row must be a non-empty sequence")
        row: list[int] = []
        for cell in raw_row:
            if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell <= 15:
                raise ValueError("cells must be integer ARC colors in [0, 15]")
            row.append(cell)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError("grid must be rectangular")
        rows.append(tuple(row))
    return tuple(rows)


def _digest(payload: object, n: int = 12) -> str:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:n]


def _component_cells(grid: Grid, *, background: int = 0) -> list[tuple[int, set[tuple[int, int]]]]:
    h, w = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, set[tuple[int, int]]]] = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or grid[r][c] == background:
                continue
            color = grid[r][c]
            q: deque[tuple[int, int]] = deque([(r, c)])
            seen.add((r, c))
            cells: set[tuple[int, int]] = set()
            while q:
                rr, cc = q.popleft()
                cells.add((rr, cc))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = rr + dr, cc + dc
                    if not (0 <= nr < h and 0 <= nc < w):
                        continue
                    if (nr, nc) in seen or grid[nr][nc] != color:
                        continue
                    seen.add((nr, nc))
                    q.append((nr, nc))
            out.append((color, cells))
    return out


def _node(color: int, cells: Iterable[tuple[int, int]]) -> ObjectNode:
    pts = sorted(cells)
    min_r = min(r for r, _ in pts)
    min_c = min(c for _, c in pts)
    max_r = max(r for r, _ in pts)
    max_c = max(c for _, c in pts)
    norm = sorted((r - min_r, c - min_c) for r, c in pts)
    shape_key = _digest(norm)
    return ObjectNode(
        color=color,
        area=len(pts),
        bbox=(min_r, min_c, max_r, max_c),
        bbox_center_x2=(min_r + max_r, min_c + max_c),
        shape_key=shape_key,
        color_shape_key=_digest((color, norm)),
    )


def encode_object_graph(raw: Sequence[Sequence[int]], *, background: int = 0) -> dict[str, object]:
    grid = normalize_grid(raw)
    nodes = [_node(color, cells) for color, cells in _component_cells(grid, background=background)]
    nodes.sort(key=lambda n: (n.bbox[0], n.bbox[1], n.color, n.area, n.shape_key))
    return {
        "h": len(grid),
        "w": len(grid[0]),
        "bg": background,
        "n": len(nodes),
        "o": [node.compact() for node in nodes],
    }


def compact_json(raw: Sequence[Sequence[int]], *, background: int = 0) -> str:
    return json.dumps(encode_object_graph(raw, background=background), separators=(",", ":"), sort_keys=True)


def raw_ascii(raw: Sequence[Sequence[int]]) -> str:
    grid = normalize_grid(raw)
    return "\n".join(" ".join(str(cell) for cell in row) for row in grid)


def stable_shape_multiset(raw: Sequence[Sequence[int]], *, background: int = 0) -> tuple[str, ...]:
    encoded = encode_object_graph(raw, background=background)
    return tuple(sorted(obj["s"] for obj in encoded["o"]))
