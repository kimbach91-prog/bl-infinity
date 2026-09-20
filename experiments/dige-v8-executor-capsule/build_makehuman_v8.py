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

# C27: deterministic anatomy refinement from official MakeHuman modeling targets.
C27_OFFICIAL_ANATOMY=os.environ.get("DIGE_C27_OFFICIAL_ANATOMY","0").strip()=="1"
C27_DATA_ROOT=os.environ.get("DIGE_C27_MAKEHUMAN_DATA","").strip()
C27_MAKEHUMAN_COMMIT=os.environ.get("DIGE_C27_MAKEHUMAN_COMMIT","").strip()
c27_target_receipts=[]
if C27_OFFICIAL_ANATOMY:
    if not C27_DATA_ROOT:
        raise RuntimeError("C27 requires DIGE_C27_MAKEHUMAN_DATA")
    data_root=Path(C27_DATA_ROOT).resolve()
    if not data_root.exists():
        raise RuntimeError(f"C27 MakeHuman data root missing: {data_root}")

    macro_selected={
        "female","young","asian","averagemuscle","averageweight","averageheight",
        "averagecup","averagefirmness","regularproportions"
    }
    macro_all={
        "male","female","baby","child","young","old","caucasian","asian","african",
        "maxmuscle","averagemuscle","minmuscle","minweight","averageweight","maxweight",
        "minheight","averageheight","maxheight","mincup","averagecup","maxcup",
        "minfirmness","averagefirmness","maxfirmness",
        "uncommonproportions","regularproportions","idealproportions"
    }

    def c27_component_key(path):
        rel=path.relative_to(data_root)
        tokens=[]
        deps=[]
        parts=list(rel.parts[:-1])+[rel.stem]
        for part in parts:
            for token in part.replace("_","-").replace(".","-").split("-"):
                token=token.strip().lower()
                if not token or token=="targets":
                    continue
                if token in macro_all:
                    deps.append(token)
                else:
                    tokens.append(token)
        return "-".join(tokens),deps

    components=[]
    for p in data_root.rglob("*.target"):
        key,deps=c27_component_key(p)
        components.append((key,deps,p))

    curated=[
        ("forehead-scale-vert-decr",0.32),
        ("forehead-trans-backward",0.10),
        ("eyebrows-trans-forward",0.20),
        ("l-eye-eyefold-convex",0.20),
        ("r-eye-eyefold-convex",0.20),
        ("l-eye-eyefold-up",0.08),
        ("r-eye-eyefold-up",0.08),
        ("l-cheek-bones-incr",0.20),
        ("r-cheek-bones-incr",0.20),
        ("nose-scale-depth-incr",0.20),
        ("nose-volume-incr",0.12),
        ("mouth-upperlip-volume-incr",0.14),
        ("mouth-lowerlip-volume-incr",0.11),
        ("mouth-philtrum-volume-incr",0.09),
        ("mouth-cupidsbow-incr",0.11),
        ("chin-prominent-incr",0.09),
        ("chin-bones-incr",0.07),
        ("head-age-incr",0.06),
    ]

    for suffix,weight in curated:
        matches=[row for row in components if row[0]==suffix or row[0].endswith("-"+suffix)]
        active=[]
        modified=set()
        for key,deps,p in matches:
            factor=1.0
            for dep in deps:
                if dep not in macro_selected:
                    factor=0.0
                    break
            if factor<=0.0:
                continue
            raw=p.read_bytes()
            for line in raw.decode("utf-8",errors="strict").splitlines():
                s=line.strip()
                if not s or s.startswith("#"):
                    continue
                fields=s.split()
                if len(fields)!=4:
                    continue
                idx=int(fields[0])
                if idx<0 or idx>=len(morphed):
                    raise RuntimeError(f"C27 target index out of range {idx}: {p}")
                dx,dy,dz=(float(fields[1]),float(fields[2]),float(fields[3]))
                # Convert MakeHuman delta to Blender axes before normalization.
                morphed[idx][0] += weight*factor*dx
                morphed[idx][1] += weight*factor*dz
                morphed[idx][2] += weight*factor*dy
                modified.add(idx)
            active.append({
                "path":str(p.relative_to(data_root)).replace("\\","/"),
                "sha256":hashlib.sha256(raw).hexdigest(),
                "dependencies":deps,
                "factor":factor,
            })
        if not active:
            nearby=sorted({key for key,_,_ in components if suffix.split("-")[0] in key})[:20]
            raise RuntimeError(f"C27 no active official target for {suffix}; nearby={nearby}")
        c27_target_receipts.append({
            "suffix":suffix,
            "weight":weight,
            "active_components":active,
            "modified_vertices":len(modified),
        })

