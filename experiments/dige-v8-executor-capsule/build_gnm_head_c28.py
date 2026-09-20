#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from gnm.shape import gnm_landmarks
from gnm.shape import gnm_numpy

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime" / "gnm_c28"
RUNTIME.mkdir(parents=True, exist_ok=True)

GNM_COMMIT = os.environ.get("DIGE_GNM_COMMIT", "").strip()
IDENTITY_SEED = int(os.environ.get("DIGE_GNM_IDENTITY_SEED", "20262828"))
IDENTITY_SIGMA = float(os.environ.get("DIGE_GNM_IDENTITY_SIGMA", "0.34"))

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

gnm = gnm_numpy.GNM.from_local(
    version=gnm_numpy.GNMMajorVersion.V3,
    variant=gnm_numpy.GNMVariant.HEAD,
)

rng = np.random.default_rng(IDENTITY_SEED)
identity = np.zeros(gnm.identity_dim, dtype=np.float32)
# Only randomize the head-shape block. Keep eyeball and dental identity blocks
# neutral on the first causal C28 pass so the visual delta primarily tests the
# scan-learned head prior rather than a broad stochastic identity search.
head_identity_dim = min(170, gnm.identity_dim)
identity[:head_identity_dim] = np.clip(
    rng.normal(0.0, IDENTITY_SIGMA, size=head_identity_dim),
    -0.90,
    0.90,
).astype(np.float32)

expression = np.zeros(gnm.expression_dim, dtype=np.float32)
rotations = np.zeros((gnm.num_joints, 3), dtype=np.float32)
translation = np.zeros((3,), dtype=np.float32)

vertices_raw = np.asarray(
    gnm(identity, expression, rotations, translation), dtype=np.float64
)
if vertices_raw.ndim == 3:
    if vertices_raw.shape[0] != 1:
        raise RuntimeError(f"Unexpected GNM batch shape: {vertices_raw.shape}")
    vertices_raw = vertices_raw[0]
if vertices_raw.shape != (gnm.num_vertices, 3):
    raise RuntimeError(
        f"Unexpected GNM vertex shape {vertices_raw.shape}; expected {(gnm.num_vertices, 3)}"
    )
triangles = np.asarray(gnm.triangles, dtype=np.int64)
uvs = np.asarray(gnm.vertex_uvs, dtype=np.float64)
if uvs.shape[0] != vertices_raw.shape[0] or uvs.shape[1] != 2:
    raise RuntimeError(f"Unexpected GNM vertex UV shape: {uvs.shape}")

cfg = gnm_landmarks.load_landmarks(
    gnm_landmarks.GNMLandmarksType.HEAD_SPARSE_68
)
landmarks_raw = (
    vertices_raw[cfg.indices] * cfg.weights[..., None]
).sum(axis=1)
if landmarks_raw.shape != (68, 3):
    raise RuntimeError(f"Unexpected GNM 68-landmark shape: {landmarks_raw.shape}")

# Canonicalize GNM to DIGE Blender-space semantics:
# X = left/right, Y = face-forward, Z = up.
left_eye_raw = landmarks_raw[36:42].mean(axis=0)
right_eye_raw = landmarks_raw[42:48].mean(axis=0)
mouth_raw = landmarks_raw[48:60].mean(axis=0)
nose_raw = landmarks_raw[27:36].mean(axis=0)

eye_delta = left_eye_raw - right_eye_raw
x_axis = int(np.argmax(np.abs(eye_delta)))
remaining = [i for i in range(3) if i != x_axis]
eye_mid_raw = (left_eye_raw + right_eye_raw) * 0.5
vertical_signal = eye_mid_raw - mouth_raw
z_axis = max(remaining, key=lambda i: abs(vertical_signal[i]))
y_axis = next(i for i in remaining if i != z_axis)

x_sign = 1.0 if eye_delta[x_axis] > 0 else -1.0
z_sign = 1.0 if vertical_signal[z_axis] > 0 else -1.0
forward_signal = nose_raw[y_axis] - eye_mid_raw[y_axis]
y_sign = 1.0 if forward_signal > 0 else -1.0

def canon(arr: np.ndarray) -> np.ndarray:
    out = np.empty_like(arr, dtype=np.float64)
    out[..., 0] = arr[..., x_axis] * x_sign
    out[..., 1] = arr[..., y_axis] * y_sign
    out[..., 2] = arr[..., z_axis] * z_sign
    return out

vertices = canon(vertices_raw)
landmarks = canon(landmarks_raw)

# Center around eye midpoint in X/Y but retain Z so the renderer can align from
# exact landmark coordinates. This keeps all components in one shared frame.
eye_mid = (landmarks[36:42].mean(axis=0) + landmarks[42:48].mean(axis=0)) * 0.5
vertices[:, 0] -= eye_mid[0]
vertices[:, 1] -= eye_mid[1]
landmarks[:, 0] -= eye_mid[0]
landmarks[:, 1] -= eye_mid[1]

