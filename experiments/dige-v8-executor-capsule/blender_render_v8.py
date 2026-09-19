import bpy, bmesh, math, json, hashlib, random, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
OUT=RUNTIME/"renders"
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

def make_skin():
    m=bpy.data.materials.new("DIGE_V8_SKIN")
    m.use_nodes=True
    nt=m.node_tree; bs=nt.nodes.get("Principled BSDF")
    set_input(bs,"Base Color",(0.30,0.115,0.072,1))
    set_input(bs,"IOR",1.42)
    set_input(bs,"Subsurface Weight",0.16)
    set_input(bs,"Subsurface Scale",0.0035)
    if hasattr(bs,"subsurface_method"):
        bs.subsurface_method='RANDOM_WALK_SKIN'
    if hasattr(bs,"distribution"):
        bs.distribution='MULTI_GGX'
    set_input(bs,"Subsurface Radius",(1.0,.45,.20))
    set_input(bs,"Specular IOR Level",.28)

    macro=nt.nodes.new("ShaderNodeTexNoise")
    macro.inputs["Scale"].default_value=5.0
    macro.inputs["Detail"].default_value=2.0
    tone=nt.nodes.new("ShaderNodeValToRGB")
    tone.color_ramp.elements[0].position=.20
    tone.color_ramp.elements[0].color=(0.255,0.090,0.058,1)
    tone.color_ramp.elements[1].position=.80
    tone.color_ramp.elements[1].color=(0.335,0.145,0.090,1)
    nt.links.new(macro.outputs["Fac"],tone.inputs["Fac"])
    nt.links.new(tone.outputs["Color"],bs.inputs["Base Color"])
    rough_map=nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value=0.0
    rough_map.inputs["From Max"].default_value=1.0
    rough_map.inputs["To Min"].default_value=0.46
    rough_map.inputs["To Max"].default_value=0.62
    nt.links.new(macro.outputs["Fac"],rough_map.inputs["Value"])
    nt.links.new(rough_map.outputs["Result"],bs.inputs["Roughness"])

    pore=nt.nodes.new("ShaderNodeTexNoise")
    pore.inputs["Scale"].default_value=260.0
    pore.inputs["Detail"].default_value=4.0
    pore.inputs["Roughness"].default_value=.62
    micro=nt.nodes.new("ShaderNodeTexNoise")
    micro.inputs["Scale"].default_value=850.0
    micro.inputs["Detail"].default_value=2.0
    pscale=nt.nodes.new("ShaderNodeMath"); pscale.operation='MULTIPLY'; pscale.inputs[1].default_value=.68
    mscale=nt.nodes.new("ShaderNodeMath"); mscale.operation='MULTIPLY'; mscale.inputs[1].default_value=.32
    mix=nt.nodes.new("ShaderNodeMath"); mix.operation='ADD'
    nt.links.new(pore.outputs["Fac"],pscale.inputs[0])
    nt.links.new(micro.outputs["Fac"],mscale.inputs[0])
    nt.links.new(pscale.outputs[0],mix.inputs[0]); nt.links.new(mscale.outputs[0],mix.inputs[1])
    bump=nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.075
    bump.inputs["Distance"].default_value=.00020
    nt.links.new(mix.outputs[0],bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m

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
        set_input(h,"Melanin",.78)
        set_input(h,"Melanin Redness",.18)
        set_input(h,"Random Color",.08)
        set_input(h,"Roughness",.28)
        set_input(h,"Radial Roughness",.34)
        set_input(h,"Random Roughness",.12)
        set_input(h,"Coat",.10)
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
        for p,co in zip(sp.bezier_points,pts):
            p.co=co
            p.handle_left_type='AUTO'
            p.handle_right_type='AUTO'
    ob.data.materials.append(mat); return ob

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

skin=make_skin()
sclera=principled("SCLERA",(0.58,0.52,0.48),rough=.30,ior=1.376,subsurface=.02)
iris=principled("IRIS",(0.070,0.026,0.012),rough=.32,ior=1.40)
iris_ring=principled("IRIS_RING",(0.012,0.005,0.003),rough=.34,ior=1.40)
black=principled("BLACK",(0.005,0.004,0.004),rough=.28)
cornea=principled("CORNEA",(0.92,0.92,0.92),rough=.008,ior=1.376,transmission=1.0)
lip=principled("LIP",(0.18,0.035,0.032),rough=.44,ior=1.40,subsurface=.04)
mouth_dark=principled("MOUTH_DARK",(0.018,0.004,0.004),rough=.58,ior=1.35)
scalp_mat=principled("SCALP_CAP_SURFACE",(0.012,0.005,0.003),rough=.52,ior=1.45)
hair=hair_material()
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
curve_object("DIGE_V8_MOUTH_GAP",[mouth_line],.00018,mouth_dark)

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
curve_object("DIGE_V8_BROWS",brow_hairs,.00015,hair)
curve_object("DIGE_V8_LASHES",lashes,.00013,black)

# Partial scalp cap hides root discontinuities while keeping forehead/face unobstructed.
eye_z=(landmarks["left_eye"]["center"][2]+landmarks["right_eye"]["center"][2])*.5
bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=48,location=(0,-.038,eye_z+.048))
scalp=bpy.context.object
scalp.name="DIGE_V8_SCALP_CAP"
scalp.scale=(.099,.079,.068)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bmcap=bmesh.new(); bmcap.from_mesh(scalp.data)
kill=[]
for v in bmcap.verts:
    wp=scalp.matrix_world @ v.co
    if wp.y>-.006 and wp.z<eye_z+.102:
        kill.append(v)