# Normalize from the actual body group, not helper/joint vertices.
pre_group=None
body_source_ids=set()
for line in base_text.splitlines():
    if line.startswith("g "):
        pre_group=line[2:].strip()
    elif line.startswith("f ") and pre_group=="body":
        for tok in line.split()[1:]:
            body_source_ids.add(int(tok.split("/")[0])-1)
if not body_source_ids:
    raise RuntimeError("body source id set empty before normalization")

body_source_pts=[morphed[i] for i in sorted(body_source_ids)]
mins=[min(v[a] for v in body_source_pts) for a in range(3)]
maxs=[max(v[a] for v in body_source_pts) for a in range(3)]
height=maxs[2]-mins[2]
if not (5.0 < height < 30.0):
    raise RuntimeError(f"unexpected MakeHuman body source height {height}")
scale=TARGET_HEIGHT_M/height
cx=(mins[0]+maxs[0])/2
cy=(mins[1]+maxs[1])/2
normalized=[[(x-cx)*scale,(y-cy)*scale,(z-mins[2])*scale] for x,y,z in morphed]

# C12 full hm08 fit reference: preserve every normalized source/helper vertex so MHCLO assets
# can reference helper indices above the compact body prefix (e.g. high-poly eyes at 14598+).
fit_reference_path=RUNTIME/"DIGE_V8_FIT_REFERENCE.json"
fit_reference_payload={
    "schema":"DIGE_V8_FIT_REFERENCE_V1",
    "coordinate_system":"BLENDER_X_DEPTH_Y_UP_Z_NORMALIZED_BODY_REFERENCED",
    "vertices":normalized,
}
fit_reference_path.write_text(json.dumps(fit_reference_payload,separators=(",",":"))+"\n",encoding="utf-8")
fit_reference_sha=hashlib.sha256(fit_reference_path.read_bytes()).hexdigest()

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

def emit_compact_group(group_name, filename):
    cur=None
    faces=[]
    used=set()
    for line in base_text.splitlines():
        if line.startswith("g "):
            cur=line[2:].strip()
        elif line.startswith("f ") and cur == group_name:
            face=[int(tok.split("/")[0])-1 for tok in line.split()[1:]]
            faces.append(face)
            used.update(face)
    ids=sorted(used)
    if not ids or not faces:
        raise RuntimeError(f"empty compact group: {group_name}")
    remap={old:i+1 for i,old in enumerate(ids)}
    lines=[f"g {group_name}"]
    for old in ids:
        x,y,z=normalized[old]
        lines.append(f"v {x:.9f} {y:.9f} {z:.9f}")
    for face in faces:
        lines.append("f "+" ".join(str(remap[i]) for i in face))
    path=RUNTIME/filename
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return path,len(ids),len(faces),hashlib.sha256(path.read_bytes()).hexdigest()

left_eye,left_eye_vertices,left_eye_faces,left_eye_sha=emit_compact_group("helper-l-eye","dige_makehuman_l_eye_v8.obj")
right_eye,right_eye_vertices,right_eye_faces,right_eye_sha=emit_compact_group("helper-r-eye","dige_makehuman_r_eye_v8.obj")
eye_contract=CANON["assets"]["eye_helpers"]
if (left_eye_vertices,left_eye_faces)!=(eye_contract["left"]["vertices"],eye_contract["left"]["faces"]):
    raise RuntimeError(f"left helper-eye topology drift: vertices={left_eye_vertices} faces={left_eye_faces}")
if (right_eye_vertices,right_eye_faces)!=(eye_contract["right"]["vertices"],eye_contract["right"]["faces"]):
    raise RuntimeError(f"right helper-eye topology drift: vertices={right_eye_vertices} faces={right_eye_faces}")
if not C27_OFFICIAL_ANATOMY:
    if left_eye_sha != eye_contract["left"]["compact_obj_sha256"]:
        raise RuntimeError(f"left helper-eye hash drift: {left_eye_sha}")
    if right_eye_sha != eye_contract["right"]["compact_obj_sha256"]:
        raise RuntimeError(f"right helper-eye hash drift: {right_eye_sha}")

def emit_filtered_compact_group(group_name, filename, keep_face):
    cur=None
    faces=[]
    used=set()
    source_face_count=0
    removed=0
    for line in base_text.splitlines():
        if line.startswith("g "):
            cur=line[2:].strip()
        elif line.startswith("f ") and cur == group_name:
            source_face_count+=1
            face=[int(tok.split("/")[0])-1 for tok in line.split()[1:]]
            if keep_face(face):
                faces.append(face)
                used.update(face)
            else:
                removed+=1
    ids=sorted(used)
    if not ids or not faces:
        raise RuntimeError(f"empty filtered compact group: {group_name}")
    remap={old:i+1 for i,old in enumerate(ids)}
    lines=[f"g {group_name}"]
    for old in ids:
        x,y,z=normalized[old]
        lines.append(f"v {x:.9f} {y:.9f} {z:.9f}")
    for face in faces:
        lines.append("f "+" ".join(str(remap[i]) for i in face))
    path=RUNTIME/filename
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return path,len(ids),len(faces),source_face_count,removed,hashlib.sha256(path.read_bytes()).hexdigest()

