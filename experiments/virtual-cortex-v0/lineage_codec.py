#!/usr/bin/env python3
"""BL Virtual Cortex v0: generic lineage-recognition + response-depth prototype.

Public mechanism only. Private lineage/state stays outside the repository.
This is a routing/calibration experiment, not proof of identity, truth, AGI,
consciousness, or biological equivalence.
"""
from __future__ import annotations

import base64
import hashlib
import json
import zlib
from dataclasses import dataclass, asdict
from typing import Tuple


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class CellCode:
    root_lineage: str
    branch_lineage: str
    logic_family: str
    function_class: str
    interface_profile: Tuple[str, ...]
    maturity: str
    version: str
    causal_head: str
    compatibility_markers: Tuple[str, ...] = ()
    immune_markers: Tuple[str, ...] = ()
    state_digest: str = ""
    provenance_pointer: str = ""

    def compact_dict(self) -> dict:
        return {
            "r": self.root_lineage,
            "b": self.branch_lineage,
            "l": self.logic_family,
            "f": self.function_class,
            "i": list(self.interface_profile),
            "m": self.maturity,
            "v": self.version,
            "c": self.causal_head,
            "cm": list(self.compatibility_markers),
            "im": list(self.immune_markers),
            "s": self.state_digest,
            "p": self.provenance_pointer,
        }


def encode_cell_code(code: CellCode) -> dict:
    raw = _canonical_json(code.compact_dict()).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    token = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return {
        "token": token,
        "digest": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
        "compressed_bytes": len(compressed),
    }


def decode_cell_code(token: str, expected_digest: str | None = None) -> CellCode:
    pad = "=" * ((4 - len(token) % 4) % 4)
    raw = zlib.decompress(base64.urlsafe_b64decode(token + pad))
    digest = hashlib.sha256(raw).hexdigest()
    if expected_digest and digest != expected_digest:
        raise ValueError("DIGEST_MISMATCH")
    d = json.loads(raw)
    return CellCode(
        root_lineage=d["r"],
        branch_lineage=d["b"],
        logic_family=d["l"],
        function_class=d["f"],
        interface_profile=tuple(d["i"]),
        maturity=d["m"],
        version=d["v"],
        causal_head=d["c"],
        compatibility_markers=tuple(d.get("cm", [])),
        immune_markers=tuple(d.get("im", [])),
        state_digest=d.get("s", ""),
        provenance_pointer=d.get("p", ""),
    )


IMMUNE_ALERTS = {
    "AUTHORITY_ESCALATION",
    "REPLAY_CONFLICT",
    "IMPOSSIBLE_VERSION_JUMP",
    "EXCESSIVE_FANOUT",
    "PROVENANCE_MISMATCH",
}


def recognize(local: CellCode, incoming: CellCode) -> dict:
    """Fast kin/function/interface recognition. Never returns truth/authority."""
    if not incoming.root_lineage or not incoming.causal_head or not incoming.provenance_pointer:
        return {"mode": "QUARANTINE", "reason": "MALFORMED_OR_UNBOUND"}
    if local.root_lineage != incoming.root_lineage:
        return {"mode": "OBSERVE_ONLY", "reason": "FOREIGN_LINEAGE", "same_root": False}

    alerts = sorted(set(incoming.immune_markers) & IMMUNE_ALERTS)
    if alerts:
        return {"mode": "QUARANTINE", "reason": "IMMUNE_MARKER", "flags": alerts, "same_root": True}

    interface_overlap = sorted(set(local.interface_profile) & set(incoming.interface_profile))
    compatibility_overlap = sorted(set(local.compatibility_markers) & set(incoming.compatibility_markers))
    same_branch = local.branch_lineage == incoming.branch_lineage

    if interface_overlap and compatibility_overlap:
        mode = "DIRECT_SYNAPSE"
    elif interface_overlap:
        mode = "SHADOW_ONLY"
    else:
        mode = "ADAPTER_REQUIRED"

    return {
        "mode": mode,
        "same_root": True,
        "same_branch": same_branch,
        "interface_overlap": interface_overlap,
        "compatibility_overlap": compatibility_overlap,
    }


@dataclass(frozen=True)
class DepthVector:
    causal_depth: float = 0.0
    hidden_variable_density: float = 0.0
    coupling_scope: float = 0.0
    time_horizon: float = 0.0
    irreversibility: float = 0.0
    externality: float = 0.0
    novelty: float = 0.0
    model_disagreement: float = 0.0
    evidence_gap: float = 0.0
    authority_impact: float = 0.0
    resource_exposure: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


def choose_response_mode(depth: DepthVector, familiarity: float, calibration: float) -> str:
    """Choose how much thinking is worth doing; not a truth score.

    Rules intentionally use qualitative gates instead of one universal scalar.
    Mathematics calibrates the policy; it should not force foreground cognition
    to recompute a giant utility function for every familiar decision.
    """
    critical = max(depth.irreversibility, depth.externality, depth.authority_impact, depth.coupling_scope)
    epistemic = max(depth.novelty, depth.model_disagreement, depth.evidence_gap, depth.hidden_variable_density)

    if critical >= 0.75:
        return "DEEP_VERIFY"
    if depth.evidence_gap >= 0.85 and (depth.novelty >= 0.60 or depth.model_disagreement >= 0.60):
        return "HOLD_UNKNOWN"
    if familiarity >= 0.92 and calibration >= 0.88 and critical <= 0.20 and epistemic <= 0.25:
        return "REFLEX"
    if familiarity >= 0.80 and calibration >= 0.82 and critical <= 0.35 and epistemic <= 0.45:
        return "INTUITION"
    if familiarity >= 0.65 and calibration >= 0.72 and critical <= 0.45 and epistemic <= 0.55:
        return "HEURISTIC"
    return "DELIBERATION"


def fast_conclusion_policy(depth: DepthVector, familiarity: float, calibration: float) -> dict:
    mode = choose_response_mode(depth, familiarity, calibration)
    direct = mode in {"REFLEX", "INTUITION", "HEURISTIC"}
    if not direct:
        return {
            "mode": mode,
            "direct": False,
            "provisional": False,
            "retro_verify": mode == "DEEP_VERIFY",
        }

    provisional = mode != "REFLEX" or depth.evidence_gap > 0.15 or depth.novelty > 0.20
    return {
        "mode": mode,
        "direct": True,
        "provisional": provisional,
        "retro_verify": provisional or depth.evidence_gap > 0.10,
    }


if __name__ == "__main__":
    local = CellCode("BL∞", "CURRENT", "distributed-cortex", "ORCHESTRATOR", ("event-dag", "sparse-router"), "PROTOTYPE", "0", "A1", ("DCX-v0",), (), "s1", "p1")
    peer = CellCode("BL∞", "LEGACY", "distributed-cortex", "CRITIC", ("event-dag", "critique"), "SHADOW", "0", "L1", ("DCX-v0",), (), "s2", "p2")
    packet = encode_cell_code(peer)
    assert decode_cell_code(packet["token"], packet["digest"]).branch_lineage == "LEGACY"
    assert recognize(local, peer)["mode"] == "DIRECT_SYNAPSE"
    assert choose_response_mode(DepthVector(evidence_gap=0.10), 0.95, 0.92) == "REFLEX"
    assert choose_response_mode(DepthVector(irreversibility=0.90), 0.95, 0.92) == "DEEP_VERIFY"
    assert choose_response_mode(DepthVector(evidence_gap=0.95, novelty=0.70), 0.20, 0.30) == "HOLD_UNKNOWN"
    print(json.dumps({"packet": packet, "recognition": recognize(local, peer)}, ensure_ascii=False, indent=2))
