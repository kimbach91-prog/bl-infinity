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
    set_input(bs,"Base Color",(0.43,0.205,0.135,1))
    set_input(bs,"IOR",1.42)
    set_input(bs,"Subsurface Weight",1.0)
    set_input(bs,"Subsurface Scale",0.008)
    if hasattr(bs,"subsurface_method"):
        bs.subsurface_method='RANDOM_WALK_SKIN'
    if hasattr(bs,"distribution"):
        bs.distribution='MULTI_GGX'

    macro=nt.nodes.new("ShaderNodeTexNoise")
    macro.inputs["Scale"].default_value=5.0
    macro.inputs["Detail"].default_value=2.0
    rough_map=nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value=0.0
    rough_map.inputs["From Max"].default_value=1.0
    rough_map.inputs["To Min"].default_value=0.38
    rough_map.inputs["To Max"].default_value=0.54
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
    bump.inputs["Strength"].default_value=.11
    bump.inputs["Distance"].default_value=.00028
    bump.inputs["Midlevel"].default_value=.5
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
    cu=bpy.data.curves.new(name,"CURVE"); cu.dimensions='3D'; cu.resolution_u=1
    cu.bevel_depth=bevel; cu.bevel_resolution=1; cu.fill_mode='FULL'
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob)
    for pts in splines:
        sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts): p.co=(*co,1.0)
    ob.data.materials.append(mat); return ob

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

skin=make_skin()
sclera=principled("SCLERA",(0.82,0.79,0.72),rough=.34,ior=1.38,subsurface=.04)
iris=principled("IRIS",(0.105,0.045,0.022),rough=.24,ior=1.40)
black=principled("BLACK",(0.005,0.004,0.004),rough=.28)
cornea=principled("CORNEA",(0.98,0.98,0.98),rough=.012,ior=1.376,transmission=1.0)
lip=principled("LIP",(0.31,0.075,0.065),rough=.34,ior=1.40,subsurface=.12)
hair=hair_material()
cloth=principled("CLOTH",(0.08,0.065,0.055),rough=.63,sheen=.28)
floor_mat=principled("FLOOR",(0.12,0.12,0.125),rough=.70)

mesh_path=RUNTIME/"dige_makehuman_v8.obj"
bpy.ops.wm.obj_import(filepath=str(mesh_path))
body=bpy.context.selected_objects[0]
body.name="DIGE_V8_MAKEHUMAN_BODY"
body.data.materials.append(skin)
bpy.ops.object.shade_smooth()
sub=body.modifiers.new("DIGE_V8_SUBDIV","SUBSURF"); sub.levels=1; sub.render_levels=1
# Preserve topology metrics before subdivision
bm=bmesh.new(); bm.from_mesh(body.data)
nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
boundary=sum(1 for e in bm.edges if e.is_boundary)
bm.free()
topology={"vertices":len(body.data.vertices),"polygons":len(body.data.polygons),"nonmanifold_edges":nonmanifold,"boundary_edges":boundary}

# Eyes: generic optical stack; identity-specific placement remains a later private gate.
eye_z=1.585; eye_y=.092
for sx in (-1,1):
    x=.0325*sx
    uv(f"SCLERA_{sx}",(x,eye_y,eye_z),(.0215,.0195,.021),sclera)
    cylinder(f"IRIS_{sx}",(x,eye_y+.0188,eye_z),.0088,.0015,iris)
    cylinder(f"PUPIL_{sx}",(x,eye_y+.0200,eye_z),.0032,.0012,black)
    uv(f"CORNEA_{sx}",(x,eye_y+.0030,eye_z),(.0222,.0212,.0212),cornea)
uv("UPPER_LIP",(0,.100,1.505),(.030,.0068,.0055),lip)
uv("LOWER_LIP",(0,.101,1.495),(.032,.0075,.0060),lip)

# Brows + lashes
brows=[]; lashes=[]
for sx in (-1,1):
    pts=[]
    for i in range(8):
        t=i/7; xx=sx*(.015+.038*t); zz=1.622+.004*math.sin(t*math.pi)
        pts.append((xx,.101,zz))
    brows.append(pts)
    for j in range(9):
        t=(j-4)/4; x=sx*(.0325+.014*t)
        lashes.append([(x,.111,1.592),(x+sx*.0015,.117,1.596+.0015*(1-abs(t)))])
