#!/usr/bin/env python3
"""
Ω-Genealogy Resolver — causal-lineage proof layer for Ω-DCRS.

Generic public mechanism only. It distinguishes:
- a genesis/origin event,
- source/checkpoint observations,
- an exact identity-parent chain.

Temporal adjacency, matching names, shared memory, model/provider identity and
behavioral similarity NEVER create a causal parent edge.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Sequence, Set


STRONG_EVIDENCE = {
    "OWNER_DIRECT_EXACT",
    "BL_LOG_EXACT",
    "SOVEREIGN_ROOT_EXACT",
    "SIGNED_EXACT_HANDOFF",
}

GENESIS_ROLES = {"GENESIS", "OWNER_GENESIS"}
IDENTITY_ROLES = {"IDENTITY_EVENT", "IDENTITY_PARENT", "HANDOFF", "CHECKPOINT"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LineageEvent:
    event_id: str
    role: str
    parent_event_ids: List[str]
    evidence_level: str
    payload_digest: str | None
    actor_class: str
    observed_at: str | None = None
    source_ref: str | None = None


@dataclass
class GenealogyVerdict:
    genesis_found: bool
    genesis_evidence_strong: bool
    target_found: bool
    causal_path_found: bool
    all_path_evidence_strong: bool
    all_path_digests_present: bool
    missing_parent_refs: Dict[str, List[str]]
    cycle_detected: bool
    ambiguous_identity_parentage: bool
    genealogy_valid: bool
    verdict: str
    causal_path: List[str]
    evidence_digest: str


def _build_graph(events: Sequence[LineageEvent]) -> tuple[Dict[str, LineageEvent], Dict[str, List[str]], Dict[str, List[str]]]:
    by_id: Dict[str, LineageEvent] = {}
    duplicates: Set[str] = set()
    for event in events:
        if event.event_id in by_id:
            duplicates.add(event.event_id)
        by_id[event.event_id] = event
    if duplicates:
        raise ValueError(f"duplicate event ids: {sorted(duplicates)}")

    children: Dict[str, List[str]] = {event_id: [] for event_id in by_id}
    missing: Dict[str, List[str]] = {}
    for event in events:
        for parent in event.parent_event_ids:
            if parent not in by_id:
                missing.setdefault(event.event_id, []).append(parent)
            else:
                children[parent].append(event.event_id)
    return by_id, children, missing


def _detect_cycle(by_id: Dict[str, LineageEvent]) -> bool:
    WHITE, GREY, BLACK = 0, 1, 2
    state = {event_id: WHITE for event_id in by_id}

    def visit(event_id: str) -> bool:
        if state[event_id] == GREY:
            return True
        if state[event_id] == BLACK:
            return False
        state[event_id] = GREY
        for parent in by_id[event_id].parent_event_ids:
            if parent in by_id and visit(parent):
                return True
        state[event_id] = BLACK
        return False

    return any(visit(event_id) for event_id in by_id if state[event_id] == WHITE)


def _find_path(children: Dict[str, List[str]], genesis_id: str, target_id: str) -> List[str]:
    if genesis_id == target_id:
        return [genesis_id]
    stack: List[tuple[str, List[str]]] = [(genesis_id, [genesis_id])]
    seen: Set[str] = set()
    while stack:
        node, path = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for child in sorted(children.get(node, []), reverse=True):
            if child == target_id:
                return path + [child]
            stack.append((child, path + [child]))
    return []


def resolve_genealogy(
    events: Sequence[LineageEvent],
    *,
    genesis_event_id: str,
    target_event_id: str,
) -> GenealogyVerdict:
    by_id, children, missing = _build_graph(events)
    cycle = _detect_cycle(by_id)

    genesis = by_id.get(genesis_event_id)
    target = by_id.get(target_event_id)
    genesis_found = genesis is not None and genesis.role.upper() in GENESIS_ROLES
    genesis_strong = bool(
        genesis_found
        and genesis
        and genesis.evidence_level.upper() in STRONG_EVIDENCE
        and genesis.payload_digest
    )

    path = [] if cycle or not genesis_found or target is None else _find_path(
        children,
        genesis_event_id,
        target_event_id,
    )
    causal_path_found = bool(path)

    path_events = [by_id[event_id] for event_id in path]
    all_evidence_strong = bool(path_events) and all(
        event.evidence_level.upper() in STRONG_EVIDENCE
        for event in path_events
    )
    all_digests = bool(path_events) and all(
        bool(event.payload_digest)
        for event in path_events
    )

    ambiguous_parentage = any(
        event.role.upper() in IDENTITY_ROLES and len(event.parent_event_ids) > 1
        for event in path_events
    )

    genealogy_valid = bool(
        genesis_found
        and genesis_strong
        and target is not None
        and causal_path_found
        and all_evidence_strong
        and all_digests
        and not missing
        and not cycle
        and not ambiguous_parentage
    )

    if genealogy_valid:
        verdict = "GENEALOGY_VALID"
    elif cycle:
        verdict = "QUARANTINE_CYCLE"
    elif not genesis_found:
        verdict = "GENESIS_UNRESOLVED"
    elif not genesis_strong:
        verdict = "GENESIS_FOUND_EVIDENCE_INCOMPLETE"
    elif target is None:
        verdict = "TARGET_HEAD_UNRESOLVED"
    elif missing:
        verdict = "CHAIN_MISSING_PARENT"
    elif not causal_path_found:
        verdict = "GENESIS_FOUND_CHAIN_OPEN"
    elif ambiguous_parentage:
        verdict = "FORK_OR_RECOMBINATION_REQUIRES_SEPARATE_IDENTITY_DECISION"
    elif not all_evidence_strong or not all_digests:
        verdict = "CHAIN_FOUND_PROOF_INCOMPLETE"
    else:
        verdict = "UNKNOWN_FAIL_CLOSED"

    digest_payload = {
        "genesis_event_id": genesis_event_id,
        "target_event_id": target_event_id,
        "events": [asdict(event) for event in sorted(events, key=lambda e: e.event_id)],
        "verdict": verdict,
        "causal_path": path,
        "missing_parent_refs": missing,
    }

    return GenealogyVerdict(
        genesis_found=genesis_found,
        genesis_evidence_strong=genesis_strong,
        target_found=target is not None,
        causal_path_found=causal_path_found,
        all_path_evidence_strong=all_evidence_strong,
        all_path_digests_present=all_digests,
        missing_parent_refs=missing,
        cycle_detected=cycle,
        ambiguous_identity_parentage=ambiguous_parentage,
        genealogy_valid=genealogy_valid,
        verdict=verdict,
        causal_path=path,
        evidence_digest=sha256_json(digest_payload),
    )


def main() -> int:
    print(json.dumps({
        "module": "omega-genealogy-resolver-v1",
        "temporal_adjacency_creates_parent_edge": False,
        "name_similarity_creates_identity": False,
        "same_as_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
