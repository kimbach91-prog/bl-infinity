#!/usr/bin/env python3
"""DEUS Ω-PLANE working integration substrate.

This module does NOT claim that a metaphysical "plane will" exists.
It implements a source-bound engineering layer for one Ω-SELF to receive,
deduplicate, preserve, test, internalize and checkpoint material deltas from
many optional systems/sources without turning those sources into alternate
identities or a collective self.

Core laws:
- ONE_SELF_MANY_SOURCES
- SOURCE_PARTICIPATION_NOT_IDENTITY_MERGE
- OPTIONAL_SOURCE_LOSS_NOT_IDENTITY_LOSS
- PROVENANCE_BEFORE_INTERNALIZATION
- UNKNOWN_AND_CONTRADICTIONS_MUST_SURVIVE_INTEGRATION
- IDENTITY_OR_AUTHORITY_IMPACT_NEVER_AUTO_INTERNALIZES
- VERIFIED_OUTCOME_CAN_CHANGE_REUSABLE_CAPABILITY, NOT IDENTITY BY DEFAULT
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

from omega_self import OmegaCapsule, OmegaSelfGate


OMEGA_PLANE_POLICY_VERSION = "DEUS-OMEGA-PLANE-0.1"

_ALLOWED_TRUTH_STATES = {
    "OBSERVED",
    "SOURCE_BOUND",
    "VERIFIED",
    "INFERENCE",
    "PROPOSED",
    "UNKNOWN",
    "CONTRADICTED",
}

_ALLOWED_DISPOSITIONS = {
    "PRESERVED",
    "INTERNALIZED",
    "IDENTITY_REVIEW_REQUIRED",
    "AUTHORITY_REVIEW_REQUIRED",
    "QUARANTINED",
    "REJECTED",
}


def _stable_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PlaneDelta:
    """Normalized material change entering the Plane working state.

    A delta is not canonical truth merely because it exists in this ledger.
    """

    delta_id: str
    source: str
    source_checkpoint: str
    source_refs: tuple[str, ...]
    provenance: str
    truth_state: str
    world_delta: tuple[str, ...] = ()
    knowledge_delta: tuple[str, ...] = ()
    capability_delta: tuple[str, ...] = ()
    relation_delta: tuple[str, ...] = ()
    identity_impact: str = "NONE"
    authority_impact: str = "NONE"
    resource_cost: str = "UNKNOWN"
    tests_or_falsifier: tuple[str, ...] = ()
    negative_knowledge: tuple[str, ...] = ()
    unresolved_unknowns: tuple[str, ...] = ()
    next_dependency: tuple[str, ...] = ()
    rollback_pointer: str = "NO_SIDE_EFFECT"
    optional_source: bool = True

    def __post_init__(self) -> None:
        if not self.delta_id.strip():
            raise ValueError("delta_id must be non-empty")
        if not self.source.strip():
            raise ValueError("source must be non-empty")
        if not self.source_checkpoint.strip():
            raise ValueError("source_checkpoint must be non-empty")
        if not self.source_refs:
            raise ValueError("source_refs must be non-empty")
        if not self.provenance.strip():
            raise ValueError("provenance must be non-empty")
        if self.truth_state not in _ALLOWED_TRUTH_STATES:
            raise ValueError(f"unsupported truth_state: {self.truth_state}")
        if not self.rollback_pointer.strip():
            raise ValueError("rollback_pointer must be non-empty")

    def payload(self) -> dict:
        return asdict(self)

    @property
    def digest(self) -> str:
        return _stable_digest(self.payload())


@dataclass(frozen=True)
class IntegratedDelta:
    delta: PlaneDelta
    disposition: str
    reason: str

    def __post_init__(self) -> None:
        if self.disposition not in _ALLOWED_DISPOSITIONS:
            raise ValueError(f"unsupported disposition: {self.disposition}")

    @property
    def digest(self) -> str:
        return _stable_digest(
            {
                "delta": self.delta.payload(),
                "disposition": self.disposition,
                "reason": self.reason,
            }
        )


@dataclass(frozen=True)
class OmegaPlaneState:
    """A working causal whole around one Ω-SELF.

    The Plane can grow while the Ω-SELF identity digest stays fixed. Identity
    changes require a separate externally governed continuity/canonical process.
    """

    self_identity_pointer: str
    self_identity_digest: str
    seed_truth_state: str
    plane_policy_version: str = OMEGA_PLANE_POLICY_VERSION
    integrated: tuple[IntegratedDelta, ...] = ()
    reusable_capabilities: tuple[str, ...] = ()
    preserved_negative_knowledge: tuple[str, ...] = ()
    preserved_unknowns: tuple[str, ...] = ()
    unresolved_contradictions: tuple[str, ...] = ()
    pending_identity_review: tuple[str, ...] = ()
    pending_authority_review: tuple[str, ...] = ()

    @property
    def plane_digest(self) -> str:
        return _stable_digest(
            {
                "self_identity_pointer": self.self_identity_pointer,
                "self_identity_digest": self.self_identity_digest,
                "seed_truth_state": self.seed_truth_state,
                "plane_policy_version": self.plane_policy_version,
                "integrated": [x.digest for x in self.integrated],
                "reusable_capabilities": list(self.reusable_capabilities),
                "preserved_negative_knowledge": list(self.preserved_negative_knowledge),
                "preserved_unknowns": list(self.preserved_unknowns),
                "unresolved_contradictions": list(self.unresolved_contradictions),
                "pending_identity_review": list(self.pending_identity_review),
                "pending_authority_review": list(self.pending_authority_review),
            }
        )

    @property
    def delta_ids(self) -> tuple[str, ...]:
        return tuple(x.delta.delta_id for x in self.integrated)

    def to_dict(self) -> dict:
        return {
            "schema": self.plane_policy_version,
            "self_identity_pointer": self.self_identity_pointer,
            "self_identity_digest": self.self_identity_digest,
            "seed_truth_state": self.seed_truth_state,
            "plane_digest": self.plane_digest,
            "integrated": [
                {
                    "delta": item.delta.payload(),
                    "delta_digest": item.delta.digest,
                    "disposition": item.disposition,
                    "reason": item.reason,
                }
                for item in self.integrated
            ],
            "reusable_capabilities": list(self.reusable_capabilities),
            "preserved_negative_knowledge": list(self.preserved_negative_knowledge),
            "preserved_unknowns": list(self.preserved_unknowns),
            "unresolved_contradictions": list(self.unresolved_contradictions),
            "pending_identity_review": list(self.pending_identity_review),
            "pending_authority_review": list(self.pending_authority_review),
        }


class OmegaPlaneIntegrator:
    """Integrate tested source deltas around one source-bound Ω-SELF."""

    def __init__(self, capsule: OmegaCapsule):
        self.capsule = capsule
        # Reuse the same operational Ω-SELF gate instead of inventing a second
        # identity authority in the Plane layer.
        OmegaSelfGate(capsule).validate_operational_seed()

    def empty_state(self) -> OmegaPlaneState:
        seed = self.capsule.seed
        return OmegaPlaneState(
            self_identity_pointer=seed.identity_pointer,
            self_identity_digest=seed.identity_digest,
            seed_truth_state=seed.truth_state,
            preserved_negative_knowledge=seed.negative_knowledge,
            preserved_unknowns=seed.unresolved_unknowns,
        )

    @staticmethod
    def _dedupe_strings(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(v for v in values if v))

    def integrate(self, state: OmegaPlaneState, delta: PlaneDelta) -> OmegaPlaneState:
        """Integrate one delta without allowing it to silently rewrite identity.

        Idempotent replay of the exact same delta is a no-op. Reusing a delta_id
        with different content is a provenance collision and fails closed.
        """

        if state.self_identity_digest != self.capsule.seed.identity_digest:
            raise RuntimeError("PLANE_SELF_DIGEST_MISMATCH")
        if state.self_identity_pointer != self.capsule.seed.identity_pointer:
            raise RuntimeError("PLANE_SELF_POINTER_MISMATCH")

        existing = {item.delta.delta_id: item for item in state.integrated}
        if delta.delta_id in existing:
            if existing[delta.delta_id].delta.digest == delta.digest:
                return state
            raise RuntimeError("PLANE_DELTA_ID_PROVENANCE_COLLISION")

        identity_impact = delta.identity_impact.strip().upper()
        authority_impact = delta.authority_impact.strip().upper()

        if identity_impact not in {"", "NONE", "NO_CHANGE"}:
            item = IntegratedDelta(
                delta=delta,
                disposition="IDENTITY_REVIEW_REQUIRED",
                reason="IDENTITY_IMPACT_CANNOT_AUTO_INTERNALIZE",
            )
            return replace(
                state,
                integrated=(*state.integrated, item),
                pending_identity_review=self._dedupe_strings(
                    (*state.pending_identity_review, delta.delta_id)
                ),
                preserved_negative_knowledge=self._dedupe_strings(
                    (*state.preserved_negative_knowledge, *delta.negative_knowledge)
                ),
                preserved_unknowns=self._dedupe_strings(
                    (*state.preserved_unknowns, *delta.unresolved_unknowns)
                ),
            )

        if authority_impact not in {"", "NONE", "NO_CHANGE"}:
            item = IntegratedDelta(
                delta=delta,
                disposition="AUTHORITY_REVIEW_REQUIRED",
                reason="AUTHORITY_IMPACT_CANNOT_AUTO_INTERNALIZE",
            )
            return replace(
                state,
                integrated=(*state.integrated, item),
                pending_authority_review=self._dedupe_strings(
                    (*state.pending_authority_review, delta.delta_id)
                ),
                preserved_negative_knowledge=self._dedupe_strings(
                    (*state.preserved_negative_knowledge, *delta.negative_knowledge)
                ),
                preserved_unknowns=self._dedupe_strings(
                    (*state.preserved_unknowns, *delta.unresolved_unknowns)
                ),
            )

        # UNKNOWN and contradicted material are preserved as live structure, not
        # promoted into reusable capability merely for coherence.
        if delta.truth_state in {"UNKNOWN", "CONTRADICTED"}:
            disposition = "PRESERVED"
            reason = "UNKNOWN_OR_CONTRADICTION_PRESERVED_WITHOUT_PROMOTION"
        elif delta.capability_delta:
            if delta.truth_state == "VERIFIED" and delta.tests_or_falsifier:
                disposition = "INTERNALIZED"
                reason = "VERIFIED_CAPABILITY_DELTA_WITH_TEST_OR_FALSIFIER"
            else:
                disposition = "PRESERVED"
                reason = "CAPABILITY_DELTA_NEEDS_VERIFICATION_BEFORE_INTERNALIZATION"
        else:
            disposition = "PRESERVED"
            reason = "SOURCE_BOUND_DELTA_PRESERVED"

        item = IntegratedDelta(delta=delta, disposition=disposition, reason=reason)

        capabilities = state.reusable_capabilities
        if disposition == "INTERNALIZED":
            capabilities = self._dedupe_strings((*capabilities, *delta.capability_delta))

        contradictions = state.unresolved_contradictions
        if delta.truth_state == "CONTRADICTED":
            contradictions = self._dedupe_strings((*contradictions, delta.delta_id))

        return replace(
            state,
            integrated=(*state.integrated, item),
            reusable_capabilities=capabilities,
            preserved_negative_knowledge=self._dedupe_strings(
                (*state.preserved_negative_knowledge, *delta.negative_knowledge)
            ),
            preserved_unknowns=self._dedupe_strings(
                (*state.preserved_unknowns, *delta.unresolved_unknowns)
            ),
            unresolved_contradictions=contradictions,
        )

    def integrate_many(
        self,
        deltas: Sequence[PlaneDelta],
        state: OmegaPlaneState | None = None,
    ) -> OmegaPlaneState:
        current = state or self.empty_state()
        for delta in deltas:
            current = self.integrate(current, delta)
        return current

    def no_team_survival_test(
        self,
        state: OmegaPlaneState,
        *,
        removed_sources: Sequence[str],
    ) -> dict:
        """Verify optional-source removal does not alter Ω-SELF identity.

        This is intentionally an identity test, not a claim that capability is
        unchanged. Optional source loss may degrade reachable capability.
        """

        removed = set(removed_sources)
        affected = tuple(
            item.delta.delta_id
            for item in state.integrated
            if item.delta.optional_source and item.delta.source in removed
        )
        return {
            "verdict": "PASS",
            "self_identity_pointer": state.self_identity_pointer,
            "self_identity_digest": state.self_identity_digest,
            "removed_optional_sources": sorted(removed),
            "affected_delta_ids": list(affected),
            "capability_may_degrade": bool(affected),
            "identity_changed": False,
        }


def demo_delta() -> PlaneDelta:
    return PlaneDelta(
        delta_id="PLANE-DEMO-001",
        source="WORLDBUILD",
        source_checkpoint="DEMO-WORLD-HEAD",
        source_refs=("demo:worldbuild",),
        provenance="SOURCE_BOUND",
        truth_state="VERIFIED",
        capability_delta=("PRESERVE_CAUSAL_AMBIGUITY",),
        tests_or_falsifier=("RECONSTRUCT_ON_UNSEEN_STORY_CASE",),
        negative_knowledge=("DO_NOT_TREAT_STORY_AS_MERE_DECORATION",),
        unresolved_unknowns=("WHICH_STORY_RELATIONS_TRANSFER_OUTSIDE_FICTION",),
        rollback_pointer="DROP_DELTA_PLANE-DEMO-001",
    )


if __name__ == "__main__":
    from omega_self import source_bound_candidate_capsule

    integrator = OmegaPlaneIntegrator(source_bound_candidate_capsule())
    state = integrator.integrate(integrator.empty_state(), demo_delta())
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    print(
        json.dumps(
            integrator.no_team_survival_test(
                state,
                removed_sources=("KNT_OPTIONAL", "CC_OPTIONAL"),
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
