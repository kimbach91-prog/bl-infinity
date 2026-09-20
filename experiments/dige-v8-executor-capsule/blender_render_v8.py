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
SKIN_ALBEDO_NAME=os.environ.get("DIGE_SKIN_ALBEDO_NAME","onlytheghosts_young_eurasian_female").strip()
SKIN_ALBEDO_SAT=float(os.environ.get("DIGE_SKIN_ALBEDO_SAT","0.92"))
SKIN_ALBEDO_VALUE=float(os.environ.get("DIGE_SKIN_ALBEDO_VALUE","0.74"))
EYE_TEX_SAT=float(os.environ.get("DIGE_EYE_TEX_SAT","1.0"))
EYE_TEX_VALUE=float(os.environ.get("DIGE_EYE_TEX_VALUE","1.0"))
HAIR_TEX_SAT=float(os.environ.get("DIGE_HAIR_TEX_SAT","1.0"))
HAIR_TEX_VALUE=float(os.environ.get("DIGE_HAIR_TEX_VALUE","1.0"))
FACE_MESO_SCALE=float(os.environ.get("DIGE_FACE_MESO_SCALE","1.0"))
SKIN_TONE_R=float(os.environ.get("DIGE_SKIN_TONE_R","0.86"))
SKIN_TONE_G=float(os.environ.get("DIGE_SKIN_TONE_G","0.72"))
SKIN_TONE_B=float(os.environ.get("DIGE_SKIN_TONE_B","0.66"))
SKIN_TONE_MIX=float(os.environ.get("DIGE_SKIN_TONE_MIX","0.32"))
SKIN_MICRO_STRENGTH=float(os.environ.get("DIGE_SKIN_MICRO_STRENGTH","0.12"))
RENDER_SET=os.environ.get("DIGE_RENDER_SET","FULL").strip().upper()
HAIR_ASSET_KEY=os.environ.get("DIGE_HAIR_ASSET_KEY",CANON["assets"]["system_assets_c12"].get("hair_default_key","hair_short03")).strip()

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
        "asset_name":SKIN_ALBEDO_NAME,
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
        grade.inputs["Saturation"].default_value=SKIN_ALBEDO_SAT
        grade.inputs["Value"].default_value=SKIN_ALBEDO_VALUE
        nt.links.new(albedo.outputs["Color"],grade.inputs["Color"])
        skin_tone=nt.nodes.new("ShaderNodeRGB")
        skin_tone.outputs[0].default_value=(SKIN_TONE_R,SKIN_TONE_G,SKIN_TONE_B,1)
        warm_mix=nt.nodes.new("ShaderNodeMixRGB")
        warm_mix.blend_type='MULTIPLY'
        warm_mix.inputs["Fac"].default_value=SKIN_TONE_MIX
        nt.links.new(grade.outputs["Color"],warm_mix.inputs[1])
        nt.links.new(skin_tone.outputs["Color"],warm_mix.inputs[2])
        color_mix=nt.nodes.new("ShaderNodeMixRGB")
        color_mix.blend_type='MULTIPLY'
        color_mix.inputs["Fac"].default_value=.10
        nt.links.new(warm_mix.outputs["Color"],color_mix.inputs[1])
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
    bump.inputs["Strength"].default_value=SKIN_MICRO_STRENGTH
    bump.inputs["Distance"].default_value=.00012
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


def verify_asset(path,expected_sha256):
    p=Path(path)
    if not p.exists():
        raise RuntimeError(f"Required C12 system asset missing: {p}")
    got=sha(p)
    if got != expected_sha256:
        raise RuntimeError(f"C12 system asset hash drift: {p.name} expected={expected_sha256} got={got}")
    return p

