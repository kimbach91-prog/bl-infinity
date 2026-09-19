from pathlib import Path
from urllib.request import Request, urlopen
import hashlib, json, math, os
from collections import Counter

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)
CANON_PATH=ROOT/"DIGE_CANON_EXECUTION_MANIFEST.json"
CANON_BYTES=CANON_PATH.read_bytes()
CANON=json.loads(CANON_BYTES)
CANON_SHA256=hashlib.sha256(CANON_BYTES).hexdigest()
BASE_URL=CANON["assets"]["base"]["url"]
TARGET_URL=CANON["assets"]["target"]["url"]
BASE_BLOB_SHA=CANON["assets"]["base"]["git_blob_sha1"]
TARGET_BLOB_SHA=CANON["assets"]["target"]["git_blob_sha1"]
ASSET_LICENSE=CANON["assets"]["base"]["license"]
MORPH_WEIGHT=1.0
TARGET_HEIGHT_M=1.70

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_exact(env_key: str, url: str, expected_blob: str):
    local=os.environ.get(env_key)
    if local:
        p=Path(local)
        data=p.read_bytes()
        acquisition={"mode":"LOCAL_PRESTAGED","source":str(p.resolve())}
    else:
        req=Request(url,headers={"User-Agent":"DEUS-DIGE-V8/1.1"})
        with urlopen(req,timeout=60) as r:
            data=r.read()
        acquisition={"mode":"NETWORK_FETCH_HASH_LOCKED","source":url}
    got=git_blob_sha(data)
    if got != expected_blob:
        raise RuntimeError(f"asset blob mismatch: expected={expected_blob} got={got} source={acquisition['source']}")
    return data, acquisition

base,base_acquisition=load_exact("DIGE_MAKEHUMAN_BASE",BASE_URL,BASE_BLOB_SHA)
target,target_acquisition=load_exact("DIGE_MAKEHUMAN_TARGET",TARGET_URL,TARGET_BLOB_SHA)
(RUNTIME/"makehuman_base.obj").write_bytes(base)
(RUNTIME/"asian-female-young.target").write_bytes(target)

base_text=base.decode("utf-8",errors="strict")
target_text=target.decode("utf-8",errors="strict")
verts=[]
for line in base_text.splitlines():
    if line.startswith("v "):
        p=line.split()
        verts.append([float(p[1]),float(p[2]),float(p[3])])

deltas={}
for line in target_text.splitlines():
    s=line.strip()
    if not s or s.startswith("#"):
        continue
    p=s.split()
    if len(p) != 4:
        continue
    i=int(p[0]); deltas[i]=(float(p[1]),float(p[2]),float(p[3]))

if not verts or not deltas:
    raise RuntimeError("empty base mesh or morph target")
if max(deltas) >= len(verts):
    raise RuntimeError("target index exceeds base vertex count")

morphed=[]
for i,(x,y,z) in enumerate(verts):
    dx,dy,dz=deltas.get(i,(0.0,0.0,0.0))
    x += MORPH_WEIGHT*dx
    y += MORPH_WEIGHT*dy
    z += MORPH_WEIGHT*dz
    if not all(math.isfinite(v) for v in (x,y,z)):
        raise RuntimeError(f"non-finite vertex {i}")
    # MakeHuman: X lateral, Y vertical, Z front/back. Blender: X lateral, Y depth, Z up.
    morphed.append([x,z,y])

mins=[min(v[a] for v in morphed) for a in range(3)]
maxs=[max(v[a] for v in morphed) for a in range(3)]
height=maxs[2]-mins[2]
if not (5.0 < height < 30.0):
    raise RuntimeError(f"unexpected MakeHuman source height {height}")
scale=TARGET_HEIGHT_M/height
cx=(mins[0]+maxs[0])/2
cy=(mins[1]+maxs[1])/2
normalized=[[(x-cx)*scale,(y-cy)*scale,(z-mins[2])*scale] for x,y,z in morphed]

# Parse exact face groups for deterministic landmarks and helper-derived garment geometry.
group_vertex_ids={}
current_group=None
for line in base_text.splitlines():
    if line.startswith("g "):
        current_group=line[2:].strip()
        group_vertex_ids.setdefault(current_group,set())
    elif line.startswith("f ") and current_group:
        ids=group_vertex_ids.setdefault(current_group,set())
        for tok in line.split()[1:]:
            ids.add(int(tok.split("/")[0])-1)

