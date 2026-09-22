# DEUS GPT Native Video Skill V1

STATUS: CANDIDATE / GPT_SIDE_ROUTING_INSTALL
AGENT_ID: GPT-NATIVE-VIDEO-01
ENGINE_ID: DEUS_NATIVE_VIDEO_ENGINE_V0
PARENT: DEUS_DIGE_S2_ANATOMY_DYNAMICS_V1

## Purpose

Give an authorized GPT/provider session a deterministic DEUS-native route for producing video from DEUS-owned scene state without calling external image/video generation models.

This file installs an operational routing/skill contract inside the DEUS code/state plane. It does **not** modify the native OpenAI/ChatGPT tool registry and must never be described as an OpenAI-native plugin installation.

## Trigger

Use this route when the owner asks for:
- video nội sinh / native DEUS video;
- animate a DEUS S1/S2 scene;
- render a character motion without HeyGen/Higgsfield/Seedance/Kling or another video generator;
- a receipt-backed MP4 from a DEUS scene.

Do not select this route merely because a video provider failed. Select it when the requested output is compatible with the native scene/runtime and the quality/cost tradeoff is acceptable.

## Truth boundary

NATIVE_VIDEO means:
1. source scene/geometry/materials are supplied by or generated inside the DEUS scene pipeline;
2. motion is applied by deterministic scene/rig/physics code;
3. frames are rendered by a general renderer such as Blender, not by an external image/video generative model;
4. encoding/muxing is performed by deterministic media tooling such as FFmpeg;
5. completion requires an attributable MP4 hash + render/encode receipt.

NATIVE_VIDEO does not mean:
- GPT itself is a GPU/video model;
- logical supercells are physical GPU/VRAM;
- a configured workflow has executed;
- a static render proves animation, lip sync, cloth dynamics or audio generation.

## GPT packet

The GPT/provider worker translates the user brief into a compact packet:

```json
{
  "schema": "deus-native-video-packet/1",
  "scene_ref": "...",
  "motion": [
    {"op": "hold", "t0": 0.0, "t1": 0.5},
    {"op": "root_bounce", "t0": 0.5, "t1": 1.0, "amplitude_m": 0.025},
    {"op": "root_spin", "t0": 1.0, "t1": 3.2, "turns": 1.0},
    {"op": "root_lean", "t0": 3.2, "t1": 4.0, "degrees": 3.0}
  ],
  "camera": {"mode": "fixed"},
  "render": {"fps": 12, "width": 360, "height": 640, "engine": "BLENDER_EEVEE_NEXT"},
  "audio": {"mode": "none"},
  "acceptance": {
    "external_video_model_calls": 0,
    "external_image_model_calls": 0,
    "mp4_required": true,
    "receipt_required": true
  }
}
```

## V0 executable operators

EXECUTABLE:
- hold
- root_bounce
- root_spin
- root_lean
- fixed camera
- frame-sequence render
- H.264 MP4 encode
- optional existing-audio mux

MAPPED_NOT_EXECUTED:
- skeletal arm wave
- hand/finger articulation
- TMJ/jaw speech articulation
- phoneme/viseme lip sync
- soft-tissue temporal dynamics
- cloth simulation
- hair dynamics
- native speech synthesis

The GPT worker must not promote MAPPED_NOT_EXECUTED operators to EXECUTED.

## Runtime order

1. Resolve a verified scene artifact, preferring the latest accepted S2/S-series source.
2. Validate that the scene can be opened and that a render camera exists.
3. Compile the motion brief to keyframes/operators.
4. Parent character render objects under a motion root without parenting cameras, lights or stage geometry.
5. Apply keyframes.
6. Render a bounded canary first.
7. Encode MP4 with FFmpeg.
8. Probe the MP4 with ffprobe.
9. Produce `DEUS_NATIVE_VIDEO_RECEIPT.json` including:
   - source scene reference/hash when available;
   - frame count, fps, width, height, duration;
   - MP4 SHA256;
   - renderer and encoder versions;
   - operator execution states;
   - external model call counters;
   - truth boundary.
10. Promote only after readback.

## GPT-side routing rule

When this skill is active:
- GPT is packet builder, orchestrator and verifier.
- Blender/FFmpeg are the execution substrate.
- Drive remains canonical state.
- GitHub remains code/version state.
- Runtime receipts remain execution truth.
- Provider video tools are fallback/alternative routes, not part of the native receipt.

## V0 Definition of Done

A V0 canary is VERIFIED only when:
- one real DEUS scene is opened;
- at least one temporal motion operator changes the scene over time;
- frames are actually rendered;
- FFmpeg emits a playable MP4;
- ffprobe verifies codec/dimensions/duration;
- MP4 SHA256 is recorded;
- receipt states external image/video generation calls = 0;
- artifact and receipt are retained by an attributable runtime.

## Next upgrades after V0

V1: armature adapter + wave gesture.
V2: jaw/viseme contract + native/authorized audio lane.
V3: cloth/hair secondary dynamics.
V4: motion compiler from natural-language timing to constrained rig actions.
V5: quality selector between EEVEE canary and Cycles final render.

END