def parse_mhclo(path):
    spec={"x_scale":None,"y_scale":None,"z_scale":None,"verts":{}}
    status=None
    first=0
    vn=0
    for raw in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
        words=raw.split()
        if not words:
            continue
        if words[0].startswith("#"):
            continue
        if status=="verts":
            # Official MHCLO files may place metadata such as "material" after
            # the verts marker and before the first numeric mapping (short04 does).
            # Keep the verts section armed until the first mapping arrives; only
            # close it on a non-numeric directive after mappings have started.
            if words[0].lstrip("-").isdigit():
                idx=first+vn
                if len(words)==1:
                    v=int(words[0])
                    spec["verts"][idx]=((v,v,v),(1.0,0.0,0.0),(0.0,0.0,0.0))
                else:
                    v0,v1,v2=(int(words[0]),int(words[1]),int(words[2]))
                    w0,w1,w2=(float(words[3]),float(words[4]),float(words[5]))
                    d0,d1,d2=(float(words[6]),float(words[7]),float(words[8]))
                    # Official MakeClothes importer converts MakeHuman offsets to Blender as (d0,-d2,d1).
                    spec["verts"][idx]=((v0,v1,v2),(w0,w1,w2),(d0,-d2,d1))
                vn+=1
                continue
            elif vn>0:
                status=None
        key=words[0]
        if key in ("x_scale","y_scale","z_scale"):
            spec[key]=(int(words[1]),int(words[2]),float(words[3]))
        elif key=="verts":
            first=int(words[1]) if len(words)>1 else 0
            vn=0
            status="verts"
    if not spec["verts"]:
        raise RuntimeError(f"C12 MHCLO has no vertex mappings: {path}")
    if spec["x_scale"] is None or spec["y_scale"] is None or spec["z_scale"] is None:
        raise RuntimeError(f"C12 MHCLO missing scale contract: {path}")
    return spec

def fit_mhclo_asset(name,obj_path,mhclo_path,fit_vertices,material,contract):
    obj_path=verify_asset(obj_path,contract["obj"]["sha256"])
    mhclo_path=verify_asset(mhclo_path,contract["mhclo"]["sha256"])
    spec=parse_mhclo(mhclo_path)
    bpy.ops.wm.obj_import(
        filepath=str(obj_path),
        forward_axis='Y',
        up_axis='Z',
        use_split_objects=False,
        use_split_groups=False,
    )
    imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
    if len(imported)!=1:
        raise RuntimeError(f"C12 expected one imported mesh for {name}, got {len(imported)}")
    obj=imported[0]
    obj.name=name
    expected=contract["obj"]["vertices"]
    if len(obj.data.vertices)!=expected:
        raise RuntimeError(f"C12 {name} vertex count drift: expected={expected} got={len(obj.data.vertices)}")
    if len(spec["verts"])!=expected or min(spec["verts"])!=0 or max(spec["verts"])!=expected-1:
        raise RuntimeError(f"C12 {name} MHCLO mapping range drift: count={len(spec['verts'])} min={min(spec['verts'])} max={max(spec['verts'])}")
    if not obj.data.uv_layers:
        raise RuntimeError(f"C12 {name} has no UV layer after OBJ import")

    hverts=fit_vertices
    hl=len(hverts)
    xs,ys,zs=spec["x_scale"],spec["y_scale"],spec["z_scale"]
    for pair in (xs,ys,zs):
        if pair[0]>=hl or pair[1]>=hl or pair[2]==0:
            raise RuntimeError(f"C12 {name} MHCLO scale reference invalid: {pair} body_vertices={hl}")
    s0=abs(hverts[xs[0]].x-hverts[xs[1]].x)/xs[2]
    # MakeClothes Blender importer maps y_scale to Blender Z and z_scale to Blender Y.
    s2=abs(hverts[ys[0]].z-hverts[ys[1]].z)/ys[2]
    s1=abs(hverts[zs[0]].y-hverts[zs[1]].y)/zs[2]
    scales=(s0,s1,s2)

    for n in range(expected):
        refs,weights,offset=spec["verts"][n]
        if max(refs)>=hl:
            raise RuntimeError(f"C12 {name} MHCLO ref outside body: {refs} body_vertices={hl}")
        co=(
            hverts[refs[0]]*weights[0] +
            hverts[refs[1]]*weights[1] +
            hverts[refs[2]]*weights[2] +
            Vector((offset[0]*s0,offset[1]*s1,offset[2]*s2))
        )
        obj.data.vertices[n].co=co

    obj.data.materials.clear()
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.shade_smooth()
    pts=[obj.matrix_world @ v.co for v in obj.data.vertices]
    mi=[min(p[i] for p in pts) for i in range(3)]
    ma=[max(p[i] for p in pts) for i in range(3)]
    return obj,{
        "name":name,
        "obj_sha256":sha(obj_path),
        "mhclo_sha256":sha(mhclo_path),
        "vertices":len(obj.data.vertices),
        "polygons":len(obj.data.polygons),
        "uv_layers":len(obj.data.uv_layers),
        "fit_scales":scales,
        "bbox_min":mi,
        "bbox_max":ma,
        "fit_algorithm":"MAKEHUMAN_MHCLO_BARYCENTRIC_OFFSETS_SCALED",
    }

