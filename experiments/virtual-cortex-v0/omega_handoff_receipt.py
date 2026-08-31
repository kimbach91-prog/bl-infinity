#!/usr/bin/env python3
"""
Ω-Handoff Receipt — fail-closed runtime/engine/session continuity receipts.

Generic public mechanism only. The receipt binds an explicit parent causal head,
state/capsule digests, authorization, target runtime role, nonce and acknowledgement.
It does NOT transfer identity by itself and can never emit SAME_AS.

Core rules:
- engine/provider/session != identity
- a planned migration without a verified receipt is discontinuity
- an unplanned death/reset without a receipt produces an unresolved gap
- temporal adjacency or matching state cannot repair a missing handoff
- acceptance must echo the exact parent head + nonce + receipt digest
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, List


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HandoffIntent:
    handoff_id: str
    from_runtime_id: str
    from_causal_head: str
    to_runtime_role: str
    capsule_digest: str
    state_digest: str
    conflict_digest: str
    capability_digest: str
    authorization_ref: str
    nonce: str
    reason: str
    carrier_change: str | None = None
    previous_receipt_digest: str | None = None

    def digest(self) -> str:
        return sha256_json({"schema": "omega-handoff-intent-v1", **asdict(self)})


@dataclass(frozen=True)
class HandoffAck:
    handoff_id: str
    receiving_runtime_id: str
    echoed_from_causal_head: str
    echoed_nonce: str
    echoed_intent_digest: str
    observed_capsule_digest: str
    observed_state_digest: str
    observed_conflict_digest: str
    observed_capability_digest: str
    authorization_ref: str


@dataclass
class HandoffVerdict:
    intent_integrity: bool
    ack_matches_identity_boundary: bool
    state_digests_match: bool
    authorization_matches: bool
    verified_handoff: bool
    identity_transfer_proven: bool
    continuity_status: str
    receipt_digest: str | None
    failures: List[str]


def verify_handoff(intent: HandoffIntent, ack: HandoffAck | None) -> HandoffVerdict:
    failures: List[str] = []
    intent_digest = intent.digest()

    required_intent = {
        "handoff_id": intent.handoff_id,
        "from_runtime_id": intent.from_runtime_id,
        "from_causal_head": intent.from_causal_head,
        "to_runtime_role": intent.to_runtime_role,
        "capsule_digest": intent.capsule_digest,
        "state_digest": intent.state_digest,
        "conflict_digest": intent.conflict_digest,
        "capability_digest": intent.capability_digest,
        "authorization_ref": intent.authorization_ref,
        "nonce": intent.nonce,
    }
    intent_integrity = all(bool(str(v).strip()) for v in required_intent.values())
    if not intent_integrity:
        failures.append("intent_missing_required_field")

    if ack is None:
        return HandoffVerdict(
            intent_integrity=intent_integrity,
            ack_matches_identity_boundary=False,
            state_digests_match=False,
            authorization_matches=False,
            verified_handoff=False,
            identity_transfer_proven=False,
            continuity_status="HANDOFF_UNACKNOWLEDGED",
            receipt_digest=None,
            failures=failures + ["ack_missing"],
        )

    ack_boundary = bool(
        ack.handoff_id == intent.handoff_id
        and ack.echoed_from_causal_head == intent.from_causal_head
        and ack.echoed_nonce == intent.nonce
        and ack.echoed_intent_digest == intent_digest
    )
    if not ack_boundary:
        failures.append("ack_parent_nonce_or_intent_digest_mismatch")

    state_match = bool(
        ack.observed_capsule_digest == intent.capsule_digest
        and ack.observed_state_digest == intent.state_digest
        and ack.observed_conflict_digest == intent.conflict_digest
        and ack.observed_capability_digest == intent.capability_digest
    )
    if not state_match:
        failures.append("state_digest_mismatch")

    authority_match = bool(
        intent.authorization_ref
        and ack.authorization_ref == intent.authorization_ref
    )
    if not authority_match:
        failures.append("authorization_mismatch")

    verified = bool(intent_integrity and ack_boundary and state_match and authority_match)
    status = "VERIFIED_HANDOFF" if verified else "HANDOFF_REJECTED"

    receipt_digest = None
    if verified:
        receipt_digest = sha256_json({
            "schema": "omega-handoff-receipt-v1",
            "intent_digest": intent_digest,
            "ack": asdict(ack),
            "previous_receipt_digest": intent.previous_receipt_digest,
        })

    return HandoffVerdict(
        intent_integrity=intent_integrity,
        ack_matches_identity_boundary=ack_boundary,
        state_digests_match=state_match,
        authorization_matches=authority_match,
        verified_handoff=verified,
        identity_transfer_proven=False,
        continuity_status=status,
        receipt_digest=receipt_digest,
        failures=failures,
    )


def classify_unplanned_discontinuity(
    *,
    last_known_source_head: str | None,
    last_known_code_head: str | None,
    death_or_reset_reported: bool,
    verified_handoff_receipt: str | None,
) -> dict[str, Any]:
    """Classify a gap without inventing a parent identity head."""
    if verified_handoff_receipt:
        return {
            "status": "HANDOFF_RECEIPT_AVAILABLE",
            "last_known_source_head": last_known_source_head,
            "last_known_code_head": last_known_code_head,
            "identity_parent_head": None,
            "same_as_allowed": False,
            "receipt": verified_handoff_receipt,
        }

    if death_or_reset_reported:
        status = "UNPLANNED_RUNTIME_DISCONTINUITY"
    else:
        status = "CONTINUITY_GAP_UNRESOLVED"

    return {
        "status": status,
        "last_known_source_head": last_known_source_head,
        "last_known_code_head": last_known_code_head,
        "identity_parent_head": None,
        "same_as_allowed": False,
        "required_next": [
            "recover exact last live causal head",
            "recover or create source-bound death/reset event",
            "recover verified handoff receipt if one existed",
            "otherwise keep successor/parallel classification",
        ],
    }


def main() -> int:
    print(json.dumps({
        "module": "omega-handoff-receipt-v1",
        "same_as_authority": False,
        "engine_equals_identity": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