def keep_hair_face(face):
    cy=sum(normalized[i][1] for i in face)/len(face)
    return cy <= 0.01

hair_guide,hair_vertices,hair_faces,hair_source_faces,hair_removed,hair_sha=emit_filtered_compact_group(
    "helper-hair","dige_makehuman_hair_guide_v8.obj",keep_hair_face
)
hair_contract=CANON["assets"]["filtered_hair_helper"]
if hair_source_faces != hair_contract["source_faces"]:
    raise RuntimeError(f"helper-hair source face drift: {hair_source_faces}")
if hair_removed != hair_contract["removed_front_faces"]:
    raise RuntimeError(f"helper-hair removed-face drift: {hair_removed}")
if (hair_vertices,hair_faces)!=(hair_contract["retained_vertices"],hair_contract["retained_faces"]):
    raise RuntimeError(f"filtered hair topology drift: vertices={hair_vertices} faces={hair_faces}")
if not C27_OFFICIAL_ANATOMY and hair_sha != hair_contract["compact_obj_sha256"]:
    raise RuntimeError(f"filtered hair hash drift: {hair_sha}")

body_ids=sorted(group_vertex_ids["body"])
mouth_candidates=[
    normalized[i] for i in body_ids
    if abs(normalized[i][0]) < 0.045 and 1.500 <= normalized[i][2] <= 1.530
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
if not C27_OFFICIAL_ANATOMY and tights_sha != CANON["assets"]["garment_helper_tights"]["normalized_obj_sha256"]:
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
  "c27_official_anatomy":{
    "enabled":C27_OFFICIAL_ANATOMY,
    "makehuman_commit":C27_MAKEHUMAN_COMMIT or None,
    "data_root":C27_DATA_ROOT or None,
    "macro_selected":sorted(macro_selected) if C27_OFFICIAL_ANATOMY else [],
    "targets":c27_target_receipts,
  },
  "normalization":{"height_m":TARGET_HEIGHT_M,"scale":scale,"reference_group":"body","ground_z_m":0.0,"source_bbox_min":mins,"source_bbox_max":maxs,"bbox_min":final_mins,"bbox_max":final_maxs},
  "mesh":{"source_vertices":len(normalized),"vertices_written":expected_body_vertices,"referenced_body_vertices":len(referenced_vertices),"faces":face_count,"undirected_edges":len(edge_counts),"boundary_edges":boundary_edges,"nonmanifold_edges":nonmanifold_edges,"output":out.name,"sha256":body_sha},
  "fit_reference":{"vertices":len(normalized),"output":fit_reference_path.name,"sha256":fit_reference_sha,"coordinate_system":"BLENDER_X_DEPTH_Y_UP_Z_NORMALIZED_BODY_REFERENCED"},
  "garment_helper":{"group":garment_group,"faces":tights_face_count,"output":tights.name,"sha256":tights_sha},
  "eye_helpers":{
    "left":{"group":"helper-l-eye","vertices":left_eye_vertices,"faces":left_eye_faces,"output":left_eye.name,"sha256":left_eye_sha},
    "right":{"group":"helper-r-eye","vertices":right_eye_vertices,"faces":right_eye_faces,"output":right_eye.name,"sha256":right_eye_sha}
  },
  "hair_guide":{
    "group":"helper-hair",
    "source_faces":hair_source_faces,
    "removed_front_faces":hair_removed,
    "vertices":hair_vertices,
    "faces":hair_faces,
    "output":hair_guide.name,
    "sha256":hair_sha,
    "filter":"centroid_y_m <= 0.01"
  },
  "landmarks":landmarks,
  "mesh_policy":CANON["mesh_policy"],
  "expected_body_only_normalized_obj_sha256":CANON["assets"]["candidate_body_only_normalized_obj_sha256"] if not C27_OFFICIAL_ANATOMY else None,
  "baseline_body_only_normalized_obj_sha256":CANON["assets"]["candidate_body_only_normalized_obj_sha256"],
  "c27_geometry_hash_policy":"TOPOLOGY_LOCKED_HASH_ALLOWED_TO_CHANGE_UNDER_OFFICIAL_ANATOMY_TARGETS" if C27_OFFICIAL_ANATOMY else "BASELINE_HASH_LOCKED",
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
if not C27_OFFICIAL_ANATOMY and manifest["mesh"]["sha256"] != CANON["assets"]["candidate_body_only_normalized_obj_sha256"]:
    raise RuntimeError(f"body-only normalized OBJ drift: expected={CANON['assets']['candidate_body_only_normalized_obj_sha256']} got={manifest['mesh']['sha256']}")
(RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,sort_keys=True))