curve_object("DIGE_V8_BROWS",brows,.0012,black)
curve_object("DIGE_V8_LASHES",lashes,.00034,black)

# Dense deterministic strand groom. Hair is an engine-evaluation groom, not canonical identity hair.
random.seed(20260919)
strands=[]
for i in range(3200):
    phi=random.uniform(-math.pi,math.pi)
    theta=random.uniform(.18,1.38)
    x=.091*math.sin(theta)*math.cos(phi)
    y=.090*math.sin(theta)*math.sin(phi)
    z=1.615+.105*math.cos(theta)
    if y>.052 and z<1.655: continue
    side=1 if x>=0 else -1
    L=random.uniform(.20,.48)
    strands.append([
      (x,y,z),
      (x*1.02,y-.010,z-L*.25),
      (x*1.06+side*random.uniform(0,.010),y-.020,z-L*.62),
      (x*1.10+side*random.uniform(0,.018),y-.028,z-L)
    ])
for i in range(180):
    phi=random.uniform(-math.pi,math.pi); theta=random.uniform(.22,1.15)
    x=.092*math.sin(theta)*math.cos(phi); y=.092*math.sin(theta)*math.sin(phi); z=1.615+.107*math.cos(theta)
    side=1 if x>=0 else -1
    strands.append([(x,y,z),(x+side*.014,y-.018,z+.012),(x+side*.032,y-.040,z-.050)])
curve_object("DIGE_V8_STRAND_GROOM",strands,.00038,hair)

# Simple cloth shell for modest full-body presentation; generated from primitives, not reference textures.
bpy.ops.mesh.primitive_uv_sphere_add(segments=80,ring_count=40,location=(0,0,1.05))
shirt=bpy.context.object; shirt.name="DIGE_V8_TOP"; shirt.scale=(.235,.145,.27)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); shirt.data.materials.append(cloth); bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_cone_add(vertices=96,radius1=.25,radius2=.17,depth=.42,location=(0,0,.72))
skirt=bpy.context.object; skirt.name="DIGE_V8_SKIRT"; skirt.data.materials.append(cloth); bpy.ops.object.shade_smooth()

bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.006))
floor=bpy.context.object; floor.data.materials.append(floor_mat)

def area(name,loc,energy,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; o.data.color=color
    d=Vector((0,0,1.25))-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    return o
area("KEY",(2.1,2.8,2.8),1100,2.3,(1.0,.88,.78))
area("FILL",(-2.0,2.1,1.8),360,2.7,(.72,.84,1.0))
area("RIM",(0,-2.3,2.5),520,1.6,(1.0,.72,.50))
area("FACE",(0,1.4,1.8),190,.9,(1.0,.91,.84))

world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(0.012,0.014,0.020,1); bg.inputs["Strength"].default_value=.14

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
scene.view_settings.look='Medium High Contrast'
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
 ("04_HERO85",(0,2.7,1.59),(0,.025,1.57),85,2.8,720,720),
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
aim((0,2.7,1.59),(0,.025,1.57),85,2.8)
scene.render.resolution_x=720; scene.render.resolution_y=720
scene.cycles.seed=hero_seed

scene.cycles.use_denoising=False; scene.cycles.samples=hero_samples
scene.render.image_settings.file_format='OPEN_EXR_MULTILAYER'; scene.render.image_settings.color_depth='32'
raw=OUT/"04_HERO85_RAW_AOV_V8.exr"; scene.render.filepath=str(raw)
bpy.ops.render.render(write_still=True)

scene.cycles.use_denoising=True; scene.cycles.samples=hero_samples; scene.cycles.seed=hero_seed
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
denoised=OUT/"04_HERO85_DENOISED_V8.png"; scene.render.filepath=str(denoised)
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"DIGE_V8_scene.blend"))
geom=json.loads((RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").read_text())
if geom.get("canon_execution_manifest_sha256") != CANON_SHA256:
    raise RuntimeError("geometry/canon manifest causal binding mismatch")
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
 "topology_metrics":topology,
 "drive_compute_priors":geom["drive_compute_priors"],
 "skin_model":{"subsurface_method":"RANDOM_WALK_SKIN","subsurface_weight":1.0,"subsurface_scale":0.008,"roughness_range":[0.38,0.54],"micro_bump_scales":[260,850]},
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