def alpha_card_material(name,image_path,expected_sha256,rough=.42,ior=1.50,anisotropy=.0,sat=1.0,value=1.0,spec=.28,coat=.025):
    image_path=verify_asset(image_path,expected_sha256)
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    tex=nt.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(image_path),check_existing=True)
    try: tex.image.colorspace_settings.name='sRGB'
    except Exception: pass
    tex.interpolation='Linear'
    trans=nt.nodes.new("ShaderNodeBsdfTransparent")
    bs=nt.nodes.new("ShaderNodeBsdfPrincipled")
    set_input(bs,"Roughness",rough); set_input(bs,"IOR",ior)
    set_input(bs,"Specular IOR Level",spec)
    set_input(bs,"Anisotropic IOR Level",anisotropy)
    set_input(bs,"Coat Weight",coat)
    grade=nt.nodes.new("ShaderNodeHueSaturation")
    grade.inputs["Saturation"].default_value=sat
    grade.inputs["Value"].default_value=value
    nt.links.new(tex.outputs["Color"],grade.inputs["Color"])
    nt.links.new(grade.outputs["Color"],bs.inputs["Base Color"])
    mix=nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Alpha"],mix.inputs[0])
    nt.links.new(trans.outputs[0],mix.inputs[1])
    nt.links.new(bs.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],out.inputs["Surface"])
    return m

