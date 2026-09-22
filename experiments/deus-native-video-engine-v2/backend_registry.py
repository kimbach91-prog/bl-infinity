"""DEUS V2 backend registry.

Metadata only. Importing this module does not download, execute, or license a model.
Third-party implementation is not vendored here.
"""

BACKENDS = {
    "pyramid_flow": {
        "source": "https://github.com/jy0205/Pyramid-Flow",
        "code_license": "MIT",
        "modes": ["text_to_video", "image_to_video"],
        "generation": "flow_matching",
        "video_latent": "causal_video_vae",
        "priority": 1,
        "route_state": "CANDIDATE_RUNTIME_UNVERIFIED",
        "reason": "permissive code license; public low-VRAM/offload path makes it the first current-hardware falsifier",
    },
    "wan2_2_ti2v_5b": {
        "source": "https://github.com/Wan-Video/Wan2.2",
        "code_license": "Apache-2.0",
        "modes": ["text_image_to_video"],
        "generation": "flow_diffusion",
        "video_latent": "vae_with_reference_mask",
        "priority": 2,
        "route_state": "CANDIDATE_RUNTIME_UNVERIFIED",
        "reason": "strong image anchor + native temporal latent design",
    },
    "wan2_2_animate_14b": {
        "source": "https://github.com/Wan-Video/Wan2.2",
        "code_license": "Apache-2.0",
        "modes": ["reference_pose_face_to_video"],
        "generation": "flow_diffusion",
        "video_latent": "vae_plus_pose_face_reference_streams",
        "priority": 3,
        "route_state": "HEAVY_CANDIDATE_RUNTIME_UNVERIFIED",
        "reason": "best architectural match for identity + body motion + expression but materially heavier",
    },
    "mochi1": {
        "source": "https://github.com/genmoai/mochi",
        "code_license": "Apache-2.0",
        "modes": ["text_to_video"],
        "generation": "diffusion_flow_family",
        "video_latent": "temporal_video_vae",
        "priority": 4,
        "route_state": "CANDIDATE_RUNTIME_UNVERIFIED",
        "reason": "useful motion/temporal latent reference; not first constrained-hardware route",
    },
    "ltx2": {
        "source": "https://github.com/Lightricks/LTX-2",
        "code_license": "Lightricks-Community-License",
        "modes": ["text_image_to_video", "keyframe_conditioned", "audio_video"],
        "generation": "diffusion_family",
        "video_latent": "diffusion_vae",
        "priority": 90,
        "route_state": "RESEARCH_ONLY_LICENSE_GATE",
        "reason": "architectural study only until explicit license review",
    },
    "hunyuanvideo": {
        "source": "https://github.com/Tencent-Hunyuan/HunyuanVideo",
        "code_license": "Tencent-Community-License",
        "modes": ["text_to_video"],
        "generation": "diffusion_transformer",
        "video_latent": "video_latent",
        "priority": 99,
        "route_state": "RESEARCH_ONLY_LICENSE_GATE",
        "reason": "architectural comparison only in V2",
    },
}


def ranked_executable_candidates():
    return [
        (name, spec)
        for name, spec in sorted(BACKENDS.items(), key=lambda kv: kv[1]["priority"])
        if "RESEARCH_ONLY" not in spec["route_state"]
    ]
