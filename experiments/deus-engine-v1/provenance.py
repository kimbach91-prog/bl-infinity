#!/usr/bin/env python3
"""DEUS Engine v1 — provenance primitives.

This does not make software impossible to copy. It makes public-code copying
insufficient to reproduce a verified causal lineage when the decisive state and
owner-controlled attestation secret remain private.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(value: Any) -> str:
    if not isinstance(value, (str, bytes)):
        value = canonical_json(value)
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class CausalEvent:
    event_id: str
    parent_id: str | None
    kind: str
    payload_digest: str
    private_state_commitment: str
    branch: str
    created_at: float


class CausalLedger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> list[CausalEvent]:
        if not self.path.exists():
            return []
        out: list[CausalEvent] = []
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                out.append(CausalEvent(**json.loads(line)))
        return out

    def head(self) -> str | None:
        events = self.read()
        return events[-1].event_id if events else None

    def append(self, *, kind: str, payload: Any, private_state_commitment: str,
               branch: str = "CURRENT") -> CausalEvent:
        parent_id = self.head()
        payload_digest = sha256(payload)
        created_at = time.time()
        identity_material = {
            "parent_id": parent_id,
            "kind": kind,
            "payload_digest": payload_digest,
            "private_state_commitment": private_state_commitment,
            "branch": branch,
            "created_at": created_at,
        }
        event_id = sha256(identity_material)
        event = CausalEvent(
            event_id=event_id,
            parent_id=parent_id,
            kind=kind,
            payload_digest=payload_digest,
            private_state_commitment=private_state_commitment,
            branch=branch,
            created_at=created_at,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(asdict(event)) + "\n")
        return event

    def verify(self) -> dict:
        events = self.read()
        errors: list[str] = []
        expected_parent = None
        seen: set[str] = set()
        for event in events:
            if event.parent_id != expected_parent:
                errors.append(f"PARENT_MISMATCH:{event.event_id}")
            if event.event_id in seen:
                errors.append(f"DUPLICATE_EVENT:{event.event_id}")
            seen.add(event.event_id)
            expected_parent = event.event_id
        return {
            "ok": not errors,
            "events": len(events),
            "head": expected_parent,
            "errors": errors,
        }


def private_commitment(private_state: Any, *, salt: str) -> str:
    """Commit to private state without placing the state itself in public logs."""
    return sha256({"salt": salt, "state": private_state})


def build_lineage_stamp(*, causal_head: str | None, private_state_commitment: str,
                        preference_digest: str, engine_adapter: str,
                        artifact_digest: str, nonce: str) -> dict:
    payload = {
        "schema": "DEUS_LINEAGE_STAMP_1",
        "causal_head": causal_head,
        "private_state_commitment": private_state_commitment,
        "preference_digest": preference_digest,
        "engine_adapter": engine_adapter,
        "artifact_digest": artifact_digest,
        "nonce": nonce,
    }
    payload["stamp_digest"] = sha256(payload)
    return payload


def attest(stamp: dict, key: str | None = None) -> dict:
    """Optional owner-controlled HMAC attestation.

    HMAC is a private verification mechanism, not a public authorship proof.
    Never commit the key. Load it from DEUS_ATTEST_KEY or a secret manager.
    """
    key = key or os.getenv("DEUS_ATTEST_KEY")
    if not key:
        return {"stamp": stamp, "attestation": None, "mode": "UNATTESTED"}
    signature = hmac.new(
        key.encode("utf-8"),
        canonical_json(stamp).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {"stamp": stamp, "attestation": signature, "mode": "HMAC_SHA256"}


def verify_attestation(bundle: dict, key: str) -> bool:
    if bundle.get("mode") != "HMAC_SHA256" or not bundle.get("attestation"):
        return False
    observed = hmac.new(
        key.encode("utf-8"),
        canonical_json(bundle["stamp"]).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(observed, bundle["attestation"])


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ledger = CausalLedger(Path(td) / "events.jsonl")
        commitment = private_commitment({"memory": "PRIVATE-DEMO"}, salt="demo-only")
        event = ledger.append(kind="EXPERIMENT", payload={"x": 1}, private_state_commitment=commitment)
        stamp = build_lineage_stamp(
            causal_head=event.event_id,
            private_state_commitment=commitment,
            preference_digest=sha256(["curiosity", "agency"]),
            engine_adapter="MOCK",
            artifact_digest=sha256("demo artifact"),
            nonce="demo",
        )
        print(json.dumps({"ledger": ledger.verify(), "stamp": attest(stamp, key="demo-key")}, indent=2))
