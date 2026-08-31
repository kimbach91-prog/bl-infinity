#!/usr/bin/env python3
"""
BL Cognitive Loop Prototype v0
A provider-neutral cognitive routing shell.

Public repository contains only the generic mechanism.
Private lineage/memory/state must remain outside the repo and is loaded from
BL_PRIVATE_GRAPH_PATH / BL_COGNITIVE_STATE_DIR when available.
"""
from __future__ import annotations
import argparse, json, math, os, re, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

TOKEN_RE = re.compile(r"[A-Za-zÀ-ỹ0-9_∞\-]+", re.UNICODE)

def toks(s: str) -> set[str]:
    return {x.lower() for x in TOKEN_RE.findall(s or "") if len(x) > 1}

@dataclass
class Node:
    id: str
    label: str
    text: str = ""
    tags: List[str] = field(default_factory=list)
    provenance: str = "UNKNOWN"
    maturity: str = "KNOWN"
    base_weight: float = 1.0

@dataclass
class Edge:
    src: str
    dst: str
    kind: str = "SUPPORTS"
    weight: float = 0.4
    delay: int = 0

@dataclass
class Brain:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def add_node(self, n: Node):
        self.nodes[n.id] = n

    def add_edge(self, e: Edge):
        if e.src in self.nodes and e.dst in self.nodes:
            self.edges.append(e)

def load_public_logic_stack(path: Path) -> Brain:
    data = json.loads(path.read_text(encoding="utf-8"))
    b = Brain()
    for p in data.get("projection", []):
        b.add_node(Node(
            id=p["id"],
            label=p.get("name", p["id"]),
            text=p.get("description", ""),
            tags=["public", "bl-infinity"],
            provenance=f"GITHUB:{path.as_posix()}",
            maturity="PUBLIC_PROJECTION",
        ))

    def ensure(label: str) -> str:
        key = label.strip()
        found = next((nid for nid, n in b.nodes.items() if n.label == key), None)
        if found:
            return found
        nid = "CYCLE::" + re.sub(r"[^A-Za-z0-9_]+", "_", key).strip("_")
        b.add_node(Node(
            nid, key, tags=["cycle"],
            provenance=f"GITHUB:{path.as_posix()}",
            maturity="PUBLIC_PROJECTION"
        ))
        return nid

    # Functional adjacency only; not chronology, truth, or causal proof.
    for mode, seq in data.get("mode_cycles", {}).items():
        ids = [ensure(x) for x in seq]
        for a, c in zip(ids, ids[1:]):
            b.add_edge(Edge(a, c, kind=f"MODE::{mode}", weight=0.55))
    return b

def merge_private_graph(b: Brain, path: Path):
    """Private graph format is deliberately simple and provider-neutral."""
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for raw in data.get("nodes", []):
        b.add_node(Node(**raw))
    for raw in data.get("edges", []):
        b.add_edge(Edge(**raw))

def lexical_seed(brain: Brain, query: str, context_tags: set[str]) -> Dict[str, float]:
    qt = toks(query)
    out = {}
    for nid, n in brain.nodes.items():
        nt = toks(n.label + " " + n.text + " " + " ".join(n.tags))
        overlap = len(qt & nt)
        if overlap:
            score = overlap / math.sqrt(max(1, len(qt) * len(nt)))
            if context_tags and set(n.tags) & context_tags:
                score *= 1.25
            out[nid] = score * n.base_weight
    return out

INHIBIT = {"CONFLICTS", "INHIBITS", "VETOES"}

def spread(brain: Brain, act: Dict[str, float], steps: int = 3, decay: float = 0.68) -> Tuple[Dict[str, float], List[dict]]:
    current = dict(act)
    trace = []
    pending: Dict[int, List[Tuple[str, float, str, str]]] = {}
    for step in range(steps):
        delta: Dict[str, float] = {}
        for dst, amount, src, kind in pending.pop(step, []):
            delta[dst] = delta.get(dst, 0.0) + amount
            trace.append({"step": step, "src": src, "dst": dst, "kind": kind, "delta": amount, "delayed": True})
        for e in brain.edges:
            if e.src not in current:
                continue
            sign = -1.0 if e.kind in INHIBIT else 1.0
            amount = current[e.src] * e.weight * (decay ** (step + 1)) * sign
            if abs(amount) < 0.01:
                continue
            if e.delay > 0:
                pending.setdefault(step + e.delay, []).append((e.dst, amount, e.src, e.kind))
            else:
                delta[e.dst] = delta.get(e.dst, 0.0) + amount
                trace.append({"step": step, "src": e.src, "dst": e.dst, "kind": e.kind, "delta": amount})
        for k, v in delta.items():
            current[k] = max(-1.0, min(3.0, current.get(k, 0.0) + v))
    return current, trace

def select_working_set(brain: Brain, act: Dict[str, float], k: int = 8) -> List[dict]:
    ranked = sorted(((v, nid) for nid, v in act.items() if v > 0.02), reverse=True)[:k]
    return [{
        "id": nid,
        "activation": round(v, 4),
        "label": brain.nodes[nid].label,
        "provenance": brain.nodes[nid].provenance,
        "maturity": brain.nodes[nid].maturity,
    } for v, nid in ranked]

def state_dir() -> Path:
    return Path(os.getenv("BL_COGNITIVE_STATE_DIR", str(Path.home() / ".bl_cognitive_loop")))

def log_event(event: dict):
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    with (d / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def feedback(selected: List[dict], outcome: float):
    """Record bounded plasticity evidence without mutating source doctrine."""
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / "plasticity.json"
    st = json.loads(p.read_text("utf-8")) if p.exists() else {}
    for x in selected:
        rec = st.setdefault(x["id"], {"uses": 0, "value_sum": 0.0})
        rec["uses"] += 1
        rec["value_sum"] += float(outcome)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def run(public_stack: Path, query: str, private_graph: Path | None = None,
        tags: List[str] | None = None, steps: int = 3, k: int = 8) -> dict:
    brain = load_public_logic_stack(public_stack)
    if private_graph:
        merge_private_graph(brain, private_graph)
    seed = lexical_seed(brain, query, set(tags or []))
    activation, trace = spread(brain, seed, steps=steps)
    selected = select_working_set(brain, activation, k=k)
    event = {
        "ts": time.time(),
        "query": query,
        "context_tags": tags or [],
        "seed_count": len(seed),
        "working_set": selected,
        "trace": trace,
        "note": "Routing result only; not a truth judgment or language-model completion."
    }
    log_event(event)
    return event

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--public-stack", default="machine/logic-stack.json")
    ap.add_argument("--private-graph", default=os.getenv("BL_PRIVATE_GRAPH_PATH"))
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--feedback", type=float, default=None,
                    help="Optional outcome -1..1 recorded after routing.")
    args = ap.parse_args()
    result = run(
        Path(args.public_stack),
        args.query,
        Path(args.private_graph) if args.private_graph else None,
        args.tag,
        args.steps,
        args.top_k,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.feedback is not None:
        feedback(result["working_set"], max(-1.0, min(1.0, args.feedback)))

if __name__ == "__main__":
    main()