if kill:
    bmesh.ops.delete(bmcap,geom=kill,context='VERTS')
bmcap.to_mesh(scalp.data); bmcap.free()
scalp.data.materials.append(scalp_mat)
bpy.context.view_layer.objects.active=scalp
bpy.ops.object.shade_smooth()

# Swept-back deterministic groom. Long strands are limited to side/back; frontal roots remain short.
random.seed(20260919)
hair_box=landmarks["hair_helper"]
scalp_center=(0.0,-.034,eye_z+.050)
rx=min(.118,(hair_box["bbox_max"][0]-hair_box["bbox_min"][0])*.44)
ry=min(.092,(hair_box["bbox_max"][1]-hair_box["bbox_min"][1])*.34)
rz=.065
strands=[]
for i in range(2200):
    phi=random.uniform(-math.pi,math.pi)
    theta=random.uniform(.12,1.38)
    x=scalp_center[0]+rx*math.sin(theta)*math.cos(phi)
    y=scalp_center[1]+ry*math.sin(theta)*math.sin(phi)
    z=scalp_center[2]+rz*math.cos(theta)
    front_zone=(y>-.006 and abs(x)<.078)
    side=1 if x>=0 else -1
    if front_zone:
        continue
    L=random.uniform(.15,.37)
    strands.append([
        (x,y,z),
        (x*1.02,y-.012,z-L*.22),
        (x*1.05+side*random.uniform(0,.008),y-.025,z-L*.58),
        (x*1.08+side*random.uniform(0,.015),y-.035,z-L)
    ])
# Fine procedural hairline uses a separate, much thinner curve object to avoid visible root spikes.
hairline=[]
for i in range(420):
    t=(i+.5)/420
    x=-.082+.164*t
    xn=x/.082
    arch=max(0.0,1.0-xn*xn)
    root_y=-.002-.010*abs(xn)
    root_z=eye_z+.070+.020*arch
    side=1 if x>=0 else -1
    jitter=(random.random()-.5)*.0025
    hairline.append([
        (x,root_y,root_z),
        (x+side*.002+jitter,root_y-.018,root_z+.018),
        (x+side*.005+jitter,root_y-.040,root_z+.032)
    ])
curve_object("DIGE_V8_HAIRLINE",hairline,.000070,hair)

for i in range(90):
    phi=random.uniform(-math.pi,math.pi)
    theta=random.uniform(.18,1.15)
    x=scalp_center[0]+rx*math.sin(theta)*math.cos(phi)
    y=scalp_center[1]+ry*math.sin(theta)*math.sin(phi)
    z=scalp_center[2]+rz*math.cos(theta)
    if y>.006 and abs(x)<.068:
        continue
    side=1 if x>=0 else -1
    strands.append([(x,y,z),(x+side*.010,y-.018,z+.010),(x+side*.027,y-.038,z-.040)])
curve_object("DIGE_V8_STRAND_GROOM",strands,.00019,hair)

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
gsub=tights.modifiers.new("DIGE_V8_TIGHTS_SUBDIV","SUBSURF"); gsub.levels=1; gsub.render_levels=1
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
views=[
 ("01_FRONT50",(0,5.1,1.03),(0,0,.92),50,7.1,512,768),
 ("02_LEFT_PROFILE50",(5.1,0,1.08),(0,0,.98),50,7.1,512,768),
 ("03_THREE_QUARTER50",(3.60,3.60,1.10),(0,0,1.00),50,6.3,512,768),
 ("04_HERO85",(0,1.10,1.595),(0,.030,1.580),85,4.5,900,900),
 ("05_BACK_THREE_QUARTER50",(-3.60,-3.60,1.08),(0,0,1.00),50,6.3,512,768)
]
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
 "canon_execution_manifest_sha256":CANON_SHA256,
 "runtime_commit":os.environ.get("DIGE_RUNTIME_COMMIT") or os.environ.get("GITHUB_SHA"),
 "runner":{"name":os.environ.get("RUNNER_NAME"),"os":os.environ.get("RUNNER_OS"),"arch":os.environ.get("RUNNER_ARCH")},
 "geometry_manifest_sha256":sha(RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json"),
 "geometry_source":"MakeHuman bundled CC0 base mesh + CC0 asian-female-young morph target",
 "garment_helper":geom["garment_helper"],
 "eye_helpers":geom["eye_helpers"],
 "landmark_binding_sha256":hashlib.sha256(json.dumps(geom["landmarks"],sort_keys=True).encode()).hexdigest(),
 "topology_metrics":topology,
 "drive_compute_priors":geom["drive_compute_priors"],
 "skin_model":{"subsurface_method":"RANDOM_WALK_SKIN","subsurface_weight":0.16,"subsurface_scale":0.0035,"roughness_range":[0.46,0.62],"micro_bump_scales":[260,850]},
 "hair_curve_count":len(strands),
 "provenance":{
   "source_pixels_used":False,
   "reference_pixels_read_by_renderer":False,
   "reference_images_composited":False,
   "reference_textures_used":False,
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