def group_stats(name):
    ids=sorted(group_vertex_ids.get(name,()))
    if not ids:
        raise RuntimeError(f"missing required MakeHuman group: {name}")
    pts=[normalized[i] for i in ids]
    mi=[min(p[a] for p in pts) for a in range(3)]
    ma=[max(p[a] for p in pts) for a in range(3)]
    ce=[sum(p[a] for p in pts)/len(pts) for a in range(3)]
    return {"center":ce,"bbox_min":mi,"bbox_max":ma,"vertex_count":len(ids)}

# Compact body OBJ: retain exactly the contiguous body-referenced vertex prefix.
out_lines=[]
vi=0
face_count=0
edge_counts=Counter()
referenced_vertices=set()
expected_body_vertices=CANON["mesh_policy"]["expected_body_vertices"]
current_group=None
allowed_groups=set(CANON["mesh_policy"]["include_face_groups"])
for line in base_text.splitlines():
    if line.startswith("v "):
        x,y,z=normalized[vi]
        if vi < expected_body_vertices:
            out_lines.append(f"v {x:.9f} {y:.9f} {z:.9f}")
        vi+=1
    elif line.startswith("g "):
        current_group=line[2:].strip()
        if current_group in allowed_groups:
            out_lines.append(line)
    elif line.startswith("f "):
        if current_group in allowed_groups:
            face_count+=1
            face_indices=[int(tok.split("/")[0])-1 for tok in line.split()[1:]]
            referenced_vertices.update(face_indices)
            for a,bidx in zip(face_indices,face_indices[1:]+face_indices[:1]):
                edge_counts[tuple(sorted((a,bidx)))]+=1
            out_lines.append(line)
    else:
        out_lines.append(line)

out=RUNTIME/"dige_makehuman_v8.obj"
out.write_text("\n".join(out_lines)+"\n",encoding="utf-8")
body_sha=hashlib.sha256(out.read_bytes()).hexdigest()

# Separate helper-tights OBJ: preserve the complete source vertex table because helper faces reference helper vertices.
garment_group=CANON["mesh_policy"]["garment_helper_group"]
tights_lines=[]
vi=0
current_group=None
tights_face_count=0
for line in base_text.splitlines():
    if line.startswith("v "):
        x,y,z=normalized[vi]; vi+=1
        tights_lines.append(f"v {x:.9f} {y:.9f} {z:.9f}")
    elif line.startswith("g "):
        current_group=line[2:].strip()
        if current_group == garment_group:
            tights_lines.append(line)
    elif line.startswith("f "):
        if current_group == garment_group:
            tights_face_count+=1
            tights_lines.append(line)
    else:
        tights_lines.append(line)

tights=RUNTIME/"dige_makehuman_tights_v8.obj"
tights.write_text("\n".join(tights_lines)+"\n",encoding="utf-8")
tights_sha=hashlib.sha256(tights.read_bytes()).hexdigest()

body_ids=sorted(group_vertex_ids["body"])
mouth_candidates=[
    normalized[i] for i in body_ids
    if abs(normalized[i][0]) < 0.045 and 1.525 <= normalized[i][2] <= 1.560
]
if not mouth_candidates:
    raise RuntimeError("mouth surface landmark candidates empty")
mouth_front=max(mouth_candidates,key=lambda p:p[1])

landmarks={
    "left_eye":group_stats("helper-l-eye"),
    "right_eye":group_stats("helper-r-eye"),
    "left_upperlid":group_stats("joint-l-upperlid"),
    "right_upperlid":group_stats("joint-r-upperlid"),
    "left_lowerlid":group_stats("joint-l-lowerlid"),
    "right_lowerlid":group_stats("joint-r-lowerlid"),
    "neck":group_stats("joint-neck"),
    "left_shoulder":group_stats("joint-l-shoulder"),
    "right_shoulder":group_stats("joint-r-shoulder"),
    "pelvis":group_stats("joint-pelvis"),
    "mouth_front":{"center":mouth_front},
    "hair_helper":group_stats("helper-hair")
}

if tights_face_count != CANON["assets"]["garment_helper_tights"]["expected_faces"]:
    raise RuntimeError(f"garment face-count drift: expected={CANON['assets']['garment_helper_tights']['expected_faces']} got={tights_face_count}")