components = list(gnm.mesh_component_names)
tri_by_component: dict[str, np.ndarray] = {}
covered = set()
for name in components:
    idx = np.asarray(gnm.triangle_indices_for_group(name), dtype=np.int64)
    tri_by_component[name] = idx
    covered.update(int(x) for x in idx.tolist())

all_indices = set(range(len(triangles)))
uncovered = sorted(all_indices - covered)
if uncovered:
    raise RuntimeError(f"GNM component triangle coverage incomplete: {len(uncovered)}")

def safe_name(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("~", "not_")
    )

def write_obj(path: Path, tri_indices: np.ndarray, component: str) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# DIGE C28 GNM Head component={component}\n")
        f.write(f"o DIGE_C28_GNM_{safe_name(component)}\n")
        for x, y, z in vertices:
            f.write(f"v {x:.10f} {y:.10f} {z:.10f}\n")
        for u, v in uvs:
            f.write(f"vt {u:.10f} {v:.10f}\n")
        f.write(f"g {safe_name(component)}\n")
        for ti in tri_indices.tolist():
            a, b, c = triangles[ti] + 1
            f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")

files = {}
for component, tri_indices in tri_by_component.items():
    path = RUNTIME / f"gnm_{safe_name(component)}.obj"
    write_obj(path, tri_indices, component)
    files[component] = {
        "file": path.name,
        "sha256": sha256(path),
        "triangles": int(len(tri_indices)),
    }

np.save(RUNTIME / "gnm_landmarks68.npy", landmarks.astype(np.float32))
landmarks_json = RUNTIME / "gnm_landmarks68.json"
landmarks_json.write_text(
    json.dumps(landmarks.tolist(), indent=2) + "\n", encoding="utf-8"
)

bbox_min = vertices.min(axis=0)
bbox_max = vertices.max(axis=0)
left_eye = landmarks[36:42].mean(axis=0)
right_eye = landmarks[42:48].mean(axis=0)
mouth = landmarks[48:60].mean(axis=0)
nose = landmarks[27:36].mean(axis=0)
brow_left = landmarks[17:22].mean(axis=0)
brow_right = landmarks[22:27].mean(axis=0)
interocular = float(np.linalg.norm(left_eye - right_eye))

manifest = {
    "schema": "DIGE_C28_GNM_HEAD_BUILD_RECEIPT_V1",
    "source_repo": "google/GNM",
    "source_commit": GNM_COMMIT or None,
    "license": "Apache-2.0",
    "model": "GNM Head v3",
    "model_basis": "scan-learned high-fidelity statistical human head",
    "identity_bound": False,
    "identity_seed": IDENTITY_SEED,
    "identity_sigma": IDENTITY_SIGMA,
    "identity_dim": int(gnm.identity_dim),
    "head_identity_dim_randomized": int(head_identity_dim),
    "expression_dim": int(gnm.expression_dim),
    "num_vertices": int(gnm.num_vertices),
    "num_triangles": int(len(triangles)),
    "mesh_component_names": components,
    "bbox_min": bbox_min.tolist(),
    "bbox_max": bbox_max.tolist(),
    "bbox_extent": (bbox_max - bbox_min).tolist(),
    "canonical_axes": {
        "x_source_axis": x_axis,
        "y_source_axis": y_axis,
        "z_source_axis": z_axis,
        "x_sign": x_sign,
        "y_sign": y_sign,
        "z_sign": z_sign,
        "semantic": "X lateral; Y face-forward; Z up",
    },
    "landmarks68_file": landmarks_json.name,
    "landmarks68_sha256": sha256(landmarks_json),
    "anchors": {
        "left_eye_center": left_eye.tolist(),
        "right_eye_center": right_eye.tolist(),
        "eye_mid": ((left_eye + right_eye) * 0.5).tolist(),
        "interocular_distance": interocular,
        "mouth_center": mouth.tolist(),
        "nose_center": nose.tolist(),
        "left_brow_center": brow_left.tolist(),
        "right_brow_center": brow_right.tolist(),
        "chin": landmarks[8].tolist(),
        "jaw_left": landmarks[0].tolist(),
        "jaw_right": landmarks[16].tolist(),
    },
    "files": files,
}
manifest_path = RUNTIME / "DIGE_C28_GNM_HEAD_MANIFEST.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
manifest["manifest_sha256"] = sha256(manifest_path)
manifest_path.write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)

print(json.dumps({
    "status": "PASS",
    "manifest": str(manifest_path),
    "manifest_sha256": sha256(manifest_path),
    "vertices": gnm.num_vertices,
    "triangles": len(triangles),
    "components": components,
    "interocular_distance": interocular,
}, sort_keys=True))