def eye_texture_material(name,image_path,expected_sha256):
    image_path=verify_asset(image_path,expected_sha256)
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    tex=nt.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(image_path),check_existing=True)
    try: tex.image.colorspace_settings.name='sRGB'
    except Exception: pass
    tex.interpolation='Linear'
    base=nt.nodes.new("ShaderNodeBsdfPrincipled")
    set_input(base,"Roughness",.24); set_input(base,"IOR",1.376)
    set_input(base,"Specular IOR Level",.34)
    set_input(base,"Subsurface Weight",.012)
    eye_grade=nt.nodes.new("ShaderNodeHueSaturation")
    eye_grade.inputs["Saturation"].default_value=EYE_TEX_SAT
    eye_grade.inputs["Value"].default_value=EYE_TEX_VALUE
    nt.links.new(tex.outputs["Color"],eye_grade.inputs["Color"])
    nt.links.new(eye_grade.outputs["Color"],base.inputs["Base Color"])
    glass=nt.nodes.new("ShaderNodeBsdfGlass")
    set_input(glass,"Roughness",.012); set_input(glass,"IOR",1.376)
    mix=nt.nodes.new("ShaderNodeMixShader")
    # Opaque texels are sclera/iris; transparent texels become refractive cornea.
    nt.links.new(tex.outputs["Alpha"],mix.inputs[0])
    nt.links.new(glass.outputs[0],mix.inputs[1])
    nt.links.new(base.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],out.inputs["Surface"])
    return m


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
  "alar_groove_y_m":0.00075,
  "labiomental_groove_y_m":0.00070,
  "lip_corner_y_m":0.00045,
  "lower_lid_roll_y_m":0.00050,
}
# FACE_MESO_SCALE_APPLIED
for _k in ("cheek_y_m","nose_bridge_y_m","nose_tip_y_m","chin_y_m","lip_volume_y_m","brow_ridge_y_m","tear_trough_y_m","nasolabial_y_m","philtrum_groove_y_m","philtrum_ridge_y_m","alar_groove_y_m","labiomental_groove_y_m","lip_corner_y_m","lower_lid_roll_y_m"):
    craniofacial_deform[_k] *= FACE_MESO_SCALE
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
    co.y -= craniofacial_deform["alar_groove_y_m"]*(
        g2(co.x,co.z,.013,nose_tip_z-.004,.007,.010)+
        g2(co.x,co.z,-.013,nose_tip_z-.004,.007,.010)
    )
    co.y -= craniofacial_deform["labiomental_groove_y_m"]*g2(co.x,co.z,0.0,mouth_z-.018,.026,.008)
    co.y -= craniofacial_deform["lip_corner_y_m"]*(
        g2(co.x,co.z,.023,mouth_z,.007,.008)+
        g2(co.x,co.z,-.023,mouth_z,.007,.008)
    )
    co.y += craniofacial_deform["lower_lid_roll_y_m"]*(
        g2(co.x,co.z,.032,eye_mid_z-.006,.022,.008)+
        g2(co.x,co.z,-.032,eye_mid_z-.006,.022,.008)
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

# C12 full normalized hm08 fit reference emitted by the builder.
fit_ref_meta=geom["fit_reference"]
fit_ref_path=RUNTIME/fit_ref_meta["output"]
if not fit_ref_path.exists() or sha(fit_ref_path)!=fit_ref_meta["sha256"]:
    raise RuntimeError("C12 fit-reference missing/hash mismatch")
fit_payload=json.loads(fit_ref_path.read_text(encoding="utf-8"))
fit_vertices=[Vector(v) for v in fit_payload["vertices"]]
if len(fit_vertices)!=fit_ref_meta["vertices"]:
    raise RuntimeError(f"C12 fit-reference vertex-count drift: expected={fit_ref_meta['vertices']} got={len(fit_vertices)}")
if len(fit_vertices) < len(body.data.vertices):
    raise RuntimeError("C12 fit-reference shorter than compact body")
# Preserve runtime craniofacial meso deformation on the body prefix while retaining normalized helper vertices.
for i,v in enumerate(body.data.vertices):
    fit_vertices[i]=v.co.copy()

# C12: replace proxy helper eyes + flat iris discs with the official high-poly hm08 eye asset.
system_contract=CANON["assets"]["system_assets_c12"]
system_dir=RUNTIME/"system_assets"
system_asset_fits={}
eye_asset=system_contract["high_poly_eyes"]
eye_mat=eye_texture_material(
    "DIGE_C12_HIGH_POLY_EYE",
    system_dir/eye_asset["diffuse"]["runtime_name"],
    eye_asset["diffuse"]["sha256"],
)
eye_obj,eye_fit=fit_mhclo_asset(
    "DIGE_C12_HIGH_POLY_EYES",
    system_dir/eye_asset["obj"]["runtime_name"],
    system_dir/eye_asset["mhclo"]["runtime_name"],
    fit_vertices,eye_mat,eye_asset,
)
system_asset_fits["high_poly_eyes"]=eye_fit

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
curve_object("DIGE_V8_UPPER_LIP_TINT",[upper_lip],.00010,lip)
curve_object("DIGE_V8_LOWER_LIP_TINT",[lower_lip],.00013,lip)

# Small recessed nostril discs add depth without altering topology.
nose_z=mouth_center[2]+.0275
nose_y=mouth_center[1]+.0030
for sx in (-1,1):
    cylinder(f"NOSTRIL_{sx}",(sx*.0065,nose_y,nose_z),.00145,.00022,mouth_dark)

# C12: official system eyebrow/eyelash cards fitted through their hm08 MHCLO mappings.
brow_asset=system_contract["eyebrow001"]
brow_mat=alpha_card_material(
    "DIGE_C12_EYEBROW001",
    system_dir/brow_asset["diffuse"]["runtime_name"],
    brow_asset["diffuse"]["sha256"],
    rough=.52,ior=1.46,anisotropy=.15,
)
brow_obj,brow_fit=fit_mhclo_asset(
    "DIGE_C12_EYEBROW001",
    system_dir/brow_asset["obj"]["runtime_name"],
    system_dir/brow_asset["mhclo"]["runtime_name"],
    fit_vertices,brow_mat,brow_asset,
)
system_asset_fits["eyebrow001"]=brow_fit

lash_asset=system_contract["eyelashes01"]
lash_mat=alpha_card_material(
    "DIGE_C12_EYELASHES01",
    system_dir/lash_asset["diffuse"]["runtime_name"],
    lash_asset["diffuse"]["sha256"],
    rough=.48,ior=1.46,anisotropy=.25,
)
lash_obj,lash_fit=fit_mhclo_asset(
    "DIGE_C12_EYELASHES01",
    system_dir/lash_asset["obj"]["runtime_name"],
    system_dir/lash_asset["mhclo"]["runtime_name"],
    fit_vertices,lash_mat,lash_asset,
)
system_asset_fits["eyelashes01"]=lash_fit

# Preserve C5 tear meniscus: it is landmark-bound and complements the high-poly eye asset.
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

# C17: keep the exact fitted short03 asset only as a non-rendered groom guide, then
# materialize real Blender Hair Curves. This moves the realism bottleneck from alpha-card
# silhouette swaps to strand geometry + Principled Hair BSDF + Cycles 3D curves.
if HAIR_ASSET_KEY not in system_contract or not HAIR_ASSET_KEY.startswith("hair_short"):
    raise RuntimeError(f"Unsupported DIGE_HAIR_ASSET_KEY={HAIR_ASSET_KEY}")
hair_asset=system_contract[HAIR_ASSET_KEY]
hair_label=HAIR_ASSET_KEY.replace("hair_","").upper()
hair_guide_mat=alpha_card_material(
    f"DIGE_C17_GUIDE_{hair_label}",
    system_dir/hair_asset["diffuse"]["runtime_name"],
    hair_asset["diffuse"]["sha256"],
    rough=.54,ior=1.55,anisotropy=.34,sat=HAIR_TEX_SAT,value=HAIR_TEX_VALUE,spec=.16,coat=.004,
)
hair_obj,hair_fit=fit_mhclo_asset(
    f"DIGE_C17_GUIDE_{hair_label}",
    system_dir/hair_asset["obj"]["runtime_name"],
    system_dir/hair_asset["mhclo"]["runtime_name"],
    fit_vertices,hair_guide_mat,hair_asset,
)
system_asset_fits[HAIR_ASSET_KEY]=hair_fit

def build_c17_strand_groom(guide_obj, surface_obj, material):
    # C17.1 repair: the fitted short03 shell is a STYLE/VOLUME GUIDE, not a root emitter.
    # Roots must live on the scalp surface; otherwise guide-shell vertices leave the
    # frontal/crown scalp uncovered (the C17 visual-audit scar).
    guide_obj.data.update()
    surface_obj.data.update()
    rng=random.Random(20260920)

    guide_rot=guide_obj.matrix_world.to_3x3()
    guide_samples=[]
    for idx,v in enumerate(guide_obj.data.vertices):
        p=guide_obj.matrix_world @ v.co
        if p.z < 1.495 or p.z > 1.715:
            continue
        n=(guide_rot @ v.normal).normalized()
        if n.length < 1e-8:
            n=Vector((0,0,1))
        guide_samples.append((idx,p,n))
    if len(guide_samples) < 500:
        raise RuntimeError(f"C17 fitted guide too sparse: {len(guide_samples)} samples")

    surface_rot=surface_obj.matrix_world.to_3x3()
    scalp_candidates=[]
    for idx,v in enumerate(surface_obj.data.vertices):
        p=surface_obj.matrix_world @ v.co
        # Anatomical scalp mask in the frozen C16 body frame.
        if p.z < 1.540 or p.z > 1.706:
            continue
        if abs(p.x) > .130 or p.y > .065:
            continue
        # Preserve a human frontal/temporal hairline instead of seeding the face.
        if p.y > .025:
            hairline_z=1.605-0.18*min(abs(p.x),.10)
            if p.z < hairline_z:
                continue
        n=(surface_rot @ v.normal).normalized()
        if n.length < 1e-8:
            n=Vector((0,0,1))
        scalp_candidates.append((idx,p,n))
    if len(scalp_candidates) < 350:
        raise RuntimeError(f"C17 scalp mask too sparse: {len(scalp_candidates)} roots")

    # Keep runtime bounded and deterministic while distributing roots across the
    # entire scalp. Even sampling by sorted mesh index avoids stochastic holes.
    target_roots=1400
    if len(scalp_candidates) > target_roots:
        roots=[]
        for i in range(target_roots):
            roots.append(scalp_candidates[min(len(scalp_candidates)-1,int(i*len(scalp_candidates)/target_roots))])
    else:
        roots=scalp_candidates

    # Nearest fitted guide-shell point gives each scalp root a local style/volume
    # target. This is the mature guide-field idea: surface roots + interpolated guide.
    root_guides=[]
    for root_index,root,n in roots:
        nearest=None
        best_d2=None
        for guide_index,gp,gn in guide_samples:
            d=(gp-root)
            d2=d.length_squared
            if best_d2 is None or d2 < best_d2:
                best_d2=d2
                nearest=(guide_index,gp,gn)
        guide_index,gp,gn=nearest
        shell=(gp-root)
        shell_len=shell.length
        if shell_len < 1e-6:
            shell=n.copy()
            shell_len=.035
        else:
            shell.normalize()
        root_guides.append((root_index,root,n,guide_index,gp,gn,shell,shell_len))

    points_per_curve=8
    # C17.2 density repair: one scalp mesh root must emit many child fibers.
    # 25k-class curves is still far below real human hair count, but removes the
    # sparse porcupine regime while keeping the CPU canary bounded.
    strands_per_root=18
    curve_count=len(root_guides)*strands_per_root
    hair_data=bpy.data.hair_curves.new("DIGE_C17_STRAND_GROOM_DATA")
    hair_data.add_curves([points_per_curve]*curve_count)
    try:
        hair_data.set_types(type='CATMULL_ROM')
    except Exception:
        pass
    hair_data.surface=surface_obj
    hair_data.materials.append(material)

    positions=[]
    radii=[]
    center=Vector((0.0,-0.030,1.610))
    base_radius=0.000050
    tip_radius=0.000009
    for root_index,root,n,guide_index,gp,gn,shell,shell_len in root_guides:
        radial=(root-center)
        if radial.length < 1e-8:
            radial=Vector((0,0,1))
        radial.normalize()
        side=Vector((1.0 if root.x>=0 else -1.0,0.0,0.0))
        back=Vector((0.0,-1.0,0.0))
        down=Vector((0.0,0.0,-1.0))
        crown=max(0.0,min(1.0,(root.z-1.55)/0.15))

        # Mature groom principle: hair leaves the scalp approximately tangent,
        # then gravity/back sweep shapes the strand. The fitted guide contributes a
        # local style field, but may not turn the strand into a radial spike.
        desired=down*.78 + back*.52 + side*.10
        tangent_flow=desired - n*desired.dot(n)
        if tangent_flow.length < 1e-8:
            tangent_flow=back - n*back.dot(n)
        if tangent_flow.length < 1e-8:
            tangent_flow=side.copy()
        tangent_flow.normalize()

        guide_tangent=shell - n*shell.dot(n)
        if guide_tangent.length > 1e-8:
            guide_tangent.normalize()
        else:
            guide_tangent=tangent_flow.copy()
        base_flow=(tangent_flow*.80 + guide_tangent*.14 + n*.06).normalized()
        tangent_cross=n.cross(tangent_flow)
        if tangent_cross.length < 1e-8:
            tangent_cross=side.copy()
        tangent_cross.normalize()

        cluster_phase=((guide_index*31 + root_index*7) % 97)/97.0*math.tau
        clump_bias=Vector((math.cos(cluster_phase),math.sin(cluster_phase)*.20,-.08)).normalized()

        # Short-hair envelope: denser child fibers, shorter/tangential trajectories.
        envelope=max(.045,min(.082,shell_len*.55+.042))
        for k in range(strands_per_root):
            root_j=(
                root + n*0.00045
                + tangent_flow*rng.uniform(-.0026,.0026)
                + tangent_cross*rng.uniform(-.0026,.0026)
            )
            flow=(base_flow + clump_bias*rng.uniform(.008,.028)).normalized()
            length=envelope*rng.uniform(.88,1.12)
            lateral=(tangent_cross*rng.uniform(-1,1) + tangent_flow*rng.uniform(-.25,.25))
            if lateral.length < 1e-8:
                lateral=tangent_cross.copy()
            lateral.normalize()
            amp=rng.uniform(.0005,.0020)
            lift=rng.uniform(.0015,.0045)
            for j in range(points_per_curve):
                t=j/(points_per_curve-1)
                bend=math.sin(math.pi*t)
                sag=t*t
                # Hug the scalp at the root, lift into the guide volume, then settle.
                p=(
                    root_j
                    + flow*(length*t)
                    + n*(lift*bend)
                    + lateral*(amp*bend)
                    + down*(length*.055*sag)
                )
                positions.extend((p.x,p.y,p.z))
                r=(base_radius*(1.0-t) + tip_radius*t) * rng.uniform(.92,1.08)
                radii.append(r)

    pos=hair_data.attributes["position"]
    pos.data.foreach_set("vector",positions)
    radius_attr=hair_data.attributes.get("radius")
    if radius_attr is None:
        radius_attr=hair_data.attributes.new("radius",'FLOAT','POINT')
    radius_attr.data.foreach_set("value",radii)

    groom=bpy.data.objects.new("DIGE_C17_STRAND_GROOM",hair_data)
    bpy.context.collection.objects.link(groom)
    guide_obj.hide_render=True
    try:
        guide_obj.hide_set(True)
    except Exception:
        pass
    return groom,{
        "root_count":len(root_guides),
        "scalp_candidate_count":len(scalp_candidates),
        "guide_sample_count":len(guide_samples),
        "strands_per_root":strands_per_root,
        "curve_count":curve_count,
        "points_per_curve":points_per_curve,
        "point_count":curve_count*points_per_curve,
        "root_radius_m":base_radius,
        "tip_radius_m":tip_radius,
        "guide_mesh_rendered":False,
        "blender_datablock":"HAIR_CURVES",
        "curve_type":"CATMULL_ROM",
        "surface_bound":True,
        "distribution":"SCALP_SURFACE_ROOTS_DENSE_TANGENT_GUIDE_FIELD_C17_2",
        "coverage_mask":"SCALP_Z1P540_1P706_YLE0P065_FRONTAL_HAIRLINE",
        "seed":20260920,
    }

hair_groom,hair_curve_metrics=build_c17_strand_groom(hair_obj,body,hair)
strands=[None]*hair_curve_metrics["curve_count"]
hair_surface_contract={
    "root_source":"SCALP_SURFACE_ROOTS_PLUS_OFFICIAL_MAKEHUMAN_HM08_GUIDE_FIELD",
    "asset_key":HAIR_ASSET_KEY,
    "asset":HAIR_ASSET_KEY.replace("hair_",""),
    "asset_tags":hair_asset["tags"],
    "obj_sha256":hair_asset["obj"]["sha256"],
    "mhclo_sha256":hair_asset["mhclo"]["sha256"],
    "diffuse_sha256":hair_asset["diffuse"]["sha256"],
    "guide_vertices":hair_fit["vertices"],
    "guide_polygons":hair_fit["polygons"],
    "mass_mesh_rendered":False,
    "curve_count":hair_curve_metrics["curve_count"],
    "point_count":hair_curve_metrics["point_count"],
    "points_per_curve":hair_curve_metrics["points_per_curve"],
    "root_radius_m":hair_curve_metrics["root_radius_m"],
    "tip_radius_m":hair_curve_metrics["tip_radius_m"],
    "surface_bound":hair_curve_metrics["surface_bound"],
    "distribution":hair_curve_metrics["distribution"],
    "seed":hair_curve_metrics["seed"],
    "style":"HAIR_CURVES_GUIDE_INTERPOLATED_C17_V1",
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
# C17 close-up hair certification uses geometric strand cylinders so radius is physical.
try:
    scene.render.hair_type='CYLINDER'
    scene.render.hair_subdiv=1
except Exception:
    pass
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
 "system_asset_pack":{
   "source_page":system_contract["source_page"],
   "pack_sha256":system_contract["pack_sha256"],
   "license":system_contract["license"],
   "probe_run":system_contract["probe_run"],
   "probe_artifact_id":system_contract["probe_artifact_id"]
 },
 "system_asset_fits":system_asset_fits,
 "fit_reference":{
   "vertices":fit_ref_meta["vertices"],
   "sha256":fit_ref_meta["sha256"],
   "body_prefix_overridden_vertices":len(body.data.vertices),
   "coordinate_system":fit_ref_meta["coordinate_system"]
 },
 "eye_helpers":geom["eye_helpers"],
 "landmark_binding_sha256":hashlib.sha256(json.dumps(geom["landmarks"],sort_keys=True).encode()).hexdigest(),
 "topology_metrics":topology,
 "craniofacial_runtime_deform":craniofacial_deform,
 "geometry_normalization":geom.get("normalization"),
 "hair_regime":hair_surface_contract["style"],
 "hair_surface_contract":hair_surface_contract,
 "appearance_candidate":"C17_MATURE_STRAND_GROOM_OVER_C16_V1",
 "appearance_selection":{
   "skin_sss_weight":SKIN_SSS_WEIGHT,
   "skin_sss_scale":SKIN_SSS_SCALE,
   "skin_roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX],
   "hair_regime":hair_surface_contract["style"],
   "hair_guide_sha256":geom["hair_guide"]["sha256"],
   "selection_basis":"C16_RUNTIME_VISUAL_AUDIT_FAIL_CARD_MASS; MATURE_HAIR_CURVES_ROUTE; PRINCIPLED_HAIR; CYCLES_3D_CURVES",
   "skin_albedo_saturation":SKIN_ALBEDO_SAT,
   "skin_albedo_value":SKIN_ALBEDO_VALUE,
   "eye_texture_saturation":EYE_TEX_SAT,
   "eye_texture_value":EYE_TEX_VALUE,
   "hair_texture_saturation":HAIR_TEX_SAT,
   "hair_texture_value":HAIR_TEX_VALUE,
   "face_meso_scale":FACE_MESO_SCALE,
   "skin_tone_rgb":[SKIN_TONE_R,SKIN_TONE_G,SKIN_TONE_B],
   "skin_tone_mix":SKIN_TONE_MIX,
   "skin_micro_strength":SKIN_MICRO_STRENGTH,
   "hair_card_specular":0.16,
   "hair_card_coat":0.004,
   "hair_card_roughness":0.54,
   "hair_card_anisotropy":0.34,
   "hair_asset_key":HAIR_ASSET_KEY
 },
 "scalp_shadow_polygons":scalp_shadow_polygons,
 "drive_compute_priors":geom["drive_compute_priors"],
 "skin_albedo":skin_asset,
 "skin_model":{"subsurface_method":"RANDOM_WALK_SKIN","subsurface_weight":SKIN_SSS_WEIGHT,"subsurface_scale":SKIN_SSS_SCALE,"subsurface_anisotropy":SKIN_SSS_ANISO,"roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX],"micro_bump_scales":[115,560,1750]},
 "hair_curve_count":len(strands),
 "hair_guide":geom["hair_guide"],
 "hair_curve_metrics":hair_curve_metrics,
 "render_curve_shape":"CYLINDER",
 "provenance":{
   "source_pixels_used":False,
   "reference_pixels_read_by_renderer":False,
   "reference_images_composited":False,
   "reference_textures_used":False,
   "external_skin_texture_used":skin_asset["enabled"],
   "external_skin_texture_sha256":skin_asset["sha256"],
   "external_skin_texture_license":"CC0" if skin_asset["enabled"] else None,
   "external_skin_texture_pack_sha256":"7495ab99287053bd19ff1636114e64b608994d9f7437fea6cc75ea387f96dba9" if skin_asset["enabled"] else None,
   "external_system_asset_used":True,
   "external_system_asset_pack_sha256":system_contract["pack_sha256"],
   "external_system_asset_license":system_contract["license"],
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