if tights_sha != CANON["assets"]["garment_helper_tights"]["normalized_obj_sha256"]:
    raise RuntimeError(f"garment normalized OBJ drift: expected={CANON['assets']['garment_helper_tights']['normalized_obj_sha256']} got={tights_sha}")

final_mins=[min(v[a] for v in normalized) for a in range(3)]
final_maxs=[max(v[a] for v in normalized) for a in range(3)]
boundary_edges=sum(1 for count in edge_counts.values() if count == 1)
nonmanifold_edges=sum(1 for count in edge_counts.values() if count > 2)

manifest={
  "pipeline":"DIGE_V8_MAKEHUMAN_CC0_TOPOLOGY",
  "canon_execution_manifest_sha256":CANON_SHA256,
  "canon_drive":CANON["canonical_drive"],
  "state":"GEOMETRY_BUILT_PROVENANCE_VERIFIED",
  "identity_bound":False,
  "geometry_source":{
    "repo":"makehumancommunity/makehuman",
    "base_path":"makehuman/data/3dobjs/base.obj",
    "base_git_blob_sha1":BASE_BLOB_SHA,
    "base_sha256":sha256_bytes(base),
    "target_path":"makehuman/data/targets/macrodetails/asian-female-young.target",
    "target_git_blob_sha1":TARGET_BLOB_SHA,
    "target_sha256":sha256_bytes(target),
    "asset_license":ASSET_LICENSE,
    "base_acquisition":base_acquisition,
    "target_acquisition":target_acquisition,
    "source_pixels_used":False,
    "reference_images_used":False
  },
  "morph":{"weight":MORPH_WEIGHT,"target_name":"asian-female-young"},
  "normalization":{"height_m":TARGET_HEIGHT_M,"scale":scale,"bbox_min":final_mins,"bbox_max":final_maxs},
  "mesh":{"source_vertices":len(normalized),"vertices_written":expected_body_vertices,"referenced_body_vertices":len(referenced_vertices),"faces":face_count,"undirected_edges":len(edge_counts),"boundary_edges":boundary_edges,"nonmanifold_edges":nonmanifold_edges,"output":out.name,"sha256":body_sha},
  "garment_helper":{"group":garment_group,"faces":tights_face_count,"output":tights.name,"sha256":tights_sha},
  "landmarks":landmarks,
  "mesh_policy":CANON["mesh_policy"],
  "expected_body_only_normalized_obj_sha256":CANON["assets"]["candidate_body_only_normalized_obj_sha256"],
  "drive_compute_priors":{
    "V6_06":{"face_ratio":0.746,"eye_ratio":0.206,"nose_ratio":0.210,"mouth_ratio":0.340,"skin_roughness":0.46,"hair_density_norm":0.9955,"grain":0.0022,"total_loss":0.008275},
    "V6C_122":{"face_wl":0.746,"eye_face":0.210,"jaw_taper":0.82,"fullbody_m":5.1,"hero_m":2.7,"total_loss":0.01876451613}
  },
  "truth_boundary":"CC0 production topology candidate; not DEUS identity; not hyperreal certification; render receipt required separately."
}
if face_count != CANON["mesh_policy"]["expected_body_faces"]:
    raise RuntimeError(f"body face-count drift: expected={CANON['mesh_policy']['expected_body_faces']} got={face_count}")
if len(referenced_vertices) != expected_body_vertices or min(referenced_vertices) != 0 or max(referenced_vertices) != expected_body_vertices-1:
    raise RuntimeError(f"body vertex-range drift: expected contiguous 0..{expected_body_vertices-1}, got count={len(referenced_vertices)} min={min(referenced_vertices)} max={max(referenced_vertices)}")
if boundary_edges != CANON["mesh_policy"]["expected_boundary_edges"]:
    raise RuntimeError(f"body boundary-edge drift: expected={CANON['mesh_policy']['expected_boundary_edges']} got={boundary_edges}")
if nonmanifold_edges != CANON["mesh_policy"]["expected_nonmanifold_edges"]:
    raise RuntimeError(f"body non-manifold drift: expected={CANON['mesh_policy']['expected_nonmanifold_edges']} got={nonmanifold_edges}")
if manifest["mesh"]["sha256"] != CANON["assets"]["candidate_body_only_normalized_obj_sha256"]:
    raise RuntimeError(f"body-only normalized OBJ drift: expected={CANON['assets']['candidate_body_only_normalized_obj_sha256']} got={manifest['mesh']['sha256']}")
(RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,sort_keys=True))
