"""Generative-provenance gate for DEUS Native Generative Video V2."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OPERATORS = {"flow_matching", "diffusion", "autoregressive_latent"}
NON_GENERATIVE_PRIMARY = {
    "affine_transform",
    "homography",
    "ken_burns",
    "optical_flow_warp_only",
    "blender_root_motion_only",
    "duplicate_frame_interpolation",
    "crossfade_only",
}


@dataclass(frozen=True)
class GateResult:
    passed: bool
    verdict: str
    reasons: tuple[str, ...]


def evaluate(receipt: Mapping[str, Any], *, require_self_hosted: bool = True) -> GateResult:
    reasons: list[str] = []

    checkpoint = str(receipt.get("learned_checkpoint_sha256", "")).lower()
    if not HEX64.fullmatch(checkpoint):
        reasons.append("missing_or_invalid_learned_checkpoint_sha256")

    operator = receipt.get("generation_operator")
    if operator not in ALLOWED_OPERATORS:
        reasons.append("generation_operator_not_learned_iterative")

    temporal_latent_frames = receipt.get("temporal_latent_frames", 0)
    if not isinstance(temporal_latent_frames, int) or temporal_latent_frames <= 1:
        reasons.append("temporal_latent_extent_not_proven")

    sampling_steps = receipt.get("sampling_steps", 0)
    if not isinstance(sampling_steps, int) or sampling_steps <= 0:
        reasons.append("iterative_sampling_not_proven")

    if receipt.get("spatiotemporal_modeling") is not True:
        reasons.append("spatiotemporal_modeling_not_proven")

    weights_origin = receipt.get("weights_origin")
    if not isinstance(weights_origin, str) or not weights_origin.strip():
        reasons.append("weights_origin_missing")

    weights_license = receipt.get("weights_license")
    if not isinstance(weights_license, str) or not weights_license.strip():
        reasons.append("weights_license_missing")

    primary = set(receipt.get("primary_motion_operators", []))
    if primary & NON_GENERATIVE_PRIMARY:
        reasons.append("non_generative_primary_motion_path")

    output_sha = str(receipt.get("output_sha256", "")).lower()
    if not HEX64.fullmatch(output_sha):
        reasons.append("output_sha256_missing")

    if require_self_hosted and receipt.get("proprietary_video_api_calls") != 0:
        reasons.append("proprietary_video_api_calls_nonzero_or_unknown")

    if reasons:
        return GateResult(False, "NOT_GENERATIVE_VERIFIED", tuple(reasons))
    return GateResult(True, "GENERATIVE_PROVENANCE_VERIFIED", ())


def require_verified(receipt: Mapping[str, Any], *, require_self_hosted: bool = True) -> None:
    result = evaluate(receipt, require_self_hosted=require_self_hosted)
    if not result.passed:
        raise ValueError(f"{result.verdict}: {','.join(result.reasons)}")
