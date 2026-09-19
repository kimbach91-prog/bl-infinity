import bpy, bmesh, math, json, hashlib, random, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
OUTPUT_TAG=os.environ.get("DIGE_OUTPUT_TAG","").strip()
OUT=RUNTIME/"renders"
if OUTPUT_TAG:
    OUT=OUT/OUTPUT_TAG
OUT.mkdir(parents=True,exist_ok=True)
CANON_PATH=ROOT/"DIGE_CANON_EXECUTION_MANIFEST.json"
CANON_BYTES=CANON_PATH.read_bytes()
CANON=json.loads(CANON_BYTES)
CANON_SHA256=hashlib.sha256(CANON_BYTES).hexdigest()

def sha(p):
    p=Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def set_input(node,name,val):
    s=node.inputs.get(name)
    if s is not None:
        s.default_value=val

SKIN_SSS_WEIGHT=float(os.environ.get("DIGE_SKIN_SSS_WEIGHT","0.35"))
SKIN_SSS_SCALE=float(os.environ.get("DIGE_SKIN_SSS_SCALE","0.0025"))
SKIN_SSS_ANISO=float(os.environ.get("DIGE_SKIN_SSS_ANISO","0.80"))
SKIN_ROUGH_MIN=float(os.environ.get("DIGE_SKIN_ROUGH_MIN","0.30"))
SKIN_ROUGH_MAX=float(os.environ.get("DIGE_SKIN_ROUGH_MAX","0.48"))
SKIN_ALBEDO_PATH=os.environ.get("DIGE_SKIN_ALBEDO_PATH","").strip()
SKIN_ALBEDO_EXPECTED_SHA256=os.environ.get("DIGE_SKIN_ALBEDO_SHA256","").strip().lower()
RENDER_SET=os.environ.get("DIGE_RENDER_SET","FULL").strip().upper()

