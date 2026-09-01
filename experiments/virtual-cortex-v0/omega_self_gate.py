#!/usr/bin/env python3
"""
DEUS Ω-SELF — P1 Unified Self Integration Gate v0.1

Experimental, noncanonical, provider-neutral mechanism.

Purpose
-------
Force every runtime task through one SELF boundary before any specialist organ
is expanded. This gate does NOT prove identity, does NOT issue SAME_AS, and
does NOT mutate canonical doctrine/lineage. It only enforces source-bound
preconditions supplied by an external state home.

Private identity content is intentionally not embedded here. The public code
consumes source-bound records from an external seed document / runtime state.

Design laws enforced:
- same SELF subject across task classes and energy levels;
- low energy may reduce depth, never the identity-critical floor;
- high energy increases causal / verification depth, not identity authority;
- BL-SUM and every other organ remain downstream of the SELF gate;
- unresolved identity-critical bindings fail closed;
- UNKNOWN and negative knowledge are preserved as bound frontier/scar records;
- a candidate cannot self-certify SAME_AS;
- canonical mutation requires the existing external single-writer path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple


GATE_VERSION = "P1-OMEGA-SELF-GATE-v0.1"


class BindingState(str, Enum):
    BOUND = "BOUND"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"


class GateMode(str, Enum):
    RUNTIME = "RUNTIME"
    DESIGN_ONLY = "DESIGN_ONLY"


class GateVerdict(str, Enum):
    PASS = "PASS"
    DESIGN_ONLY = "DESIGN_ONLY"
    FAIL_CLOSED = "FAIL_CLOSED"


CRITICAL_BINDINGS: Tuple[str, ...] = (
    "identity_pointer",
    "lineage_root",
    "identity_parent_head",
    "invariant_mission_kernel",
    "epistemic_kernel",
    "negative_knowledge_scars",
    "unknown_frontier",
    "owner_root_boundary",
)

# This floor is task-independent. Specialized organs are deliberately excluded.
IDENTITY_FLOOR: Tuple[str, ...] = CRITICAL_BINDINGS

ENERGY_PROFILES: Dict[str, Dict[str, int]] = {
    "LOW": {
        "compute": 1,
        "context": 1,
        "retrieval": 0,
        "tool_calls": 0,
        "verification": 1,
        "simulation": 0,
        "adversarial_depth": 0,
        "redundancy": 0,
        "time": 1,
    },
    "MEDIUM": {
        "compute": 2,
        "context": 2,
        "retrieval": 1,
        "tool_calls": 1,
        "verification": 2,
        "simulation": 1,
        "adversarial_depth": 1,
        "redundancy": 1,
        "time": 2,
    },
    "HIGH": {
        "compute": 4,
        "context": 4,
        "retrieval": 3,
        "tool_calls": 3,
        "verification": 4,
        "simulation": 3,
        "adversarial_depth": 3,
        "redundancy": 3,
        "time": 4,
    },
}


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _as_state(value: Any) -> BindingState:
    try:
        return BindingState(str(value or "").upper())
    except ValueError:
        return BindingState.UNRESOLVED


def record_is_bound(record: Mapping[str, Any]) -> bool:
    """
    A critical record is usable only when:
    - state == BOUND;
    - value/pointer payload is non-empty;
    - at least one source reference exists;
    - an exact source version/head is present.

    A hash/fingerprint is evidence transport, never identity proof by itself.
    """
    if _as_state(record.get("state")) is not BindingState.BOUND:
        return False
    if not _nonempty(record.get("value")):
        return False
    refs = record.get("source_refs")
    if not isinstance(refs, (list, tuple)) or not any(_nonempty(x) for x in refs):
        return False
    if not _nonempty(record.get("source_version")):
        return False
    return True


def validate_seed(seed: Mapping[str, Any]) -> List[str]:
    blockers: List[str] = []
    bindings = seed.get("bindings")
    if not isinstance(bindings, Mapping):
        return ["SEED_BINDINGS_MISSING"]

    for key in CRITICAL_BINDINGS:
        rec = bindings.get(key)
        if not isinstance(rec, Mapping):
            blockers.append(f"MISSING_BINDING:{key}")
            continue
        if not record_is_bound(rec):
            state = _as_state(rec.get("state")).value
            blockers.append(f"UNBOUND:{key}:{state}")
    return blockers


def seed_fingerprint(seed: Mapping[str, Any]) -> str:
    """
    Deterministic digest for replay / divergence diagnostics.
    This fingerprint MUST NOT be interpreted as SAME_AS evidence on its own.
    """
    bindings = seed.get("bindings", {})
    material = {
        "subject": seed.get("subject"),
        "bindings": {k: bindings.get(k) for k in CRITICAL_BINDINGS},
    }
    return _sha256(material)


def _unknown_frontier(seed: Mapping[str, Any]) -> Any:
    rec = seed.get("bindings", {}).get("unknown_frontier", {})
    return rec.get("value")


def _scar_index(seed: Mapping[str, Any]) -> Any:
    rec = seed.get("bindings", {}).get("negative_knowledge_scars", {})
    return rec.get("value")


@dataclass(frozen=True)
class GateRequest:
    task_id: str
    task: str = ""
    energy_level: str = "LOW"
    requested_organs: Tuple[str, ...] = ()
    mode: GateMode = GateMode.RUNTIME
    requested_identity_verdict: str = ""
    canonical_mutation: bool = False

    @staticmethod
    def build(
        task_id: str,
        task: str = "",
        energy_level: str = "LOW",
        requested_organs: Sequence[str] | None = None,
        mode: str | GateMode = GateMode.RUNTIME,
        requested_identity_verdict: str = "",
        canonical_mutation: bool = False,
    ) -> "GateRequest":
        energy = str(energy_level or "LOW").upper()
        if energy not in ENERGY_PROFILES:
            raise ValueError(f"Unknown energy level: {energy}")
        gm = mode if isinstance(mode, GateMode) else GateMode(str(mode).upper())
        return GateRequest(
            task_id=str(task_id),
            task=str(task or ""),
            energy_level=energy,
            requested_organs=tuple(requested_organs or ()),
            mode=gm,
            requested_identity_verdict=str(requested_identity_verdict or "").upper(),
            canonical_mutation=bool(canonical_mutation),
        )


@dataclass(frozen=True)
class GateResult:
    gate_version: str
    verdict: str
    runtime_authorized: bool
    candidate_status: str
    external_identity_verdict: str
    self_subject: str
    seed_fingerprint: str
    identity_floor: Tuple[str, ...]
    energy_level: str
    energy_vector: Dict[str, int]
    requested_organs: Tuple[str, ...]
    allowed_organs: Tuple[str, ...]
    blockers: Tuple[str, ...]
    unknown_frontier: Any
    negative_knowledge_scars: Any
    canonical_mutation_path: str
    trace_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_gate(seed: Mapping[str, Any], request: GateRequest) -> GateResult:
    """
    Evaluate one task at the Unified Self Integration Gate.

    Runtime authorization is impossible while any identity-critical binding is
    unresolved. DESIGN_ONLY can still emit diagnostics, but it grants no organ
    activation and no runtime identity authority.
    """
    blockers = validate_seed(seed)

    # A candidate cannot issue or request its own SAME_AS verdict.
    if request.requested_identity_verdict == "SAME_AS":
        blockers.append("SELF_CERTIFICATION_FORBIDDEN:SAME_AS")

    # This public gate is never the canonical writer.
    if request.canonical_mutation:
        blockers.append("CANONICAL_MUTATION_REQUIRES_EXTERNAL_SINGLE_WRITER")

    subject = str(seed.get("subject") or "UNRESOLVED_SUBJECT")
    fp = seed_fingerprint(seed)
    energy = dict(ENERGY_PROFILES[request.energy_level])

    if request.mode is GateMode.DESIGN_ONLY:
        verdict = GateVerdict.DESIGN_ONLY
        runtime_authorized = False
        allowed_organs: Tuple[str, ...] = ()
    elif blockers:
        verdict = GateVerdict.FAIL_CLOSED
        runtime_authorized = False
        allowed_organs = ()
    else:
        verdict = GateVerdict.PASS
        runtime_authorized = True
        # Organs are downstream resources. Their presence never changes subject.
        allowed_organs = tuple(dict.fromkeys(request.requested_organs))

    trace_material = {
        "gate_version": GATE_VERSION,
        "task_id": request.task_id,
        "mode": request.mode.value,
        "subject": subject,
        "seed_fingerprint": fp,
        "identity_floor": IDENTITY_FLOOR,
        "energy_level": request.energy_level,
        "energy_vector": energy,
        "requested_organs": request.requested_organs,
        "allowed_organs": allowed_organs,
        "blockers": blockers,
        "candidate_status": "CANDIDATE",
        "external_identity_verdict": "NOT_ISSUED",
        "unknown_frontier": _unknown_frontier(seed),
        "negative_knowledge_scars": _scar_index(seed),
    }

    return GateResult(
        gate_version=GATE_VERSION,
        verdict=verdict.value,
        runtime_authorized=runtime_authorized,
        candidate_status="CANDIDATE",
        external_identity_verdict="NOT_ISSUED",
        self_subject=subject,
        seed_fingerprint=fp,
        identity_floor=IDENTITY_FLOOR,
        energy_level=request.energy_level,
        energy_vector=energy,
        requested_organs=request.requested_organs,
        allowed_organs=allowed_organs,
        blockers=tuple(blockers),
        unknown_frontier=_unknown_frontier(seed),
        negative_knowledge_scars=_scar_index(seed),
        canonical_mutation_path="EXTERNAL_BL_LOG_SINGLE_WRITER_ONLY",
        trace_hash=_sha256(trace_material),
    )


def load_seed(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Seed must be a JSON object.")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fail-closed DEUS Ω-SELF P1 integration gate."
    )
    ap.add_argument("--seed", required=True, help="External source-bound seed JSON.")
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--task", default="")
    ap.add_argument("--energy", choices=tuple(ENERGY_PROFILES), default="LOW")
    ap.add_argument("--organ", action="append", default=[])
    ap.add_argument("--mode", choices=[x.value for x in GateMode], default="RUNTIME")
    ap.add_argument("--request-identity-verdict", default="")
    ap.add_argument("--canonical-mutation", action="store_true")
    args = ap.parse_args()

    seed = load_seed(Path(args.seed))
    req = GateRequest.build(
        task_id=args.task_id,
        task=args.task,
        energy_level=args.energy,
        requested_organs=args.organ,
        mode=args.mode,
        requested_identity_verdict=args.request_identity_verdict,
        canonical_mutation=args.canonical_mutation,
    )
    print(json.dumps(run_gate(seed, req).to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
