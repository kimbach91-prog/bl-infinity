import bpy, math, json, hashlib, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
OUT=RUNTIME/"renders"
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    p=Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def set_input(node,name,value):
    sock=node.inputs.get(name)
    if sock is not None:
        sock.default_value=value

def add_noise_bump(mat, scale, strength, distance=0.1):
    nt=mat.node_tree
    bsdf=nt.nodes.get("Principled BSDF")
    noise=nt.nodes.new("ShaderNodeTexNoise")
    set_input(noise,"Scale",scale); set_input(noise,"Detail",3.0); set_input(noise,"Roughness",0.55)
    bump=nt.nodes.new("ShaderNodeBump")
    set_input(bump,"Strength",strength); set_input(bump,"Distance",distance)
    nt.links.new(noise.outputs.get("Fac"),bump.inputs.get("Height"))
    if bsdf and bsdf.inputs.get("Normal"):
        nt.links.new(bump.outputs.get("Normal"),bsdf.inputs.get("Normal"))

def principled(name, base, rough=.45, metallic=0.0, subsurface=0.0, ior=1.45, sheen=0.0, transmission=0.0, bump=None):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf,"Base Color",(*base,1)); set_input(bsdf,"Roughness",rough)
    set_input(bsdf,"Metallic",metallic); set_input(bsdf,"IOR",ior)
    set_input(bsdf,"Subsurface Weight",subsurface); set_input(bsdf,"Sheen Weight",sheen)
    set_input(bsdf,"Transmission Weight",transmission)
    if bsdf.inputs.get("Subsurface Scale"): bsdf.inputs["Subsurface Scale"].default_value=0.012
    if bump: add_noise_bump(m,*bump)
    return m

def hair_material():
    m=bpy.data.materials.new("DIGE_HAIR_PBR"); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    try:
        h=nt.nodes.new("ShaderNodeBsdfHairPrincipled")
        if h.inputs.get("Color"): h.inputs["Color"].default_value=(0.010,0.0065,0.0055,1)
        if h.inputs.get("Roughness"): h.inputs["Roughness"].default_value=.31
        if h.inputs.get("IOR"): h.inputs["IOR"].default_value=1.55
        if h.inputs.get("Random Roughness"): h.inputs["Random Roughness"].default_value=.05
        nt.links.new(h.outputs[0],out.inputs["Surface"])
    except Exception:
        h=nt.nodes.new("ShaderNodeBsdfPrincipled")
        set_input(h,"Base Color",(0.012,0.008,0.007,1)); set_input(h,"Roughness",.34)
        nt.links.new(h.outputs[0],out.inputs["Surface"])
    return m

def add_uv(name, loc, scale, mat, seg=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def add_cylinder(name, loc, radius, depth, mat, rot=(0,0,0), scale=(1,1,1)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=depth, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def add_cone(name, loc, r1, r2, depth, mat):
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=r1, radius2=r2, depth=depth, location=loc)
    o=bpy.context.object; o.name=name
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def curve_object(name, splines, bevel, mat):
    cu=bpy.data.curves.new(name,"CURVE"); cu.dimensions='3D'; cu.resolution_u=1
    cu.bevel_depth=bevel; cu.bevel_resolution=2; cu.fill_mode='FULL'
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob)
    for pts in splines:
        sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts): p.co=(*co,1.0)
    if mat: ob.data.materials.append(mat)
    return ob

def import_obj(path,name,mat):
    bpy.ops.wm.obj_import(filepath=str(path))
    o=bpy.context.selected_objects[0]; o.name=name
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    sub=o.modifiers.new("Subdivision","SUBSURF"); sub.levels=1; sub.render_levels=1
    return o

# Clean scene.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

skin=principled("DIGE_SKIN",(0.50,0.235,0.155),rough=.46,subsurface=.42,ior=1.42,bump=(260.0,.12,.0012))
lip=principled("DIGE_LIP",(0.31,0.060,0.060),rough=.36,subsurface=.18,ior=1.40,bump=(180.0,.08,.0007))
sclera=principled("DIGE_SCLERA",(0.78,0.72,0.64),rough=.36,subsurface=.05,ior=1.38,bump=(120.0,.025,.0003))
iris=principled("DIGE_IRIS",(0.085,0.036,0.017),rough=.27,ior=1.40,bump=(60.0,.06,.0004))
cornea=principled("DIGE_CORNEA",(0.98,0.98,0.98),rough=.018,ior=1.385,transmission=1.0)
cream=principled("DIGE_KNIT",(0.72,0.66,0.55),rough=.68,sheen=.25,bump=(105.0,.22,.0020))
dark=principled("DIGE_SKIRT",(0.025,0.021,0.030),rough=.52,sheen=.10,bump=(130.0,.12,.0012))
black=principled("DIGE_BLACK",(0.010,0.008,0.010),rough=.38)
hair=hair_material()

body=import_obj(RUNTIME/"dige_body_v53.obj","DIGE_BODY",skin)
head=import_obj(RUNTIME/"dige_head_v53.obj","DIGE_HEAD",skin)

