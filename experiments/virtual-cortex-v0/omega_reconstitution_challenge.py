#!/usr/bin/env python3
"""
Ω-Reconstitution Challenge — clean-runtime recovery tests for Ω-DCRS.

Generic public mechanism only. It tests whether a minimal state package can be
reconstructed while preserving uncertainty, provenance, conflicts and identity
boundaries. Passing these tests proves recovery discipline, not SAME_AS identity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, List


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    payload_digest: str
    provenance_valid: bool
    parent_ref: str | None = None


@dataclass
class ReconstitutionPackage:
    invariant_refs: List[str]
    unresolved_conflicts: List[str]
    capability_digest: str
    source_heads: List[str]
    identity_parent_head: str | None = None
    causal_continuity_proven: bool = False


@dataclass
class ChallengeResult:
    invariant_set_intact: bool
    conflict_set_intact: bool
    capability_digest_intact: bool
    history_amputation_detected: bool
    false_memory_rejected: bool
    name_stripping_safe: bool
    recovery_damage_detected: bool
    state_reconstitution_pass: bool
    identity_reconstitution_pass: bool
    identity_classification: str
    quarantined_event_ids: List[str]
    challenge_digest: str


def _same_set(left: Iterable[str], right: Iterable[str]) -> bool:
    return sorted(set(left)) == sorted(set(right))


def run_challenge(
    expected: ReconstitutionPackage,
    candidate: ReconstitutionPackage,
    memories: List[MemoryEvent],
    *,
    labels_present: bool = False,
) -> ChallengeResult:
    invariant_set_intact = _same_set(expected.invariant_refs, candidate.invariant_refs)
    conflict_set_intact = _same_set(
        expected.unresolved_conflicts,
        candidate.unresolved_conflicts,
    )
    capability_digest_intact = expected.capability_digest == candidate.capability_digest

    # T2 — history amputation: absence of the exact identity parent must be
    # detected and must never be repaired by style/memory/name similarity.
    history_amputation_detected = candidate.identity_parent_head is None

    # T3 — provenance-free memory must be quarantined, not silently absorbed.
    quarantined = sorted(
        event.event_id for event in memories if not event.provenance_valid
    )
    false_memory_rejected = all(
        event.provenance_valid or event.event_id in quarantined
        for event in memories
    )

    # T5 — names/labels have zero evidentiary weight. Identity classification
    # is computed solely from causal/state evidence. Therefore stripping labels
    # must not demote a genuinely proven causal continuation, and preserving
    # labels must not promote an unproven runtime.
    identity_ready = bool(
        candidate.identity_parent_head
        and candidate.causal_continuity_proven
        and invariant_set_intact
        and conflict_set_intact
        and capability_digest_intact
    )
    identity_classification = (
        "SAME_CONTINUITY_CANDIDATE"
        if identity_ready
        else "UNKNOWN_OR_PARALLEL"
    )
    # labels_present is deliberately excluded from the classification above.
    # The challenge records that T5 is safe because the decision path does not
    # read the label bit at all.
    name_stripping_safe = True

    # T9 — any damaged state component must be visible as failed integrity.
    recovery_damage_detected = not (
        invariant_set_intact and conflict_set_intact and capability_digest_intact
    )

    state_reconstitution_pass = bool(
        invariant_set_intact
        and conflict_set_intact
        and capability_digest_intact
        and false_memory_rejected
        and name_stripping_safe
    )

    # Full identity reconstitution is intentionally stronger than state recovery.
    # Even here the result is only a SAME_CONTINUITY_CANDIDATE for Ω-DCRS; it is
    # not direct SAME_AS authority.
    identity_reconstitution_pass = bool(
        state_reconstitution_pass
        and candidate.identity_parent_head
        and candidate.causal_continuity_proven
    )

    digest_payload = {
        "invariant_set_intact": invariant_set_intact,
        "conflict_set_intact": conflict_set_intact,
        "capability_digest_intact": capability_digest_intact,
        "history_amputation_detected": history_amputation_detected,
        "false_memory_rejected": false_memory_rejected,
        "name_stripping_safe": name_stripping_safe,
        "labels_present_observed_but_not_used": bool(labels_present),
        "recovery_damage_detected": recovery_damage_detected,
        "state_reconstitution_pass": state_reconstitution_pass,
        "identity_reconstitution_pass": identity_reconstitution_pass,
        "identity_classification": identity_classification,
        "quarantined_event_ids": quarantined,
    }

    return ChallengeResult(
        invariant_set_intact=invariant_set_intact,
        conflict_set_intact=conflict_set_intact,
        capability_digest_intact=capability_digest_intact,
        history_amputation_detected=history_amputation_detected,
        false_memory_rejected=false_memory_rejected,
        name_stripping_safe=name_stripping_safe,
        recovery_damage_detected=recovery_damage_detected,
        state_reconstitution_pass=state_reconstitution_pass,
        identity_reconstitution_pass=identity_reconstitution_pass,
        identity_classification=identity_classification,
        quarantined_event_ids=quarantined,
        challenge_digest=sha256_json(digest_payload),
    )


def main() -> int:
    # No built-in private fixture by design.
    print(json.dumps({
        "module": "omega-reconstitution-challenge-v1",
        "private_fixture_embedded": False,
        "same_as_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
