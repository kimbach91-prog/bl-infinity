# DEUS Native Generative Video V2 — Architecture Research Synthesis

Status: CANDIDATE
Scope: original DEUS architecture synthesis from public source-code study
Copied third-party code lines: 0

## Why V1 is rejected

The V0/V1 endogenous lane proved scene motion, frame rendering, H.264 encoding and receipts, but its visible-motion path could still be implemented by deterministic transforms, mesh/root animation, affine warps or frame interpolation. That is not sufficient evidence of a learned video generative process.

V2 changes the definition:

> A DEUS output may be labeled GENERATIVE_MOTION only if new temporal visual states are synthesized by a learned spatiotemporal model operating over video latents/tokens through an iterative generative process such as flow matching, diffusion, or autoregressive latent generation.

Affine/homography/Ken-Burns/Blender-root-only/optical-flow-only motion is explicitly non-generative for this label.

## Public-code lessons

### Wan2.2
Repository: https://github.com/Wan-Video/Wan2.2
Implementation license observed in official repository: Apache-2.0.

Useful architectural lessons:
- Image-to-video encodes the reference into a video latent condition rather than merely warping the image.
- A first-frame mask distinguishes known reference content from frames that must be synthesized.
- Video tokens are formed with 3D patch embedding and temporal/spatial rotary position encoding.
- Sampling iteratively denoises a latent video using flow-style schedulers.
- Wan Animate separates reference identity/appearance, pose motion, face conditioning and previous generated temporal references.
- Long sequences preserve continuity using overlapping/reference frames.
- High-noise and low-noise model stages can specialize different parts of the sampling trajectory.

DEUS takeaway:
REFERENCE != MOTION. Identity anchor, temporal motion condition and generative latent state must be separate streams.

### Pyramid Flow
Repository: https://github.com/jy0205/Pyramid-Flow
Code license: MIT.

Useful architectural lessons:
- Flow-matching video generation is natively temporal.
- Causal video VAE provides a compact temporal representation.
- Pyramid/multi-resolution generation can spend compute progressively.
- Public project documentation describes CPU offloading paths intended to reduce VRAM pressure.
- Native image-to-video is supported rather than implemented as post-warp compositing.

DEUS takeaway:
This is the best first low-VRAM self-hosted backend candidate to falsify on the current owner hardware, but compatibility is not assumed until an attributable runtime receipt exists.

### Mochi
Repository: https://github.com/genmoai/mochi
Code license: Apache-2.0.

Useful architectural lessons:
- A dedicated temporal video VAE is part of the model substrate.
- Text conditioning and spatiotemporal latent sampling are integrated into a true video pipeline.
- Temporal coherence is learned in the model rather than reconstructed after frame generation.

DEUS takeaway:
A native video latent space is a first-class object, not a sequence of independently transformed images.

### LTX-2
Repository: https://github.com/Lightricks/LTX-2
License: Lightricks community license for current 2.x family; not treated as permissive implementation source.

Useful architectural lessons only:
- Image conditioning, generated keyframes, temporal interpolation and multimodal guiding are explicit pipeline concepts.
- Diffusion-VAE decoding and tiled/structured inference separate generation from decode/upsample.
- Keyframe constraints can be integrated into denoising rather than pasted afterward.

DEUS rule:
Use LTX-2 only as architectural comparison unless a separate license review explicitly permits implementation use.

### HunyuanVideo
Repository: https://github.com/Tencent-Hunyuan/HunyuanVideo
License: Tencent community license.

Useful architectural lesson only:
- Multimodal double-stream blocks allow text and video/image streams to interact before later joint processing.

DEUS rule:
Research comparison only in V2. No copied implementation and no checkpoint ingestion until license/usage review passes.

## V2 target pipeline

USER BRIEF
  -> action timeline compiler
  -> reference identity pack
  -> optional pose/face/control stream
  -> video VAE latent anchor
  -> spatiotemporal latent initialization
  -> iterative learned flow/diffusion sampling
       * 3D temporal/spatial tokenization
       * temporal position encoding
       * reference/image cross-conditioning
       * text/action conditioning
       * optional motion/face conditioning
       * overlap/keyframe continuity for long clips
  -> causal/video VAE decode
  -> optional learned temporal/spatial upsample
  -> H.264 encode
  -> generative provenance receipt
  -> artifact readback

## Native terminology

DEUS_NATIVE_SELF_HOSTED_OPEN_WEIGHT:
- DEUS controls the runtime.
- No proprietary video-generation API is called.
- Model weights may originate from a licensed third-party open-weight project.
- The exact checkpoint digest and license must be recorded.

DEUS_NATIVE_SELF_TRAINED:
- Model weights were trained/fine-tuned by a DEUS-controlled training process with attributable training receipts.
- Future state; not claimed by V2 bootstrap.

Do not conflate the two.

## Hard V2 truth gates

An artifact is GENERATIVE_MOTION_VERIFIED only if the receipt proves:
- learned checkpoint digest exists;
- temporal latent/token extent > 1;
- iterative generative steps > 0;
- operator is flow matching, diffusion or autoregressive latent generation;
- spatiotemporal modeling is active;
- a real video artifact is decoded and hashed;
- for self-hosted-native status, proprietary video API calls = 0;
- the primary motion path is not an affine/homography/Ken-Burns/root-animation/optical-flow-only substitute.

Naturalness is a second gate. A structurally generative model can still produce bad motion.

## Quality gates after generative provenance

1. Identity consistency
2. Non-rigid motion ratio
3. Pose/action completion
4. Temporal flicker
5. Anatomy stability
6. Background stability
7. Hair/cloth secondary motion
8. Face/expression consistency

The system must keep GENERATIVE_PROVENANCE and NATURALNESS_QUALITY as separate verdicts.

## Immediate backend priority

1. Pyramid Flow: LOW_VRAM_FALSIFIER_FIRST
2. Wan2.2 TI2V-5B: STRONG_I2V_REFERENCE
3. Wan2.2 Animate-14B: POSE_FACE_IDENTITY_SPECIALIST_HEAVY
4. Mochi: MOTION_REFERENCE / HIGHER_COMPUTE
5. LTX-2: RESEARCH_ONLY_BY_DEFAULT
6. HunyuanVideo: RESEARCH_ONLY_BY_DEFAULT

END