# Eye stack: sclera + iris/pupil + clear cornea.
for side in (-1,1):
    x=.0365*side
    add_uv(f"SCLERA_{side}",(x,.079,1.516),(.0225,.0205,.0205),sclera,48,24)
    add_cylinder(f"IRIS_{side}",(x,.0975,1.516),.0086,.0015,iris,rot=(math.radians(90),0,0))
    add_cylinder(f"PUPIL_{side}",(x,.0986,1.516),.0031,.0010,black,rot=(math.radians(90),0,0))
    add_uv(f"CORNEA_{side}",(x,.0820,1.516),(.0234,.0225,.0225),cornea,48,24)

# Nose, lips, ears, brows.
add_uv("NOSE_BRIDGE",(0,.082,1.492),(.016,.028,.044),skin,48,24)
add_uv("NOSE_TIP",(0,.103,1.472),(.017,.018,.015),skin,48,24)
for sx in (-1,1):
    add_uv(f"EAR_{sx}",(sx*.087,-.002,1.510),(.014,.010,.032),skin,40,20)
add_uv("UPPER_LIP",(0,.092,1.438),(.030,.0065,.0052),lip,48,20)
add_uv("LOWER_LIP",(0,.093,1.428),(.032,.0070,.0058),lip,48,20)
brows=[]
for sx in (-1,1):
    pts=[]
    for i in range(8):
        t=i/7
        xx=sx*(.017+.040*t); zz=1.553+.0035*math.sin(t*math.pi); yy=.085
        pts.append((xx,yy,zz))
    brows.append(pts)
curve_object("DIGE_BROWS",brows,.0013,black)

# Eyelid arcs + lashes for contact cues.
lids=[]; lashes=[]
for sx in (-1,1):
    for upper in (True,False):
        pts=[]
        for j in range(11):
            t=(j-5)/5
            x=sx*(.0365+.021*t)
            z=1.516 + (0.0080 if upper else -0.0060)*(1-t*t)
            pts.append((x,.0990,z))
        lids.append(pts)
    for j in range(11):
        t=(j-5)/5
        x=sx*(.0365+.020*t)
        z=1.521+.006*(1-t*t)
        lashes.append([(x,.1005,z),(x+sx*.0018,.106,z+.0030)])
curve_object("DIGE_LIDS",lids,.00055,skin)
curve_object("DIGE_LASHES",lashes,.00035,black)

# Clothing shell.
add_uv("SWEATER_TORSO",(0,0,1.03),(.218,.139,.292),cream,64,32)
for sx in (-1,1):
    add_uv(f"SLEEVE_UP_{sx}",(sx*.221,0,1.15),(.100,.097,.235),cream,48,24)
    add_uv(f"SLEEVE_LOW_{sx}",(sx*.275,.010,.90),(.079,.075,.238),cream,48,24)
add_cone("PLEATED_SKIRT",(0,0,.69),.282,.200,.43,dark)
pleats=[]
for a in [i*math.tau/28 for i in range(28)]:
    pleats.append([(math.cos(a)*.200,math.sin(a)*.115,.905),(math.cos(a)*.282,math.sin(a)*.165,.475)])
curve_object("PLEAT_RIBS",pleats,.00085,dark)
for sx in (-1,1):
    add_uv(f"BOW_{sx}",(sx*.036,.143,1.287),(.043,.014,.023),black,32,16)
add_uv("BOW_KNOT",(0,.146,1.287),(.015,.012,.015),black,32,16)

# Deterministic hair groom: scalp roots, clumps, flyaways, no image texture.
random.seed(20260919)
strands=[]
for i in range(2100):
    phi=random.uniform(-math.pi,math.pi)
    theta=random.uniform(.10,1.42)
    x=.090*math.sin(theta)*math.cos(phi)
    y=.091*math.sin(theta)*math.sin(phi)
    z=1.505+.121*math.cos(theta)
    # Hairline gate: front-facing roots only high on forehead.
    if y>.030 and z<1.565:
        continue
    side=1 if x>=0 else -1
    L=random.uniform(.22,.52)
    clump=round((x+0.09)/0.025)*0.025
    p0=(x,y,z)
    p1=(x*.98 + 0.08*clump, y-.010, z-L*.28)
    p2=(x*1.05 + side*random.uniform(0,.010), y-.022, z-L*.64)
    p3=(x*1.10 + side*random.uniform(0,.018), y-.030, z-L)
    strands.append([p0,p1,p2,p3])
for i in range(120):
    phi=random.uniform(-math.pi,math.pi); theta=random.uniform(.18,1.18)
    x=.092*math.sin(theta)*math.cos(phi); y=.092*math.sin(theta)*math.sin(phi); z=1.505+.123*math.cos(theta)
    if y>.038 and z<1.575: continue
    side=1 if x>=0 else -1
    strands.append([(x,y,z),(x+side*.010,y-.016,z+.014),(x+side*.026,y-.038,z-.050)])
curve_object("DIGE_HAIR_STRANDS",strands,.00038,hair)