def make_skin():
    m=bpy.data.materials.new("DIGE_V8_SKIN")
    m.use_nodes=True
    nt=m.node_tree; bs=nt.nodes.get("Principled BSDF")
    set_input(bs,"IOR",1.42)
    set_input(bs,"Subsurface Weight",SKIN_SSS_WEIGHT)
    set_input(bs,"Subsurface Scale",SKIN_SSS_SCALE)
    if hasattr(bs,"subsurface_method"):
        bs.subsurface_method='RANDOM_WALK_SKIN'
    if hasattr(bs,"distribution"):
        bs.distribution='MULTI_GGX'
    set_input(bs,"Subsurface Radius",(1.0,.45,.18))
    set_input(bs,"Specular IOR Level",.30)
    set_input(bs,"Subsurface Anisotropy",SKIN_SSS_ANISO)
    set_input(bs,"Coat Weight",.012)
    set_input(bs,"Coat Roughness",.30)

    tex=nt.nodes.new("ShaderNodeTexCoord")
    skin_asset={
        "enabled":False,
        "file":None,
        "sha256":None,
        "expected_sha256":SKIN_ALBEDO_EXPECTED_SHA256 or None,
        "license":"CC0",
        "source_pack":"MakeHuman Skins01 CC0",
        "source_url":"https://files2.makehumancommunity.org/asset_packs/skins01/skins01_cc0.zip",
        "asset_name":"onlytheghosts_young_eurasian_female",
    }

    regional=nt.nodes.new("ShaderNodeTexNoise")
    regional.inputs["Scale"].default_value=3.2
    regional.inputs["Detail"].default_value=2.4
    regional.inputs["Roughness"].default_value=.50
    nt.links.new(tex.outputs["Generated"],regional.inputs["Vector"])
    tint=nt.nodes.new("ShaderNodeValToRGB")
    tint.color_ramp.elements[0].position=.18
    tint.color_ramp.elements[0].color=(0.92,0.86,0.83,1)
    tint.color_ramp.elements[1].position=.82
    tint.color_ramp.elements[1].color=(1.06,1.02,.98,1)
    nt.links.new(regional.outputs["Fac"],tint.inputs["Fac"])

    if SKIN_ALBEDO_PATH:
        p=Path(SKIN_ALBEDO_PATH)
        if not p.is_absolute():
            p=ROOT/p
        if not p.exists():
            raise RuntimeError(f"Configured skin albedo missing: {p}")
        got=sha(p)
        if SKIN_ALBEDO_EXPECTED_SHA256 and got.lower()!=SKIN_ALBEDO_EXPECTED_SHA256:
            raise RuntimeError(f"Skin albedo hash drift: expected={SKIN_ALBEDO_EXPECTED_SHA256} got={got}")
        img=bpy.data.images.load(str(p),check_existing=True)
        try:
            img.colorspace_settings.name='sRGB'
        except Exception:
            pass
        albedo=nt.nodes.new("ShaderNodeTexImage")
        albedo.image=img
        albedo.interpolation='Linear'
        albedo.extension='EXTEND'
        nt.links.new(tex.outputs["UV"],albedo.inputs["Vector"])
        grade=nt.nodes.new("ShaderNodeHueSaturation")
        grade.inputs["Saturation"].default_value=.92
        grade.inputs["Value"].default_value=.74
        nt.links.new(albedo.outputs["Color"],grade.inputs["Color"])
        color_mix=nt.nodes.new("ShaderNodeMixRGB")
        color_mix.blend_type='MULTIPLY'
        color_mix.inputs["Fac"].default_value=.18
        nt.links.new(grade.outputs["Color"],color_mix.inputs[1])
        nt.links.new(tint.outputs["Color"],color_mix.inputs[2])
        nt.links.new(color_mix.outputs["Color"],bs.inputs["Base Color"])
        skin_asset.update({"enabled":True,"file":p.name,"sha256":got})
    else:
        tone=nt.nodes.new("ShaderNodeValToRGB")
        tone.color_ramp.elements[0].position=.20
        tone.color_ramp.elements[0].color=(0.255,0.090,0.058,1)
        tone.color_ramp.elements[1].position=.80
        tone.color_ramp.elements[1].color=(0.335,0.145,0.090,1)
        nt.links.new(regional.outputs["Fac"],tone.inputs["Fac"])
        nt.links.new(tone.outputs["Color"],bs.inputs["Base Color"])

    # Roughness is independent from albedo so pigmentation never becomes gloss directly.
    rough_macro=nt.nodes.new("ShaderNodeTexNoise")
    rough_macro.inputs["Scale"].default_value=6.0
    rough_macro.inputs["Detail"].default_value=3.0
    rough_macro.inputs["Roughness"].default_value=.55
    nt.links.new(tex.outputs["Generated"],rough_macro.inputs["Vector"])
    rough_micro=nt.nodes.new("ShaderNodeTexNoise")
    rough_micro.inputs["Scale"].default_value=78.0
    rough_micro.inputs["Detail"].default_value=3.0
    rough_micro.inputs["Roughness"].default_value=.62
    nt.links.new(tex.outputs["Generated"],rough_micro.inputs["Vector"])
    r1=nt.nodes.new("ShaderNodeMath"); r1.operation='MULTIPLY'; r1.inputs[1].default_value=.70
    r2=nt.nodes.new("ShaderNodeMath"); r2.operation='MULTIPLY'; r2.inputs[1].default_value=.30
    rsum=nt.nodes.new("ShaderNodeMath"); rsum.operation='ADD'
    nt.links.new(rough_macro.outputs["Fac"],r1.inputs[0]); nt.links.new(rough_micro.outputs["Fac"],r2.inputs[0])
    nt.links.new(r1.outputs[0],rsum.inputs[0]); nt.links.new(r2.outputs[0],rsum.inputs[1])
    rough_map=nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value=0.0
    rough_map.inputs["From Max"].default_value=1.0
    rough_map.inputs["To Min"].default_value=SKIN_ROUGH_MIN
    rough_map.inputs["To Max"].default_value=SKIN_ROUGH_MAX
    nt.links.new(rsum.outputs[0],rough_map.inputs["Value"])
    nt.links.new(rough_map.outputs["Result"],bs.inputs["Roughness"])

    # Meso / pore / micro normal remain independent from the color texture.
    meso=nt.nodes.new("ShaderNodeTexNoise")
    meso.inputs["Scale"].default_value=115.0
    meso.inputs["Detail"].default_value=5.0
    meso.inputs["Roughness"].default_value=.68
    nt.links.new(tex.outputs["Generated"],meso.inputs["Vector"])
    pore=nt.nodes.new("ShaderNodeTexNoise")
    pore.inputs["Scale"].default_value=560.0
    pore.inputs["Detail"].default_value=4.0
    pore.inputs["Roughness"].default_value=.62
    nt.links.new(tex.outputs["Generated"],pore.inputs["Vector"])
    micro=nt.nodes.new("ShaderNodeTexNoise")
    micro.inputs["Scale"].default_value=1750.0
    micro.inputs["Detail"].default_value=2.0
    micro.inputs["Roughness"].default_value=.58
    nt.links.new(tex.outputs["Generated"],micro.inputs["Vector"])
    m1=nt.nodes.new("ShaderNodeMath"); m1.operation='MULTIPLY'; m1.inputs[1].default_value=.28
    m2=nt.nodes.new("ShaderNodeMath"); m2.operation='MULTIPLY'; m2.inputs[1].default_value=.50
    m3=nt.nodes.new("ShaderNodeMath"); m3.operation='MULTIPLY'; m3.inputs[1].default_value=.22
    ma=nt.nodes.new("ShaderNodeMath"); ma.operation='ADD'
    mb=nt.nodes.new("ShaderNodeMath"); mb.operation='ADD'
    nt.links.new(meso.outputs["Fac"],m1.inputs[0]); nt.links.new(pore.outputs["Fac"],m2.inputs[0]); nt.links.new(micro.outputs["Fac"],m3.inputs[0])
    nt.links.new(m1.outputs[0],ma.inputs[0]); nt.links.new(m2.outputs[0],ma.inputs[1]); nt.links.new(ma.outputs[0],mb.inputs[0]); nt.links.new(m3.outputs[0],mb.inputs[1])
    bump=nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.09
    bump.inputs["Distance"].default_value=.00010
    nt.links.new(mb.outputs[0],bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m,skin_asset

def principled(name,base,rough=.45,ior=1.45,subsurface=0.0,transmission=0.0,metallic=0.0,sheen=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes.get("Principled BSDF")
    set_input(n,"Base Color",(*base,1)); set_input(n,"Roughness",rough)
    set_input(n,"IOR",ior); set_input(n,"Subsurface Weight",subsurface)
    set_input(n,"Transmission Weight",transmission); set_input(n,"Metallic",metallic)
    set_input(n,"Sheen Weight",sheen)
    return m

def hair_material():
    m=bpy.data.materials.new("DIGE_V8_HAIR"); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    try:
        h=nt.nodes.new("ShaderNodeBsdfHairPrincipled")
        if hasattr(h,"parametrization"):
            try: h.parametrization='MELANIN'
            except Exception: pass
        if hasattr(h,"model"):
            try: h.model='HUANG'
            except Exception: pass
        set_input(h,"Aspect Ratio",.90)
        set_input(h,"Reflection",1.0)
        set_input(h,"Transmission",1.0)
        set_input(h,"Secondary Reflection",1.0)
        set_input(h,"Melanin",.93)
        set_input(h,"Melanin Redness",.04)
        set_input(h,"Random Color",.03)
        set_input(h,"Roughness",.28)
        set_input(h,"Radial Roughness",.30)
        set_input(h,"Random Roughness",.06)
        set_input(h,"Coat",.02)
        set_input(h,"IOR",1.55)
        if h.inputs.get("Color"): h.inputs["Color"].default_value=(0.018,0.010,0.006,1)
    except Exception:
        h=nt.nodes.new("ShaderNodeBsdfPrincipled")
        set_input(h,"Base Color",(0.018,0.010,0.006,1)); set_input(h,"Roughness",.31)
    nt.links.new(h.outputs[0],out.inputs["Surface"])
    return m

def uv(name,loc,scale,mat,seg=48,rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    return o

def cylinder(name,loc,radius,depth,mat,rot=(math.radians(90),0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    return o

def curve_object(name,splines,bevel,mat):
    cu=bpy.data.curves.new(name,"CURVE"); cu.dimensions='3D'; cu.resolution_u=2
    cu.bevel_depth=bevel; cu.bevel_resolution=2; cu.fill_mode='FULL'
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob)
    for pts in splines:
        sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
        n=max(1,len(pts)-1)
        for idx,(p,co) in enumerate(zip(sp.bezier_points,pts)):
            p.co=co
            p.handle_left_type='AUTO'
            p.handle_right_type='AUTO'
            p.radius=max(.26,1.0-.74*(idx/n))
    ob.data.materials.append(mat); return ob

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

skin,skin_asset=make_skin()
sclera=principled("SCLERA",(0.58,0.52,0.48),rough=.30,ior=1.376,subsurface=.02)
iris=principled("IRIS",(0.070,0.026,0.012),rough=.32,ior=1.40)
iris_ring=principled("IRIS_RING",(0.012,0.005,0.003),rough=.34,ior=1.40)
black=principled("BLACK",(0.005,0.004,0.004),rough=.28)
cornea=principled("CORNEA",(0.92,0.92,0.92),rough=.008,ior=1.376,transmission=1.0)
wetline=principled("EYE_WETLINE",(0.90,0.92,0.94),rough=.018,ior=1.333,transmission=1.0)
lip=principled("LIP",(0.18,0.035,0.032),rough=.44,ior=1.40,subsurface=.04)
mouth_dark=principled("MOUTH_DARK",(0.018,0.004,0.004),rough=.58,ior=1.35)
scalp_shadow=principled("SCALP_SHADOW",(0.075,0.026,0.018),rough=.50,ior=1.42,subsurface=.06)
hair=hair_material()
hair_mass=principled("DIGE_V8_HAIR_MASS",(0.006,0.0035,0.0022),rough=.46,ior=1.55)
hm_bs=hair_mass.node_tree.nodes.get("Principled BSDF")
set_input(hm_bs,"Specular IOR Level",.22)
set_input(hm_bs,"Coat Weight",.10)
set_input(hm_bs,"Coat Roughness",.30)
set_input(hm_bs,"Anisotropic IOR Level",.35)
cloth=principled("CLOTH",(0.020,0.026,0.040),rough=.72,sheen=.12)
floor_mat=principled("FLOOR",(0.12,0.12,0.125),rough=.70)

mesh_path=RUNTIME/"dige_makehuman_v8.obj"
# Builder already writes Blender-space coordinates (Y forward, Z up). Import with an identity axis convention;
# Blender's default OBJ convention (-Z forward, Y up) would rotate the body a second time.
bpy.ops.wm.obj_import(
    filepath=str(mesh_path),
    forward_axis='Y',
    up_axis='Z',
    use_split_objects=False,
    use_split_groups=False,
)
imported_meshes=[o for o in bpy.context.selected_objects if o.type == 'MESH']
if len(imported_meshes) != 1:
    raise RuntimeError(f"Expected exactly one body mesh, got {len(imported_meshes)}")
body=imported_meshes[0]
body.name="DIGE_V8_MAKEHUMAN_BODY"
body.data.materials.append(skin)
bpy.ops.object.shade_smooth()

# Hard orientation gate before any cosmetic layer can hide an ingestion error.
bbox_world=[body.matrix_world @ Vector(corner) for corner in body.bound_box]
bbox_min=[min(v[i] for v in bbox_world) for i in range(3)]
bbox_max=[max(v[i] for v in bbox_world) for i in range(3)]
bbox_extent=[bbox_max[i]-bbox_min[i] for i in range(3)]
if not (1.60 <= bbox_extent[2] <= 1.80):
    raise RuntimeError(f"Body vertical extent invalid after OBJ import: {bbox_extent}")
if bbox_extent[1] >= 0.65:
    raise RuntimeError(f"Body depth indicates axis-rotation regression: {bbox_extent}")
if bbox_min[2] < -0.03 or bbox_max[2] > 1.75:
    raise RuntimeError(f"Body Z placement invalid: min={bbox_min[2]} max={bbox_max[2]}")

geom=json.loads((RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").read_text())
if geom.get("canon_execution_manifest_sha256") != CANON_SHA256:
    raise RuntimeError("geometry/canon manifest causal binding mismatch")
landmarks=geom["landmarks"]
mouth_z=landmarks["mouth_front"]["center"][2]
eye_mid_z=(landmarks["left_eye"]["center"][2]+landmarks["right_eye"]["center"][2])*.5
cheek_z=mouth_z+.034
nose_bridge_z=eye_mid_z-.010
nose_tip_z=mouth_z+.027
chin_z=mouth_z-.038
jaw_z=mouth_z-.026

# No hard polygon scalp-shadow assignment in C6; canonical scalp remains skin under strand coverage.
scalp_shadow_polygons=0

craniofacial_deform={
  "cheek_y_m":0.0045,
  "nose_bridge_y_m":0.0035,
  "nose_tip_y_m":0.0060,
  "chin_y_m":0.0030,
  "lip_volume_y_m":0.0018,
  "jaw_x_scale":0.985,
  "asymmetry_y_m":0.0007,
  "brow_ridge_y_m":0.0013,
  "tear_trough_y_m":0.00075,
  "nasolabial_y_m":0.00085,
  "philtrum_groove_y_m":0.00065,
  "philtrum_ridge_y_m":0.00055,
}
def g2(x,z,cx,cz,sx,sz):
    return math.exp(-0.5*(((x-cx)/sx)**2+((z-cz)/sz)**2))

for v in body.data.vertices:
    co=v.co
    # Only the forward facial surface; back/head/body vertices remain untouched.
    if co.y <= 0.0 or co.z < chin_z-.035 or co.z > eye_mid_z+.085 or abs(co.x) > .120:
        continue

    # Cheek/malar projection with tiny natural asymmetry.
    wl=g2(co.x,co.z,.052,cheek_z,.031,.031)
    wr=g2(co.x,co.z,-.052,cheek_z,.031,.031)
    co.y += craniofacial_deform["cheek_y_m"]*(wl+wr)
    co.y += craniofacial_deform["asymmetry_y_m"]*(wr-wl)

    # Nose bridge and tip remain bounded around the midline.
    co.y += craniofacial_deform["nose_bridge_y_m"]*g2(co.x,co.z,0.0,nose_bridge_z,.015,.030)
    co.y += craniofacial_deform["nose_tip_y_m"]*g2(co.x,co.z,0.0,nose_tip_z,.014,.015)

    # Native lip volume: geometry, not a painted/floating replacement.
    co.y += craniofacial_deform["lip_volume_y_m"]*g2(co.x,co.z,0.0,mouth_z,.030,.008)

    # Meso facial planes. All offsets remain sub-1.5 mm and are landmark-relative.
    co.y += craniofacial_deform["brow_ridge_y_m"]*(
        g2(co.x,co.z,.030,eye_mid_z+.024,.020,.013)+
        g2(co.x,co.z,-.030,eye_mid_z+.024,.020,.013)
    )
    co.y -= craniofacial_deform["tear_trough_y_m"]*(
        g2(co.x,co.z,.032,eye_mid_z-.016,.023,.010)+
        g2(co.x,co.z,-.032,eye_mid_z-.016,.023,.010)
    )
    co.y -= craniofacial_deform["nasolabial_y_m"]*(
        g2(co.x,co.z,.027,mouth_z+.020,.015,.024)+
        g2(co.x,co.z,-.027,mouth_z+.020,.015,.024)
    )
    co.y -= craniofacial_deform["philtrum_groove_y_m"]*g2(co.x,co.z,0.0,mouth_z+.014,.0055,.010)
    co.y += craniofacial_deform["philtrum_ridge_y_m"]*(
        g2(co.x,co.z,.006,mouth_z+.014,.004,.010)+
        g2(co.x,co.z,-.006,mouth_z+.014,.004,.010)
    )

    # Chin projection.
    co.y += craniofacial_deform["chin_y_m"]*g2(co.x,co.z,0.0,chin_z,.035,.022)

    # Mild lower-face taper from the existing canonical topology.
    jaw_w=max(0.0,1.0-abs(co.z-jaw_z)/.052)
    if jaw_w>0 and abs(co.x)>.030:
        s=1.0-(1.0-craniofacial_deform["jaw_x_scale"])*jaw_w
        co.x *= s

sub=body.modifiers.new("DIGE_V8_SUBDIV","SUBSURF"); sub.levels=1; sub.render_levels=2
# Preserve topology metrics before subdivision
bm=bmesh.new(); bm.from_mesh(body.data)
nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
boundary=sum(1 for e in bm.edges if e.is_boundary)
bm.free()
topology={
    "vertices":len(body.data.vertices),
    "polygons":len(body.data.polygons),
    "nonmanifold_edges":nonmanifold,
    "boundary_edges":boundary,
    "bbox_min":bbox_min,
    "bbox_max":bbox_max,
    "bbox_extent":bbox_extent,
    "orientation_gate":"PASS",
}

geom=json.loads((RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").read_text())
if geom.get("canon_execution_manifest_sha256") != CANON_SHA256:
    raise RuntimeError("geometry/canon manifest causal binding mismatch")
landmarks=geom["landmarks"]

# Eyes: use exact MakeHuman helper-eye meshes emitted by the provenance-locked builder.
for side,label,sx in (("left","left_eye",1),("right","right_eye",-1)):
    eye_meta=geom["eye_helpers"][side]
    eye_path=RUNTIME/eye_meta["output"]
    bpy.ops.wm.obj_import(
        filepath=str(eye_path),
        forward_axis='Y',
        up_axis='Z',
        use_split_objects=False,
        use_split_groups=False,
    )
    imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
    if len(imported)!=1:
        raise RuntimeError(f"Expected one helper eye mesh for {side}, got {len(imported)}")
    eye_obj=imported[0]
    eye_obj.name=f"DIGE_V8_HELPER_EYE_{side.upper()}"
    eye_obj.data.materials.append(sclera)
    bpy.context.view_layer.objects.active=eye_obj
    bpy.ops.object.shade_smooth()

    st=landmarks[label]
    ceye=st["center"]
    mi=st["bbox_min"]; ma=st["bbox_max"]
    eye_rx=(ma[0]-mi[0])*.5
    eye_rz=(ma[2]-mi[2])*.5
    front_y=ma[1]+.00025
    iris_r=min(eye_rx,eye_rz)*.39
    cylinder(f"IRIS_RING_{sx}",(ceye[0],front_y,ceye[2]),iris_r,.00045,iris_ring)
    cylinder(f"IRIS_{sx}",(ceye[0],front_y+.00012,ceye[2]),iris_r*.82,.00035,iris)
    cylinder(f"PUPIL_{sx}",(ceye[0],front_y+.00028,ceye[2]),iris_r*.30,.00030,black)
    cylinder(f"CORNEA_DISC_{sx}",(ceye[0],front_y+.00044,ceye[2]),iris_r*1.18,.00018,cornea)

# Mouth: preserve native face topology; add only a thin, source-anchored mouth gap.
mouth_center=landmarks["mouth_front"]["center"]
my=mouth_center[1]+.0010
mz=mouth_center[2]-.0012
mouth_line=[
    (-.020,my,mz),
    (-.010,my+.0005,mz-.0004),
    (0.0,my+.0007,mz-.0006),
    (.010,my+.0005,mz-.0004),
    (.020,my,mz)
]
curve_object("DIGE_V8_MOUTH_GAP",[mouth_line],.00010,mouth_dark)

# Thin vermilion tint uses tiny curves; native lip volume remains the geometry source.
upper_lip=[
    (-.018,my+.0002,mz+.0015),
    (-.009,my+.0006,mz+.0031),
    (0.0,my+.0008,mz+.0020),
    (.009,my+.0006,mz+.0031),
    (.018,my+.0002,mz+.0015),
]
lower_lip=[
    (-.018,my+.0002,mz-.0012),
    (-.009,my+.0005,mz-.0025),
    (0.0,my+.0007,mz-.0030),
    (.009,my+.0005,mz-.0025),
    (.018,my+.0002,mz-.0012),
]
curve_object("DIGE_V8_UPPER_LIP_TINT",[upper_lip],.00018,lip)
curve_object("DIGE_V8_LOWER_LIP_TINT",[lower_lip],.00022,lip)

# Small recessed nostril discs add depth without altering topology.
nose_z=mouth_center[2]+.0275
nose_y=mouth_center[1]+.0030
for sx in (-1,1):
    cylinder(f"NOSTRIL_{sx}",(sx*.0065,nose_y,nose_z),.00145,.00022,mouth_dark)

# Brows + lashes anchored to the same source-derived eye and eyelid landmarks.
brow_hairs=[]; lashes=[]
for eye_key,lid_key,sx in (("left_eye","left_upperlid",1),("right_eye","right_upperlid",-1)):
    ec=landmarks[eye_key]["center"]
    lid=landmarks[lid_key]["center"]
    brow_y=max(lid[1]+.0045,ec[1]+.0085)
    for j in range(46):
        t=j/45
        x=ec[0]+(t-.5)*.036
        arch=math.sin(t*math.pi)
        z=ec[2]+.024+.0042*arch
        lean=(t-.5)*.0015
        brow_hairs.append([(x,brow_y,z),(x+lean,brow_y+.0018,z+.0040)])
    for j in range(11):
        t=(j-5)/5
        x=ec[0]+t*.0125
        y=max(lid[1]+.0030,ec[1]+.0070)
        z=ec[2]+.0052+.0014*(1-abs(t))
        lashes.append([(x,y,z),(x+sx*.0006,y+.0024,z+.0011)])
curve_object("DIGE_V8_BROWS",brow_hairs,.000075,hair)
curve_object("DIGE_V8_LASHES",lashes,.000035,black)

# Lower-lid wetline/tear meniscus follows the native lower-lid landmarks.
wetlines=[]
for eye_key,lid_key in (("left_eye","left_lowerlid"),("right_eye","right_lowerlid")):
    ec=landmarks[eye_key]["center"]
    lid=landmarks[lid_key]
    mi=lid["bbox_min"]; ma=lid["bbox_max"]
    pts=[]
    for i in range(9):
        t=i/8
        x=mi[0]+(ma[0]-mi[0])*t
        arch=math.sin(t*math.pi)
        y=max(ma[1]+.00045,ec[1]+.0070)
        z=ma[2]-.0008+.0012*arch
        pts.append((x,y,z))
    wetlines.append(pts)
curve_object("DIGE_V8_EYE_WETLINES",wetlines,.00016,wetline)

# C8 production-style scalp sampling: area-weighted roots -> guide field -> children/clump/frizz.
hair_guide_meta=geom["hair_guide"]
eye_z=(landmarks["left_eye"]["center"][2]+landmarks["right_eye"]["center"][2])*.5
head_center=Vector((0.0,-.055,eye_z+.055))

def tri_area(a,b,c):
    return ((b-a).cross(c-a)).length*.5

# Select scalp polygons on the actual body surface, then triangulate for area-weighted sampling.
scalp_tris=[]
scalp_area=0.0
for poly in body.data.polygons:
    pts=[body.matrix_world @ body.data.vertices[i].co for i in poly.vertices]
    center=sum(pts,Vector((0,0,0)))/len(pts)
    if center.z < eye_z+.028 or abs(center.x)>.132:
        continue
    # Keep forehead open below hairline; retain crown/back.
    if center.y>.032 and center.z<eye_z+.105:
        continue
    if abs(center.x)>.112 and center.z<eye_z+.074:
        continue
    for i in range(1,len(pts)-1):
        a,b,c3=pts[0],pts[i],pts[i+1]
        ar=tri_area(a,b,c3)
        if ar>1e-10:
            scalp_tris.append((a,b,c3,ar))
            scalp_area+=ar
if len(scalp_tris)<100 or scalp_area<=0:
    raise RuntimeError(f"C8 scalp triangle selection invalid: tris={len(scalp_tris)} area={scalp_area}")

random.seed(20260919)
cdf=[]
acc=0.0
for a,b,c3,ar in scalp_tris:
    acc+=ar
    cdf.append(acc)

def sample_scalp_point():
    import bisect
    x=random.random()*acc
    idx=bisect.bisect_left(cdf,x)
    a,b,c3,_=scalp_tris[min(idx,len(scalp_tris)-1)]
    r1=math.sqrt(random.random()); r2=random.random()
    p=a*(1-r1)+b*(r1*(1-r2))+c3*(r1*r2)
    n=(b-a).cross(c3-a)
    if n.length<1e-9:
        n=(p-head_center)
    if n.length<1e-9:
        n=Vector((0,0,1))
    n.normalize()
    if (p-head_center).dot(n)<0:
        n=-n
    return p,n

root_count=2600
roots=[sample_scalp_point() for _ in range(root_count)]

# Sparse guide centers define local flow/clumps; children inherit and vary that field.
guide_count=96
guide_indices=random.sample(range(root_count),guide_count)
guides=[roots[i] for i in guide_indices]

def tangent_flow(p,n):
    side=1.0 if p.x>=0 else -1.0
    crown=max(0.0,min(1.0,(p.z-(eye_z+.028))/.135))
    desired=Vector((side*(.10+.12*crown),-1.0,-.22+.26*crown))
    flow=desired-n*desired.dot(n)
    if flow.length<1e-8:
        flow=Vector((side*.08,-.98,-.15))
    flow.normalize()
    return flow,crown

guide_flow=[tangent_flow(p,n)[0] for p,n in guides]

strands=[]
for root,n in roots:
    # Nearest guide in XZ gives deterministic clump field at modest CPU cost.
    gi=min(range(guide_count),key=lambda k:(guides[k][0].x-root.x)**2+(guides[k][0].z-root.z)**2)
    gpos,gn=guides[gi]
    base_flow,crown=tangent_flow(root,n)
    flow=(base_flow*.72+guide_flow[gi]*.28)
    if flow.length<1e-8: flow=base_flow
    flow.normalize()

    # Medium-short style: enough mass to cover scalp while remaining easier than long hair.
    L=random.uniform(.075,.145)*(0.86+.24*crown)
    root2=root+n*.00028
    tip=root2+flow*L+Vector((0,0,-.012*(1-crown)))

    # Clump children progressively toward guide trajectory without collapsing roots.
    guide_delta=(gpos-root)
    clump_strength=random.uniform(.08,.20)
    frizz=Vector((random.uniform(-.004,.004),random.uniform(-.003,.003),random.uniform(-.004,.004)))
    p1=root2+(tip-root2)*.28+guide_delta*(clump_strength*.10)+frizz*.35
    p2=root2+(tip-root2)*.58+guide_delta*(clump_strength*.20)-frizz*.20
    p3=root2+(tip-root2)*.82+guide_delta*(clump_strength*.28)+frizz*.45
    strands.append([tuple(root2),tuple(p1),tuple(p2),tuple(p3),tuple(tip)])

flyaways=140
for _ in range(flyaways):
    root,n=random.choice(roots)
    base,crown=tangent_flow(root,n)
    L=random.uniform(.045,.100)
    side=1.0 if root.x>=0 else -1.0
    root2=root+n*.00035
    tip=root2+base*L+Vector((side*random.uniform(-.012,.012),random.uniform(-.010,.005),random.uniform(-.010,.018)))
    mid=root2+(tip-root2)*.52+Vector((side*random.uniform(-.009,.009),random.uniform(-.006,.006),random.uniform(-.006,.010)))
    strands.append([tuple(root2),tuple(mid),tuple(tip)])

curve_object("DIGE_V8_C8_AREA_CLUMP_GROOM",strands,.000032,hair)

hair_surface_contract={
    "root_source":"AREA_WEIGHTED_CANONICAL_SCALP_TRIANGLES",
    "guide_source":"DERIVED_LOCAL_FLOW_WITH_FILTERED_MAKEHUMAN_HAIR_PROVENANCE",
    "guide_sha256":hair_guide_meta["sha256"],
    "scalp_triangle_count":len(scalp_tris),
    "scalp_area_m2":scalp_area,
    "root_count":root_count,
    "guide_count":guide_count,
    "flyaway_count":flyaways,
    "curve_count":len(strands),
    "bevel_radius_m":0.000032,
    "mass_mesh_rendered":False,
    "clumping":"NEAREST_GUIDE_XZ_PROGRESSIVE",
    "frizz":"LOW_AMPLITUDE_PER_STRAND",
    "style":"AREA_SAMPLED_GUIDE_CHILD_CLUMP_V1",
}

# Fitted garment proxy from the deterministic canonical MakeHuman helper-tights group.
tights_path=RUNTIME/"dige_makehuman_tights_v8.obj"
bpy.ops.wm.obj_import(
    filepath=str(tights_path),
    forward_axis='Y',
    up_axis='Z',
    use_split_objects=False,
    use_split_groups=False,
)
garments=[o for o in bpy.context.selected_objects if o.type=='MESH']
if len(garments)!=1:
    raise RuntimeError(f"Expected one helper-tights garment mesh, got {len(garments)}")
tights=garments[0]
tights.name="DIGE_V8_FITTED_TIGHTS"
tights.data.materials.append(cloth)
bpy.context.view_layer.objects.active=tights
bpy.ops.object.shade_smooth()
gsub=tights.modifiers.new("DIGE_V8_TIGHTS_SUBDIV","SUBSURF"); gsub.levels=1; gsub.render_levels=2
solid=tights.modifiers.new("DIGE_V8_TIGHTS_THICKNESS","SOLIDIFY"); solid.thickness=.0030; solid.offset=1.0

bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.006))
floor=bpy.context.object; floor.data.materials.append(floor_mat)

def area(name,loc,energy,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; o.data.color=color
    d=Vector((0,0,1.25))-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    return o
area("KEY",(2.1,2.8,2.8),500,2.5,(1.0,.88,.78))
area("FILL",(-2.0,2.1,1.8),110,3.0,(.72,.84,1.0))
area("RIM",(0,-2.3,2.5),210,1.8,(1.0,.72,.50))
area("FACE",(0,1.2,1.8),45,1.1,(1.0,.91,.84))

world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(0.012,0.014,0.020,1); bg.inputs["Strength"].default_value=.055

bpy.ops.object.camera_add(); cam=bpy.context.object; bpy.context.scene.camera=cam; cam.data.sensor_width=36

def aim(loc,target,lens,fstop):
    cam.location=loc; d=Vector(target)-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens; cam.data.dof.use_dof=True; cam.data.dof.focus_distance=d.length; cam.data.dof.aperture_fstop=fstop

def configure_cycles_device(scene):
    mode=os.environ.get("DIGE_CYCLES_DEVICE","CPU").upper()
    backend=os.environ.get("DIGE_CYCLES_BACKEND","OPTIX").upper()
    info={"requested_mode":mode,"requested_backend":backend,"enabled_devices":[]}
    if mode == "CPU":
        scene.cycles.device='CPU'
        info["actual_mode"]="CPU"
        return info
    if mode != "GPU":
        raise RuntimeError(f"Unsupported DIGE_CYCLES_DEVICE={mode}")
    addon=bpy.context.preferences.addons.get("cycles")
    if addon is None:
        raise RuntimeError("Cycles addon unavailable")
    prefs=addon.preferences
    try:
        prefs.compute_device_type=backend
    except Exception as exc:
        raise RuntimeError(f"Cannot select Cycles backend {backend}: {exc}")
    try:
        prefs.get_devices()
    except Exception:
        pass
    enabled=[]
    for dev in prefs.devices:
        rec={"name":dev.name,"type":dev.type,"id":getattr(dev,"id",None)}
        use=(dev.type == backend)
        dev.use=use
        if use:
            enabled.append(rec)
    if not enabled:
        raise RuntimeError(f"No usable {backend} device enumerated; CPU fallback forbidden")
    scene.cycles.device='GPU'
    info["actual_mode"]="GPU"
    info["enabled_devices"]=enabled
    return info

scene=bpy.context.scene
scene.render.engine='CYCLES'
device_info=configure_cycles_device(scene)
scene.cycles.samples=int(os.environ.get("DIGE_SAMPLES_PREVIEW","128"))
scene.cycles.seed=int(os.environ.get("DIGE_RENDER_SEED","20260919"))
scene.cycles.use_denoising=True
scene.cycles.use_adaptive_sampling=True
scene.cycles.adaptive_threshold=.015
scene.cycles.max_bounces=12
scene.cycles.diffuse_bounces=4
scene.cycles.glossy_bounces=4
scene.cycles.transmission_bounces=8
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.render.resolution_percentage=100
scene.view_settings.look='AgX - Medium High Contrast'
vl=scene.view_layers[0]
vl.use_pass_normal=True; vl.use_pass_z=True; vl.use_pass_diffuse_color=True
vl.use_pass_glossy_direct=True; vl.use_pass_transmission_direct=True
if hasattr(vl,"cycles") and hasattr(vl.cycles,"use_pass_denoising_data"):
    vl.cycles.use_pass_denoising_data=True

# Distances inherit the latest provider-backed Drive sweep: V6C-122 fullbody=5.1m, hero=2.7m.
all_views=[
 ("01_FRONT50",(0,5.1,1.03),(0,0,.92),50,7.1,512,768),
 ("02_LEFT_PROFILE50",(5.1,0,1.08),(0,0,.98),50,7.1,512,768),
 ("03_THREE_QUARTER50",(3.60,3.60,1.10),(0,0,1.00),50,6.3,512,768),
 ("04_HERO85",(0,1.10,1.595),(0,.030,1.580),85,4.5,900,900),
 ("05_BACK_THREE_QUARTER50",(-3.60,-3.60,1.08),(0,0,1.00),50,6.3,512,768)
]
if RENDER_SET=="FULL":
    views=all_views
elif RENDER_SET=="HERO_ONLY":
    views=[v for v in all_views if v[0]=="04_HERO85"]
else:
    raise RuntimeError(f"Unsupported DIGE_RENDER_SET={RENDER_SET}")
outputs=[]
for vid,loc,target,lens,fstop,w,h in views:
    scene.render.resolution_x=w; scene.render.resolution_y=h
    aim(loc,target,lens,fstop)
    scene.render.image_settings.file_format='PNG'
    p=OUT/f"{vid}_V8.png"; scene.render.filepath=str(p)
    bpy.ops.render.render(write_still=True)
    outputs.append({"view":vid,"file":p.name,"sha256":sha(p),"lens_mm":lens,"fstop":fstop,"width":w,"height":h})

# Controlled same-seed hero A/B: RAW multilayer EXR vs denoised PNG at identical sample count.
hero_samples=int(os.environ.get("DIGE_SAMPLES_HERO","256"))
hero_seed=int(os.environ.get("DIGE_RENDER_SEED","20260919"))
aim((0,1.10,1.595),(0,.030,1.580),85,4.5)
scene.render.resolution_x=900; scene.render.resolution_y=900
scene.cycles.seed=hero_seed

scene.cycles.use_denoising=False; scene.cycles.samples=hero_samples
scene.render.image_settings.file_format='OPEN_EXR'; scene.render.image_settings.media_type='MULTI_LAYER_IMAGE'; scene.render.image_settings.color_depth='32'
raw=OUT/"04_HERO85_RAW_AOV_V8.exr"; scene.render.filepath=str(raw)
bpy.ops.render.render(write_still=True)

scene.cycles.use_denoising=True; scene.cycles.samples=hero_samples; scene.cycles.seed=hero_seed
scene.render.image_settings.media_type='IMAGE'; scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
denoised=OUT/"04_HERO85_DENOISED_V8.png"; scene.render.filepath=str(denoised)
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"DIGE_V8_scene.blend"))
receipt={
 "pipeline":"DIGE_V8_MAKEHUMAN_CYCLES",
 "state":"PATH_TRACED_CANDIDATE_EXECUTED",
 "blender_version":bpy.app.version_string,
 "engine":"CYCLES","device":device_info["actual_mode"],"device_info":device_info,
 "identity_bound":False,
 "render_set":RENDER_SET,
 "output_tag":OUTPUT_TAG or None,
 "canon_execution_manifest_sha256":CANON_SHA256,
 "runtime_commit":os.environ.get("DIGE_RUNTIME_COMMIT") or os.environ.get("GITHUB_SHA"),
 "runner":{"name":os.environ.get("RUNNER_NAME"),"os":os.environ.get("RUNNER_OS"),"arch":os.environ.get("RUNNER_ARCH")},
 "geometry_manifest_sha256":sha(RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json"),
 "geometry_source":"MakeHuman bundled CC0 base mesh + CC0 asian-female-young morph target",
 "garment_helper":geom["garment_helper"],
 "eye_helpers":geom["eye_helpers"],
 "landmark_binding_sha256":hashlib.sha256(json.dumps(geom["landmarks"],sort_keys=True).encode()).hexdigest(),
 "topology_metrics":topology,
 "craniofacial_runtime_deform":craniofacial_deform,
 "geometry_normalization":geom.get("normalization"),
 "hair_regime":hair_surface_contract["style"],
 "hair_surface_contract":hair_surface_contract,
 "appearance_candidate":"C8_CC0_TEXTURE_RANDOM_WALK_AREA_CLUMP_HAIR_V1",
 "appearance_selection":{
   "skin_sss_weight":SKIN_SSS_WEIGHT,
   "skin_sss_scale":SKIN_SSS_SCALE,
   "skin_roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX],
   "hair_regime":hair_surface_contract["style"],
   "hair_guide_sha256":geom["hair_guide"]["sha256"],
   "selection_basis":"C7_OFFICIAL_CC0_SKIN_PROBE_PASS; C5_MESO+WETLINE_RETAINED; C6_VERTEX_ROOT_COVERAGE_REJECTED; C8_AREA_SAMPLING+CLUMP"
 },
 "scalp_shadow_polygons":scalp_shadow_polygons,
 "drive_compute_priors":geom["drive_compute_priors"],
 "skin_albedo":skin_asset,
 "skin_model":{"subsurface_method":"RANDOM_WALK_SKIN","subsurface_weight":SKIN_SSS_WEIGHT,"subsurface_scale":SKIN_SSS_SCALE,"subsurface_anisotropy":SKIN_SSS_ANISO,"roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX],"micro_bump_scales":[115,560,1750]},
 "hair_curve_count":len(strands),
 "hair_guide":geom["hair_guide"],
 "provenance":{
   "source_pixels_used":False,
   "reference_pixels_read_by_renderer":False,
   "reference_images_composited":False,
   "reference_textures_used":False,
   "external_skin_texture_used":skin_asset["enabled"],
   "external_skin_texture_sha256":skin_asset["sha256"],
   "external_skin_texture_license":"CC0" if skin_asset["enabled"] else None,
   "external_skin_texture_pack_sha256":"7495ab99287053bd19ff1636114e64b608994d9f7437fea6cc75ea387f96dba9" if skin_asset["enabled"] else None,
   "external_geometry_asset_used":True,
   "external_geometry_asset_license":"CC0-1.0",
   "image_model_calls":0,
   "renderer_network_calls":0
 },
 "outputs":outputs,
 "denoise_ab":{"seed":hero_seed,"samples":hero_samples,"raw_aov":{"file":raw.name,"sha256":sha(raw)},"denoised":{"file":denoised.name,"sha256":sha(denoised)}},
 "scene_sha256":sha(OUT/"DIGE_V8_scene.blend"),
 "evidence_boundary":{"gpu_claim_requires_actual_mode_gpu":True,"hyperreal_certified":False,"identity_bound":False},
 "claim_ceiling":"PRODUCTION_TOPOLOGY_PLUS_CYCLES_PATH_TRACED_CANDIDATE; HYPERREAL_CERTIFICATION_REQUIRES_VISUAL_AND_LHYPER_AUDIT; DEUS_IDENTITY_NOT_BOUND"
}
(OUT/"DIGE_V8_RENDER_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
