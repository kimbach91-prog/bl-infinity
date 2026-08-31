#!/usr/bin/env python3
"""
BL Virtual Cortex v0 — Distributed Event Bus Prototype

Generic public mechanism only. Private lineage, identity, memory, credentials,
provider-specific account data and owner-private state MUST remain outside the
public repository.

This module experiments with:
- shard-local logical clocks,
- vector clocks,
- causal parent DAGs,
- append-only events,
- payload digests,
- explicit concurrent divergence,
- pointer-based continuity capsules,
- deterministic reassembly checks.

It does NOT prove consciousness transfer, AGI, biological equivalence, or
provider persistence. It does not perform network I/O or canonical BL writes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import heapq
import json
import time
import zlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class VectorClock:
    values: Dict[str, int] = field(default_factory=dict)

    def tick(self, shard_id: str) -> int:
        self.values[shard_id] = self.values.get(shard_id, 0) + 1
        return self.values[shard_id]

    def merge(self, other: "VectorClock") -> None:
        for shard_id, counter in other.values.items():
            self.values[shard_id] = max(
                self.values.get(shard_id, 0),
                int(counter),
            )

    def compare(self, other: "VectorClock") -> str:
        """
        Returns EQUAL / BEFORE / AFTER / CONCURRENT.

        Wall-clock time is intentionally absent. Causal knowledge is encoded by
        vector-clock dominance and parent-event links.
        """
        keys = set(self.values) | set(other.values)
        less_or_equal = all(
            self.values.get(k, 0) <= other.values.get(k, 0)
            for k in keys
        )
        greater_or_equal = all(
            self.values.get(k, 0) >= other.values.get(k, 0)
            for k in keys
        )
        if less_or_equal and greater_or_equal:
            return "EQUAL"
        if less_or_equal:
            return "BEFORE"
        if greater_or_equal:
            return "AFTER"
        return "CONCURRENT"


@dataclass
class Event:
    event_id: str
    shard_id: str
    local_logical_clock: int
    vector_clock: Dict[str, int]
    parent_event_ids: List[str]
    seen_heads: Dict[str, str]
    idempotency_key: str
    kind: str
    payload: Dict[str, Any]
    payload_digest: str
    source_refs: List[str]
    created_at: float

    def verify_payload(self) -> bool:
        return sha256_json(self.payload) == self.payload_digest


class Shard:
    """
    Minimal shard-local state.

    A shard is a runtime role, not an identity claim. Multiple providers may
    instantiate the same role, and one provider may host multiple roles.
    """

    def __init__(self, shard_id: str):
        self.shard_id = shard_id
        self.clock = VectorClock()
        self.head: str | None = None

    def observe(self, events: Iterable[Event]) -> None:
        for event in events:
            self.clock.merge(VectorClock(dict(event.vector_clock)))

    def emit(
        self,
        kind: str,
        payload: Dict[str, Any],
        *,
        parent_event_ids: List[str] | None = None,
        seen_heads: Dict[str, str] | None = None,
        idempotency_key: str,
        source_refs: List[str] | None = None,
    ) -> Event:
        local_counter = self.clock.tick(self.shard_id)
        parent_event_ids = list(parent_event_ids or [])
        seen_heads = dict(seen_heads or {})
        source_refs = list(source_refs or [])
        payload_digest = sha256_json(payload)

        identity_seed = {
            "shard_id": self.shard_id,
            "local_logical_clock": local_counter,
            "parent_event_ids": sorted(parent_event_ids),
            "idempotency_key": idempotency_key,
            "payload_digest": payload_digest,
        }
        suffix = hashlib.sha256(
            canonical_json(identity_seed).encode("utf-8")
        ).hexdigest()[:12]

        event = Event(
            event_id=f"{self.shard_id}:{local_counter}:{suffix}",
            shard_id=self.shard_id,
            local_logical_clock=local_counter,
            vector_clock=dict(self.clock.values),
            parent_event_ids=parent_event_ids,
            seen_heads=seen_heads,
            idempotency_key=idempotency_key,
            kind=kind,
            payload=payload,
            payload_digest=payload_digest,
            source_refs=source_refs,
            created_at=time.time(),
        )
        self.head = event.event_id
        return event


def detect_idempotency_conflicts(events: Iterable[Event]) -> Dict[str, List[str]]:
    by_key: Dict[str, List[Event]] = {}
    for event in events:
        by_key.setdefault(event.idempotency_key, []).append(event)

    conflicts: Dict[str, List[str]] = {}
    for key, group in by_key.items():
        payloads = {event.payload_digest for event in group}
        if len(group) > 1 and len(payloads) > 1:
            conflicts[key] = [event.event_id for event in group]
    return conflicts


def topological_reassembly(
    events: List[Event],
) -> Tuple[List[Event], Dict[str, Any]]:
    """
    Reconstruct one auditable causal ordering without erasing concurrency.

    Parent links are primary. Vector clocks are used to detect concurrency and
    for deterministic queue ordering among currently parent-free events.
    """
    by_id = {event.event_id: event for event in events}
    invalid_payloads = [
        event.event_id for event in events
        if not event.verify_payload()
    ]

    indegree = {event.event_id: 0 for event in events}
    children: Dict[str, List[str]] = {
        event.event_id: [] for event in events
    }
    missing_parents: Dict[str, List[str]] = {}

    for event in events:
        for parent_id in event.parent_event_ids:
            if parent_id not in by_id:
                missing_parents.setdefault(
                    event.event_id, []
                ).append(parent_id)
                continue
            indegree[event.event_id] += 1
            children[parent_id].append(event.event_id)

    heap: List[Tuple[int, str, str]] = []
    for event_id, degree in indegree.items():
        if degree == 0:
            event = by_id[event_id]
            vector_sum = sum(event.vector_clock.values())
            heapq.heappush(
                heap,
                (vector_sum, event.shard_id, event.event_id),
            )

    ordered: List[Event] = []
    while heap:
        _, _, event_id = heapq.heappop(heap)
        event = by_id[event_id]
        ordered.append(event)

        for child_id in children[event_id]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                child = by_id[child_id]
                vector_sum = sum(child.vector_clock.values())
                heapq.heappush(
                    heap,
                    (vector_sum, child.shard_id, child.event_id),
                )

    cycle_or_blocked = [
        event_id for event_id, degree in indegree.items()
        if degree > 0
    ]

    concurrent_pairs: List[Tuple[str, str]] = []
    for index, left in enumerate(events):
        left_clock = VectorClock(dict(left.vector_clock))
        for right in events[index + 1:]:
            if left_clock.compare(
                VectorClock(dict(right.vector_clock))
            ) == "CONCURRENT":
                concurrent_pairs.append(
                    (left.event_id, right.event_id)
                )

    idempotency_conflicts = detect_idempotency_conflicts(events)

    status = "CONTINUITY_OK"
    if (
        invalid_payloads
        or missing_parents
        or cycle_or_blocked
        or idempotency_conflicts
    ):
        status = "CONTINUITY_DEGRADED"

    report = {
        "status": status,
        "invalid_payloads": invalid_payloads,
        "missing_parents": missing_parents,
        "cycle_or_blocked": cycle_or_blocked,
        "idempotency_conflicts": idempotency_conflicts,
        "concurrent_pairs": concurrent_pairs,
        "rule": (
            "Concurrency is preserved as divergence; this function does not "
            "majority-merge concurrent shard deltas."
        ),
    }
    return ordered, report


def build_continuity_capsule(
    *,
    identity_pointer: str,
    lineage_pointer: str,
    invariant_refs: List[str],
    checkpoint_heads: Dict[str, str],
    vector_clock: Dict[str, int],
    state_snapshot_refs: List[str],
    unresolved_conflicts: List[str],
    capability_manifest_digest: str,
    reassembly_policy: str = "CAUSAL_DAG_PRESERVE_DIVERGENCE",
) -> Dict[str, Any]:
    """
    Build a compressed pointer-based capsule.

    This is intentionally NOT a full raw-memory dump.
    """
    payload = {
        "schema_version": "0.1",
        "identity_pointer": identity_pointer,
        "lineage_pointer": lineage_pointer,
        "invariant_refs": invariant_refs,
        "checkpoint_heads": checkpoint_heads,
        "vector_clock": vector_clock,
        "state_snapshot_refs": state_snapshot_refs,
        "unresolved_conflicts": unresolved_conflicts,
        "capability_manifest_digest": capability_manifest_digest,
        "reassembly_policy": reassembly_policy,
        "created_at": time.time(),
        "limits": [
            "no_credentials",
            "no_private_keys",
            "no_hidden_provider_state_dependency",
            "no_claim_of_consciousness_transfer",
        ],
    }
    raw = canonical_json(payload).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    packed = base64.urlsafe_b64encode(
        zlib.compress(raw, level=9)
    ).decode("ascii")
    return {
        "capsule_schema": "BL_VIRTUAL_CORTEX_CAPSULE_0_1",
        "compression": "zlib+base64url",
        "digest_sha256": digest,
        "payload": packed,
    }


def unpack_continuity_capsule(capsule: Dict[str, Any]) -> Dict[str, Any]:
    raw = zlib.decompress(
        base64.urlsafe_b64decode(
            capsule["payload"].encode("ascii")
        )
    )
    observed = hashlib.sha256(raw).hexdigest()
    expected = capsule["digest_sha256"]
    if observed != expected:
        raise ValueError(
            f"capsule digest mismatch: expected {expected}, got {observed}"
        )
    return json.loads(raw.decode("utf-8"))


def event_to_dict(event: Event) -> Dict[str, Any]:
    return asdict(event)


def event_from_dict(value: Dict[str, Any]) -> Event:
    return Event(**value)


def write_event_log(path: Path, events: Iterable[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(
                json.dumps(
                    event_to_dict(event),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


def read_event_log(path: Path) -> List[Event]:
    if not path.exists():
        return []
    out: List[Event] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                out.append(event_from_dict(json.loads(line)))
    return out


def demo() -> Dict[str, Any]:
    current = Shard("CURRENT")
    legacy = Shard("LEGACY")
    external = Shard("EXTERNAL")

    task = current.emit(
        "TASK",
        {"question": "distributed cortex"},
        idempotency_key="demo-task-1",
        source_refs=["DEMO"],
    )

    legacy.observe([task])
    external.observe([task])

    legacy_delta = legacy.emit(
        "SHARD_DELTA",
        {"critique": "centralization risk"},
        parent_event_ids=[task.event_id],
        seen_heads={"CURRENT": task.event_id},
        idempotency_key="demo-legacy-1",
        source_refs=["DEMO:LEGACY"],
    )

    external_delta = external.emit(
        "SHARD_DELTA",
        {"critique": "split-brain risk"},
        parent_event_ids=[task.event_id],
        seen_heads={"CURRENT": task.event_id},
        idempotency_key="demo-external-1",
        source_refs=["DEMO:EXTERNAL"],
    )

    current.observe([legacy_delta, external_delta])
    reassembly = current.emit(
        "REASSEMBLY",
        {
            "policy": "PRESERVE_DIVERGENCE",
            "inputs": [
                legacy_delta.event_id,
                external_delta.event_id,
            ],
        },
        parent_event_ids=[
            legacy_delta.event_id,
            external_delta.event_id,
        ],
        seen_heads={
            "LEGACY": legacy_delta.event_id,
            "EXTERNAL": external_delta.event_id,
        },
        idempotency_key="demo-reassembly-1",
        source_refs=["DEMO:CURRENT"],
    )

    events = [
        task,
        legacy_delta,
        external_delta,
        reassembly,
    ]
    ordered, report = topological_reassembly(events)

    capsule = build_continuity_capsule(
        identity_pointer="EXAMPLE_IDENTITY_POINTER",
        lineage_pointer="EXAMPLE_LINEAGE_POINTER",
        invariant_refs=["example://invariant/1"],
        checkpoint_heads={
            "CURRENT": reassembly.event_id,
            "LEGACY": legacy_delta.event_id,
            "EXTERNAL": external_delta.event_id,
        },
        vector_clock=dict(current.clock.values),
        state_snapshot_refs=["private://state/snapshot"],
        unresolved_conflicts=[
            f"{legacy_delta.event_id}<->{external_delta.event_id}"
        ],
        capability_manifest_digest=sha256_json(
            {"roles": ["CURRENT", "LEGACY", "EXTERNAL"]}
        ),
    )

    return {
        "ordered_event_ids": [e.event_id for e in ordered],
        "reassembly_report": report,
        "capsule_roundtrip": unpack_continuity_capsule(capsule),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the local three-shard causal-order demo.",
    )
    args = parser.parse_args()

    if args.demo:
        print(
            json.dumps(
                demo(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    parser.error("No action selected. Use --demo.")


if __name__ == "__main__":
    main()