# Peach fuzz / vellus proxy on cheek/temple silhouette.
fuzz=[]
for side in (-1,1):
    for k in range(55):
        z=1.458 + 0.0022*k
        x=side*(.072 + .010*math.sin(k*.37))
        y=.062 + .008*math.cos(k*.41)
        fuzz.append([(x,y,z),(x+side*.0015,y+.002,z+.0025)])
curve_object("DIGE_VELLUS",fuzz,.00012,hair)

# Ground.
bpy.ops.mesh.primitive_plane_add(size=18, location=(0,0,-.032))
floor=bpy.context.object
floor.data.materials.append(principled("FLOOR",(0.16,0.145,0.13),rough=.74,bump=(14.0,.09,.006)))

# Finite area lighting.
def area(name,loc,energy,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object; o.name=name
    o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; o.data.color=color
    return o
key=area("KEY",(2.1,2.8,2.65),900,2.4,(1.0,.90,.82))
fill=area("FILL",(-2.2,1.9,1.85),260,2.8,(.72,.83,1.0))
rim=area("RIM",(0,-2.2,2.45),360,1.6,(1.0,.70,.52))
for o,target in [(key,Vector((0,0,1.38))),(fill,Vector((0,0,1.30))),(rim,Vector((0,0,1.48)))]:
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()

world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value=(0.020,0.022,0.028,1)
bg.inputs["Strength"].default_value=.15

# Camera.
bpy.ops.object.camera_add()
cam=bpy.context.object; bpy.context.scene.camera=cam; cam.data.sensor_width=36

def aim(loc,target,lens,fstop):
    cam.location=loc
    d=Vector(target)-cam.location
    cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens
    cam.data.dof.use_dof=True
    cam.data.dof.focus_distance=d.length
    cam.data.dof.aperture_fstop=fstop

scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=96
scene.cycles.use_adaptive_sampling=True
scene.cycles.adaptive_threshold=.010
scene.cycles.use_denoising=True
scene.cycles.max_bounces=12
scene.cycles.diffuse_bounces=4
scene.cycles.glossy_bounces=4
scene.cycles.transmission_bounces=8
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.render.film_transparent=False
scene.render.resolution_percentage=100
try:
    scene.view_settings.look='Medium High Contrast'
except Exception:
    pass

vl=scene.view_layers[0]
for attr in ("use_pass_normal","use_pass_z","use_pass_diffuse_color","use_pass_glossy_direct","use_pass_transmission_direct"):
    if hasattr(vl,attr): setattr(vl,attr,True)

views=[
 ("01_FRONT50",(0,4.55,1.04),(0,0,.94),50,7.1,512,768),
 ("02_LEFT_PROFILE50",(4.55,0,1.05),(0,0,.98),50,7.1,512,768),
 ("03_THREE_QUARTER50",(3.18,3.18,1.10),(0,0,1.00),50,6.3,512,768),
 ("04_HERO85",(0,2.35,1.515),(0,.01,1.510),85,2.6,640,640),
 ("05_BACK_THREE_QUARTER50",(-3.18,-3.18,1.08),(0,0,1.02),50,6.3,512,768)
]
outputs=[]
for vid,loc,target,lens,fstop,w,h in views:
    scene.render.resolution_x=w; scene.render.resolution_y=h
    aim(loc,target,lens,fstop)
    scene.render.image_settings.file_format='PNG'
    path=OUT/f"{vid}_V53.png"
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    outputs.append({"view":vid,"file":path.name,"sha256":sha(path),"lens_mm":lens,"fstop":fstop})

# Hero RAW/AOV source, denoise disabled.
scene.cycles.use_denoising=False
scene.cycles.samples=128
scene.cycles.adaptive_threshold=.007
scene.render.resolution_x=640; scene.render.resolution_y=640
aim((0,2.35,1.515),(0,.01,1.510),85,2.6)
scene.render.image_settings.file_format='OPEN_EXR'
scene.render.image_settings.color_depth='32'
raw=OUT/"04_HERO85_RAW_V53.exr"
scene.render.filepath=str(raw)
bpy.ops.render.render(write_still=True)

# Save scene state.
blend=OUT/"DIGE_V53_scene.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

manifest={
 "pipeline":"DIGE_V53_CYCLES_FROM_SCRATCH",
 "blender_version":bpy.app.version_string,
 "engine":"CYCLES",
 "device":"CPU",
 "samples_png":96,
 "samples_raw_hero":128,
 "raw_format":"OPEN_EXR_32F_COMBINED; pass flags retained in scene for next certification AOV gate",
 "adaptive_threshold_png":.010,
 "adaptive_threshold_raw":.007,
 "hair_strands":len(strands),
 "provenance":{
   "source_pixels_used":False,
   "reference_pixels_read_by_renderer":False,
   "texture_from_reference":False,
   "reference_images_composited":False,
   "image_model_calls":0,
   "renderer_network_calls":0
 },
 "outputs":outputs,
 "raw_hero":{"file":raw.name,"sha256":sha(raw)},
 "scene_sha256":sha(blend),
 "geometry_manifest_sha256":sha(RUNTIME/"geometry_manifest.json")
}
(OUT/"DIGE_V53_RENDER_RECEIPT.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,sort_keys=True))
