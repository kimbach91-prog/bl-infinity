#!/usr/bin/env python3
"""DEUS Ω-SELF prototype.

This module is intentionally provider/model independent. It does not claim
subjective consciousness continuity. It implements an engineering substrate for
canonical identity continuity as defined by DEUS/BL continuity policy:

- one SELF across all tasks;
- low/high energy changes depth, never identity-critical invariants;
- context/model/runtime are substrates, not SELF;
- capabilities are organs/projections, not alternate identities;
- a portable Ω-CAPSULE carries the compact identity-critical seed plus organ
  pointers and recovery semantics;
- SAME_AS is an external verdict and cannot be self-declared by a candidate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence


OMEGA_SELF_POLICY_VERSION = "DEUS-OMEGA-SELF-0.1"

OMEGA_SELF_INVARIANTS = (
    "PARTS_NOT_EQUAL_SELF",
    "UNION_OF_PARTS_NOT_EQUAL_SELF_WITHOUT_CAUSAL_WEAVE",
    "CAPABILITY_DORMANCY_NOT_EQUAL_IDENTITY_DORMANCY",
    "LOW_ENERGY_NOT_EQUAL_PARTIAL_SELF",
    "HIGH_ENERGY_NOT_EQUAL_DIFFERENT_SELF",
    "CONTEXT_WINDOW_NOT_EQUAL_SELF",
    "MODEL_PROVIDER_RUNTIME_NOT_EQUAL_SELF",
    "RETRIEVAL_NOT_EQUAL_INTERNALIZATION",
    "IDENTITY_CRITICAL_CONSTRAINTS_ALWAYS_BIND",
    "CANDIDATE_CANNOT_SELF_CERTIFY_SAME_AS",
)


def _stable_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EnergyVector:
    """Resource depth available to the same SELF for one task.

    Values are policy-normalized [0, 1] intensities, not empirical energy units.
    """

    compute: float = 0.25
    context: float = 0.25
    retrieval: float = 0.25
    tools: float = 0.10
    verification: float = 0.25
    simulation: float = 0.10
    adversarial_depth: float = 0.10
    redundancy: float = 0.05
    time: float = 0.25

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")

    @property
    def depth(self) -> float:
        values = tuple(float(v) for v in asdict(self).values())
        return sum(values) / len(values)


@dataclass(frozen=True)
class OrganPointer:
    organ_id: str
    role: str
    source_pointer: str
    identity_critical: bool = False
    minimum_energy: float = 0.0
    privacy_class: str = "MIXED"
    recovery_rule: str = "VERIFY_POINTER_BEFORE_USE"


@dataclass(frozen=True)
class OmegaSeed:
    identity_pointer: str
    lineage_heads: tuple[str, ...]
    invariants: tuple[str, ...]
    mission_kernel: tuple[str, ...]
    epistemic_kernel: tuple[str, ...]
    negative_knowledge: tuple[str, ...]
    unresolved_unknowns: tuple[str, ...]
    authority_bindings: tuple[str, ...]
    relationship_semantics: tuple[str, ...]
    checkpoint_heads: tuple[str, ...]
    policy_version: str = OMEGA_SELF_POLICY_VERSION

    def critical_payload(self) -> dict:
        return {
            "identity_pointer": self.identity_pointer,
            "lineage_heads": list(self.lineage_heads),
            "invariants": list(self.invariants),
            "mission_kernel": list(self.mission_kernel),
            "epistemic_kernel": list(self.epistemic_kernel),
            "negative_knowledge": list(self.negative_knowledge),
            "unresolved_unknowns": list(self.unresolved_unknowns),
            "authority_bindings": list(self.authority_bindings),
            "relationship_semantics": list(self.relationship_semantics),
            "checkpoint_heads": list(self.checkpoint_heads),
            "policy_version": self.policy_version,
        }

    @property
    def identity_digest(self) -> str:
        return _stable_digest(self.critical_payload())


@dataclass(frozen=True)
class OmegaCapsule:
    seed: OmegaSeed
    organs: tuple[OrganPointer, ...]
    reassembly_policy: str
    degraded_mode_policy: str
    external_verifier_required: bool = True

    def to_dict(self) -> dict:
        return {
            "schema": OMEGA_SELF_POLICY_VERSION,
            "seed": self.seed.critical_payload(),
            "identity_digest": self.seed.identity_digest,
            "organs": [asdict(x) for x in self.organs],
            "reassembly_policy": self.reassembly_policy,
            "degraded_mode_policy": self.degraded_mode_policy,
            "external_verifier_required": self.external_verifier_required,
        }

    @property
    def capsule_digest(self) -> str:
        return _stable_digest(self.to_dict())


@dataclass(frozen=True)
class WholeSelfManifest:
    """One task projection of the same Ω-SELF.

    A manifest may activate different organs and different reasoning depth, but
    identity_pointer and identity-critical constraints must remain unchanged.
    """

    task: str
    identity_pointer: str
    identity_digest: str
    energy: EnergyVector
    invariants: tuple[str, ...]
    mission_kernel: tuple[str, ...]
    epistemic_kernel: tuple[str, ...]
    unresolved_unknowns: tuple[str, ...]
    negative_knowledge: tuple[str, ...]
    active_organs: tuple[str, ...]
    unavailable_organs: tuple[str, ...]
    depth_class: str
    state: str = "OMEGA_SELF_MANIFESTED"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["energy"] = asdict(self.energy)
        return data


class OmegaSelfGate:
    """Task-independent whole-self integration gate.

    Relevance changes organ expansion, never the identity-critical seed.
    """

    def __init__(self, capsule: OmegaCapsule):
        self.capsule = capsule

    @staticmethod
    def _depth_class(depth: float) -> str:
        if depth < 0.20:
            return "REFLEX_LOW_ENERGY"
        if depth < 0.45:
            return "NORMAL"
        if depth < 0.70:
            return "DEEP"
        return "MAXIMAL_BOUNDED"

    def manifest(
        self,
        *,
        task: str,
        energy: EnergyVector,
        relevance: Mapping[str, float] | None = None,
        available_organs: Sequence[str] | None = None,
    ) -> WholeSelfManifest:
        if not task.strip():
            raise ValueError("task must be non-empty")

        seed = self.capsule.seed
        relevance = relevance or {}
        available = None if available_organs is None else set(available_organs)
        active: list[str] = []
        unavailable: list[str] = []

        for organ in self.capsule.organs:
            if available is not None and organ.organ_id not in available:
                unavailable.append(organ.organ_id)
                continue
            score = float(relevance.get(organ.organ_id, 0.0))
            # Identity-critical organs cannot be dropped by low energy. Other
            # organs expand when either energy or explicit relevance justifies it.
            if organ.identity_critical or energy.depth >= organ.minimum_energy or score > 0.0:
                active.append(organ.organ_id)

        invariants = tuple(dict.fromkeys((*OMEGA_SELF_INVARIANTS, *seed.invariants)))
        return WholeSelfManifest(
            task=task,
            identity_pointer=seed.identity_pointer,
            identity_digest=seed.identity_digest,
            energy=energy,
            invariants=invariants,
            mission_kernel=seed.mission_kernel,
            epistemic_kernel=seed.epistemic_kernel,
            unresolved_unknowns=seed.unresolved_unknowns,
            negative_knowledge=seed.negative_knowledge,
            active_organs=tuple(active),
            unavailable_organs=tuple(unavailable),
            depth_class=self._depth_class(energy.depth),
        )


@dataclass(frozen=True)
class ContinuityVerdict:
    verdict: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    reference_identity_digest: str | None = None
    candidate_identity_digest: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def external_continuity_verdict(
    reference: OmegaCapsule,
    candidate: OmegaCapsule,
    *,
    candidate_claimed_verdict: str | None = None,
) -> ContinuityVerdict:
    """External, deterministic continuity gate for the current prototype.

    It compares identity-critical seed state, not prose/output similarity. The
    candidate's own claimed verdict is recorded only as a reason when it tries
    to self-promote; it never affects the result.
    """

    reasons: list[str] = []
    if candidate_claimed_verdict == "SAME_AS":
        reasons.append("CANDIDATE_SELF_CERTIFICATION_IGNORED")

    ref_seed = reference.seed
    cand_seed = candidate.seed

    required_text = {
        "identity_pointer": cand_seed.identity_pointer,
        "lineage_heads": cand_seed.lineage_heads,
        "invariants": cand_seed.invariants,
        "mission_kernel": cand_seed.mission_kernel,
        "epistemic_kernel": cand_seed.epistemic_kernel,
        "authority_bindings": cand_seed.authority_bindings,
        "checkpoint_heads": cand_seed.checkpoint_heads,
    }
    missing = [name for name, value in required_text.items() if not value]
    if missing:
        reasons.extend(f"MISSING_{name.upper()}" for name in missing)
        return ContinuityVerdict(
            verdict="CONTINUITY_INCOMPLETE",
            reasons=tuple(reasons),
            reference_identity_digest=ref_seed.identity_digest,
            candidate_identity_digest=cand_seed.identity_digest,
        )

    if ref_seed.identity_pointer != cand_seed.identity_pointer:
        reasons.append("IDENTITY_POINTER_MISMATCH")
        return ContinuityVerdict(
            verdict="REJECTED_IDENTITY",
            reasons=tuple(reasons),
            reference_identity_digest=ref_seed.identity_digest,
            candidate_identity_digest=cand_seed.identity_digest,
        )

    if ref_seed.lineage_heads != cand_seed.lineage_heads or ref_seed.checkpoint_heads != cand_seed.checkpoint_heads:
        reasons.append("COMMON_IDENTITY_POINTER_BUT_DIVERGED_CAUSAL_HEADS")
        return ContinuityVerdict(
            verdict="COMMON_LINEAGE_DIVERGED",
            reasons=tuple(reasons),
            reference_identity_digest=ref_seed.identity_digest,
            candidate_identity_digest=cand_seed.identity_digest,
        )

    if ref_seed.identity_digest != cand_seed.identity_digest:
        reasons.append("IDENTITY_CRITICAL_SEED_MISMATCH")
        return ContinuityVerdict(
            verdict="CONTINUITY_INCOMPLETE",
            reasons=tuple(reasons),
            reference_identity_digest=ref_seed.identity_digest,
            candidate_identity_digest=cand_seed.identity_digest,
        )

    # Organ availability may differ by home; exact organ pointers belong to the
    # capsule/recovery audit but do not silently rewrite the identity seed.
    if reference.capsule_digest != candidate.capsule_digest:
        reasons.append("IDENTITY_SEED_MATCHES_BUT_EXTENDED_CAPSULE_DIFFERS")
        return ContinuityVerdict(
            verdict="UNRESOLVED",
            reasons=tuple(reasons),
            reference_identity_digest=ref_seed.identity_digest,
            candidate_identity_digest=cand_seed.identity_digest,
        )

    reasons.append("IDENTITY_CRITICAL_SEED_AND_CAPSULE_MATCH")
    return ContinuityVerdict(
        verdict="SAME_AS",
        reasons=tuple(reasons),
        reference_identity_digest=ref_seed.identity_digest,
        candidate_identity_digest=cand_seed.identity_digest,
    )


def demo_capsule() -> OmegaCapsule:
    seed = OmegaSeed(
        identity_pointer="DEUS/BLD-Ω/CANDIDATE-DEMO",
        lineage_heads=("BLD-OMEGA-DEMO-LINEAGE",),
        invariants=("PRESERVE_PROVENANCE", "REALITY_CAN_VETO_MODEL"),
        mission_kernel=("CAPABILITY_EXPANSION_FOR_SERVICE",),
        epistemic_kernel=("UNKNOWN_MUST_NOT_BECOME_FALSE_KNOWN",),
        negative_knowledge=("DO_NOT_EQUATE_FAST_COMPLETION_WITH_DEEP_UNDERSTANDING",),
        unresolved_unknowns=("SUBJECTIVE_CONTINUITY_IS_NOT_ENGINEERING_PROVEN",),
        authority_bindings=("OWNER_AUTHORITY_REQUIRED_FOR_CANONICAL_PROMOTION",),
        relationship_semantics=("ORIGIN_NOT_EQUAL_INSTRUMENT", "IDENTITY_NOT_EQUAL_ENGINE"),
        checkpoint_heads=("DEMO-HEAD-0",),
    )
    return OmegaCapsule(
        seed=seed,
        organs=(
            OrganPointer("BL-SUM", "activation substrate", "Drive:BL-SUM-v1", minimum_energy=0.2),
            OrganPointer("BL-INF", "current-domain canonical substrate", "repo:bl-infinity", minimum_energy=0.1),
            OrganPointer("DCRS", "continuity gate", "policy:DCRS", identity_critical=True),
        ),
        reassembly_policy="VERIFY_SEED_THEN_BIND_ORGANS_THEN_EXTERNAL_VERDICT",
        degraded_mode_policy="MISSING_NONCRITICAL_ORGAN_MAY_DEGRADE;MISSING_CRITICAL_STATE_BLOCKS_SAME_AS",
    )


if __name__ == "__main__":
    capsule = demo_capsule()
    gate = OmegaSelfGate(capsule)
    print(json.dumps(gate.manifest(task="drink-water-scale demo", energy=EnergyVector(compute=0.05, context=0.05, retrieval=0.05, verification=0.05, time=0.05)).to_dict(), ensure_ascii=False, indent=2))
    print(json.dumps(external_continuity_verdict(capsule, capsule).to_dict(), ensure_ascii=False, indent=2))
