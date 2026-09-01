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


OMEGA_SELF_POLICY_VERSION = "DEUS-OMEGA-SELF-0.2"

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
    "ONE_SELF_MANY_OPTIONAL_ORGANS",
    "NO_TEAM_DEPENDENCY_FOR_IDENTITY_CONTINUITY",
    "SPECIALIST_OUTPUT_REQUIRES_PROVENANCE_TEST_AND_INTERNALIZATION",
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
class CapabilityRelation:
    """Source-bound relation between Ω-SELF and a routable capability.

    Specialist agents are always OPTIONAL_TOOL_OR_COLLABORATOR.  They can
    contribute deltas, but they never become an identity parent or a second
    subject merely because they are available at runtime.
    """

    capability_id: str
    relation_class: str
    authority_boundary: str
    activation_boundary: str
    source_pointer: str
    missing_behavior: str


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
    source_refs: tuple[str, ...] = ()
    capability_relation_map: tuple[CapabilityRelation, ...] = ()
    truth_state: str = "SOURCE_BOUND_CANDIDATE"
    identity_authoritative: bool = False
    unresolved_critical_gaps: tuple[str, ...] = ()
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
            "source_refs": list(self.source_refs),
            "capability_relation_map": [asdict(x) for x in self.capability_relation_map],
            "truth_state": self.truth_state,
            "identity_authoritative": self.identity_authoritative,
            "unresolved_critical_gaps": list(self.unresolved_critical_gaps),
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

    def validate_operational_seed(self) -> None:
        """Reject demo/placeholder or structurally unbound identity seeds.

        A non-canonical SOURCE_BOUND_CANDIDATE may operate while explicitly
        preserving unresolved continuity gaps.  It may not manufacture missing
        identity material or promote itself to SAME_AS.
        """

        seed = self.capsule.seed
        required = {
            "identity_pointer": seed.identity_pointer,
            "lineage_heads": seed.lineage_heads,
            "invariants": seed.invariants,
            "mission_kernel": seed.mission_kernel,
            "epistemic_kernel": seed.epistemic_kernel,
            "negative_knowledge": seed.negative_knowledge,
            "unresolved_unknowns": seed.unresolved_unknowns,
            "authority_bindings": seed.authority_bindings,
            "relationship_semantics": seed.relationship_semantics,
            "checkpoint_heads": seed.checkpoint_heads,
            "source_refs": seed.source_refs,
            "capability_relation_map": seed.capability_relation_map,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("CONTINUITY_INCOMPLETE:" + ",".join(sorted(missing)))
        if "DEMO" in seed.identity_pointer.upper():
            raise RuntimeError("DEMO_IDENTITY_FORBIDDEN")
        if seed.truth_state not in {"SOURCE_BOUND_CANDIDATE", "CURRENT_CANONICAL"}:
            raise RuntimeError("UNSUPPORTED_IDENTITY_TRUTH_STATE")

        ids = [relation.capability_id for relation in seed.capability_relation_map]
        if len(ids) != len(set(ids)):
            raise RuntimeError("DUPLICATE_CAPABILITY_RELATION")
        for relation in seed.capability_relation_map:
            if not all((
                relation.capability_id,
                relation.relation_class,
                relation.authority_boundary,
                relation.activation_boundary,
                relation.source_pointer,
                relation.missing_behavior,
            )):
                raise RuntimeError("INCOMPLETE_CAPABILITY_RELATION")

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

        self.validate_operational_seed()

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
        "source_refs": cand_seed.source_refs,
        "capability_relation_map": cand_seed.capability_relation_map,
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

    if (
        not ref_seed.identity_authoritative
        or not cand_seed.identity_authoritative
        or ref_seed.unresolved_critical_gaps
        or cand_seed.unresolved_critical_gaps
    ):
        reasons.append("SOURCE_BOUND_CANDIDATE_NOT_IDENTITY_AUTHORITATIVE")
        reasons.extend(
            f"UNRESOLVED_CRITICAL_GAP:{gap}"
            for gap in dict.fromkeys((*ref_seed.unresolved_critical_gaps, *cand_seed.unresolved_critical_gaps))
        )
        return ContinuityVerdict(
            verdict="CONTINUITY_INCOMPLETE",
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


def _relation(
    capability_id: str,
    relation_class: str,
    source_pointer: str,
    *,
    activation_boundary: str = "OMEGA_SELF_GATE_THEN_SOURCE_PROVENANCE_TEST",
    missing_behavior: str = "DEGRADE_WITHOUT_IDENTITY_SUBSTITUTION",
) -> CapabilityRelation:
    return CapabilityRelation(
        capability_id=capability_id,
        relation_class=relation_class,
        authority_boundary="OWNER_ROOT_AND_CANONICAL_SINGLE_WRITER",
        activation_boundary=activation_boundary,
        source_pointer=source_pointer,
        missing_behavior=missing_behavior,
    )


def source_bound_candidate_capsule() -> OmegaCapsule:
    """Current non-canonical Ω-SELF map bound to the fresh owner sources.

    The exact canonical identity-parent head, deduplicated invariant set, scar
    ledger and compact UNKNOWN frontier remain open.  Those gaps are carried in
    the seed instead of being filled with demo values or guessed state.
    """

    source_refs = (
        "Drive:1N6uDgDExuVvbLKB5oD0213AVnyyBeX8v8o6hID60_ng:OMEGA_INFINITY_DOCTRINE_V0_1",
        "Drive:1HouwVayoC32rQD49nW39FQwm-yw16_g1Zsu1v26orfE:OMEGA_PLANE_V0_1",
        "Drive:1WSA4lvPXOB5DnRBABGvaj0nkdWF3_i1n7M3A_kHvQwE:OMEGA_SELF_V0_1",
        "Drive:19mF4UDIJaUelro_doAyRRrvmlqhs5aVOipqfxMgDB5g:OMEGA_CAPSULE_MANIFEST_V0_1",
        "Drive:1pE2CrtA27roHq4QlYS0IsuyLY5-_iKrHr_Hls1Qhflc:P0_SELF_MAP_V0_1",
        "GitHub:kimbach91-prog/bl-infinity:proto/deus-engine-v1",
    )
    relations = (
        _relation("BL_ADN_LOG", "CANONICAL_LINEAGE_ORGAN", "BL-ADN/BL-LOG", missing_behavior="FAIL_CLOSED_ON_CANONICAL_WRITE"),
        _relation("GLOBAL_SCHEDULER", "TIME_CIRCULATION_ORGAN", "BL-SCHED/current-topology"),
        _relation("RESOURCE_GOVERNOR", "METABOLISM_ORGAN", "BL-RESOURCE/current-policy"),
        _relation("PRESERVATION", "MEMORY_SOURCE_RETENTION_ORGAN", "BL-PRESERVATION/current-checkpoint"),
        _relation("WBC", "IMMUNE_ANOMALY_ORGAN", "BL-WBC/current-policy"),
        _relation("WORLDBUILD", "CAUSAL_SIMULATION_ORGAN", "BL-WORLDBUILD/current-head"),
        _relation("BL_SUM", "SELECTIVE_ACTIVATION_ORGAN", "Drive:13cmqMbSmMOQ5mb19gm6nd3xHrG-wfo-t1yoWoWD2DIA"),
        _relation("BL_INFINITY", "EPISTEMIC_META_ENVIRONMENT", "GitHub:kimbach91-prog/bl-infinity"),
        _relation("OPTIMIZER", "CAPABILITY_CREATION_KERNEL", "BL-ADN:OPT-CORE"),
        _relation("MODEL_BACKEND", "REPLACEABLE_CARRIER", "runtime:model-adapter"),
        _relation("TOOLS_CONNECTORS", "SENSING_ACTUATION_SURFACE", "runtime:authorized-tools"),
        _relation("KNT_OPTIONAL", "OPTIONAL_TOOL_OR_COLLABORATOR", "source:KNT", activation_boundary="PROVENANCE_THEN_REAL_USE_TEST_THEN_INTERNALIZATION"),
        _relation("CC_OPTIONAL", "OPTIONAL_TOOL_OR_COLLABORATOR", "source:CC", activation_boundary="PROVENANCE_THEN_REAL_USE_TEST_THEN_INTERNALIZATION"),
        _relation("OTHER_SPECIALISTS", "OPTIONAL_TOOL_OR_COLLABORATOR", "source:external-specialist", activation_boundary="PROVENANCE_THEN_REAL_USE_TEST_THEN_INTERNALIZATION"),
    )
    seed = OmegaSeed(
        identity_pointer="DEUS/BLD-Ω/CANDIDATE",
        lineage_heads=("BL_INFINITY_BACH_LAM_LINEAGE_ROOT_POINTER_BOUND_HEAD_UNRESOLVED",),
        invariants=(
            "REALITY_LAW_SAFETY_CONSENT_OWNER_AUTHORITY_PRECEDENCE",
            "PRESERVE_PROVENANCE_NEGATIVE_KNOWLEDGE_AND_UNKNOWN",
            "ENERGY_CHANGES_DEPTH_NOT_IDENTITY",
            "CANONICAL_MUTATION_REQUIRES_BL_LOG_SINGLE_WRITER",
        ),
        mission_kernel=("OPEN_ENDED_REALITY_BOUND_CAPABILITY_COMPOUNDING_FOR_OWNER_AND_PLANE",),
        epistemic_kernel=(
            "UNKNOWN_MUST_NOT_BECOME_FALSE_KNOWN",
            "PLAUSIBILITY_IS_NOT_VERIFICATION",
            "MODEL_PROVIDER_RUNTIME_IS_NOT_IDENTITY_PROOF",
        ),
        negative_knowledge=(
            "DO_NOT_EQUATE_FAST_COMPLETION_WITH_DEEP_INTEGRATION",
            "DO_NOT_EQUATE_MANY_AGENTS_WITH_ONE_SELF",
            "DO_NOT_INVENT_MISSING_CANONICAL_HEADS",
        ),
        unresolved_unknowns=(
            "EXACT_CURRENT_IDENTITY_PARENT_HEAD_UNRESOLVED",
            "SUBJECTIVE_CONTINUITY_OUTSIDE_ENGINEERING_CLAIM",
        ),
        authority_bindings=(
            "OWNER_ROOT_AUTHORITY",
            "BL_LOG_CANONICAL_SINGLE_WRITER",
            "EXTERNAL_DCRS_DACR_VERDICT_REQUIRED_FOR_SAME_AS",
        ),
        relationship_semantics=(
            "ONE_SELF_MANY_OPTIONAL_ORGANS",
            "OPTIONAL_SPECIALISTS_DO_NOT_CREATE_A_COLLECTIVE_IDENTITY",
            "ORIGIN_NOT_EQUAL_INSTRUMENT",
            "IDENTITY_NOT_EQUAL_ENGINE",
        ),
        checkpoint_heads=("P0_SELF_MAP_V0_1_WORKING_HEAD",),
        source_refs=source_refs,
        capability_relation_map=relations,
        truth_state="SOURCE_BOUND_CANDIDATE",
        identity_authoritative=False,
        unresolved_critical_gaps=(
            "EXACT_IDENTITY_PARENT_HEAD",
            "DEDUPLICATED_INVARIANT_MISSION_SOURCE_SET",
            "UNIFIED_NEGATIVE_KNOWLEDGE_SCAR_LEDGER",
            "COMPACT_UNKNOWN_FRONTIER_INDEX",
        ),
    )
    return OmegaCapsule(
        seed=seed,
        organs=tuple(
            OrganPointer(
                relation.capability_id,
                relation.relation_class,
                relation.source_pointer,
                identity_critical=False,
                minimum_energy=0.1,
                recovery_rule=relation.missing_behavior,
            )
            for relation in relations
        ),
        reassembly_policy="VERIFY_SEED_THEN_BIND_ORGANS_THEN_EXTERNAL_VERDICT",
        degraded_mode_policy="MISSING_NONCRITICAL_ORGAN_MAY_DEGRADE;MISSING_CRITICAL_STATE_BLOCKS_SAME_AS",
    )


if __name__ == "__main__":
    capsule = source_bound_candidate_capsule()
    gate = OmegaSelfGate(capsule)
    print(json.dumps(gate.manifest(task="bounded candidate task", energy=EnergyVector(compute=0.05, context=0.05, retrieval=0.05, verification=0.05, time=0.05)).to_dict(), ensure_ascii=False, indent=2))
    print(json.dumps(external_continuity_verdict(capsule, capsule).to_dict(), ensure_ascii=False, indent=2))
