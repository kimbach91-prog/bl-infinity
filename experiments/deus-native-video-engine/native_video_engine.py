import argparse
import hashlib
import json
import math
import os
import pathlib
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", required=True)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--seconds", type=float, default=4.0)
    p.add_argument("--width", type=int, default=360)
    p.add_argument("--height", type=int, default=640)
    p.add_argument("--engine", default="BLENDER_EEVEE_NEXT")
    return p.parse_args(argv)


def bbox_center_world(obj):
    if not hasattr(obj, "bound_box") or not obj.bound_box:
        return obj.matrix_world.translation.copy()
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(pts, Vector()) / len(pts)


def character_objects(body):
    center = bbox_center_world(body)
    keep = []
    stage_tokens = ("floor", "stage", "backdrop", "ground", "cyclorama", "camera", "light")
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            continue
        name = obj.name.lower()
        if any(t in name for t in stage_tokens):
            continue
        if obj == body:
            keep.append(obj)
            continue
        dims = tuple(float(x) for x in obj.dimensions)
        if max(dims or (0.0,)) > 3.0:
            continue
        d = (bbox_center_world(obj) - center).length
        if d <= 1.75:
            keep.append(obj)
    return keep


def key(root, frame, location=None, rotation=None):
    if location is not None:
        root.location = location
        root.keyframe_insert(data_path="location", frame=frame)
    if rotation is not None:
        root.rotation_euler = rotation
        root.keyframe_insert(data_path="rotation_euler", frame=frame)


def set_linear(root):
    try:
        action = root.animation_data.action if root.animation_data else None
        if action and hasattr(action, "fcurves"):
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    except Exception as exc:
        print("WARN interpolation:", exc)


def main():
    args = parse_args()
    outdir = pathlib.Path(args.outdir)
    frames_dir = outdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    if scene.camera is None:
        raise RuntimeError("NATIVE_VIDEO_CAMERA_MISSING")

    body = bpy.data.objects.get("DIGE_V8_MAKEHUMAN_BODY")
    if body is None:
        raise RuntimeError("NATIVE_VIDEO_BODY_MISSING:DIGE_V8_MAKEHUMAN_BODY")

    chars = character_objects(body)
    if body not in chars or len(chars) < 1:
        raise RuntimeError("NATIVE_VIDEO_CHARACTER_SET_EMPTY")

    root = bpy.data.objects.new("DEUS_NATIVE_VIDEO_ROOT", None)
    scene.collection.objects.link(root)
    body_world = body.matrix_world.translation.copy()
    root.location = (float(body_world.x), float(body_world.y), 0.0)
    root.rotation_mode = "XYZ"

    for obj in chars:
        mw = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = mw

    fps = args.fps
    end = max(8, int(round(args.seconds * fps)))
    scene.frame_start = 1
    scene.frame_end = end
    scene.render.fps = fps
    requested_engine = args.engine
    allowed_engines = {
        item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items
    }
    engine_aliases = {
        "BLENDER_EEVEE_NEXT": "BLENDER_EEVEE",
        "BLENDER_EEVEE": "BLENDER_EEVEE_NEXT",
    }
    actual_engine = requested_engine
    if actual_engine not in allowed_engines:
        actual_engine = engine_aliases.get(requested_engine)
    if actual_engine not in allowed_engines:
        raise RuntimeError(
            "NATIVE_VIDEO_RENDER_ENGINE_UNAVAILABLE:"
            f"requested={requested_engine};allowed={sorted(allowed_engines)}"
        )
    scene.render.engine = actual_engine
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.film_transparent = False

    base_loc = root.location.copy()
    zero_rot = root.rotation_euler.copy()

    f_hold = max(2, int(0.45 * fps))
    f_bounce = max(f_hold + 1, int(0.75 * fps))
    f_settle = max(f_bounce + 1, int(1.00 * fps))
    f_spin_start = f_settle
    f_spin_end = max(f_spin_start + 2, int(3.15 * fps))
    f_lean = max(f_spin_end + 1, int(3.55 * fps))

    key(root, 1, location=base_loc, rotation=zero_rot)
    key(root, f_hold, location=base_loc, rotation=zero_rot)

    bounce_loc = base_loc.copy()
    bounce_loc.z += 0.025
    key(root, f_bounce, location=bounce_loc, rotation=zero_rot)
    key(root, f_settle, location=base_loc, rotation=zero_rot)

    spin0 = zero_rot.copy()
    spin1 = zero_rot.copy()
    spin1.z += 2.0 * math.pi
    key(root, f_spin_start, location=base_loc, rotation=spin0)
    key(root, f_spin_end, location=base_loc, rotation=spin1)

    lean = spin1.copy()
    lean.x += math.radians(3.0)
    key(root, f_lean, location=base_loc, rotation=lean)
    key(root, end, location=base_loc, rotation=spin1)
    set_linear(root)

    animated_blend = outdir / "DEUS_NATIVE_VIDEO_CANARY.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(animated_blend))

    print(json.dumps({
        "event": "native_video_render_start",
        "blender": bpy.app.version_string,
        "engine_requested": requested_engine,
        "engine_actual": scene.render.engine,
        "engine_allowed": sorted(allowed_engines),
        "camera": scene.camera.name,
        "character_object_count": len(chars),
        "character_objects": [o.name for o in chars],
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": fps,
        "resolution": [args.width, args.height]
    }, sort_keys=True))

    bpy.ops.render.render(animation=True)

    frame_files = sorted(frames_dir.glob("frame_*.png"))
    if len(frame_files) != end:
        raise RuntimeError(f"NATIVE_VIDEO_FRAME_COUNT_MISMATCH:{len(frame_files)}!={end}")

    receipt = {
        "schema": "deus-native-video-render-receipt/1",
        "engine_id": "DEUS_NATIVE_VIDEO_ENGINE_V0",
        "renderer": "Blender",
        "blender_version": bpy.app.version_string,
        "render_engine_requested": requested_engine,
        "render_engine": scene.render.engine,
        "render_engine_allowed": sorted(allowed_engines),
        "source_blend": os.path.basename(bpy.data.filepath),
        "animated_blend": animated_blend.name,
        "camera": scene.camera.name,
        "character_root": root.name,
        "character_object_count": len(chars),
        "character_objects": [o.name for o in chars],
        "operators": {
            "root_bounce": "EXECUTED",
            "root_spin": "EXECUTED",
            "root_lean": "EXECUTED",
            "arm_wave": "NOT_EXECUTED",
            "tmj_jaw": "NOT_EXECUTED",
            "viseme_lipsync": "NOT_EXECUTED",
            "cloth_dynamics": "NOT_EXECUTED",
            "hair_dynamics": "NOT_EXECUTED"
        },
        "frames": len(frame_files),
        "fps": fps,
        "width": args.width,
        "height": args.height,
        "duration_seconds_nominal": end / fps,
        "external_image_generation_calls": 0,
        "external_video_generation_calls": 0,
        "truth_boundary": "FRAMES_RENDERED__MP4_ENCODE_AND_PROBE_PENDING"
    }
    (outdir / "DEUS_NATIVE_VIDEO_RENDER_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
